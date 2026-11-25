"""
Numbers for the Compass: metrics on structural_baseline findings, people cost,
unit columns, unit warnings, manager types, broken reporting lines and role families.
Acceptance tests from the owner's PRD run on the sample files in fixtures/countries.
"""

import copy
import io
import json
import re
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

COUNTRIES = Path(__file__).parent / "fixtures" / "countries"
ORG_TEXT = (COUNTRIES / "meridian_org_by_country.csv").read_text()
PACKETS = {c: json.loads((COUNTRIES / f"{c.lower()}_compass_handoff.json").read_text()) for c in ("Arden", "Belmar", "Caldera")}
SAMPLE = json.loads((COUNTRIES / "belmar_return_org_modeling.json").read_text())
BASELINE_REFS = ("baseline.layers", "baseline.spans", "baseline.health")
PRIVATE = re.compile(r"\b[A-Z]{2} Person \d{3}\b|\bE\d{3}\b")


async def upload(client, text: str = ORG_TEXT, name: str = "org.csv"):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": (name, text.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()


async def link(client, *countries):
    for c in countries:
        r = await client.post("/api/v1/compass/import", json={"packet": PACKETS[c]})
        assert r.status_code == 200, r.text


async def belmar_file(client):
    r = await client.get("/api/v1/compass/return", params={"link": "Belmar"})
    assert r.status_code == 200, r.text
    return r.json()


def by_ref(ret):
    return {f["ref"]: f for f in ret["findings"]}


# ------------------------------------------------------------- 1. metrics on the exports

@pytest.mark.asyncio
async def test_belmar_baseline_carries_the_metrics_numbers(client: AsyncClient):
    await upload(client)
    await link(client, "Belmar")
    ret = await belmar_file(client)
    f = by_ref(ret)
    m = f["baseline.layers"]["metrics"]
    expected = {"headcount": 26, "managers": 9, "manager_ratio_pct": 34.6, "layers": 5, "median_span": 2,
                "spans_within": 1, "spans_below": 8, "spans_above": 0, "single_report_managers": 2, "total_cost": 2263000}
    assert {k: m[k] for k in expected} == expected
    assert isinstance(m["health_score"], int) and 0 <= m["health_score"] <= 100
    assert all(isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0 for v in m.values())  # numbers only
    assert isinstance(m["total_cost"], int) and isinstance(m["median_span"], int)  # 2263000, not 2263000.0
    # The same metrics on all three baseline findings (test 2)
    assert f["baseline.spans"]["metrics"] == m == f["baseline.health"]["metrics"]
    # Existing wording kept; the cost note is added to source_note
    assert f["baseline.layers"]["figure"] == "5 layers" and f["baseline.spans"]["figure"] == "1 of 9 managers"
    assert f["baseline.layers"]["source_note"] == \
        "Computed from the uploaded org file (26 people in Belmar). People cost is the Salary column for 26 people."


@pytest.mark.asyncio
async def test_belmar_file_has_the_samples_header_and_metrics_keys(client: AsyncClient):
    await upload(client)
    await link(client, "Belmar")
    ret = await belmar_file(client)
    assert set(ret) == set(SAMPLE)
    sample = {f["ref"]: f for f in SAMPLE["findings"]}
    ours = by_ref(ret)
    for ref in ("baseline.layers", "baseline.spans"):
        sample_keys, our_keys = set(sample[ref]["metrics"]), set(ours[ref]["metrics"])
        assert sample_keys <= our_keys and our_keys - sample_keys <= {"health_score", "supervisors_no_reports"}
        assert {k: ours[ref]["metrics"][k] for k in sample_keys} == sample[ref]["metrics"]
    assert all("metrics" in ours[r] for r in BASELINE_REFS)
    # Readable text: one figures line for the unit
    text = (await client.get("/api/v1/compass/return.txt", params={"link": "Belmar"})).text
    assert "Head-count 26 · managers 9 (34.6%) · layers 5 · median span 2 · 1 of 9 managers within benchmark · " \
           "people cost 2,263,000 (base salary)" in text
    assert not PRIVATE.search(json.dumps(ret) + text)  # test 6


@pytest.mark.asyncio
async def test_whole_organization_file_carries_metrics_too(client: AsyncClient):
    await upload(client)
    whole = by_ref((await client.get("/api/v1/compass/return")).json())
    m = whole["baseline.layers"]["metrics"]
    assert m["headcount"] == 84 and m["layers"] == 6 and m["total_cost"] == 9270000
    assert whole["baseline.spans"]["metrics"] == m == whole["baseline.health"]["metrics"]
    assert whole["baseline.layers"]["source_note"].endswith("People cost is the Salary column for 84 people.")


@pytest.mark.asyncio
async def test_values_that_cannot_be_worked_out_are_left_out(client: AsyncClient):
    """A unit with no managers has no span to judge: median_span and spans_* are left out, not sent as 0."""
    text = ("Employee ID,Name,Job Title,Grade,Level,Line Manager,Country,Salary\n"
            "E1,Ana Lee,CEO,G1,1,,Arden,300000\n"
            "E2,Bo Lim,Analyst,G5,2,Ana Lee,Dorne,\n"
            "E3,Cy Ong,Analyst,G5,2,Ana Lee,Dorne,\n")
    await upload(client, text)
    dorne = copy.deepcopy(PACKETS["Belmar"])
    dorne["engagement"].update(country="Dorne", key="MERIDIANDO")
    assert (await client.post("/api/v1/compass/import", json={"packet": dorne})).status_code == 200
    ret = (await client.get("/api/v1/compass/return", params={"link": "Dorne"})).json()
    m = by_ref(ret)["baseline.spans"]["metrics"]
    assert m["headcount"] == 2 and m["managers"] == 0
    assert not {"median_span", "spans_within", "spans_below", "spans_above"} & set(m)
    # Nobody has a salary from the file and there is no grade table: cost is left out too
    assert "total_cost" not in m
    assert "No salary is known" in by_ref(ret)["baseline.spans"]["source_note"]
