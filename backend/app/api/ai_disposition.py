"""Optional AI-role overlay API: tag job titles automate / augment / keep human."""

import json
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import AIDisposition, OrgAnalysis
from ..services.ai_analysis_service import AIAnalysisService
from ..services.ai_disposition_service import DISPOSITIONS, build_prompt, role_inventory, summarize, validate_tag
from ..services.claude_service import claude_service
from ..services.llm_client import AnalysisRefused, run_analysis
from ..services.metrics_store import load_grades, enrich_employees_with_grade_salary

router = APIRouter(prefix="/api/v1/ai-disposition", tags=["ai-disposition"])


class RoleTag(BaseModel):
    job_title: str
    disposition: Optional[str] = None  # None clears the tag
    capacity_freed_pct: Optional[float] = None
    rationale: Optional[str] = None


class Toggle(BaseModel):
    enabled: bool


class SuggestRequest(BaseModel):
    industry: Optional[str] = None


async def get_overlay(analysis: OrgAnalysis, db: AsyncSession) -> Optional[AIDisposition]:
    return (await db.execute(select(AIDisposition).where(AIDisposition.analysis_id == analysis.id))).scalar_one_or_none()


async def active_roles(analysis: OrgAnalysis, db: AsyncSession) -> Dict[str, Dict]:
    """Tags that should affect scenarios and comparisons (empty when unused or switched off)."""
    overlay = await get_overlay(analysis, db)
    return dict(overlay.roles or {}) if overlay and overlay.enabled else {}


async def _context(db: AsyncSession, create: bool = True):
    analysis = (await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    overlay = await get_overlay(analysis, db)
    if not overlay and create:
        overlay = AIDisposition(analysis_id=analysis.id, enabled=1, roles={})
        db.add(overlay)
        await db.commit()
        await db.refresh(overlay)
    return analysis, overlay


async def _payload(analysis: OrgAnalysis, overlay: Optional[AIDisposition], db: AsyncSession) -> Dict:
    employees = enrich_employees_with_grade_salary(analysis.raw_data["employees"], await load_grades(db))
    roles = dict(overlay.roles or {}) if overlay else {}
    inventory = role_inventory(employees)
    for r in inventory:
        r["tag"] = roles.get(r["job_title"])
    return {
        "enabled": bool(overlay.enabled) if overlay else False,
        "dispositions": DISPOSITIONS,
        "roles": inventory,
        "summary": summarize(employees, roles),
        "ai_available": claude_service.is_configured(),
    }


@router.get("")
async def get_dispositions(db: AsyncSession = Depends(get_session)):
    analysis, overlay = await _context(db, create=False)
    return await _payload(analysis, overlay, db)


@router.put("/enabled")
async def set_enabled(request: Toggle, db: AsyncSession = Depends(get_session)):
    analysis, overlay = await _context(db)
    overlay.enabled = 1 if request.enabled else 0
    await db.commit()
    return await _payload(analysis, overlay, db)


@router.put("/role")
async def tag_role(request: RoleTag, db: AsyncSession = Depends(get_session)):
    analysis, overlay = await _context(db)
    roles = json.loads(json.dumps(overlay.roles or {}))
    if request.disposition is None:
        roles.pop(request.job_title, None)
    else:
        problem = validate_tag(request.disposition, request.capacity_freed_pct)
        if problem:
            raise HTTPException(status_code=400, detail=problem)
        roles[request.job_title] = {
            "disposition": request.disposition,
            "capacity_freed_pct": request.capacity_freed_pct or 0,
            "rationale": request.rationale or "",
            "source": "user",
        }
    overlay.roles = roles
    await db.commit()
    return await _payload(analysis, overlay, db)


@router.post("/suggest")
async def suggest(request: SuggestRequest, db: AsyncSession = Depends(get_session)):
    """AI suggestions for untagged roles; never overwrites the designer's own tags."""
    if not claude_service.is_configured():
        raise HTTPException(status_code=400, detail="Claude API key not configured. Please set it in Settings.")
    analysis, overlay = await _context(db)
    inventory = role_inventory(analysis.raw_data["employees"])
    service = AIAnalysisService(api_key=claude_service.api_key)
    try:
        text, _ = run_analysis(service.client, build_prompt(inventory, request.industry), max_tokens=24000)
    except AnalysisRefused as e:
        raise HTTPException(status_code=422, detail=str(e))
    parsed = service._parse_text(text)

    titles = {r["job_title"] for r in inventory}
    roles = json.loads(json.dumps(overlay.roles or {}))
    added = 0
    for s in parsed.get("roles", []) or []:
        title = s.get("job_title")
        try:
            pct = float(s.get("capacity_freed_pct") or 0)
        except (TypeError, ValueError):
            continue
        if title not in titles or validate_tag(s.get("disposition"), pct):
            continue
        if roles.get(title, {}).get("source") == "user":
            continue
        roles[title] = {"disposition": s["disposition"], "capacity_freed_pct": pct, "rationale": s.get("rationale", ""),
                        "source": "ai", "confidence": s.get("confidence")}
        added += 1
    overlay.roles = roles
    await db.commit()
    payload = await _payload(analysis, overlay, db)
    payload["suggestions_added"] = added
    return payload
