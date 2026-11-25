"""
Structure inputs the designer controls: span ranges per manager type and the
words that mark a supervisory role (app-wide, Settings page), and manager
types set on screen for the latest upload. Every change recalculates metrics.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import OrgAnalysis
from ..resources.benchmarks_reference import DEFAULT_SUPERVISORY_WORDS, MANAGER_TYPES
from ..services.metrics_store import ensure_metrics
from ..services import structure_settings as st

router = APIRouter(prefix="/api/v1/structure", tags=["structure"])


class SettingsIn(BaseModel):
    type_ranges: Optional[Dict[str, List[int]]] = None
    supervisory_words: Optional[List[str]] = None


class ManagerTypeIn(BaseModel):
    employee_id: str
    manager_type: Optional[str] = None  # None clears the type set on screen


def _settings_payload(settings: Dict) -> Dict:
    return {
        **settings,
        "manager_types": [{"key": k, "label": t["label"], "description": t["description"], "starting_range": list(t["range"])}
                          for k, t in MANAGER_TYPES.items()],
        "default_supervisory_words": DEFAULT_SUPERVISORY_WORDS,
        "note": "Starting points, not targets. Each manager's span is compared with the range for their type.",
    }


@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_session)):
    return _settings_payload(await st.load_settings(db))


@router.put("/settings")
async def put_settings(request: SettingsIn, db: AsyncSession = Depends(get_session)):
    data = request.model_dump(exclude_none=True)
    problems = st.validate_settings(data)
    if problems:
        raise HTTPException(status_code=400, detail="; ".join(problems))
    return _settings_payload(await st.save_settings(db, data))


@router.post("/settings/reset")
async def reset_settings(db: AsyncSession = Depends(get_session)):
    return _settings_payload(await st.reset_settings(db))


async def _latest(db: AsyncSession) -> OrgAnalysis:
    analysis = (await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    return analysis


@router.put("/manager-type")
async def set_manager_type(request: ManagerTypeIn, db: AsyncSession = Depends(get_session)):
    """Confirm or change one manager's type (the designer's choice; no AI decides it)."""
    if request.manager_type is not None and request.manager_type not in MANAGER_TYPES:
        raise HTTPException(status_code=400, detail=f"Manager type must be one of: {', '.join(t['label'] for t in MANAGER_TYPES.values())}")
    analysis = await _latest(db)
    if request.employee_id not in {e.get("employee_id") for e in analysis.raw_data["employees"]}:
        raise HTTPException(status_code=404, detail="No one with that Employee ID in the uploaded file.")
    inputs = await st.load_inputs(analysis, db, create=True)
    types = {k: v for k, v in (inputs.manager_types or {}).items() if k != request.employee_id}
    if request.manager_type:
        types[request.employee_id] = request.manager_type
    inputs.manager_types = types
    await db.commit()
    return {"metrics": await ensure_metrics(analysis, db)}


@router.post("/manager-types/confirm-suggested")
async def confirm_suggested_types(db: AsyncSession = Depends(get_session)):
    """Confirm every suggested type as it stands (e.g. Supervisor from Work Type Operational)."""
    analysis = await _latest(db)
    metrics = await ensure_metrics(analysis, db)
    suggested = {a["manager_id"]: a["manager_type"] for a in metrics["span_of_control"].get("manager_assessments", [])
                 if a.get("manager_type_status") == "suggested"}
    inputs = await st.load_inputs(analysis, db, create=True)
    inputs.manager_types = {**(inputs.manager_types or {}), **suggested}
    await db.commit()
    return {"confirmed": len(suggested), "metrics": await ensure_metrics(analysis, db)}
