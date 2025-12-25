"""Metrics Calculation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, List, Optional

from ..models.database import get_session
from ..models.models import OrgAnalysis, GradeSalary
from ..services.metrics_service import MetricsCalculator

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def _enrich_employees_with_grade_salary(employees: List[Dict], grades: List[GradeSalary]) -> List[Dict]:
    """
    Enrich employee data with salary from grade configuration.

    If an employee's salary is 0 or missing, look up the salary from
    the grade configuration based on their grade.
    """
    # Build grade -> salary lookup
    grade_salary_map = {g.grade: g.median_salary for g in grades}

    enriched = []
    for emp in employees:
        emp_copy = emp.copy()
        current_salary = emp_copy.get("salary", 0)

        # If salary is missing or zero, try to get from grade config
        if not current_salary or current_salary == 0:
            grade = emp_copy.get("grade", "")
            if grade in grade_salary_map:
                emp_copy["salary"] = grade_salary_map[grade]

        enriched.append(emp_copy)

    return enriched


class MetricsRequest(BaseModel):
    employees: List[Dict]
    grade_order: Optional[Dict[str, int]] = None


class MetricsResponse(BaseModel):
    total_employees: int
    manager_stats: Dict
    span_of_control: Dict
    cost_analysis: Dict
    grade_gap_analysis: Dict
    layer_analysis: Dict
    health_indicators: Dict


@router.post("/calculate", response_model=MetricsResponse)
async def calculate_metrics(
    request: MetricsRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Calculate metrics for provided employee data.

    If grade_order is not provided, will attempt to load from database.
    Salary is enriched from grade configuration if not provided in employee data.
    """
    grade_order = request.grade_order

    # Load grades from DB
    result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    grades = result.scalars().all()

    # Get grade order if not provided
    if not grade_order and grades:
        grade_order = {g.grade: g.display_order for g in grades}

    # Enrich employees with salary from grade config if not provided
    employees = _enrich_employees_with_grade_salary(request.employees, grades)

    calculator = MetricsCalculator(
        employees=employees,
        grade_order=grade_order
    )

    return calculator.calculate_all_metrics()


@router.get("/latest")
async def get_latest_metrics(
    force_recalculate: bool = False,
    db: AsyncSession = Depends(get_session)
):
    """Get metrics for the most recently uploaded org data."""
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No org data found. Please upload a CSV first."
        )

    # If metrics already calculated and not forcing recalculation, return them
    if analysis.metrics and not force_recalculate:
        return {
            "analysis_id": analysis.id,
            "analysis_name": analysis.name,
            "metrics": analysis.metrics,
            "cached": True
        }

    # Calculate metrics
    employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []

    if not employees:
        raise HTTPException(
            status_code=400,
            detail="No employee data found in analysis"
        )

    # Load grades
    grade_result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    grades = grade_result.scalars().all()
    grade_order = {g.grade: g.display_order for g in grades} if grades else {}

    # Enrich employees with salary from grade config if not provided
    employees = _enrich_employees_with_grade_salary(employees, grades)

    calculator = MetricsCalculator(employees=employees, grade_order=grade_order)
    metrics = calculator.calculate_all_metrics()

    # Cache metrics in database
    analysis.metrics = metrics
    await db.commit()

    return {
        "analysis_id": analysis.id,
        "analysis_name": analysis.name,
        "metrics": metrics,
        "cached": False
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

    employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []

    if not employees:
        raise HTTPException(
            status_code=400,
            detail="No employee data found in analysis"
        )

    # Load grades
    grade_result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    grades = grade_result.scalars().all()
    grade_order = {g.grade: g.display_order for g in grades} if grades else {}

    # Enrich employees with salary from grade config if not provided
    employees = _enrich_employees_with_grade_salary(employees, grades)

    calculator = MetricsCalculator(employees=employees, grade_order=grade_order)
    metrics = calculator.calculate_all_metrics()

    # Store metrics
    analysis.metrics = metrics
    await db.commit()

    return {
        "analysis_id": analysis.id,
        "metrics": metrics,
        "message": "Metrics calculated and stored"
    }


@router.post("/recalculate")
async def recalculate_metrics(db: AsyncSession = Depends(get_session)):
    """Force recalculate metrics for the latest org data with current grade configuration.

    This endpoint enriches employee salary data from the grade configuration
    when auto-populate is used. Salary is looked up by employee grade.
    """
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No org data found. Please upload a CSV first."
        )

    employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []

    if not employees:
        raise HTTPException(
            status_code=400,
            detail="No employee data found in analysis"
        )

    # Load grades (for both order and salary lookup)
    grade_result = await db.execute(
        select(GradeSalary).order_by(GradeSalary.display_order)
    )
    grades = grade_result.scalars().all()
    grade_order = {g.grade: g.display_order for g in grades} if grades else {}
    grade_salary = {g.grade: g.median_salary for g in grades} if grades else {}

    # Enrich employees with salary from grade config if not provided
    employees = _enrich_employees_with_grade_salary(employees, grades)

    calculator = MetricsCalculator(employees=employees, grade_order=grade_order)
    metrics = calculator.calculate_all_metrics()

    # Update cached metrics
    analysis.metrics = metrics
    await db.commit()

    return {
        "analysis_id": analysis.id,
        "analysis_name": analysis.name,
        "metrics": metrics,
        "grade_order_used": grade_order,
        "grade_salary_used": grade_salary,
        "message": "Metrics recalculated successfully"
    }


@router.get("/summary")
async def get_metrics_summary(db: AsyncSession = Depends(get_session)):
    """Get a simplified metrics summary for dashboard display."""
    result = await db.execute(
        select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No metrics available. Please upload and analyze org data first."
        )

    # If no metrics cached, calculate them
    if not analysis.metrics:
        employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []
        if employees:
            grade_result = await db.execute(
                select(GradeSalary).order_by(GradeSalary.display_order)
            )
            grades = grade_result.scalars().all()
            grade_order = {g.grade: g.display_order for g in grades} if grades else {}

            # Enrich employees with salary from grade config if not provided
            employees = _enrich_employees_with_grade_salary(employees, grades)

            calculator = MetricsCalculator(employees=employees, grade_order=grade_order)
            metrics = calculator.calculate_all_metrics()
            analysis.metrics = metrics
            await db.commit()
        else:
            raise HTTPException(
                status_code=404,
                detail="No metrics available. Please upload and analyze org data first."
            )

    metrics = analysis.metrics
    return {
        "total_employees": metrics.get("total_employees", 0),
        "total_managers": metrics.get("manager_stats", {}).get("total_managers", 0),
        "manager_ratio": metrics.get("manager_stats", {}).get("manager_ratio_pct", 0),
        "average_span": metrics.get("span_of_control", {}).get("average_span", 0),
        "average_grade_gap": metrics.get("grade_gap_analysis", {}).get("average_grade_gap", 0),
        "total_cost": metrics.get("cost_analysis", {}).get("total_cost", 0),
        "layers": metrics.get("layer_analysis", {}).get("total_layers", 0),
        "health_score": metrics.get("health_indicators", {}).get("health_score", 0),
        "health_grade": metrics.get("health_indicators", {}).get("health_grade", "?"),
        "warnings": metrics.get("health_indicators", {}).get("warnings", [])
    }
