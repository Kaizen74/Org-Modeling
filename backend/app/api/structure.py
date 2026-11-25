"""
Structure inputs the designer controls: span ranges per manager type and the
words that mark a supervisory role (app-wide, Settings page), and manager
types set on screen for the latest upload. Every change recalculates metrics.
"""

import re
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
from ..services import role_families as rf

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


# ------------------------------------------------------------------ role families

class FamilyIn(BaseModel):
    name: str
    titles: List[str]


class FamilyUpdate(BaseModel):
    name: Optional[str] = None
    titles: Optional[List[str]] = None
    relates_to: Optional[List[str]] = None  # Compass cluster refs the family serves


class MergeIn(BaseModel):
    with_ref: str


class FamilyReasonIn(BaseModel):
    unit: str
    reason_class: Optional[str] = None  # None clears the reason for that unit
    text: str = ""
    compared_with: str = ""


def _units(analysis: OrgAnalysis) -> List[str]:
    return sorted({e.get("country") for e in analysis.raw_data["employees"] if e.get("country")})


def _titles(analysis: OrgAnalysis) -> set:
    return {str(e.get("job_title", "")).strip() for e in analysis.raw_data["employees"] if e.get("job_title")}


async def _cluster_refs(analysis: OrgAnalysis, db: AsyncSession) -> List[Dict]:
    from .compass import all_refs, linked  # the Compass link is optional
    return [r for r in all_refs(await linked(analysis, db)) if re.fullmatch(r"CAP-\d+", r["ref"])]


async def _families_view(analysis: OrgAnalysis, db: AsyncSession) -> Dict:
    inputs = await st.load_inputs(analysis, db)
    v = rf.view(analysis.raw_data["employees"], (inputs.families if inputs else None) or [],
                (inputs.family_reasons if inputs else None) or {}, _units(analysis))
    v["unit_label"] = (analysis.raw_data or {}).get("unit_label") or ("Country" if v["units"] else "")
    v["cluster_refs"] = await _cluster_refs(analysis, db)
    return v


@router.get("/families")
async def get_families(db: AsyncSession = Depends(get_session)):
    analysis = await _latest(db)
    return await _families_view(analysis, db)


@router.post("/families")
async def confirm_family(request: FamilyIn, db: AsyncSession = Depends(get_session)):
    """Confirm a family (from a suggestion or your own grouping); it gets the next RF number, never reused."""
    analysis = await _latest(db)
    inputs = await st.load_inputs(analysis, db, create=True)
    try:
        families, seq = rf.confirm(inputs.families or [], inputs.family_seq or 0, request.name, request.titles, _titles(analysis))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    inputs.families, inputs.family_seq = families, seq
    await db.commit()
    return await _families_view(analysis, db)


@router.put("/families/{ref}")
async def update_family(ref: str, request: FamilyUpdate, db: AsyncSession = Depends(get_session)):
    """Rename (the ID stays), change its titles, or link the Compass clusters it serves."""
    analysis = await _latest(db)
    inputs = await st.load_inputs(analysis, db, create=True)
    valid = {r["ref"] for r in await _cluster_refs(analysis, db)}
    try:
        inputs.families = rf.update(inputs.families or [], ref, _titles(analysis), name=request.name,
                                    titles=request.titles, relates_to=request.relates_to, valid_refs=valid)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return await _families_view(analysis, db)


@router.post("/families/{ref}/merge")
async def merge_families(ref: str, request: MergeIn, db: AsyncSession = Depends(get_session)):
    """Merge two families: the older ID stays; the other is retired and never reused."""
    analysis = await _latest(db)
    inputs = await st.load_inputs(analysis, db, create=True)
    try:
        families, reasons, kept = rf.merge(inputs.families or [], inputs.family_reasons or {}, ref, request.with_ref)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    inputs.families, inputs.family_reasons = families, reasons
    await db.commit()
    return {"kept": kept, **await _families_view(analysis, db)}


@router.post("/families/{ref}/retire")
async def retire_family(ref: str, db: AsyncSession = Depends(get_session)):
    analysis = await _latest(db)
    inputs = await st.load_inputs(analysis, db, create=True)
    try:
        inputs.families, inputs.family_reasons = rf.retire(inputs.families or [], inputs.family_reasons or {}, ref)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return await _families_view(analysis, db)


@router.put("/families/{ref}/reason")
async def set_family_reason(ref: str, request: FamilyReasonIn, db: AsyncSession = Depends(get_session)):
    """Why a family is, or isn't, in one unit: Required, Chosen, Inherited or Not known yet, with a sentence."""
    analysis = await _latest(db)
    units = _units(analysis)
    if request.unit not in units:
        raise HTTPException(status_code=400, detail=f"'{request.unit}' is not a unit in the uploaded org file.")
    if request.reason_class is not None and request.reason_class not in rf.REASON_CLASSES:
        raise HTTPException(status_code=400, detail="Reason must be Required, Chosen, Inherited or Not known yet.")
    compared = request.compared_with.strip()
    if compared and (compared == request.unit or compared not in units):
        raise HTTPException(status_code=400, detail="'Compared with' must be another unit in the org file.")
    inputs = await st.load_inputs(analysis, db, create=True)
    if not any(f["ref"] == ref for f in rf.active(inputs.families or [])):
        raise HTTPException(status_code=404, detail=f"No family {ref}")
    reasons = {k: dict(v) for k, v in (inputs.family_reasons or {}).items()}
    per_unit = reasons.setdefault(ref, {})
    if request.reason_class is None:
        per_unit.pop(request.unit, None)
    else:
        per_unit[request.unit] = {"reason_class": request.reason_class, "text": request.text.strip(), "compared_with": compared}
    inputs.family_reasons = reasons
    await db.commit()
    return await _families_view(analysis, db)
