"""Tests for the Country column and the by-country structural view."""

import io
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers.csv_parser import OrgCSVParser
from app.services.metrics_service import MetricsCalculator

COUNTRIES = Path(__file__).parent / "fixtures" / "countries"
ORG = COUNTRIES / "meridian_org_by_country.csv"


def _metrics(employees):
    return MetricsCalculator(employees=employees).calculate_all_metrics()


def _parse_text(csv: str):
    return OrgCSVParser(io.BytesIO(csv.encode("utf-8"))).parse()


def test_sample_org_has_three_countries_and_their_layers():
    result = OrgCSVParser(ORG).parse()
    assert result["metadata"]["total_employees"] == 84
    assert result["metadata"]["countries"] == ["Arden", "Belmar", "Caldera"]
    assert not any("Level doesn't match" in w for w in result["validation_errors"])
    rows = {r["country"]: r for r in _metrics(result["employees"])["country_analysis"]}
    assert {c: r["headcount"] for c, r in rows.items()} == {"Arden": 30, "Belmar": 26, "Caldera": 28}
    # Layers are counted from the top of the whole organization
    assert {c: r["layers"] for c, r in rows.items()} == {"Arden": 5, "Belmar": 5, "Caldera": 6}
    assert "⚑ one layer more than Arden" in rows["Caldera"]["differences"]
    assert rows["Arden"]["differences"] == []


def test_spans_cross_countries_and_cost_adds_up():
    employees = OrgCSVParser(ORG).parse()["employees"]
    m = _metrics(employees)
    by_id = {a["manager_id"]: a for a in m["span_of_control"]["manager_assessments"]}
    # The group chief executive (Arden) manages Belmar's and Caldera's managing directors too
    ceo = by_id["E001"]
    assert ceo["country"] == "Arden"
    reports = [e for e in employees if e.get("manager_id") == "E001" or e["manager_name"] == "AR Person 001"]
    assert ceo["span"] == len(reports) and {e["country"] for e in reports} >= {"Arden", "Belmar", "Caldera"}
    rows = m["country_analysis"]
    assert sum(r["total_cost"] for r in rows) == m["cost_analysis"]["total_cost"]
    assert sum(r["managers"] for r in rows) == m["manager_stats"]["total_managers"]
    for r in rows:
        h = r["health_components"]
        assert r["health_score"] == round(sum(c["score"] * c["weight"] for c in h) / 100)
    assert set(m["department_analysis_by_country"]) == {"Arden", "Belmar", "Caldera"}
    assert sum(d["headcount"] for d in m["department_analysis_by_country"]["Belmar"]) == 26


def test_country_region_header_and_blank_country():
    csv = ("Name,Job Title,Grade,Level,Line Manager,Employee ID,Country/Region\n"
           "Ana Lee,CEO,SVP,1,Top of Org,E1, Arden \n"
           "Bo Lim,Manager,H6,2,Ana Lee,E2,\n"
           "Cy Ong,Analyst,AO,3,Bo Lim,E3,Belmar\n")
    result = _parse_text(csv)
    assert [e["country"] for e in result["employees"]] == ["Arden", "Not stated", "Belmar"]
    rows = _metrics(result["employees"])["country_analysis"]
    assert [r["country"] for r in rows][-1] == "Not stated"  # its own group, never dropped
    assert sum(r["headcount"] for r in rows) == 3


def test_file_without_country_column_behaves_as_before(sample_csv_path):
    result = OrgCSVParser(sample_csv_path).parse()
    assert result["metadata"]["countries"] == []
    m = _metrics(result["employees"])
    assert m["country_analysis"] == [] and m["department_analysis_by_country"] == {}
    assert m["layer_analysis"]["total_layers"] == 6


@pytest.mark.asyncio
async def test_metrics_api_returns_countries(client: AsyncClient):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("org.csv", ORG.read_bytes(), "text/csv")})
    assert r.status_code == 200 and r.json()["employee_count"] == 84
    m = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    assert [c["country"] for c in m["country_analysis"]] == ["Arden", "Caldera", "Belmar"]
    org = (await client.get("/api/v1/org-data/latest")).json()
    assert org["hierarchy"]["data"]["country"] == "Arden"


# ------------------------------------------------------------- one Compass link per country

import copy
import json

PACKETS = {c: json.loads((COUNTRIES / f"{c.lower()}_compass_handoff.json").read_text()) for c in ("Arden", "Belmar", "Caldera")}


async def _upload_countries(client):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("org.csv", ORG.read_bytes(), "text/csv")})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_three_packets_link_to_their_countries(client: AsyncClient):
    await _upload_countries(client)
    pre = (await client.post("/api/v1/compass/preview", json={"packet": PACKETS["Arden"]})).json()
    assert pre["country"]["target"] == "Arden" and not pre["replaces"]
    assert pre["criteria"]["action"] == "set" and pre["strategy"]["action"] == "set"
    await client.post("/api/v1/compass/import", json={"packet": PACKETS["Arden"]})

    # Later packets: criteria and strategy come from the first; the preview says same or different
    pre = (await client.post("/api/v1/compass/preview", json={"packet": PACKETS["Belmar"]})).json()
    assert pre["country"]["target"] == "Belmar"
    assert pre["criteria"]["action"] == "same" and pre["strategy"]["action"] == "different"
    assert any("not ready" in w for w in pre["warnings"])  # Belmar's readiness is false: a warning, not a block
    await client.post("/api/v1/compass/import", json={"packet": PACKETS["Belmar"]})
    state = (await client.post("/api/v1/compass/import", json={"packet": PACKETS["Caldera"]})).json()

    assert [(l["country"], l["key"]) for l in state["links"]] == [("Arden", "MERIDIAN"), ("Belmar", "MERIDIANBE"), ("Caldera", "MERIDIANCA")]
    assert state["engagement"]["key"] == "MERIDIAN"  # the frame's key
    assert state["strategy_draft"] == PACKETS["Arden"]["for_apps"]["org_modeling"]["strategy_text"]
    assert set(state["contexts"]) == {"Arden", "Belmar", "Caldera"}
    assert "Strategy text kept from the first Compass file (this file's differs)" in state["applied"]

    # Importing Belmar again says it will be replaced, and nothing changes until confirmed
    again = (await client.post("/api/v1/compass/preview", json={"packet": PACKETS["Belmar"]})).json()
    assert again["replaces"] and any("will replace" in w for w in again["warnings"])
    assert len((await client.get("/api/v1/compass")).json()["links"]) == 3


@pytest.mark.asyncio
async def test_country_not_in_file_and_different_frame(client: AsyncClient):
    await _upload_countries(client)
    other = copy.deepcopy(PACKETS["Belmar"])
    other["engagement"].update(country="Dorne", key="MERIDIANDO")
    pre = (await client.post("/api/v1/compass/preview", json={"packet": other})).json()
    assert pre["country"]["needs_choice"] and "'Dorne'" in pre["country"]["note"]
    assert pre["country"]["choices"] == ["Arden", "Belmar", "Caldera", ""]
    r = await client.post("/api/v1/compass/import", json={"packet": other})
    assert r.status_code == 400 and "Choose where to link it" in r.json()["detail"]
    bad = await client.post("/api/v1/compass/import", json={"packet": other, "link_country": "Narnia"})
    assert bad.status_code == 400 and "not a country in the uploaded org file" in bad.json()["detail"]
    ok = (await client.post("/api/v1/compass/import", json={"packet": other, "link_country": ""})).json()
    assert [l["label"] for l in ok["links"]] == ["Whole organization"]
    assert ok["engagement"]["key"] == "MERIDIANDO"

    changed = copy.deepcopy(PACKETS["Caldera"])
    changed["roles"][0]["ref"] = "RL-901"
    pre = (await client.post("/api/v1/compass/preview", json={"packet": changed})).json()
    assert any("different frame" in w and "may not mean the same thing" in w for w in pre["warnings"])


@pytest.mark.asyncio
async def test_packet_with_country_and_file_without_country_column(client: AsyncClient, sample_csv_path):
    await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", sample_csv_path.read_bytes(), "text/csv")})
    pre = (await client.post("/api/v1/compass/preview", json={"packet": PACKETS["Arden"]})).json()
    assert pre["country"]["needs_choice"] and pre["country"]["choices"] == [""]
    done = (await client.post("/api/v1/compass/import", json={"packet": PACKETS["Arden"], "link_country": ""})).json()
    assert done["links"][0]["label"] == "Whole organization" and done["engagement"]["key"] == "MERIDIAN"


def test_existing_link_becomes_the_whole_organization_link(tmp_path):
    """A database made before countries keeps its link, hypotheses and grades."""
    from sqlalchemy import create_engine, text, inspect
    from app.models.database import Base
    from app.models.upgrades import upgrade_engagements

    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        Base.metadata.create_all(conn, tables=[t for name, t in Base.metadata.tables.items() if name != "engagements"])
        conn.execute(text(
            "CREATE TABLE engagements (id VARCHAR(36) PRIMARY KEY, analysis_id VARCHAR(36) NOT NULL, key VARCHAR(100), "
            "packet JSON, imported_at DATETIME, strategy_draft TEXT, hypotheses JSON, hypothesis_seq INTEGER, grades JSON, "
            "relates JSON, created_at DATETIME, updated_at DATETIME)"))
        conn.execute(text("CREATE UNIQUE INDEX ix_engagements_analysis_id ON engagements (analysis_id)"))
        conn.execute(text(
            "INSERT INTO engagements VALUES ('e1', 'a1', 'MERIDIAN', '{\"format\": \"compass-handoff\"}', NULL, 'My strategy', "
            "'[{\"ref\": \"H1\"}]', 1, '{\"H1\": \"indicated\"}', '{}', NULL, NULL)"))
    with engine.begin() as conn:
        assert upgrade_engagements(conn) is True
        assert upgrade_engagements(conn) is False  # safe to run again
    with engine.begin() as conn:
        row = conn.execute(text("SELECT country, key, strategy_draft, hypotheses, grades, role_matches FROM engagements")).one()
        assert tuple(row) == ("", "MERIDIAN", "My strategy", '[{"ref": "H1"}]', '{"H1": "indicated"}', "{}")
        # Two links on one upload are now allowed when their countries differ
        conn.execute(text("INSERT INTO engagements (id, analysis_id, country) VALUES ('e2', 'a1', 'Belmar')"))
        assert "engagements_before_countries" not in inspect(conn).get_table_names()


# ------------------------------------------------------------- Compass roles by country

async def _three_linked(client):
    await _upload_countries(client)
    for c in ("Arden", "Belmar", "Caldera"):
        await client.post("/api/v1/compass/import", json={"packet": PACKETS[c]})


def _cell(view, ref, country):
    role = next(r for r in view["roles"] if r["ref"] == ref)
    return next(c for c in role["cells"] if c["country"] == country)


@pytest.mark.asyncio
async def test_roles_screen_matches_the_acceptance_table(client: AsyncClient):
    await _three_linked(client)
    view = (await client.get("/api/v1/compass/roles")).json()
    assert len(view["roles"]) == 19 and [l["country"] for l in view["links"]] == ["Arden", "Belmar", "Caldera"]
    # Nothing confirmed yet: suggestions only, counted as neither existing nor absent
    rl11 = next(r for r in view["roles"] if r["ref"] == "RL-011")
    assert not rl11["match_confirmed"] and rl11["suggestions"] == [{"title": "Head of Pricing / Revenue Management", "kind": "exact"}]
    assert _cell(view, "RL-011", "Belmar")["presence"] == "not_matched" and _cell(view, "RL-011", "Belmar")["holders"] is None

    view = (await client.post("/api/v1/compass/roles/accept-exact")).json()
    assert view["accepted"] == 16
    for ref in ("RL-010", "RL-012", "RL-017"):  # no job title for these in the file
        view = (await client.put("/api/v1/compass/roles/match", json={"ref": ref, "titles": []})).json()

    expected = {
        ("RL-011", "Arden"): (0, "absent"), ("RL-011", "Belmar"): (1, "exists"), ("RL-011", "Caldera"): (0, "absent"),
        ("RL-004", "Arden"): (1, "thin"), ("RL-004", "Belmar"): (0, "absent"), ("RL-004", "Caldera"): (2, "exists"),
        ("RL-018", "Arden"): (0, "absent"), ("RL-018", "Belmar"): (0, "absent"), ("RL-018", "Caldera"): (1, "exists"),
    }
    for (ref, country), (holders, status) in expected.items():
        cell = _cell(view, ref, country)
        assert (cell["holders"], cell["compass_status"]) == (holders, status), (ref, country, cell)
    caldera18 = _cell(view, "RL-018", "Caldera")
    assert caldera18["status_confirmed"] is False and caldera18["presence"] == "to_confirm"
    assert caldera18["flag"] == "Still to confirm in the Compass; the org file shows 1 person."
    # A role with nobody in it is never silent
    assert _cell(view, "RL-004", "Belmar")["missing_note"] == "Why is it missing? Not recorded."
    # "To confirm" is never counted as existing or absent
    assert view["summary"]["Caldera"]["to_confirm"] == 2
    assert sum(view["summary"]["Belmar"].values()) == 19 and view["summary"]["Belmar"]["not_matched"] == 0
    belmar_empty = sorted(r["ref"] for r in view["roles"] if _cell(view, r["ref"], "Belmar")["holders"] == 0)
    assert belmar_empty == ["RL-004", "RL-007", "RL-008", "RL-010", "RL-012", "RL-017", "RL-018"]
    assert view["unmatched_titles"] == 10  # titles in the file that match no Compass role: counted, not listed
    assert [e["ref"] for e in view["match_log"]][-3:] == ["RL-010", "RL-012", "RL-017"]


@pytest.mark.asyncio
async def test_flags_reasons_and_their_validation(client: AsyncClient):
    await _three_linked(client)
    await client.post("/api/v1/compass/roles/accept-exact")
    view = (await client.get("/api/v1/compass/roles")).json()
    # Compass says Arden's Head, Analytics & AI is thin... the file agrees (1 person); Belmar says absent, file shows 0
    assert _cell(view, "RL-007", "Belmar")["flag"] is None
    belmar = copy.deepcopy(PACKETS["Belmar"])
    next(r for r in belmar["roles"] if r["ref"] == "RL-013")["status"] = "absent"
    next(r for r in belmar["roles"] if r["ref"] == "RL-004")["status"] = "exists"
    view = (await client.post("/api/v1/compass/import", json={"packet": belmar})).json()
    view = (await client.get("/api/v1/compass/roles")).json()
    assert _cell(view, "RL-013", "Belmar")["flag"] == "The Compass says absent; the org file shows 1 person."
    assert _cell(view, "RL-004", "Belmar")["flag"] == "The Compass says this role exists; the org file shows nobody in it."

    reason = {"ref": "RL-011", "country": "Belmar", "reason_class": "chosen", "compared_with": "Arden", "grade": None,
              "text": "Created in 2023 when Belmar won its two largest renewal contracts; Arden leaves pricing to finance."}
    view = (await client.put("/api/v1/compass/roles/reason", json=reason)).json()
    assert _cell(view, "RL-011", "Belmar")["reason"]["reason_class"] == "chosen"
    assert (await client.put("/api/v1/compass/roles/reason", json={**reason, "reason_class": "because"})).status_code == 400
    assert (await client.put("/api/v1/compass/roles/reason", json={**reason, "compared_with": "Belmar"})).status_code == 400
    assert (await client.put("/api/v1/compass/roles/reason", json={**reason, "country": "Dorne"})).status_code == 404
    assert (await client.put("/api/v1/compass/roles/match", json={"ref": "RL-011", "titles": ["Chief Wizard"]})).status_code == 400
    # Back to "not matched yet"
    view = (await client.put("/api/v1/compass/roles/match", json={"ref": "RL-011", "titles": None})).json()
    assert _cell(view, "RL-011", "Belmar")["presence"] == "not_matched"


@pytest.mark.asyncio
async def test_roles_screen_without_packets_is_empty(client: AsyncClient, sample_csv_path):
    await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", sample_csv_path.read_bytes(), "text/csv")})
    view = (await client.get("/api/v1/compass/roles")).json()
    assert view["roles"] == [] and view["links"] == []


# ------------------------------------------------------------- one findings file per country

import re

SAMPLE_RETURN = json.loads((COUNTRIES / "belmar_return_org_modeling.json").read_text())
BELMAR_REASON = {"ref": "RL-011", "country": "Belmar", "reason_class": "chosen", "compared_with": "Arden", "grade": None,
                 "text": "Created in 2023 when Belmar won its two largest renewal contracts; Arden leaves pricing to finance."}


async def _matched_and_reasoned(client):
    await _three_linked(client)
    await client.post("/api/v1/compass/roles/accept-exact")
    for ref in ("RL-010", "RL-012", "RL-017"):
        await client.put("/api/v1/compass/roles/match", json={"ref": ref, "titles": []})
    await client.put("/api/v1/compass/roles/reason", json=BELMAR_REASON)


@pytest.mark.asyncio
async def test_belmar_file_has_the_shape_the_compass_expects(client: AsyncClient):
    await _matched_and_reasoned(client)
    r = await client.get("/api/v1/compass/return", params={"link": "Belmar"})
    assert r.status_code == 200 and 'filename="MERIDIANBE_compass_return.json"' in r.headers["content-disposition"]
    ret = r.json()
    assert set(ret) == set(SAMPLE_RETURN)  # same header fields
    assert (ret["format"], ret["format_version"], ret["source_app"], ret["engagement_key"], ret["country"]) == \
        ("compass-return", "1.0", "org-modeling", "MERIDIANBE", "Belmar")
    sample_fields = {k for f in SAMPLE_RETURN["findings"] for k in f}
    for f in ret["findings"]:
        assert set(f) <= sample_fields and {"ref", "kind", "title", "detail", "grade", "figure", "relates_to", "source_note", "topic"} <= set(f)
    by = {f["ref"]: f for f in ret["findings"]}

    layers = by["baseline.layers"]
    assert (layers["kind"], layers["topic"], layers["figure"], layers["title"]) == \
        ("structural_baseline", "role_presence", "5 layers", "Layers in the reporting chain (Belmar)")
    assert "26 people in Belmar" in layers["source_note"]

    rl11 = by["RL-011"]
    sample11 = next(f for f in SAMPLE_RETURN["findings"] if f["ref"] == "RL-011")
    assert rl11["title"] == sample11["title"] == "Why Head of Pricing / Revenue Management exists in Belmar"
    assert (rl11["kind"], rl11["topic"], rl11["reason_class"], rl11["compared_with"], rl11["figure"], rl11["grade"]) == \
        ("role_reason", "role_reason", "chosen", "Arden", "1 person", "indicated")
    assert rl11["relates_to"] == ["RL-011", "CAP-04", "CAP-04.People"] == sample11["relates_to"]
    assert rl11["detail"] == BELMAR_REASON["text"]
    assert rl11["source_note"] == "Reason recorded by the designer; head-count from the uploaded org file."

    # Every role nobody holds in Belmar is in the file, "unknown" where no reason is recorded
    empty = ["RL-004", "RL-007", "RL-008", "RL-010", "RL-012", "RL-017", "RL-018"]
    assert sorted(ref for ref, f in by.items() if f["kind"] == "role_reason") == sorted(["RL-011", *empty])
    for ref in empty:
        f = by[ref]
        assert (f["figure"], f["reason_class"], f["detail"], f["grade"]) == ("0 people", "unknown", "Not recorded yet.", "hypothesis")
        assert "compared_with" not in f and f["title"].endswith("is absent in Belmar")
    assert by["RL-004"]["title"] == "Why Hub Duty Controller (disruption) is absent in Belmar"

    # No names and no Employee IDs anywhere
    text = json.dumps(ret) + (await client.get("/api/v1/compass/return.txt", params={"link": "Belmar"})).text
    assert not re.search(r"\b[A-Z]{2} Person \d{3}\b", text) and not re.search(r"\bE\d{3}\b", text)


@pytest.mark.asyncio
async def test_country_grades_links_and_the_whole_organization_file(client: AsyncClient):
    await _matched_and_reasoned(client)
    # The designer's grade and links on a country finding are kept on that country's file only
    await client.put("/api/v1/compass/grades", json={"ref": "RL-004", "grade": "confirmed", "country": "Belmar"})
    data = (await client.put("/api/v1/compass/relates", json={"ref": "baseline.layers", "relates_to": ["CAP-05.Structure"], "country": "Belmar"})).json()
    by = {f["ref"]: f for f in data["findings"]}
    assert by["RL-004"]["grade"] == "confirmed" and by["baseline.layers"]["relates_to"] == ["CAP-05.Structure"]
    caldera = {f["ref"]: f for f in (await client.get("/api/v1/compass/findings", params={"link": "Caldera"})).json()["findings"]}
    assert caldera["baseline.layers"]["figure"] == "6 layers" and caldera["baseline.layers"]["relates_to"] == []
    assert "RL-018" not in caldera  # Caldera has one person in it and no reason: nothing to say yet

    whole = (await client.get("/api/v1/compass/return")).json()
    assert whole["country"] == "" and whole["engagement_key"] == "MERIDIAN"
    assert not any(f["kind"] == "role_reason" for f in whole["findings"])  # not repeated in the whole-organization file
    assert next(f for f in whole["findings"] if f["ref"] == "baseline.layers")["figure"] == "6 layers"

    text = (await client.get("/api/v1/compass/return.txt", params={"link": "Belmar"})).text
    assert text.startswith("Org Modeling findings for MERIDIANBE (Belmar)")
    assert "Reason: Chosen, compared with Arden" in text

    # A country with no packet linked has no file
    assert (await client.get("/api/v1/compass/return", params={"link": "Dorne"})).status_code == 404


@pytest.mark.asyncio
async def test_roles_not_matched_are_left_out_and_counted(client: AsyncClient):
    await _three_linked(client)
    data = (await client.get("/api/v1/compass/findings", params={"link": "Belmar"})).json()
    assert data["left_out_not_matched"] == 19
    assert [f["ref"] for f in data["findings"]] == ["baseline.layers", "baseline.spans", "baseline.health"]


@pytest.mark.asyncio
async def test_names_and_employee_ids_typed_into_a_reason_are_removed(client: AsyncClient):
    await _matched_and_reasoned(client)
    await client.put("/api/v1/compass/roles/reason", json={**BELMAR_REASON,
        "text": "BE Person 031 (E031) created it; E031-B is not an ID; see also XE031."})
    f = next(x for x in (await client.get("/api/v1/compass/findings", params={"link": "Belmar"})).json()["findings"] if x["ref"] == "RL-011")
    assert "BE Person 031" not in f["detail"] and "(E031)" not in f["detail"]
    assert "the Regional Managing Director ([an employee]) created it" in f["detail"]
    assert "E031-B" in f["detail"] and "XE031" in f["detail"]  # only whole IDs are removed
    # Figures are never touched
    assert next(x for x in (await client.get("/api/v1/compass/findings", params={"link": "Belmar"})).json()["findings"]
                if x["ref"] == "baseline.layers")["figure"] == "5 layers"


def test_open_readiness_items_read_as_sentences():
    from app.services.compass_service import validate_packet
    _, warnings = validate_packet(PACKETS["Belmar"])
    w = next(x for x in warnings if "not ready" in x)
    assert "{" not in w and "'check'" not in w
    assert "Baseline version saved (Use “Save version” to freeze the baseline the scoreboard measures against) — required" in w
