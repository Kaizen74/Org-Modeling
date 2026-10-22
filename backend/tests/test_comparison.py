"""Tests for option comparison: measured/judged scoring, validation, API, AI suggestions (faked)."""

import json
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comparison_service import score_options, validate_criteria, DEFAULT_CRITERIA


OPTIONS = [
    {"id": "current", "figures": {"total_cost": 100, "layers": 6, "people_affected_pct": 0}},
    {"id": "a", "figures": {"total_cost": 80, "layers": 5, "people_affected_pct": 10}},
    {"id": "b", "figures": {"total_cost": 90, "layers": 4, "people_affected_pct": 30}},
]
CRITERIA = [
    {"id": "cost", "name": "Cost", "kind": "measured", "metric": "total_cost", "better": "lower", "weight": 50},
    {"id": "fit", "name": "Fit", "kind": "judged", "weight": 50},
]


def test_measured_scores_place_options_between_worst_and_best():
    r = score_options(OPTIONS, CRITERIA[:1], {})
    assert r["cells"]["a"]["cost"] == 100.0   # cheapest
    assert r["cells"]["current"]["cost"] == 0.0  # most expensive
    assert r["cells"]["b"]["cost"] == 50.0
    assert r["ranking"] == ["a", "b", "current"]


def test_judged_scores_and_weighted_totals():
    judgments = {"current": {"fit": {"score": 3}}, "a": {"fit": {"score": 2}}, "b": {"fit": {"score": 5}}}
    r = score_options(OPTIONS, CRITERIA, judgments)
    # b: cost 50, fit 100 -> 75 ; a: cost 100, fit 25 -> 62.5 ; current: 0 and 50 -> 25
    assert r["totals"] == {"current": 25.0, "a": 62.5, "b": 75.0}
    assert r["ranking"] == ["b", "a", "current"]
    assert r["complete"] is True


def test_missing_judgments_are_flagged_and_excluded():
    r = score_options(OPTIONS, CRITERIA, {"a": {"fit": {"score": 4}}})
    assert r["missing"]["current"] == ["fit"] and r["missing"]["a"] == []
    assert r["totals"]["current"] == 0.0  # only the measured criterion counts
    assert r["complete"] is False


def test_equal_values_do_not_penalise_anyone():
    opts = [{"id": "x", "figures": {"layers": 5}}, {"id": "y", "figures": {"layers": 5}}]
    r = score_options(opts, [{"id": "l", "kind": "measured", "metric": "layers", "weight": 1}], {})
    assert r["cells"]["x"]["l"] == r["cells"]["y"]["l"] == 100.0


def test_validation_catches_bad_criteria():
    assert validate_criteria(DEFAULT_CRITERIA) == []
    problems = validate_criteria([
        {"id": "a", "name": "A", "kind": "measured", "metric": "vibes", "weight": 1},
        {"id": "a", "name": "B", "kind": "guess", "weight": -1},
    ])
    text = " | ".join(problems)
    assert "unknown measure" in text and "share the id" in text and "kind must be" in text and "negative" in text
    assert "weight above zero" in " ".join(validate_criteria([{"id": "z", "name": "Z", "kind": "judged", "weight": 0}]))


# ---------- API ----------

async def _upload(client: AsyncClient, path):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", path.read_bytes(), "text/csv")})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_comparison_api(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    rachel = next(e for e in org if e["name"] == "Rachel Goh")
    scen = (await client.post("/api/v1/scenarios", json={
        "name": "Delayer", "moves": [{"type": "remove_role", "person_id": rachel["employee_id"]}]})).json()

    data = (await client.get("/api/v1/comparison")).json()
    assert [o["id"] for o in data["options"]] == ["current", scen["id"]]
    assert {c["id"] for c in data["criteria"]} == {c["id"] for c in DEFAULT_CRITERIA}
    assert data["result"]["cells"][scen["id"]]["cost"] == 100.0  # the cheaper option
    assert data["result"]["complete"] is False  # judged criteria not scored yet

    after = (await client.put("/api/v1/comparison/judgments", json={
        "option_id": scen["id"], "criterion_id": "strategy_fit", "score": 4, "rationale": "Faster decisions"})).json()
    assert after["judgments"][scen["id"]]["strategy_fit"]["source"] == "user"
    assert after["result"]["cells"][scen["id"]]["strategy_fit"] == 75.0

    assert (await client.put("/api/v1/comparison/judgments", json={
        "option_id": "current", "criterion_id": "strategy_fit", "score": 9})).status_code == 400
    bad = await client.put("/api/v1/comparison/criteria", json={"criteria": [{"id": "x", "name": "X", "kind": "measured", "metric": "nope", "weight": 1}]})
    assert bad.status_code == 400 and "unknown measure" in bad.json()["detail"]

    custom = [{"id": "cost", "name": "Cost", "kind": "measured", "metric": "total_cost", "better": "lower", "weight": 1}]
    only_cost = (await client.put("/api/v1/comparison/criteria", json={"criteria": custom})).json()
    assert only_cost["result"]["ranking"][0] == scen["id"]
    reset = (await client.post("/api/v1/comparison/criteria/reset")).json()
    assert len(reset["criteria"]) == len(DEFAULT_CRITERIA)


@pytest.mark.asyncio
async def test_ai_suggestions_never_overwrite_designer_scores(client: AsyncClient, sample_csv_path, monkeypatch):
    from app.api import comparison as comparison_api

    await _upload(client, sample_csv_path)
    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    rachel = next(e for e in org if e["name"] == "Rachel Goh")
    scen = (await client.post("/api/v1/scenarios", json={
        "name": "Option A", "moves": [{"type": "remove_role", "person_id": rachel["employee_id"]}]})).json()
    await client.put("/api/v1/comparison/judgments", json={"option_id": "current", "criterion_id": "strategy_fit", "score": 2})

    captured = {}

    def fake_run(_client, prompt, max_tokens=None):
        captured["prompt"] = prompt
        return json.dumps({"suggestions": [
            {"option_id": "current", "criterion_id": "strategy_fit", "score": 5, "rationale": "x"},   # user-scored: ignored
            {"option_id": scen["id"], "criterion_id": "strategy_fit", "score": 4, "rationale": "Cites moves", "evidence_class": "OBSERVABLE", "confidence": "Medium"},
            {"option_id": "ghost", "criterion_id": "strategy_fit", "score": 3},                       # unknown option: ignored
            {"option_id": scen["id"], "criterion_id": "cost", "score": 3},                            # measured criterion: ignored
        ]}), {}

    monkeypatch.setattr(comparison_api, "run_analysis", fake_run)
    monkeypatch.setattr(comparison_api.claude_service, "is_configured", lambda: True)
    monkeypatch.setattr(comparison_api.claude_service, "api_key", "test-key", raising=False)

    data = (await client.post("/api/v1/comparison/suggest")).json()
    assert data["suggestions_added"] == 1
    assert data["judgments"]["current"]["strategy_fit"] == {"score": 2, "rationale": "", "source": "user"}
    assert data["judgments"][scen["id"]]["strategy_fit"]["source"] == "ai"
    # Move descriptions name people on screen, but the AI sees job titles only
    assert "Rachel Goh" not in captured["prompt"] and "Vincent Chan" not in captured["prompt"]
    assert "Removed the Manager, Planning" in captured["prompt"]
