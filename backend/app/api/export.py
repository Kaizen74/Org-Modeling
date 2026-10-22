"""Board-ready findings pack export (self-contained HTML; print to PDF from the browser)."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import OrgAnalysis, Scenario
from ..services.archetype_scoring import reconcile_archetype_scores
from ..services.export_service import build_pack
from ..services.implementation_service import build_plan
from ..services.metrics_store import ensure_metrics
from ..services.privacy import name_map, without_names
from .comparison import _context as comparison_context, _payload as comparison_payload
from .scenarios import evaluate

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/pack", response_class=HTMLResponse)
async def findings_pack(
    scenario_id: Optional[str] = None,
    include_names: bool = False,
    db: AsyncSession = Depends(get_session),
):
    """
    Findings pack for the latest upload. The implementation section covers
    `scenario_id`, or else the top-ranked scenario in the comparison.
    Names are replaced by job titles unless include_names=true.
    """
    analysis = (await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")

    metrics = await ensure_metrics(analysis, db)
    _, comparison = await comparison_context(db)
    comp = await comparison_payload(analysis, comparison, db)

    focus_id = scenario_id or next((oid for oid in comp["result"]["ranking"] if oid != "current"), None)
    focus = plan = None
    if focus_id:
        scenario = (await db.execute(
            select(Scenario).where(Scenario.id == focus_id, Scenario.analysis_id == analysis.id)
        )).scalar_one_or_none()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        ev = await evaluate(analysis, scenario.moves or [], db)
        focus = {"name": scenario.name, "baseline": ev["baseline"], "scenario": ev["scenario"], "delta": ev["delta"]}
        plan = build_plan(ev, scenario.moves or [])

    names = name_map(analysis.raw_data["employees"])
    scrub = (lambda t: t) if include_names else (lambda t: without_names(t, names))

    html = build_pack(
        org_name=analysis.name or "Organization",
        metrics=metrics,
        ai_analysis=reconcile_archetype_scores(analysis.ai_analysis or {}),
        comparison=comp,
        focus=focus,
        plan=plan,
        strategy_provided=bool(analysis.strategy_context),
        design_criteria=analysis.design_criteria,
        scrub=scrub,
    )
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", f"FINDINGS_{analysis.name or 'org'}") + ".html"
    return HTMLResponse(html, headers={"Content-Disposition": f'inline; filename="{filename}"'})
