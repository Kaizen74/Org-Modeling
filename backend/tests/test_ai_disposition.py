"""Tests for the optional AI-role overlay (automate / augment / keep human)."""

import json
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai_disposition_service import capacity_freed, role_inventory, summarize, validate_tag


EMPS = [
    {"name": "Zed Quill", "job_title": "Analyst", "department": "CX", "salary": 100, "work_activities": "reporting"},
    {"name": "Yara Quill", "job_title": "Analyst", "department": "CX", "salary": 100, "work_activities": "reporting"},
    {"name": "Xavi Quill", "job_title": "Ramp Agent", "department": "Ops", "salary": 50},
]


def test_inventory_groups_by_title_without_names():
    inv = role_inventory(EMPS)
    assert [(r["job_title"], r["headcount"]) for r in inv] == [("Analyst", 2), ("Ramp Agent", 1)]
    assert "Quill" not in json.dumps(inv)


def test_capacity_and_summary():
    roles = {"Analyst": {"disposition": "augment", "capacity_freed_pct": 25}, "Ramp Agent": {"disposition": "keep_human", "capacity_freed_pct": 0}}
    assert capacity_freed(EMPS, roles) == (0.5, 50.0)
    s = summarize(EMPS, roles)
    assert s["by_disposition"]["augment"] == {"roles": 1, "people": 2}
    assert s["tagged_roles"] == 2 and s["tagged_people_pct"] == 100.0


def test_validation():
    assert validate_tag("augment", 30) is None
    assert "must be one of" in validate_tag("replace", 10)
    assert "between 0 and 100" in validate_tag("automate", 140)


async def _upload(client, path):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", path.read_bytes(), "text/csv")})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_workflow_unchanged_when_overlay_unused(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    data = (await client.get("/api/v1/ai-disposition")).json()
    assert data["enabled"] is False and data["summary"]["capacity_fte"] == 0
    scen = (await client.post("/api/v1/scenarios", json={"name": "S"})).json()
    assert scen["baseline"]["ai_capacity_fte"] == 0 and scen["delta"]["ai_capacity_fte"] == 0
    comp = (await client.get("/api/v1/comparison")).json()
    assert comp["result"]["totals"]["current"] is not None  # comparison works without the overlay


@pytest.mark.asyncio
async def test_tagging_flows_into_scenarios_and_can_be_switched_off(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    tagged = (await client.put("/api/v1/ai-disposition/role", json={
        "job_title": "SQ Analytics Associate", "disposition": "augment", "capacity_freed_pct": 50})).json()
    row = next(r for r in tagged["roles"] if r["job_title"] == "SQ Analytics Associate")
    assert row["tag"]["source"] == "user"
    fte = tagged["summary"]["capacity_fte"]
    assert fte == row["headcount"] * 0.5

    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    victim = next(e for e in org if e["job_title"] == "SQ Analytics Associate")
    scen = (await client.post("/api/v1/scenarios", json={"name": "S", "moves": [{"type": "remove_role", "person_id": victim["employee_id"]}]})).json()
    assert scen["baseline"]["ai_capacity_fte"] == fte
    assert scen["delta"]["ai_capacity_fte"] == -0.5
    assert scen["delta"]["headcount"] == -1  # headcount changes only through moves

    off = (await client.put("/api/v1/ai-disposition/enabled", json={"enabled": False})).json()
    assert off["enabled"] is False
    assert (await client.get(f"/api/v1/scenarios/{scen['id']}")).json()["baseline"]["ai_capacity_fte"] == 0

    assert (await client.put("/api/v1/ai-disposition/role", json={"job_title": "X", "disposition": "replace"})).status_code == 400


@pytest.mark.asyncio
async def test_ai_suggestions_respect_user_tags(client: AsyncClient, sample_csv_path, monkeypatch):
    from app.api import ai_disposition as api
    await _upload(client, sample_csv_path)
    await client.put("/api/v1/ai-disposition/role", json={"job_title": "Ramp Ops Associate", "disposition": "keep_human", "capacity_freed_pct": 5})
    captured = {}

    def fake_run(_client, prompt, max_tokens=None):
        captured["prompt"] = prompt
        return json.dumps({"roles": [
            {"job_title": "Ramp Ops Associate", "disposition": "automate", "capacity_freed_pct": 80},  # user-tagged: ignored
            {"job_title": "SQ QA Associate", "disposition": "augment", "capacity_freed_pct": 30, "rationale": "Checklist review", "confidence": "Medium"},
            {"job_title": "Imaginary Role", "disposition": "augment", "capacity_freed_pct": 30},
        ]}), {}

    monkeypatch.setattr(api, "run_analysis", fake_run)
    monkeypatch.setattr(api.claude_service, "is_configured", lambda: True)
    monkeypatch.setattr(api.claude_service, "api_key", "k", raising=False)
    data = (await client.post("/api/v1/ai-disposition/suggest", json={})).json()
    assert data["suggestions_added"] == 1
    tags = {r["job_title"]: r["tag"] for r in data["roles"] if r["tag"]}
    assert tags["Ramp Ops Associate"]["disposition"] == "keep_human"
    assert tags["SQ QA Associate"]["source"] == "ai"
    assert "Vincent Chan" not in captured["prompt"]
