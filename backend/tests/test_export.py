"""Tests for the board-ready findings pack."""

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, sample_csv_path):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", sample_csv_path.read_bytes(), "text/csv")})
    assert r.status_code == 200
    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    rachel = next(e for e in org if e["name"] == "Rachel Goh")
    sid = (await client.post("/api/v1/scenarios", json={"name": "Delayer", "moves": [
        {"type": "remove_role", "person_id": rachel["employee_id"], "note": "Rachel Goh manages one person"}]})).json()["id"]
    return sid


@pytest.mark.asyncio
async def test_pack_has_every_section_and_no_names_by_default(client: AsyncClient, sample_csv_path):
    sid = await _setup(client, sample_csv_path)
    r = await client.get("/api/v1/export/pack")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    for heading in ["Evidence inventory", "Facts from the data", "Structural options compared", "What it takes: Delayer", "Transition sequence"]:
        assert heading in html, heading
    assert "Rachel Goh" not in html and "Vincent Chan" not in html  # names scrubbed, including move notes
    assert "Manager, Planning" in html

    named = (await client.get(f"/api/v1/export/pack?scenario_id={sid}&include_names=true")).text
    assert "Rachel Goh" in named


@pytest.mark.asyncio
async def test_pack_without_scenarios_or_ai_still_renders(client: AsyncClient, sample_csv_path):
    await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", sample_csv_path.read_bytes(), "text/csv")})
    html = (await client.get("/api/v1/export/pack")).text
    assert "Facts from the data" in html and "Transition sequence" not in html
    assert (await client.get("/api/v1/export/pack?scenario_id=nope")).status_code == 404
