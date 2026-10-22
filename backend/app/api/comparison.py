"""Option comparison API: weighted design criteria applied to the current state and every scenario."""

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import Comparison, OrgAnalysis, Scenario
from ..services.comparison_service import DEFAULT_CRITERIA, MEASURABLE, score_options, validate_criteria
from ..services.claude_service import claude_service
from ..services.ai_analysis_service import AIAnalysisService
from ..services.llm_client import run_analysis, AnalysisRefused
from ..services.privacy import name_map, without_names
from .scenarios import evaluate

router = APIRouter(prefix="/api/v1/comparison", tags=["comparison"])


class CriteriaUpdate(BaseModel):
    criteria: List[Dict]


class JudgmentUpdate(BaseModel):
    option_id: str
    criterion_id: str
    score: Optional[float] = None  # 1-5; None clears the score
    rationale: Optional[str] = None


async def _context(db: AsyncSession):
    result = await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))
    analysis = result.scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    comparison = (await db.execute(select(Comparison).where(Comparison.analysis_id == analysis.id))).scalar_one_or_none()
    if not comparison:
        comparison = Comparison(analysis_id=analysis.id, criteria=[dict(c) for c in DEFAULT_CRITERIA], judgments={})
        db.add(comparison)
        await db.commit()
        await db.refresh(comparison)
    return analysis, comparison


async def _options(analysis: OrgAnalysis, db: AsyncSession) -> List[Dict]:
    base = (await evaluate(analysis, [], db))["baseline"]
    options = [{
        "id": "current", "name": "Current state", "source": "current", "description": "The organization as uploaded",
        "move_count": 0, "figures": {**base, "people_affected_pct": 0.0}, "moves_summary": [],
    }]
    scenarios = (await db.execute(
        select(Scenario).where(Scenario.analysis_id == analysis.id).order_by(Scenario.created_at)
    )).scalars().all()
    for s in scenarios:
        ev = await evaluate(analysis, s.moves or [], db)
        options.append({
            "id": s.id, "name": s.name, "source": s.source or "manual", "description": s.description,
            "move_count": len(s.moves or []),
            "figures": {**ev["scenario"], "people_affected_pct": ev["impact"]["people_affected_pct"]},
            "moves_summary": [m["message"] for m in ev["move_log"] if m["status"] == "applied"],
        })
    return options


async def _payload(analysis: OrgAnalysis, comparison: Comparison, db: AsyncSession) -> Dict:
    options = await _options(analysis, db)
    criteria = comparison.criteria or []
    judgments = comparison.judgments or {}
    return {
        "criteria": criteria,
        "measurable": MEASURABLE,
        "options": options,
        "judgments": judgments,
        "result": score_options(options, criteria, judgments),
        "ai_available": claude_service.is_configured(),
    }


@router.get("")
async def get_comparison(db: AsyncSession = Depends(get_session)):
    analysis, comparison = await _context(db)
    return await _payload(analysis, comparison, db)


@router.put("/criteria")
async def update_criteria(request: CriteriaUpdate, db: AsyncSession = Depends(get_session)):
    problems = validate_criteria(request.criteria)
    if problems:
        raise HTTPException(status_code=400, detail="; ".join(problems))
    analysis, comparison = await _context(db)
    comparison.criteria = request.criteria
    await db.commit()
    return await _payload(analysis, comparison, db)


@router.post("/criteria/reset")
async def reset_criteria(db: AsyncSession = Depends(get_session)):
    analysis, comparison = await _context(db)
    comparison.criteria = [dict(c) for c in DEFAULT_CRITERIA]
    await db.commit()
    return await _payload(analysis, comparison, db)


@router.put("/judgments")
async def update_judgment(request: JudgmentUpdate, db: AsyncSession = Depends(get_session)):
    if request.score is not None and not 1 <= request.score <= 5:
        raise HTTPException(status_code=400, detail="Scores run from 1 (poor) to 5 (strong)")
    analysis, comparison = await _context(db)
    judgments = json.loads(json.dumps(comparison.judgments or {}))  # copy so the JSON change is saved
    cell = judgments.setdefault(request.option_id, {})
    if request.score is None:
        cell.pop(request.criterion_id, None)
    else:
        cell[request.criterion_id] = {"score": request.score, "rationale": request.rationale or "", "source": "user"}
    comparison.judgments = judgments
    await db.commit()
    return await _payload(analysis, comparison, db)


def _suggest_prompt(analysis: OrgAnalysis, options: List[Dict], judged: List[Dict]) -> str:
    """Prompt for AI-suggested judged scores. Aggregates and role titles only — no names."""
    name_to_title = name_map((analysis.raw_data or {}).get("employees", []))
    ai = analysis.ai_analysis or {}
    recs = (ai.get("category_4_recommended_archetypes") or {}).get("recommendations", []) if isinstance(ai.get("category_4_recommended_archetypes"), dict) else []
    archetypes = "\n".join(f"- {r.get('archetype')}: {r.get('why_it_fits', '')[:300]}" for r in recs[:2]) or "None run yet."
    option_lines = []
    for o in options:
        f = o["figures"]
        moves = without_names("; ".join(o["moves_summary"][:12]), name_to_title) or "no changes"
        option_lines.append(
            f"- option_id={o['id']} | {o['name']} (source: {o['source']}): health {f['health_score']}, layers {f['layers']}, "
            f"managers {f['managers']}, spans within benchmark {f['spans_within_benchmark']}, cost {f['total_cost']:,.0f}, "
            f"people affected {f['people_affected_pct']}%. Moves: {moves}"
        )
    criteria_lines = "\n".join(f"- criterion_id={c['id']}: {c['name']} — {c.get('description', '')}" for c in judged)
    return f"""You are an organization design expert helping compare structural options. Score each option on each criterion from 1 (poor) to 5 (strong).

STRATEGY CONTEXT (from the designer):
{analysis.strategy_context or 'Not provided.'}

DESIGN CRITERIA (from the designer):
{analysis.design_criteria or 'Not provided.'}

RECOMMENDED ARCHETYPES FROM EARLIER ANALYSIS:
{archetypes}

OPTIONS (aggregates and design moves; no personal names):
{chr(10).join(option_lines)}

CRITERIA TO SCORE:
{criteria_lines}

Rules:
- Score relative to the other options; the current state is the reference.
- Rationale: one or two sentences citing the specific moves or figures that justify the score.
- evidence_class: OBSERVABLE if the score rests on the figures/moves above, PERCEPTUAL if on the designer's strategy text, MODEL-INFERRED if on general org design knowledge.
- confidence: High/Medium/Low; MODEL-INFERRED is capped at Medium.

Return only JSON:
```json
{{"suggestions": [{{"option_id": "...", "criterion_id": "...", "score": 3, "rationale": "...", "evidence_class": "OBSERVABLE", "confidence": "Medium"}}]}}
```"""


@router.post("/suggest")
async def suggest_judgments(db: AsyncSession = Depends(get_session)):
    """AI-suggested scores for judged criteria that the designer has not scored yet."""
    if not claude_service.is_configured():
        raise HTTPException(status_code=400, detail="Claude API key not configured. Please set it in Settings.")
    analysis, comparison = await _context(db)
    options = await _options(analysis, db)
    judged = [c for c in (comparison.criteria or []) if c.get("kind") == "judged"]
    if not judged:
        raise HTTPException(status_code=400, detail="There are no judged criteria to score.")

    service = AIAnalysisService(api_key=claude_service.api_key)
    try:
        text, _ = run_analysis(service.client, _suggest_prompt(analysis, options, judged), max_tokens=16000)
    except AnalysisRefused as e:
        raise HTTPException(status_code=422, detail=str(e))
    parsed = service._parse_text(text)

    valid_options = {o["id"] for o in options}
    valid_criteria = {c["id"] for c in judged}
    judgments = json.loads(json.dumps(comparison.judgments or {}))
    added = 0
    for s in parsed.get("suggestions", []) or []:
        oid, cid = s.get("option_id"), s.get("criterion_id")
        try:
            score = float(s.get("score"))
        except (TypeError, ValueError):
            continue
        if oid not in valid_options or cid not in valid_criteria or not 1 <= score <= 5:
            continue
        cell = judgments.setdefault(oid, {})
        if cell.get(cid, {}).get("source") == "user":
            continue  # never overwrite the designer's own score
        cell[cid] = {
            "score": score, "rationale": s.get("rationale", ""), "source": "ai",
            "evidence_class": s.get("evidence_class"), "confidence": s.get("confidence"),
        }
        added += 1
    comparison.judgments = judgments
    await db.commit()
    payload = await _payload(analysis, comparison, db)
    payload["suggestions_added"] = added
    return payload
