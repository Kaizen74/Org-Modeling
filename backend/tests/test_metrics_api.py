"""API-level tests: upload → metrics, stale cache recalculation, salary fill-in."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.models import OrgAnalysis


async def _upload(client: AsyncClient, csv_text: str, name: str = "org.csv"):
    response = await client.post(
        "/api/v1/org-data/upload-csv",
        files={"file": (name, csv_text.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_upload_then_metrics_end_to_end(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path.read_text(), "pax.csv")
    response = await client.get("/api/v1/metrics/latest")
    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["metrics_version"] >= 2
    assert metrics["total_employees"] == 64
    assert metrics["layer_analysis"]["total_layers"] == 6
    assert len(metrics["health_indicators"]["components"]) == 4

    summary = (await client.get("/api/v1/metrics/summary")).json()
    assert summary["health_score"] == metrics["health_indicators"]["health_score"]
    assert len(summary["health_components"]) == 4


@pytest.mark.asyncio
async def test_stale_cached_metrics_are_recalculated(client: AsyncClient, db_session, sample_csv_path):
    await _upload(client, sample_csv_path.read_text(), "pax.csv")
    analysis = (await db_session.execute(select(OrgAnalysis))).scalar_one()
    # Simulate metrics cached by an older engine (no version, old shape)
    analysis.metrics = {"total_employees": 64, "health_indicators": {"health_score": 55}}
    await db_session.commit()

    response = await client.get("/api/v1/metrics/latest")
    body = response.json()
    assert body["cached"] is False
    assert "components" in body["metrics"]["health_indicators"]


@pytest.mark.asyncio
async def test_missing_salaries_are_filled_from_grade_table(client: AsyncClient):
    # Grades configured first, then a CSV with no Salary column
    await client.post("/api/v1/grades/", json={"grade": "SVP", "median_salary": 300000, "display_order": 1})
    await client.post("/api/v1/grades/", json={"grade": "AO", "median_salary": 50000, "display_order": 2})
    await _upload(client, (
        "Name,Job Title,Grade,Level,Line Manager,Employee ID\n"
        "Ana Lee,CEO,SVP,1,Top of Org,E1\n"
        "Bo Lim,Analyst,AO,2,Ana Lee,E2\n"
    ))
    metrics = (await client.get("/api/v1/metrics/latest")).json()["metrics"]
    assert metrics["cost_analysis"]["total_cost"] == 350000
