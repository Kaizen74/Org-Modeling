"""Scenario Studio API: create design options and measure them against the current state."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import OrgAnalysis, Scenario
from ..services.metrics_service import MetricsCalculator
from ..services.metrics_store import ensure_metrics, load_grades, enrich_employees_with_grade_salary
from ..services.ai_disposition_service import capacity_freed
from .ai_disposition import active_roles
from ..services.scenario_engine import (
    MOVE_TYPES,
    apply_moves,
    headline,
    delta,
    department_deltas,
    people_impact,
)

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    moves: List[Dict] = []
    clone_from: Optional[str] = None  # copy the moves of an existing scenario
    source: str = "manual"


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    moves: Optional[List[Dict]] = None


class PreviewRequest(BaseModel):
    moves: List[Dict]


async def _latest_analysis(db: AsyncSession) -> OrgAnalysis:
    result = await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))
    analysis = result.scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    return analysis


async def _get_scenario(db: AsyncSession, scenario_id: str) -> Scenario:
    scenario = (await db.execute(select(Scenario).where(Scenario.id == scenario_id))).scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


async def evaluate(analysis: OrgAnalysis, moves: List[Dict], db: AsyncSession) -> Dict:
    """Apply moves to the analysis's baseline and compare the result with the current state."""
    baseline_metrics = await ensure_metrics(analysis, db)
    grades = await load_grades(db)
    grade_salary = {g.grade: g.median_salary for g in grades}
    grade_order = {g.grade: g.display_order for g in grades}

    baseline = enrich_employees_with_grade_salary(analysis.raw_data["employees"], grades)
    employees, log = apply_moves(baseline, moves, grade_salary)
    scenario_metrics = MetricsCalculator(employees=employees, grade_order=grade_order).calculate_all_metrics()

    base_head, scen_head = headline(baseline_metrics), headline(scenario_metrics)
    # Optional AI-role overlay: capacity freed, never a headcount change
    roles = await active_roles(analysis, db)
    base_head["ai_capacity_fte"], _ = capacity_freed(baseline, roles)
    scen_head["ai_capacity_fte"], _ = capacity_freed(employees, roles)
    return {
        "move_log": log,
        "baseline": base_head,
        "scenario": scen_head,
        "delta": delta(base_head, scen_head),
        "departments": department_deltas(baseline_metrics, scenario_metrics),
        "impact": people_impact(baseline, employees),
        "metrics": scenario_metrics,
        # Compact roster of the scenario's people, for the move pickers (includes new roles)
        "people": [
            {"employee_id": e["employee_id"], "name": e.get("name"), "job_title": e.get("job_title"),
             "department": e.get("department"), "manager_id": e.get("manager_id"), "grade": e.get("grade"),
             "is_new": bool(e.get("is_new"))}
            for e in employees
        ],
    }


def _summary(s: Scenario) -> Dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "source": s.source,
        "move_count": len(s.moves or []),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("/move-types")
async def move_types():
    """The design moves a scenario can contain."""
    return {"move_types": MOVE_TYPES}


@router.get("")
async def list_scenarios(db: AsyncSession = Depends(get_session)):
    """Scenarios for the current upload, each with its headline figures."""
    analysis = await _latest_analysis(db)
    rows = (await db.execute(
        select(Scenario).where(Scenario.analysis_id == analysis.id).order_by(Scenario.created_at)
    )).scalars().all()
    out = []
    for s in rows:
        result = await evaluate(analysis, s.moves or [], db)
        out.append({**_summary(s), "scenario": result["scenario"], "delta": result["delta"],
                    "skipped_moves": sum(1 for m in result["move_log"] if m["status"] == "skipped")})
    baseline = (await evaluate(analysis, [], db))["baseline"]
    return {"analysis_id": analysis.id, "baseline": baseline, "scenarios": out}


@router.post("")
async def create_scenario(request: ScenarioCreate, db: AsyncSession = Depends(get_session)):
    analysis = await _latest_analysis(db)
    moves = list(request.moves)
    if request.clone_from:
        moves = list((await _get_scenario(db, request.clone_from)).moves or []) + moves
    scenario = Scenario(analysis_id=analysis.id, name=request.name.strip(), description=request.description,
                        source=request.source, moves=moves)
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return {**_summary(scenario), **(await evaluate(analysis, moves, db)), "moves": moves}


@router.post("/preview")
async def preview(request: PreviewRequest, db: AsyncSession = Depends(get_session)):
    """Evaluate moves without saving them."""
    analysis = await _latest_analysis(db)
    return await evaluate(analysis, request.moves, db)


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str, db: AsyncSession = Depends(get_session)):
    scenario = await _get_scenario(db, scenario_id)
    analysis = (await db.execute(select(OrgAnalysis).where(OrgAnalysis.id == scenario.analysis_id))).scalar_one()
    return {**_summary(scenario), "moves": scenario.moves or [], **(await evaluate(analysis, scenario.moves or [], db))}


@router.put("/{scenario_id}")
async def update_scenario(scenario_id: str, request: ScenarioUpdate, db: AsyncSession = Depends(get_session)):
    scenario = await _get_scenario(db, scenario_id)
    if request.name is not None:
        scenario.name = request.name.strip()
    if request.description is not None:
        scenario.description = request.description
    if request.moves is not None:
        scenario.moves = list(request.moves)
    await db.commit()
    return await get_scenario(scenario_id, db)


@router.post("/{scenario_id}/moves")
async def add_move(scenario_id: str, move: Dict, db: AsyncSession = Depends(get_session)):
    """Append one design move."""
    scenario = await _get_scenario(db, scenario_id)
    if move.get("type") not in MOVE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown move type '{move.get('type')}'")
    scenario.moves = list(scenario.moves or []) + [move]  # reassign so the JSON change is saved
    await db.commit()
    return await get_scenario(scenario_id, db)


@router.delete("/{scenario_id}/moves/{index}")
async def remove_move(scenario_id: str, index: int, db: AsyncSession = Depends(get_session)):
    scenario = await _get_scenario(db, scenario_id)
    moves = list(scenario.moves or [])
    if not 0 <= index < len(moves):
        raise HTTPException(status_code=404, detail="No move at that position")
    moves.pop(index)
    scenario.moves = moves
    await db.commit()
    return await get_scenario(scenario_id, db)


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str, db: AsyncSession = Depends(get_session)):
    scenario = await _get_scenario(db, scenario_id)
    await db.delete(scenario)
    await db.commit()
    return {"message": f"Scenario '{scenario.name}' deleted"}
