"""
Shared workflow API: import a Capability Compass hand-off, keep operating-model
hypotheses, set shared evidence grades and Compass links on findings, and write
the compass-return file. Everything here is optional: the app works with no packet.
"""

from datetime import datetime
import json
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import Engagement, OrgAnalysis
from ..services import compass_service as cs
from ..services.metrics_store import ensure_metrics
from ..services.privacy import name_map, without_names
from .comparison import _context as comparison_context, _payload as comparison_payload

router = APIRouter(prefix="/api/v1/compass", tags=["compass"])


class ImportRequest(BaseModel):
    packet: Dict
    replace_criteria: bool = False  # only needed when the preview says "ask"
    replace_strategy: bool = False


class PreviewRequest(BaseModel):
    packet: Dict


class StrategyDraft(BaseModel):
    text: str = ""


class HypothesisIn(BaseModel):
    statement: str
    refuted_by: str = ""
    status: str = "open"
    note: str = ""


class GradeIn(BaseModel):
    ref: str
    grade: Optional[str] = None  # None returns to the suggested grade


class RelatesIn(BaseModel):
    ref: str
    relates_to: List[str] = []


async def latest_analysis(db: AsyncSession) -> OrgAnalysis:
    analysis = (await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    return analysis


async def get_engagement(analysis: OrgAnalysis, db: AsyncSession, create: bool = False) -> Optional[Engagement]:
    eng = (await db.execute(select(Engagement).where(Engagement.analysis_id == analysis.id))).scalar_one_or_none()
    if not eng and create:
        eng = Engagement(analysis_id=analysis.id, hypotheses=[], hypothesis_seq=0, grades={}, relates={})
        db.add(eng)
        await db.commit()
        await db.refresh(eng)
    return eng


async def findings_for(analysis: OrgAnalysis, eng: Optional[Engagement], db: AsyncSession) -> List[Dict]:
    metrics = await ensure_metrics(analysis, db)
    _, comparison = await comparison_context(db)
    comp = await comparison_payload(analysis, comparison, db)
    findings = cs.collect_findings(
        metrics, analysis.ai_analysis or {}, comp,
        (eng.hypotheses if eng else None) or [], (eng.grades if eng else None) or {}, (eng.relates if eng else None) or {},
    )
    # People stay as counts or job titles in anything that leaves the app
    names = name_map(analysis.raw_data["employees"])
    for f in findings:
        for field in ("title", "detail", "source_note"):
            f[field] = without_names(f[field] or "", names)
    return findings


async def _state(analysis: OrgAnalysis, eng: Optional[Engagement], db: AsyncSession) -> Dict:
    packet = eng.packet if eng else None
    return {
        "engagement": cs.engagement_summary(packet),
        "imported_at": eng.imported_at.isoformat() if eng and eng.imported_at else None,
        "strategy_draft": (eng.strategy_draft if eng else None) or "",
        "context": cs.packet_context(packet),
        "refs": cs.known_refs(packet) if packet else [],
        "hypotheses": (eng.hypotheses if eng else None) or [],
        "grades": cs.GRADES,
        "grade_labels": cs.GRADE_LABELS,
        "evidence_to_grade": cs.EVIDENCE_TO_GRADE,
        "grade_overrides": (eng.grades if eng else None) or {},
        "hypothesis_statuses": cs.HYPOTHESIS_STATUSES,
        "findings": await findings_for(analysis, eng, db),
    }


@router.get("")
async def get_state(db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    return await _state(analysis, await get_engagement(analysis, db), db)


async def _preview(packet: Dict, analysis: OrgAnalysis, eng: Optional[Engagement], db: AsyncSession) -> Dict:
    _, comparison = await comparison_context(db)
    current_strategy = (eng.strategy_draft if eng else None) or analysis.strategy_context or ""
    return cs.preview_import(packet, comparison.criteria or [], comparison.judgments or {}, current_strategy,
                             eng.key if eng else None)


@router.post("/preview")
async def preview(request: PreviewRequest, db: AsyncSession = Depends(get_session)):
    """What importing this file would create or change. Applies nothing."""
    analysis = await latest_analysis(db)
    return await _preview(request.packet, analysis, await get_engagement(analysis, db), db)


@router.post("/import")
async def import_packet(request: ImportRequest, db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    plan = await _preview(request.packet, analysis, eng, db)
    if not plan["ok"]:
        raise HTTPException(status_code=400, detail=" ".join(plan["errors"]))

    applied = []
    _, comparison = await comparison_context(db)
    action = plan["criteria"]["action"]
    if action == "set" or (action == "ask" and request.replace_criteria):
        comparison.criteria = plan["criteria"]["incoming"]
        applied.append(f"{len(plan['criteria']['incoming'])} comparison criteria set from the file")
    elif action == "ask":
        applied.append("Your comparison criteria were kept")
    elif action == "invalid":
        applied.append("The file's criteria were not used: " + "; ".join(plan["criteria"]["problems"]))

    action = plan["strategy"]["action"]
    if action == "set" or (action == "ask" and request.replace_strategy):
        eng.strategy_draft = plan["strategy"]["incoming"]
        applied.append("Strategy text pre-filled on the archetype page")
    elif action == "ask":
        applied.append("Your strategy text was kept")

    eng.key = request.packet["engagement"]["key"]
    eng.packet = request.packet
    eng.imported_at = datetime.utcnow()
    # Links to IDs that are not in the new packet would point nowhere
    valid = {r["ref"] for r in cs.known_refs(request.packet)}
    eng.relates = {k: [r for r in v if r in valid] for k, v in (eng.relates or {}).items()}
    await db.commit()
    applied.append(f"Linked to engagement {eng.key}")
    return {"applied": applied, "warnings": plan["warnings"], **await _state(analysis, eng, db)}


@router.put("/strategy-draft")
async def save_strategy_draft(request: StrategyDraft, db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    eng.strategy_draft = request.text
    await db.commit()
    return {"strategy_draft": eng.strategy_draft}


def _check_hypothesis(h: HypothesisIn):
    if not h.statement.strip():
        raise HTTPException(status_code=400, detail="A hypothesis needs a statement.")
    if h.status not in cs.HYPOTHESIS_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(cs.HYPOTHESIS_STATUSES)}")


@router.post("/hypotheses")
async def add_hypothesis(request: HypothesisIn, db: AsyncSession = Depends(get_session)):
    _check_hypothesis(request)
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    eng.hypothesis_seq = (eng.hypothesis_seq or 0) + 1  # numbers are never reused, even after a delete
    eng.hypotheses = [*(eng.hypotheses or []), {
        "ref": f"H{eng.hypothesis_seq}", "statement": request.statement.strip(), "refuted_by": request.refuted_by.strip(),
        "status": request.status, "note": request.note.strip(),
    }]
    await db.commit()
    return await _state(analysis, eng, db)


@router.put("/hypotheses/{ref}")
async def update_hypothesis(ref: str, request: HypothesisIn, db: AsyncSession = Depends(get_session)):
    _check_hypothesis(request)
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    items = json.loads(json.dumps(eng.hypotheses or []))
    target = next((h for h in items if h["ref"] == ref), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"No hypothesis {ref}")
    target.update(statement=request.statement.strip(), refuted_by=request.refuted_by.strip(),
                  status=request.status, note=request.note.strip())
    eng.hypotheses = items
    await db.commit()
    return await _state(analysis, eng, db)


@router.delete("/hypotheses/{ref}")
async def delete_hypothesis(ref: str, db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    if not any(h["ref"] == ref for h in eng.hypotheses or []):
        raise HTTPException(status_code=404, detail=f"No hypothesis {ref}")
    eng.hypotheses = [h for h in eng.hypotheses if h["ref"] != ref]
    eng.grades = {k: v for k, v in (eng.grades or {}).items() if k != ref}
    eng.relates = {k: v for k, v in (eng.relates or {}).items() if k != ref}
    await db.commit()
    return await _state(analysis, eng, db)


@router.put("/grades")
async def set_grade(request: GradeIn, db: AsyncSession = Depends(get_session)):
    """The assessor's grade for one finding; None goes back to the suggested grade."""
    if request.grade is not None and request.grade not in cs.GRADES:
        raise HTTPException(status_code=400, detail=f"Grade must be one of: {', '.join(cs.GRADES)}")
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    grades = {k: v for k, v in (eng.grades or {}).items() if k != request.ref}
    if request.grade:
        grades[request.ref] = request.grade
    eng.grades = grades
    await db.commit()
    return await _state(analysis, eng, db)


@router.put("/relates")
async def set_relates(request: RelatesIn, db: AsyncSession = Depends(get_session)):
    """Attach Compass IDs to a finding. Only IDs from the imported packet are accepted."""
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db, create=True)
    valid = {r["ref"] for r in cs.known_refs(eng.packet)} if eng.packet else set()
    unknown = [r for r in request.relates_to if r not in valid]
    if unknown:
        raise HTTPException(status_code=400, detail=(
            f"Not in the imported Compass file: {', '.join(unknown)}" if valid
            else "Import a Capability Compass file first; its IDs are the ones a finding can relate to."))
    relates = {k: v for k, v in (eng.relates or {}).items() if k != request.ref}
    if request.relates_to:
        relates[request.ref] = list(dict.fromkeys(request.relates_to))
    eng.relates = relates
    await db.commit()
    return await _state(analysis, eng, db)


async def _return(db: AsyncSession):
    analysis = await latest_analysis(db)
    eng = await get_engagement(analysis, db)
    ret = cs.build_return(eng.key if eng else None, await findings_for(analysis, eng, db))
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", (eng.key if eng and eng.key else analysis.name or "org")) + "_org_modeling_return"
    return ret, stem


@router.get("/return")
async def return_file(db: AsyncSession = Depends(get_session)):
    """compass-return v1.0: this app's findings in the shape the other apps read."""
    ret, stem = await _return(db)
    return JSONResponse(ret, headers={"Content-Disposition": f'attachment; filename="{stem}.json"'})


@router.get("/return.txt", response_class=PlainTextResponse)
async def return_text(db: AsyncSession = Depends(get_session)):
    ret, stem = await _return(db)
    return PlainTextResponse(cs.return_as_text(ret), headers={"Content-Disposition": f'inline; filename="{stem}.txt"'})
