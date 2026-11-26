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
                                      "A manager's span counts reports in any country. 1 manager without a confirmed type. Check:")
    assert re.search(r"Check: only 4 people, so spans and layers are not meaningful; people cost is incomplete \(2 of 4 have no salary\)\.$", spans["detail"])
    # The sample org file's units are all 26+ people with full salaries: no warnings, detail unchanged
    await upload(client)
    await link(client, "Belmar")
    assert "Check:" not in by_ref(await belmar_file(client))["baseline.spans"]["detail"]


# ------------------------------------------------------------- 4. manager types

def _belmar_row(metrics):
    return next(r for r in metrics["country_analysis"] if r["country"] == "Belmar")


@pytest.mark.asyncio
async def test_types_suggested_from_work_type_and_counted(client: AsyncClient):
    await upload(client)
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    shift = next(a for a in m["span_of_control"]["manager_assessments"] if a["manager_id"] == "E050")
    assert (shift["job_title"], shift["manager_type"], shift["manager_type_status"]) == ("Shift Supervisor", "supervisor", "suggested")
    types = _belmar_row(m)["manager_types"]
    assert types["managers_without_confirmed_type"] == 9 and types["managers_suggested_type"] == 4
    assert types["by_type"]["supervisor"]["managers"] == 4
    # A suggested Supervisor is judged on 10-20, as the Work Type rule did: test 1's figures don't move
    assert _belmar_row(m)["spans_vs_benchmark"] == {"below": 8, "within": 1, "above": 0}
    await link(client, "Belmar")
    detail = by_ref(await belmar_file(client))["baseline.spans"]["detail"]
    assert "Median span by type: Supervisor 2.5; 9 managers without a confirmed type." in detail


@pytest.mark.asyncio
async def test_type_set_on_screen_changes_the_judgement_and_scenarios_follow(client: AsyncClient):
    await upload(client)
    # Head of Commercial (3 reports) confirmed as a Specialist lead: 3-6, so within
    r = await client.put("/api/v1/structure/manager-type", json={"employee_id": "E034", "manager_type": "specialist_lead"})
    m = r.json()["metrics"]
    a = next(x for x in m["span_of_control"]["manager_assessments"] if x["manager_id"] == "E034")
    assert (a["manager_type_status"], a["benchmark_range"], a["status"]) == ("confirmed", [3, 6], "within")
    assert _belmar_row(m)["spans_vs_benchmark"]["within"] == 2
    assert (await client.get("/api/v1/metrics/latest")).json()["metrics"]["inputs_signature"] == m["inputs_signature"]
    # A scenario with no moves is judged with the same types: same spans as today
    sc = (await client.post("/api/v1/scenarios", json={"name": "No change"})).json()
    assert sc["scenario"]["spans_within_benchmark"] == sc["baseline"]["spans_within_benchmark"]
    # Confirm every suggestion at once
    done = (await client.post("/api/v1/structure/manager-types/confirm-suggested")).json()
    assert done["confirmed"] >= 4
    assert _belmar_row(done["metrics"])["manager_types"]["managers_without_confirmed_type"] == 4
    # Clearing goes back to the suggestion or nothing; bad input is refused in plain words
    assert (await client.put("/api/v1/structure/manager-type", json={"employee_id": "E034", "manager_type": "boss"})).status_code == 400
    assert (await client.put("/api/v1/structure/manager-type", json={"employee_id": "E999", "manager_type": "coach"})).status_code == 404


@pytest.mark.asyncio
async def test_span_ranges_are_editable_in_settings(client: AsyncClient):
    await upload(client)
    s = (await client.get("/api/v1/structure/settings")).json()
    assert s["type_ranges"]["supervisor"] == [10, 20] and s["type_ranges"]["specialist_lead"] == [3, 6]
    assert "Starting points, not targets" in s["note"]
    bad = await client.put("/api/v1/structure/settings", json={"type_ranges": {"supervisor": [12, 4]}})
    assert bad.status_code == 400 and "Supervisor" in bad.json()["detail"]
    await client.put("/api/v1/structure/settings", json={"type_ranges": {"supervisor": [2, 20]}})
    # The suggested Supervisors (spans 2-4 in Belmar) now fall within: metrics recalculate by themselves
    assert _belmar_row((await client.get("/api/v1/metrics/latest")).json()["metrics"])["spans_vs_benchmark"]["within"] == 5
    assert (await client.post("/api/v1/structure/settings/reset")).json()["type_ranges"]["supervisor"] == [10, 20]
    assert _belmar_row((await client.get("/api/v1/metrics/latest")).json()["metrics"])["spans_vs_benchmark"]["within"] == 1


def test_manager_type_column_any_case_and_unknown_values():
    from app.parsers.csv_parser import OrgCSVParser
    from app.services.metrics_service import MetricsCalculator
    csv = ("Name,Job Title,Grade,Level,Line Manager,Employee ID,manager TYPE\n"
           "Ana,CEO,G1,1,Top of Org,E1,Leader of leaders\n"
           "Bo,Lead,G2,2,Ana,E2,specialist-lead\n"
           "Cy,Boss,G2,2,Ana,E3,Boss\n"
           "Di,Analyst,G5,3,Bo,E4,\n")
    result = OrgCSVParser(io.BytesIO(csv.encode())).parse()
    assert [e["manager_type"] for e in result["employees"]] == ["leader_of_leaders", "specialist_lead", "", ""]
    assert any("Manager type not recognised: Boss" in w for w in result["validation_errors"])
    a = {x["manager_id"]: x for x in MetricsCalculator(employees=result["employees"]).calculate_all_metrics()["span_of_control"]["manager_assessments"]}
    assert (a["E1"]["manager_type_basis"], a["E1"]["benchmark_range"]) == ("Manager type column", [4, 8])


# ------------------------------------------------------------- 5. broken reporting lines

def broken_belmar_ramp() -> str:
    """The PRD's test 10: blank the Line Manager of Belmar's four Ramp Agents."""
    import csv
    rows = list(csv.DictReader(io.StringIO(ORG_TEXT)))
    for r in rows:
        if r["Country"] == "Belmar" and r["Job Title"] == "Ramp Agent":
            r["Line Manager"] = r["Line Manager ID"] = ""
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


SPAN_KEYS = {"median_span", "spans_within", "spans_below", "spans_above"}


@pytest.mark.asyncio
async def test_original_file_has_no_broken_lines(client: AsyncClient):
    await upload(client)
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    for r in m["country_analysis"]:
        assert r["reporting_lines"]["incomplete"] is False and r["reporting_lines"]["supervisors_no_reports"] == 0
    await link(client, "Belmar")
    metrics = by_ref(await belmar_file(client))["baseline.layers"]["metrics"]
    assert metrics["supervisors_no_reports"] == 0 and SPAN_KEYS <= set(metrics)


@pytest.mark.asyncio
async def test_blanked_ramp_agents_hide_belmars_spans(client: AsyncClient):
    await upload(client, broken_belmar_ramp(), "broken.csv")
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    belmar = next(r for r in m["country_analysis"] if r["country"] == "Belmar")["reporting_lines"]
    assert belmar["incomplete"] and belmar["supervisors_no_reports"] == 1 and belmar["people_without_manager"] == 4
    assert belmar["text"] == ("Reporting lines look incomplete in Belmar: 1 supervisory role has nobody reporting to it and "
                              "4 people have no line manager although not the top of the organization. Spans and layers here are not reliable.")
    # The people concerned are named on screen (Shift Supervisor and the four Ramp Agents)…
    assert sorted(p["job_title"] for p in belmar["people"]) == ["Ramp Agent"] * 4 + ["Shift Supervisor"]
    # …but the export carries counts only, and no span keys
    await link(client, "Belmar")
    ret = await belmar_file(client)
    f = by_ref(ret)
    for ref in BASELINE_REFS:
        assert f[ref]["metrics"]["supervisors_no_reports"] >= 1 and not SPAN_KEYS & set(f[ref]["metrics"])
    assert "reporting lines look incomplete (1 supervisory role has nobody reporting; 4 people have no line manager)" in f["baseline.spans"]["detail"]
    assert not PRIVATE.search(json.dumps(ret))
    # Arden and Caldera are untouched
    others = {r["country"]: r["reporting_lines"]["incomplete"] for r in m["country_analysis"]}
    assert others == {"Arden": False, "Belmar": True, "Caldera": False}
    # The whole-organization file doesn't send spans it shouldn't trust either
    whole = by_ref((await client.get("/api/v1/compass/return")).json())["baseline.layers"]["metrics"]
    assert not SPAN_KEYS & set(whole) and whole["supervisors_no_reports"] == 1


@pytest.mark.asyncio
async def test_supervisory_words_and_confirmed_types_count(client: AsyncClient):
    await upload(client)
    # Adding "Manager" flags the two Cargo & Pharma Managers in Belmar, who have nobody reporting to them
    await client.put("/api/v1/structure/settings", json={"supervisory_words": ["Supervisor", "Manager"]})
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    belmar = next(r for r in m["country_analysis"] if r["country"] == "Belmar")["reporting_lines"]
    assert belmar["supervisors_no_reports"] == 2 and belmar["incomplete"] is False  # 2 of 11: not more than a quarter
    await client.post("/api/v1/structure/settings/reset")
    # A confirmed type marks someone as supervising, whatever their title
    await client.put("/api/v1/structure/manager-type", json={"employee_id": "E040", "manager_type": "coach"})  # a Load Control officer
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    assert next(r for r in m["country_analysis"] if r["country"] == "Belmar")["reporting_lines"]["supervisors_no_reports"] == 1


# ------------------------------------------------------------- 6. role families

FAMILIES = [  # the PRD's test 7, in confirmation order
    ("Load control", lambda t: t.startswith("Load Control")),
    ("Ramp handling", lambda t: t in ("Ramp Agent", "Shift Supervisor")),
    ("Pricing and revenue management", lambda t: "Pricing" in t),
    ("Analytics and AI", lambda t: "Analytics" in t),
    ("Disruption control", lambda t: "Duty Controller" in t),
    ("Finance", lambda t: t.startswith("Finance ")),
]


async def confirm_prd_families(client):
    titles = [t["title"] for t in (await client.get("/api/v1/structure/families")).json()["titles"]]
    for name, rule in FAMILIES:
        r = await client.post("/api/v1/structure/families", json={"name": name, "titles": [t for t in titles if rule(t)]})
        assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_role_families_in_belmars_file_match_the_sample(client: AsyncClient):
    await upload(client)
    view = await confirm_prd_families(client)
    assert [f["ref"] for f in view["families"]] == [f"RF-0{i}" for i in range(1, 7)]
    await client.put("/api/v1/structure/families/RF-03/reason", json={
        "unit": "Belmar", "reason_class": "chosen", "compared_with": "Arden",
        "text": "Created in 2023 when Belmar won its two largest renewal contracts."})
    await link(client, "Belmar")
    ours = {f["ref"]: f for f in (await belmar_file(client))["findings"] if f["kind"] == "role_family"}
    sample = {f["ref"]: f for f in SAMPLE["findings"] if f["kind"] == "role_family"}
    assert [ours[r]["metrics"]["headcount"] for r in sorted(ours)] == [2, 5, 1, 0, 0, 2]
    assert ours == sample  # field for field


@pytest.mark.asyncio
async def test_roles_across_units(client: AsyncClient):
    await upload(client)
    view = await confirm_prd_families(client)
    fam = {f["ref"]: f for f in view["families"]}
    assert (fam["RF-03"]["presence"], fam["RF-03"]["only_in"]) == ("only", "Belmar")
    assert fam["RF-04"]["presence"] == "some" and fam["RF-04"]["by_unit"] == {"Arden": 1, "Belmar": 0, "Caldera": 1}
    assert fam["RF-05"]["presence"] == "some"
    assert {fam[r]["presence"] for r in ("RF-01", "RF-02", "RF-06")} == {"every"}
    assert view["unassigned"] == 26 - 8  # every other title still waits for a family
    suggested = {s["name"] for s in (await client.get("/api/v1/structure/families")).json()["suggestions"]}
    assert "Finance" not in suggested and "Cargo" in suggested  # confirmed titles leave the suggestions


@pytest.mark.asyncio
async def test_family_ids_rename_merge_retire_never_reused(client: AsyncClient):
    await upload(client)
    await confirm_prd_families(client)
    # Rename keeps the ID
    v = (await client.put("/api/v1/structure/families/RF-05", json={"name": "Disruption and duty control"})).json()
    assert next(f for f in v["families"] if f["ref"] == "RF-05")["name"] == "Disruption and duty control"
    # A title belongs to one family: moving it takes it from the other
    v = (await client.put("/api/v1/structure/families/RF-01", json={"titles": ["Load Control / Weight & Balance Officer", "Shift Supervisor"]})).json()
    fam = {f["ref"]: f for f in v["families"]}
    assert "Shift Supervisor" not in fam["RF-02"]["titles"] and "Shift Supervisor" in fam["RF-01"]["titles"]
    # Merge keeps the older ID, whichever way round
    await client.put("/api/v1/structure/families/RF-05/reason", json={"unit": "Arden", "reason_class": "required", "text": "Hub licence."})
    v = (await client.post("/api/v1/structure/families/RF-05/merge", json={"with_ref": "RF-04"})).json()
    assert v["kept"] == "RF-04" and {"ref": "RF-05", "name": "Disruption and duty control", "merged_into": "RF-04"} in v["retired"]
    kept = next(f for f in v["families"] if f["ref"] == "RF-04")
    assert kept["reasons"]["Arden"]["text"] == "Hub licence." and kept["by_unit"]["Caldera"] == 3
    # Retired numbers are never reused
    v = (await client.post("/api/v1/structure/families/RF-06/retire")).json()
    v = (await client.post("/api/v1/structure/families", json={"name": "Technology", "titles": ["Head of Technology"]})).json()
    assert [f["ref"] for f in v["families"]][-1] == "RF-07"
    # Plain refusals
    assert (await client.post("/api/v1/structure/families", json={"name": "Load control", "titles": ["Ramp Agent"]})).status_code == 400
    assert (await client.post("/api/v1/structure/families", json={"name": "Wizards", "titles": ["Chief Wizard"]})).status_code == 400
    assert (await client.put("/api/v1/structure/families/RF-05", json={"name": "x"})).status_code == 404
    assert (await client.put("/api/v1/structure/families/RF-01/reason", json={"unit": "Narnia", "reason_class": "chosen"})).status_code == 400
    # Linking to Compass clusters: only clusters from linked packets
    assert (await client.put("/api/v1/structure/families/RF-01", json={"relates_to": ["CAP-01"]})).status_code == 400
    await link(client, "Belmar")
    v = (await client.put("/api/v1/structure/families/RF-01", json={"relates_to": ["CAP-01"]})).json()
    assert next(f for f in v["families"] if f["ref"] == "RF-01")["relates_to"] == ["CAP-01"]
    assert by_ref(await belmar_file(client))["RF-01"]["relates_to"] == ["CAP-01"]


@pytest.mark.asyncio
async def test_new_project_clears_types_and_families(client: AsyncClient):
    await upload(client)
    await confirm_prd_families(client)
    await client.put("/api/v1/structure/manager-type", json={"employee_id": "E034", "manager_type": "coach"})
    await client.delete("/api/v1/org-data/clear-all")
    await upload(client)
    assert (await client.get("/api/v1/structure/families")).json()["families"] == []
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    assert next(a for a in m["span_of_control"]["manager_assessments"] if a["manager_id"] == "E034")["manager_type"] == ""


def test_suggestions_group_by_the_work_not_the_grade():
    """Real HRIS titles: abbreviations and grade words are set aside, so titles group by the work they name."""
    from app.services.role_families import suggest
    titles = ["Assistant Manager, Airline Relations", "Executive, Airline Relations", "Senior Executive, Airline Relations",
              "Asst Mgr, Hub Operations Planning", "AVP Building & Engineering Services", "AVP, Import Operations & DG",
              "AVP, ULD", "AVP, eCommerce Solutions", "AVP, Airline Relations, CNS & T5 Operations",
              "Executive - Building & Sustainability", "Manager, Building Services & Sustainability",
              "Officer, Building Services", "Supervisor, Building Services", "Officer II, Cargo Acceptance"]
    groups = {g["name"]: g["titles"] for g in suggest(titles)}
    assert "AVP" not in groups and "Asst mgr" not in groups  # grade words no longer make a family
    assert sorted(groups["Airline relations"]) == sorted(["Assistant Manager, Airline Relations", "Executive, Airline Relations",
                                                         "Senior Executive, Airline Relations", "AVP, Airline Relations, CNS & T5 Operations"])
    assert "Hub operations planning" in groups
    assert len(next(t for n, t in groups.items() if n.startswith("Building"))) == 5
    assert "Cargo acceptance" in groups and "ULD" in groups


@pytest.mark.asyncio
async def test_moving_titles_in_bulk(client: AsyncClient):
    await upload(client)
    await confirm_prd_families(client)
    move = lambda body: client.post("/api/v1/structure/families/move", json=body)  # noqa: E731
    # Several titles into an existing family in one step; they leave wherever they were
    v = (await move({"titles": ["Shift Supervisor", "Head of Catering"], "to": "RF-01"})).json()
    fam = {f["ref"]: f for f in v["families"]}
    assert v["moved_to"] == "RF-01" and {"Shift Supervisor", "Head of Catering"} <= set(fam["RF-01"]["titles"])
    assert "Shift Supervisor" not in fam["RF-02"]["titles"]
    # Into a new family: it gets the next RF number
    v = (await move({"titles": ["Head of Catering", "Executive Chef — Culinary Design"], "to": "new", "name": "Catering"})).json()
    assert v["moved_to"] == "RF-07" and "Head of Catering" not in {f["ref"]: f for f in v["families"]}["RF-01"]["titles"]
    # Out of every family
    v = (await move({"titles": ["Shift Supervisor"], "to": None})).json()
    assert not any("Shift Supervisor" in f["titles"] for f in v["families"])
    assert next(t for t in v["titles"] if t["title"] == "Shift Supervisor")["family"] is None
    # A family emptied by moves is flagged and left out of the unit files
    v = (await move({"titles": ["Load Control / Weight & Balance Officer"], "to": None})).json()
    assert {f["ref"]: f for f in v["families"]}["RF-01"]["empty"] is True
    await link(client, "Belmar")
    assert "RF-01" not in by_ref(await belmar_file(client))
    # Plain refusals; nothing changes
    assert (await move({"titles": ["Chief Wizard"], "to": "RF-02"})).status_code == 400
    assert (await move({"titles": [], "to": "RF-02"})).status_code == 400
    assert (await move({"titles": ["Ramp Agent"], "to": "RF-99"})).status_code == 404
    assert (await move({"titles": ["Ramp Agent"], "to": "new", "name": ""})).status_code == 400
    assert "Ramp Agent" in {f["ref"]: f for f in (await client.get("/api/v1/structure/families")).json()["families"]}["RF-02"]["titles"]
