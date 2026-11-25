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


# ------------------------------------------------------------- 2. unit column

@pytest.mark.asyncio
async def test_station_header_reads_as_the_unit(client: AsyncClient):
    countries = (await upload(client))
    by_country = {r["country"]: r for r in (await client.get("/api/v1/metrics/latest")).json()["metrics"]["country_analysis"]}
    assert countries["metadata"]["unit_label"] == "Country"

    station = ORG_TEXT.replace("Line Manager ID,Department,Country,", "Line Manager ID,Department,Station,", 1)
    assert station != ORG_TEXT
    up = await upload(client, station, "stations.csv")
    assert up["metadata"]["unit_label"] == "Station" and up["metadata"]["countries"] == ["Arden", "Belmar", "Caldera"]
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    assert m["unit_label"] == "Station"
    by_station = {r["country"]: r for r in m["country_analysis"]}
    strip = lambda r: {k: v for k, v in r.items() if k != "health_components"}  # noqa: E731
    assert {k: strip(v) for k, v in by_station.items()} == {k: strip(v) for k, v in by_country.items()}
    await link(client, "Belmar")  # matching a packet to a unit stays by name
    ret = await belmar_file(client)
    assert ret["country"] == "Belmar" and by_ref(ret)["baseline.layers"]["metrics"]["layers"] == 5


def test_unit_headers_any_case_first_in_order():
    from app.parsers.csv_parser import OrgCSVParser
    csv = ("Name,Job Title,Grade,Level,Line Manager,Employee ID,business UNIT,STATION\n"
           "Ana Lee,CEO,SVP,1,Top of Org,E1,Group,Hub A\n"
           "Bo Lim,Lead,TL,2,Ana Lee,E2,Ops,Hub B\n")
    result = OrgCSVParser(io.BytesIO(csv.encode())).parse()
    assert result["metadata"]["unit_label"] == "Station"  # Station comes before Business unit in the order
    assert [e["country"] for e in result["employees"]] == ["Hub A", "Hub B"]
    assert any("Several unit columns found" in w and "'STATION' is used" in w for w in result["validation_errors"])
    plain = OrgCSVParser(io.BytesIO("Name,Job Title,Grade,Level,Line Manager\nAna,CEO,SVP,1,Top of Org\n".encode())).parse()
    assert plain["metadata"]["unit_label"] == "" and plain["employees"][0]["country"] == ""


# ------------------------------------------------------------- 3. unit warnings

WARN_CSV = ("Employee ID,Name,Job Title,Grade,Level,Line Manager,Country,Salary\n"
            "E1,Ana Lee,CEO,G1,1,,Arden,300000\n"
            "E2,Bo Lim,Manager,G2,2,Ana Lee,Arden,150000\n"
            + "".join(f"E{10+i},P{i},Agent,G5,3,Bo Lim,Arden,50000\n" for i in range(9))
            + "E3,Cy Ong,Lead,G3,2,Ana Lee,Dorne,\n"  # Dorne: 4 people, 2 with no salary and no grade table
            + "E4,Di Koh,Agent,G9,3,Cy Ong,Dorne,\n"
            + "E5,Ed Tan,Agent,G5,3,Cy Ong,Dorne,50000\n"
            + "E6,Fa Lin,Agent,G5,3,Cy Ong,Dorne,50000\n")


def test_unit_warnings_in_words():
    from app.parsers.csv_parser import OrgCSVParser
    from app.services.metrics_service import MetricsCalculator
    employees = OrgCSVParser(io.BytesIO(WARN_CSV.encode())).parse()["employees"]
    rows = {r["country"]: r for r in MetricsCalculator(employees=employees).calculate_all_metrics()["country_analysis"]}
    dorne = {w["key"]: w for w in rows["Dorne"]["warnings"]}
    assert dorne["small_unit"]["text"] == "Only 4 people: spans and layers are not meaningful at this size."
    assert dorne["cost_incomplete"]["text"] == "2 of 4 people have no salary and no grade-table match: people cost is incomplete."
    # Arden's CEO mostly manages Dorne's lead? No: she manages Arden's manager and Dorne's lead (1 of 2 elsewhere, not most)
    assert "managers_elsewhere" not in {w["key"] for w in rows["Arden"]["warnings"]}


def test_managers_mostly_managing_other_units_are_flagged():
    from app.parsers.csv_parser import OrgCSVParser
    from app.services.metrics_service import MetricsCalculator
    csv = ("Employee ID,Name,Job Title,Grade,Level,Line Manager,Country,Salary\n"
           "E1,Ana,CEO,G1,1,,Hub,1\n" + "".join(f"E{10+i},P{i},Agent,G5,2,Ana,Field,1\n" for i in range(12)))
    rows = {r["country"]: r for r in MetricsCalculator(employees=OrgCSVParser(io.BytesIO(csv.encode())).parse()["employees"]).calculate_all_metrics()["country_analysis"]}
    w = {x["key"]: x for x in rows["Hub"]["warnings"]}
    assert w["managers_elsewhere"]["text"].startswith("1 of 1 managers here mostly manage people in other units")


@pytest.mark.asyncio
async def test_warnings_go_into_the_spans_detail_as_one_sentence(client: AsyncClient):
    await upload(client, WARN_CSV)
    dorne = copy.deepcopy(PACKETS["Belmar"])
    dorne["engagement"].update(country="Dorne", key="MERIDIANDO")
    await client.post("/api/v1/compass/import", json={"packet": dorne})
    spans = by_ref((await client.get("/api/v1/compass/return", params={"link": "Dorne"})).json())["baseline.spans"]
    assert spans["detail"].startswith("1 below, 0 above; 0 managers have one direct report. Median span 3. "
                                      "A manager's span counts reports in any country. Check:")  # existing wording kept, sentence added
    assert re.search(r"Check: only 4 people, so spans and layers are not meaningful; people cost is incomplete \(2 of 4 have no salary\)\.$", spans["detail"])
    # The sample org file's units are all 26+ people with full salaries: no warnings, detail unchanged
    await upload(client)
    await link(client, "Belmar")
    assert "Check:" not in by_ref(await belmar_file(client))["baseline.spans"]["detail"]
