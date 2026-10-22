"""Metrics Calculation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, List, Optional

from ..models.database import get_session
from ..models.models import OrgAnalysis
from ..services.metrics_service import MetricsCalculator
from ..services.metrics_store import (
    ensure_metrics,
    is_current,
    load_grades,
    enrich_employees_with_grade_salary,
)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class MetricsRequest(BaseModel):
    employees: List[Dict]
    grade_order: Optional[Dict[str, int]] = None


async def _latest_analysis(db: AsyncSession, not_found: str) -> OrgAnalysis:
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail=not_found)
    return analysis


def _require_employees(analysis: OrgAnalysis):
    employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []
    if not employees:
        raise HTTPException(status_code=400, detail="No employee data found in analysis")


@router.post("/calculate")
async def calculate_metrics(
    request: MetricsRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Calculate metrics for provided employee data.

    If grade_order is not provided, will attempt to load from database.
    Salary is enriched from grade configuration if not provided in employee data.
    """
    grades = await load_grades(db)
    grade_order = request.grade_order or {g.grade: g.display_order for g in grades}
    employees = enrich_employees_with_grade_salary(request.employees, grades)
    return MetricsCalculator(employees=employees, grade_order=grade_order).calculate_all_metrics()


@router.get("/latest")
async def get_latest_metrics(
    force_recalculate: bool = False,
    db: AsyncSession = Depends(get_session)
):
    """Get metrics for the most recently uploaded org data."""
    analysis = await _latest_analysis(db, "No org data found. Please upload a CSV first.")
    _require_employees(analysis)
    was_cached = is_current(analysis.metrics) and not force_recalculate
    metrics = await ensure_metrics(analysis, db, force=force_recalculate)
    return {
        "analysis_id": analysis.id,
        "analysis_name": analysis.name,
        "metrics": metrics,
        "cached": was_cached
    }


@router.post("/calculate-for-analysis/{analysis_id}")
async def calculate_for_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Calculate and store metrics for a specific analysis."""
    result = await db.execute(
        select(OrgAnalysis).where(OrgAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    _require_employees(analysis)
    metrics = await ensure_metrics(analysis, db, force=True)
    return {
        "analysis_id": analysis.id,
        "metrics": metrics,
        "message": "Metrics calculated and stored"
    }


@router.post("/recalculate")
async def recalculate_metrics(db: AsyncSession = Depends(get_session)):
    """Force recalculate metrics for the latest org data with current grade configuration."""
    analysis = await _latest_analysis(db, "No org data found. Please upload a CSV first.")
    _require_employees(analysis)
    metrics = await ensure_metrics(analysis, db, force=True)
    grades = await load_grades(db)
    return {
        "analysis_id": analysis.id,
        "analysis_name": analysis.name,
        "metrics": metrics,
        "grade_order_used": {g.grade: g.display_order for g in grades},
        "grade_salary_used": {g.grade: g.median_salary for g in grades},
        "message": "Metrics recalculated successfully"
    }


@router.get("/summary")
async def get_metrics_summary(db: AsyncSession = Depends(get_session)):
    """Get a simplified metrics summary for dashboard display."""
    not_found = "No metrics available. Please upload and analyze org data first."
    analysis = await _latest_analysis(db, not_found)
    if not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail=not_found)
    metrics = await ensure_metrics(analysis, db)

    health = metrics.get("health_indicators", {})
    return {
        "total_employees": metrics.get("total_employees", 0),
        "total_managers": metrics.get("manager_stats", {}).get("total_managers", 0),
        "manager_ratio": metrics.get("manager_stats", {}).get("manager_ratio_pct", 0),
        "average_span": metrics.get("span_of_control", {}).get("average_span", 0),
        "average_grade_gap": metrics.get("grade_gap_analysis", {}).get("average_grade_gap", 0),
        "total_cost": metrics.get("cost_analysis", {}).get("total_cost", 0),
        "layers": metrics.get("layer_analysis", {}).get("total_layers", 0),
        "health_score": health.get("health_score", 0),
        "health_grade": health.get("health_grade", "?"),
        "health_components": health.get("components", []),
        "warnings": health.get("warnings", [])
    }
