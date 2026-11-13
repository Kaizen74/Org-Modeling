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
from ..services import compass_roles as roles
from ..services.metrics_store import ensure_metrics
from ..services.privacy import name_map, without_names
from .comparison import _context as comparison_context, _payload as comparison_payload

router = APIRouter(prefix="/api/v1/compass", tags=["compass"])


class ImportRequest(BaseModel):
    packet: Dict
    link_country: Optional[str] = None  # where to link it when its country isn't in the file ("" = whole organization)
    replace_criteria: bool = False  # only needed when the preview says "ask"
    replace_strategy: bool = False


class PreviewRequest(BaseModel):
    packet: Dict
    link_country: Optional[str] = None


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
    country: str = ""  # "" = a whole-organization finding; else a finding in that country's file


class RelatesIn(BaseModel):
    ref: str
    relates_to: List[str] = []
    country: str = ""


async def latest_analysis(db: AsyncSession) -> OrgAnalysis:
    analysis = (await db.execute(select(OrgAnalysis).order_by(OrgAnalysis.created_at.desc()).limit(1))).scalar_one_or_none()
    if not analysis or not (analysis.raw_data or {}).get("employees"):
        raise HTTPException(status_code=404, detail="No org data found. Please upload a CSV first.")
    return analysis


async def get_engagement(analysis: OrgAnalysis, db: AsyncSession, create: bool = False, country: str = "") -> Optional[Engagement]:
    """The link for one country; country "" is the whole organization (hypotheses, grades, strategy draft)."""
    eng = (await db.execute(select(Engagement).where(
        Engagement.analysis_id == analysis.id, Engagement.country == country))).scalar_one_or_none()
    if not eng and create:
        eng = Engagement(analysis_id=analysis.id, country=country, hypotheses=[], hypothesis_seq=0, grades={},
                         relates={}, role_matches={}, role_match_log=[], role_reasons={})
        db.add(eng)
        await db.commit()
        await db.refresh(eng)
    return eng


async def linked(analysis: OrgAnalysis, db: AsyncSession) -> List[Engagement]:
    """Every link that has a Compass packet, in the order they were imported."""
    rows = (await db.execute(select(Engagement).where(Engagement.analysis_id == analysis.id))).scalars().all()
    return sorted([r for r in rows if r.packet], key=lambda r: r.imported_at or datetime.min)


def file_countries(analysis: OrgAnalysis) -> List[str]:
    return sorted({e.get("country") for e in (analysis.raw_data or {}).get("employees", []) if e.get("country")})


def engagement_header(links: List[Engagement]) -> Optional[Dict]:
    """
    What the header and exports show: the whole-organization packet if one is
    linked, else the frame (its key is the linked key that starts all others).
    """
    if not links:
        return None
    whole = next((l for l in links if not l.country), None)
    if whole:
        return {**cs.engagement_summary(whole.packet), "countries": [l.country for l in links if l.country]}
    first = cs.engagement_summary(links[0].packet)
    return {**first, "key": cs.frame_key([l.key for l in links]), "country": "",
            "countries": [l.country for l in links if l.country]}


def all_refs(links: List[Engagement]) -> List[Dict]:
    """Compass IDs across every linked packet (the same frame gives the same IDs)."""
    out, seen = [], set()
    for l in links:
        for r in cs.known_refs(l.packet):
            if r["ref"] not in seen:
                seen.add(r["ref"])
                out.append(r)
    return out


async def findings_for(analysis: OrgAnalysis, eng: Optional[Engagement], db: AsyncSession) -> List[Dict]:
    metrics = await ensure_metrics(analysis, db)
    _, comparison = await comparison_context(db)
    comp = await comparison_payload(analysis, comparison, db)
    findings = cs.collect_findings(
        metrics, analysis.ai_analysis or {}, comp,
        (eng.hypotheses if eng else None) or [], (eng.grades if eng else None) or {}, (eng.relates if eng else None) or {},
    )
    return _scrubbed(analysis, findings)


def _scrubbed(analysis: OrgAnalysis, findings: List[Dict]) -> List[Dict]:
    """People stay as counts or job titles in anything that leaves the app: no names, no Employee IDs."""
    employees = analysis.raw_data["employees"]
    names = name_map(employees)
    # Purely numeric or very short IDs can't identify anyone in a sentence, and would match figures
    ids = sorted({str(e.get("employee_id") or "") for e in employees}, key=len, reverse=True)
    ids = [i for i in ids if len(i) >= 3 and not i.isdigit() and i not in names]
    for f in findings:
        for field in ("title", "detail", "source_note"):
            text = without_names(f[field] or "", names)
            for i in ids:
                text = re.sub(rf"(?<![\w-]){re.escape(i)}(?![\w-])", "[an employee]", text)
            f[field] = text
    return findings


async def link_findings(analysis: OrgAnalysis, country: str, db: AsyncSession) -> Dict:
    """One country's file: baseline on that country's people and why its Compass roles exist or are missing."""
    link = await get_engagement(analysis, db, country=country)
    if not country or not link or not link.packet:
        raise HTTPException(status_code=404, detail=f"No Compass file is linked to {cs.link_label(country)}.")
    metrics = await ensure_metrics(analysis, db)
    row = next((r for r in metrics.get("country_analysis") or [] if r["country"] == country), None)
    view = await _roles_view(analysis, db)
    cells, left_out = [], 0
    for r in view["roles"]:
        cell = next((c for c in r["cells"] if c["country"] == country), None)
        if not cell or not cell["in_packet"]:
            continue
        if cell["holders"] is None:
            left_out += 1  # not matched to a job title yet: neither existing nor absent
            continue
        cells.append({"ref": r["ref"], "title": r["title"], "holders": cell["holders"], "reason": cell["reason"],
                      "compass_status": cell["compass_status"], "status_confirmed": cell["status_confirmed"]})
    clusters = {r["ref"]: r["cluster_ref"] for r in view["roles"]}
    findings = cs.country_findings(country, row, cells, clusters, link.grades or {}, link.relates or {})
    return {"link": {"country": country, "key": link.key, "label": cs.link_label(country)},
            "findings": _scrubbed(analysis, findings), "left_out_not_matched": left_out}


@router.get("/findings")
async def get_link_findings(link: str = "", db: AsyncSession = Depends(get_session)):
    """Findings for one link: a country's file, or ("") the whole organization's."""
    analysis = await latest_analysis(db)
    if not link:
        whole = await get_engagement(analysis, db)
        header = engagement_header(await linked(analysis, db))
        return {"link": {"country": "", "key": header["key"] if header else None, "label": cs.link_label("")},
                "findings": await findings_for(analysis, whole, db), "left_out_not_matched": 0}
    return await link_findings(analysis, link, db)


async def _state(analysis: OrgAnalysis, eng: Optional[Engagement], db: AsyncSession) -> Dict:
    """`eng` is the whole-organization link."""
    links = await linked(analysis, db)
    contexts = {l.country: cs.packet_context(l.packet) for l in links}
    return {
        "engagement": engagement_header(links),
        "links": [{"country": l.country, "label": cs.link_label(l.country), "key": l.key,
                   "imported_at": l.imported_at.isoformat() if l.imported_at else None,
                   "ready": (l.packet.get("readiness") or {}).get("ready", True)} for l in links],
        "file_countries": file_countries(analysis),
        "imported_at": links[-1].imported_at.isoformat() if links and links[-1].imported_at else None,
        "strategy_draft": (eng.strategy_draft if eng else None) or "",
        "contexts": contexts,
        # The whole organization's context, else the first linked country's
        "context": contexts.get("") or (contexts[links[0].country] if links else cs.packet_context(None)),
        "refs": all_refs(links),
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


async def _preview(packet: Dict, link_country: Optional[str], analysis: OrgAnalysis, db: AsyncSession) -> Dict:
    whole = await get_engagement(analysis, db)
    _, comparison = await comparison_context(db)
    current_strategy = (whole.strategy_draft if whole else None) or analysis.strategy_context or ""
    links = {l.country: l.packet for l in await linked(analysis, db)}
    return cs.preview_import(packet, comparison.criteria or [], comparison.judgments or {}, current_strategy,
                             file_countries=file_countries(analysis), chosen_link=link_country, links=links)


@router.post("/preview")
async def preview(request: PreviewRequest, db: AsyncSession = Depends(get_session)):
    """What importing this file would create or change. Applies nothing."""
    analysis = await latest_analysis(db)
    return await _preview(request.packet, request.link_country, analysis, db)


@router.post("/import")
async def import_packet(request: ImportRequest, db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    plan = await _preview(request.packet, request.link_country, analysis, db)
    if not plan["ok"]:
        raise HTTPException(status_code=400, detail=" ".join(plan["errors"]))
    if plan["country"]["needs_choice"]:
        raise HTTPException(status_code=400, detail=plan["country"]["note"])
    target = plan["country"]["target"]
    whole = await get_engagement(analysis, db, create=True)
    link = whole if target == "" else await get_engagement(analysis, db, create=True, country=target)

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
    elif action == "different":
        applied.append("Comparison criteria kept from the first Compass file (this file's differ)")

    action = plan["strategy"]["action"]
    if action == "set" or (action == "ask" and request.replace_strategy):
        whole.strategy_draft = plan["strategy"]["incoming"]
        applied.append("Strategy text pre-filled on the archetype page")
    elif action == "ask":
        applied.append("Your strategy text was kept")
    elif action == "different":
        applied.append("Strategy text kept from the first Compass file (this file's differs)")

    link.key = request.packet["engagement"]["key"]
    link.packet = request.packet
    link.imported_at = datetime.utcnow()
    # Reasons for roles this packet no longer has would point nowhere
    role_refs = {r.get("ref") for r in request.packet.get("roles") or []}
    link.role_reasons = {k: v for k, v in (link.role_reasons or {}).items() if k in role_refs}
    await db.flush()
    # Links on whole-organization findings to IDs no linked packet has would point nowhere
    valid = {r["ref"] for r in all_refs(await linked(analysis, db))}
    whole.relates = {k: [r for r in v if r in valid] for k, v in (whole.relates or {}).items()}
    await db.commit()
    applied.append(f"{'Replaced the link' if plan['replaces'] else 'Linked'} {cs.link_label(target)} to engagement {link.key}")
    return {"applied": applied, "warnings": plan["warnings"], **await _state(analysis, whole, db)}


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
    eng = await _link_for_update(analysis, request.country, db)
    grades = {k: v for k, v in (eng.grades or {}).items() if k != request.ref}
    if request.grade:
        grades[request.ref] = request.grade
    eng.grades = grades
    await db.commit()
    return await _after_update(analysis, request.country, eng, db)


async def _link_for_update(analysis: OrgAnalysis, country: str, db: AsyncSession) -> Engagement:
    if not country:
        return await get_engagement(analysis, db, create=True)
    link = await get_engagement(analysis, db, country=country)
    if not link or not link.packet:
        raise HTTPException(status_code=404, detail=f"No Compass file is linked to {cs.link_label(country)}.")
    return link


async def _after_update(analysis: OrgAnalysis, country: str, eng: Engagement, db: AsyncSession) -> Dict:
    return await _state(analysis, eng, db) if not country else await link_findings(analysis, country, db)


@router.put("/relates")
async def set_relates(request: RelatesIn, db: AsyncSession = Depends(get_session)):
    """Attach Compass IDs to a finding. Only IDs from the imported packet are accepted."""
    analysis = await latest_analysis(db)
    eng = await _link_for_update(analysis, request.country, db)
    valid = {r["ref"] for r in all_refs(await linked(analysis, db))}
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
    return await _after_update(analysis, request.country, eng, db)


async def _return(db: AsyncSession, link: str = ""):
    analysis = await latest_analysis(db)
    if link:
        data = await link_findings(analysis, link, db)
        key = data["link"]["key"]
        ret = cs.build_return(key, data["findings"], country=link)
        return ret, re.sub(r"[^A-Za-z0-9_-]+", "_", key or link) + "_compass_return"
    eng = await get_engagement(analysis, db)
    header = engagement_header(await linked(analysis, db))
    key = header["key"] if header else None
    ret = cs.build_return(key, await findings_for(analysis, eng, db))
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", (key or analysis.name or "org")) + "_org_modeling_return"
    return ret, stem


@router.get("/return")
async def return_file(link: str = "", db: AsyncSession = Depends(get_session)):
    """compass-return v1.0: this app's findings for one link (a country, or "" for the whole organization)."""
    ret, stem = await _return(db, link)
    return JSONResponse(ret, headers={"Content-Disposition": f'attachment; filename="{stem}.json"'})


@router.get("/return.txt", response_class=PlainTextResponse)
async def return_text(link: str = "", db: AsyncSession = Depends(get_session)):
    ret, stem = await _return(db, link)
    return PlainTextResponse(cs.return_as_text(ret), headers={"Content-Disposition": f'inline; filename="{stem}.txt"'})


# ------------------------------------------------------------------ Compass roles by country

class RoleMatchIn(BaseModel):
    ref: str
    titles: Optional[List[str]] = None  # [] = no job title in this file; None = back to "not matched yet"


class RoleReasonIn(BaseModel):
    ref: str
    country: str
    reason_class: str = "unknown"
    text: str = ""
    compared_with: str = ""
    grade: Optional[str] = None


async def _roles_view(analysis: OrgAnalysis, db: AsyncSession) -> Dict:
    whole = await get_engagement(analysis, db)
    links = [{"country": l.country, "key": l.key, "packet": l.packet, "reasons": l.role_reasons or {}}
             for l in await linked(analysis, db)]
    view = roles.build_roles_view(analysis.raw_data["employees"], links, (whole.role_matches if whole else None) or {})
    view["match_log"] = ((whole.role_match_log if whole else None) or [])[-20:]
    view["grades"] = cs.GRADES
    view["file_countries"] = file_countries(analysis)
    return view


@router.get("/roles")
async def get_roles(db: AsyncSession = Depends(get_session)):
    """Compass anchor roles with holders, Compass status and reasons per linked country."""
    analysis = await latest_analysis(db)
    return await _roles_view(analysis, db)


def _set_match(whole: Engagement, ref: str, titles: Optional[List[str]]):
    matches = dict(whole.role_matches or {})
    before = matches.get(ref)
    if titles is None:
        matches.pop(ref, None)
    else:
        matches[ref] = list(dict.fromkeys(t.strip() for t in titles if t.strip()))
    if matches.get(ref) == before:
        return
    whole.role_matches = matches
    # Every change to a match is kept, so a head-count can be traced back
    whole.role_match_log = [*(whole.role_match_log or []),
                            {"at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "ref": ref, "before": before, "after": matches.get(ref)}]


@router.put("/roles/match")
async def set_role_match(request: RoleMatchIn, db: AsyncSession = Depends(get_session)):
    analysis = await latest_analysis(db)
    view = await _roles_view(analysis, db)
    if request.ref not in {r["ref"] for r in view["roles"]}:
        raise HTTPException(status_code=404, detail=f"{request.ref} is not a role in the linked Compass files.")
    unknown = [t for t in request.titles or [] if t.strip() not in view["file_titles"]]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Not a job title in the org file: {', '.join(unknown)}")
    whole = await get_engagement(analysis, db, create=True)
    _set_match(whole, request.ref, request.titles)
    await db.commit()
    return await _roles_view(analysis, db)


@router.post("/roles/accept-exact")
async def accept_exact_matches(db: AsyncSession = Depends(get_session)):
    """Confirm every exact title match for roles not matched yet. Close matches still need a person."""
    analysis = await latest_analysis(db)
    view = await _roles_view(analysis, db)
    whole = await get_engagement(analysis, db, create=True)
    accepted = 0
    for r in view["roles"]:
        exact = [s["title"] for s in r["suggestions"] if s["kind"] == "exact"]
        if not r["match_confirmed"] and exact:
            _set_match(whole, r["ref"], exact)
            accepted += 1
    await db.commit()
    return {"accepted": accepted, **await _roles_view(analysis, db)}


@router.put("/roles/reason")
async def set_role_reason(request: RoleReasonIn, db: AsyncSession = Depends(get_session)):
    """Why a role exists, is thin or is missing in one country. The designer's; the AI never sets it."""
    if request.reason_class not in roles.REASON_CLASSES:
        raise HTTPException(status_code=400, detail=f"Reason must be one of: {', '.join(roles.REASON_LABELS.values())}")
    if request.grade is not None and request.grade not in cs.GRADES:
        raise HTTPException(status_code=400, detail=f"Grade must be one of: {', '.join(cs.GRADES)}")
    analysis = await latest_analysis(db)
    link = await get_engagement(analysis, db, country=request.country)
    if not link or not link.packet:
        raise HTTPException(status_code=404, detail=f"No Compass file is linked to {cs.link_label(request.country)}.")
    if request.ref not in {r.get("ref") for r in link.packet.get("roles") or []}:
        raise HTTPException(status_code=404, detail=f"{request.ref} is not a role in {cs.link_label(request.country)}'s Compass file.")
    compared = request.compared_with.strip()
    if compared and (compared == request.country or compared not in file_countries(analysis)):
        raise HTTPException(status_code=400, detail="'Compared with' must be another country in the org file.")
    reasons = dict(link.role_reasons or {})
    reasons[request.ref] = {"reason_class": request.reason_class, "text": request.text.strip(),
                            "compared_with": compared, "grade": request.grade}
    link.role_reasons = reasons
    await db.commit()
    return await _roles_view(analysis, db)
