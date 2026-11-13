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
