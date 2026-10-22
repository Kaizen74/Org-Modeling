"""
One place that turns a stored upload into current metrics.

Every endpoint that needs metrics goes through `ensure_metrics`, so they all
fill missing salaries from the grade table the same way and all recalculate
when the cached metrics were produced by an older version of the engine.
"""

from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import OrgAnalysis, GradeSalary
from .metrics_service import MetricsCalculator, METRICS_VERSION


def is_current(metrics: Dict) -> bool:
    """True when cached metrics were produced by the current engine version."""
    return bool(metrics) and metrics.get("metrics_version") == METRICS_VERSION


def enrich_employees_with_grade_salary(employees: List[Dict], grades: List[GradeSalary]) -> List[Dict]:
    """Fill a missing or zero salary from the grade table's median for that grade."""
    grade_salary_map = {g.grade: g.median_salary for g in grades}
    enriched = []
    for emp in employees:
        emp_copy = emp.copy()
        if not emp_copy.get("salary"):
            grade = emp_copy.get("grade", "")
            if grade in grade_salary_map:
                emp_copy["salary"] = grade_salary_map[grade]
        enriched.append(emp_copy)
    return enriched


async def load_grades(db: AsyncSession) -> List[GradeSalary]:
    result = await db.execute(select(GradeSalary).order_by(GradeSalary.display_order))
    return list(result.scalars().all())


async def ensure_metrics(analysis: OrgAnalysis, db: AsyncSession, force: bool = False) -> Dict:
    """Return current metrics for an upload, recalculating and caching when needed."""
    if not force and is_current(analysis.metrics):
        return analysis.metrics

    employees = analysis.raw_data.get("employees", []) if analysis.raw_data else []
    grades = await load_grades(db)
    grade_order = {g.grade: g.display_order for g in grades}
    employees = enrich_employees_with_grade_salary(employees, grades)

    metrics = MetricsCalculator(employees=employees, grade_order=grade_order).calculate_all_metrics()
    analysis.metrics = metrics
    await db.commit()
    return metrics
