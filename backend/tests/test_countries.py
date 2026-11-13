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
