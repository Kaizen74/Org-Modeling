"""
Shared language with the other workflow apps.

- Reads a `compass-handoff` v1.x file written by Capability Compass.
- Maps this app's evidence classes to the shared grades (a suggested default
  the assessor can change; never computed from a count of sources).
- Builds the `compass-return` v1.0 findings file.

Compass IDs are stored and shown exactly as received. The only ID this app
mints is `Hn` (operating-model hypothesis); its other findings carry
descriptive references such as `baseline.layers`.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Tuple

from .comparison_service import DEFAULT_CRITERIA, validate_criteria

HANDOFF_FORMAT = "compass-handoff"
RETURN_FORMAT = "compass-return"
SOURCE_APP = "org-modeling"

GRADES = ["confirmed", "indicated", "hypothesis"]
GRADE_LABELS = {"confirmed": "Confirmed", "indicated": "Indicated", "hypothesis": "Hypothesis"}
# Suggested default only: the grade is the assessor's judgement
EVIDENCE_TO_GRADE = {"OBSERVABLE": "confirmed", "PERCEPTUAL": "indicated", "MODEL-INFERRED": "hypothesis"}
HYPOTHESIS_STATUSES = ["open", "supported", "refuted"]
FINDING_KINDS = ["structural_baseline", "role_reason", "work_activity", "hypothesis", "option_score"]
# Optional fields a finding carries when they apply (country files)
OPTIONAL_FINDING_FIELDS = ("topic", "reason_class", "compared_with")


def suggested_grade(evidence_class: Optional[str]) -> Optional[str]:
    return EVIDENCE_TO_GRADE.get(str(evidence_class or "").strip().upper())


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:48] or "item"


# ---------------------------------------------------------------- reading the packet

def known_refs(packet: Dict) -> List[Dict]:
    """Every Compass ID in the packet, with a label, in the order a reader would look for them."""
    out: List[Dict] = []

    def add(ref, label):
        if ref and not any(r["ref"] == ref for r in out):
            out.append({"ref": str(ref), "label": str(label or "")})

    for c in packet.get("clusters") or []:
        add(c.get("ref"), c.get("name"))
        for cell in c.get("cells") or []:
            add(cell.get("ref"), f"{c.get('name')} · {cell.get('lens')}")
    for p in packet.get("pilots") or []:
        add(p.get("ref"), p.get("name"))
    for lv in packet.get("levers") or []:
        add(lv.get("ref"), lv.get("name"))
    for r in packet.get("roles") or []:
        add(r.get("ref"), r.get("title"))
    for s in packet.get("signals") or []:
        add(s.get("ref"), s.get("title") or s.get("name"))
    charter = packet.get("charter") or {}
    for p in charter.get("principles") or []:
        add(p.get("ref"), p.get("principle"))
    for c in charter.get("reference_model") or []:
        add(c.get("ref"), c.get("name"))
    for c in charter.get("design_criteria") or []:
        add(c.get("ref"), c.get("name"))
    for g in charter.get("leapfrog_gate") or []:
        add(g.get("ref"), g.get("test"))
    for d in charter.get("decision_log") or []:
        add(d.get("ref"), d.get("decision"))
    return out


def validate_packet(packet) -> Tuple[List[str], List[str]]:
    """(errors that stop the import, warnings that don't) in plain language."""
    if not isinstance(packet, dict):
        return ["This is not a Capability Compass hand-off file (it is not a JSON object)."], []
    errors, warnings = [], []
    if packet.get("format") != HANDOFF_FORMAT:
        found = packet.get("format")
        errors.append(
            "This is not a Capability Compass hand-off file: its format is "
            + (f"'{found}'" if found else "missing") + f", expected '{HANDOFF_FORMAT}'."
        )
        return errors, warnings
    version = str(packet.get("format_version") or "")
    if not version.startswith("1."):
        errors.append(f"This hand-off file is version '{version or 'unknown'}'; this app reads version 1.x.")
    if not str((packet.get("engagement") or {}).get("key") or "").strip():
        errors.append("The file has no engagement key, so its IDs could not be traced back to an engagement.")

    cluster_refs = {c.get("ref") for c in packet.get("clusters") or []}
    for section, what in (("levers", "lever"), ("roles", "role"), ("pilots", "pilot"), ("exclusions", "exclusion")):
        for item in packet.get(section) or []:
            ref = item.get("cluster_ref")
            if ref and ref not in cluster_refs:
                warnings.append(
                    f"The {what} '{item.get('ref') or item.get('name') or item.get('title')}' points to "
                    f"'{ref}', which is not a cluster in this file."
                )
    for lens in ((packet.get("for_apps") or {}).get("org_modeling") or {}).get("structure_lens") or []:
        ref = str(lens.get("ref") or "")
        if ref.split(".")[0] not in cluster_refs:
            warnings.append(f"The structure finding '{ref}' points to a cluster that is not in this file.")

    readiness = packet.get("readiness") or {}
    if readiness.get("ready") is False:
        open_items = "; ".join(_readiness_item(o) for o in readiness.get("open") or [])
        warnings.append("The Compass marks this hand-off as not ready" + (f": {open_items}" if open_items else "."))
    return errors, warnings


def _readiness_item(item) -> str:
    """One open readiness item in plain words (the Compass writes either text or {check, level, detail})."""
    if not isinstance(item, dict):
        return str(item)
    text = str(item.get("check") or "").strip()
    if item.get("detail"):
        text += f" ({item['detail']})" if text else str(item["detail"])
    if item.get("level") == "must":
        text += " — required"
    return text


def packet_criteria(packet: Dict) -> List[Dict]:
    """The comparison criteria in the packet, limited to the fields this app's criteria use (ref kept)."""
    keep = ("id", "ref", "name", "kind", "weight", "metric", "better", "description")
    block = (packet.get("for_apps") or {}).get("org_modeling") or {}
    return [{k: c[k] for k in keep if k in c} for c in block.get("design_criteria") or []]


def packet_strategy(packet: Dict) -> str:
    return str(((packet.get("for_apps") or {}).get("org_modeling") or {}).get("strategy_text") or "").strip()


def packet_context(packet: Optional[Dict]) -> Dict:
    """Read-only 'What the Compass found': evidence to test, never a score."""
    if not packet:
        return {"structure_lens": [], "clusters": []}
    block = (packet.get("for_apps") or {}).get("org_modeling") or {}
    return {
        "structure_lens": [
            {k: lens.get(k) for k in ("ref", "cluster", "level", "status", "grade")}
            for lens in block.get("structure_lens") or []
        ],
        "clusters": [
            {k: c.get(k) for k in ("ref", "name", "priority_move", "avg_level", "trajectory", "economic_weight_pct")}
            for c in packet.get("clusters") or []
        ],
    }


def engagement_summary(packet: Optional[Dict]) -> Optional[Dict]:
    if not packet:
        return None
    e = packet.get("engagement") or {}
    return {
        "key": e.get("key"), "name": e.get("name"), "organisation": e.get("organisation"),
        "country": packet_country(packet),
        "industry": e.get("industry"), "scope": e.get("scope"),
        "generated_at": packet.get("generated_at"), "format_version": packet.get("format_version"),
    }


def _same_criteria(a: List[Dict], b: List[Dict]) -> bool:
    core = lambda cs: [{k: c.get(k) for k in ("id", "name", "kind", "weight", "metric", "better")} for c in cs or []]
    return core(a) == core(b)


def packet_country(packet: Dict) -> str:
    """The country a packet's workspace covers ("" for a group-wide workspace)."""
    return str((packet.get("engagement") or {}).get("country") or "").strip()


def match_country(value: str, file_countries: List[str]) -> Optional[str]:
    """The file's spelling of a country, matched without regard to case; None if absent."""
    v = (value or "").strip().lower()
    return next((c for c in file_countries if c.lower() == v), None) if v else None


def frame_refs(packet: Dict) -> Tuple[set, set]:
    return ({c.get("ref") for c in packet.get("clusters") or []}, {r.get("ref") for r in packet.get("roles") or []})


def frame_key(keys: List[str]) -> str:
    """
    The frame's key: country keys are the frame key plus a country code
    (MERIDIAN, MERIDIANBE, MERIDIANCA), so it is the linked key that starts all
    the others. Falls back to the first key when no key starts the others.
    """
    keys = [k for k in keys if k]
    if not keys:
        return ""
    for k in sorted(keys, key=len):
        if all(o.startswith(k) for o in keys):
            return k
    return keys[0]


def link_label(country: str) -> str:
    return country or "Whole organization"


def preview_import(packet: Dict, current_criteria: List[Dict], judgments: Dict, current_strategy: str,
                   *, file_countries: Optional[List[str]] = None, chosen_link: Optional[str] = None,
                   links: Optional[Dict[str, Dict]] = None) -> Dict:
    """
    What an import would create or change. Applies nothing.

    `links` maps each already-linked country ("" = whole organization) to its
    packet. A packet links to the country it names, matched to the file's
    Country column; when there is no match the designer picks one
    (`chosen_link`, "" for the whole organization). Design criteria and
    strategy text come from the first packet linked; a later packet never
    overwrites them.
    """
    errors, warnings = validate_packet(packet)
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}
    links = links or {}
    file_countries = file_countries or []

    # Which link this packet goes to
    named = packet_country(packet)
    matched = match_country(named, file_countries)
    if chosen_link is not None:
        if chosen_link and chosen_link not in file_countries:
            return {"ok": False, "errors": [f"'{chosen_link}' is not a country in the uploaded org file."], "warnings": warnings}
        target, needs_choice = chosen_link, False
    elif matched:
        target, needs_choice = matched, False
    elif not named and not file_countries:
        target, needs_choice = "", False  # group-wide packet, file without countries: the whole organization
    else:
        target, needs_choice = None, True
    if needs_choice:
        note = (f"The file names the country '{named}', which is not in the org file's Country column." if named
                else "The file does not name a country.")
        country = {"named": named, "matched": None, "target": None, "needs_choice": True,
                   "choices": file_countries + [""], "note": note + " Choose where to link it."}
    else:
        country = {"named": named, "matched": matched, "target": target, "needs_choice": False,
                   "choices": file_countries + [""],
                   "note": f"Links to {link_label(target)}." + (" Chosen by you." if chosen_link is not None and target != matched else "")}

    replaces = target is not None and target in links
    if replaces:
        old = (links[target].get("engagement") or {}).get("key")
        warnings.append(f"A Compass file is already linked to {link_label(target)} ({old}); importing will replace it.")

    others = {c: p for c, p in links.items() if c != target}
    clusters, roles = frame_refs(packet)
    for c, other in others.items():
        oc, orl = frame_refs(other)
        if oc != clusters or orl != roles:
            warnings.append(
                f"This file comes from a different frame than the one linked to {link_label(c)}: "
                "its cluster or role IDs differ, so these IDs may not mean the same thing."
            )
            break

    incoming = packet_criteria(packet)
    problems = validate_criteria(incoming) if incoming else []
    strategy = packet_strategy(packet)
    current_strategy = (current_strategy or "").strip()
    if others:
        # A later packet never overwrites criteria or strategy; say whether they agree
        criteria_action = "same" if _same_criteria(incoming, current_criteria) else "different"
        criteria_note = ("Your comparison criteria already match the file." if criteria_action == "same" else
                         "The file's design criteria differ from yours. They are not used: criteria come from the first Compass file linked.")
        strategy_action = "same" if not strategy or strategy == current_strategy else "different"
        strategy_note = ("The strategy text matches." if strategy_action == "same" else
                         "The file's strategy text differs from yours. It is not used: strategy comes from the first Compass file linked.")
    else:
        scored = sum(len(v or {}) for v in (judgments or {}).values())
        if not incoming:
            criteria_action, criteria_note = "none", "The file carries no design criteria; yours stay as they are."
        elif problems:
            criteria_action, criteria_note = "invalid", "The file's design criteria can't be used; yours stay as they are."
        elif _same_criteria(incoming, current_criteria):
            criteria_action, criteria_note = "same", "Your comparison criteria already match the file."
        elif _same_criteria(current_criteria, DEFAULT_CRITERIA) and not scored:
            criteria_action, criteria_note = "set", "Replaces the app's starting criteria, which you have not changed."
        else:
            criteria_action = "ask"
            criteria_note = "You have changed the comparison criteria" + (
                f" and scored {scored} cell{'s' if scored != 1 else ''}" if scored else "") + \
                ". Replacing them is your choice; scores for criteria that disappear stop counting."
        if not strategy:
            strategy_action, strategy_note = "none", "The file carries no strategy text."
        elif strategy == current_strategy:
            strategy_action, strategy_note = "same", "The strategy text already matches the file."
        elif not current_strategy:
            strategy_action, strategy_note = "set", "Pre-fills the strategy box on the archetype page; you can edit it before running."
        else:
            strategy_action, strategy_note = "ask", "You already have strategy text. Replacing it is your choice."

    context = packet_context(packet)
    return {
        "ok": True, "errors": [], "warnings": warnings,
        "engagement": engagement_summary(packet),
        "country": country,
        "replaces": replaces,
        "criteria": {"action": criteria_action, "note": criteria_note, "incoming": incoming,
                     "problems": problems, "current_count": len(current_criteria or [])},
        "strategy": {"action": strategy_action, "note": strategy_note, "incoming": strategy,
                     "current": current_strategy},
        "context": {"structure_findings": len(context["structure_lens"]), "clusters": len(context["clusters"]),
                    "ids": len(known_refs(packet))},
    }


# ---------------------------------------------------------------- findings and the return file

def _work_findings(wa: Dict) -> List[Dict]:
    out = []
    groups = (
        ("duplication", "Duplicated activity", (wa.get("activity_duplication") or {}).get("duplications"), "activity", "indicated"),
        ("missing", "Missing activity", (wa.get("missing_activities") or {}).get("gaps"), "activity", "hypothesis"),
        ("handoff", "Hand-off gap", (wa.get("coordination_gaps") or {}).get("gaps"), "handoff_point", "indicated"),
    )
    for key, label, items, title_field, default in groups:
        seen = set()
        for item in items or []:
            if not isinstance(item, dict) or not item.get(title_field):
                continue
            ref = f"work.{key}.{slug(item[title_field])}"
            if ref in seen:
                continue
            seen.add(ref)
            detail = item.get("business_impact") or item.get("business_risk") or item.get("current_state") or ""
            where = ", ".join(dict.fromkeys(
                item.get("affected_departments") or [d for d in (item.get("from_department"), item.get("to_department")) if d]))
            out.append({
                "ref": ref, "kind": "work_activity", "title": f"{label}: {item[title_field]}",
                "detail": "; ".join(x for x in (detail, f"Departments: {where}" if where else "") if x),
                "figure": "",
                "evidence_class": item.get("evidence_class"),
                "suggested_grade": suggested_grade(item.get("evidence_class")) or default,
                "source_note": item.get("evidence") or item.get("confidence_rationale")
                or ("AI reading of the uploaded role descriptions" if default == "indicated" else "AI comparison with typical practice; not in the uploaded data"),
            })
    return out


def collect_findings(metrics: Dict, ai_analysis: Dict, comparison: Optional[Dict], hypotheses: List[Dict],
                     grades: Dict, relates: Dict) -> List[Dict]:
    """
    Every finding this app can send back, with its suggested grade, the
    assessor's grade where set, and the Compass IDs attached to it.
    Counts and figures only — no personal names.
    """
    findings: List[Dict] = []
    layers = metrics.get("layer_analysis") or {}
    span = metrics.get("span_of_control") or {}
    health = metrics.get("health_indicators") or {}
    vs = span.get("distribution_vs_benchmark") or {}
    managers = sum(vs.values())
    people = metrics.get("total_employees", 0)
    if people:
        base = {"kind": "structural_baseline", "evidence_class": "OBSERVABLE", "suggested_grade": "confirmed",
                "source_note": f"Computed from the uploaded org file ({people} people)"}
        findings += [
            {**base, "ref": "baseline.layers", "title": "Layers in the reporting chain",
             "detail": f"Counted from who reports to whom; the Level column declares {layers.get('declared_layers', 0)}.",
             "figure": f"{layers.get('total_layers', 0)} layers"},
            {**base, "ref": "baseline.spans", "title": "Managers within their span benchmark",
             "detail": f"{vs.get('Below benchmark', 0)} below, {vs.get('Above benchmark', 0)} above; "
                       f"{span.get('single_report_managers', 0)} managers have one direct report. Median span {span.get('median_span', 0)}.",
             "figure": f"{vs.get('Within benchmark', 0)} of {managers} managers"},
            {**base, "ref": "baseline.health", "title": "Structural health score",
             "detail": "Weighted from span fit, layers for this size, manager ratio and single-report managers.",
             "figure": f"{health.get('health_score', 0)} out of 100"},
        ]

    findings += _work_findings((ai_analysis or {}).get("work_activities_analysis") or {})

    for h in hypotheses or []:
        findings.append({
            "ref": h["ref"], "kind": "hypothesis", "title": h.get("statement", ""),
            "detail": "; ".join(x for x in (
                f"Refuted by: {h['refuted_by']}" if h.get("refuted_by") else "",
                f"Status: {h.get('status', 'open')}", h.get("note") or "") if x),
            "figure": "", "evidence_class": None, "suggested_grade": "hypothesis",
            "source_note": "Operating-model hypothesis written by the designer; test it against process evidence",
        })

    if comparison:
        criteria = comparison.get("criteria") or []
        result = comparison.get("result") or {}
        judged = [c["id"] for c in criteria if c.get("kind") == "judged"]
        used = set()
        for o in comparison.get("options") or []:
            total = (result.get("totals") or {}).get(o["id"])
            if total is None:
                continue
            ref = "option.current" if o["id"] == "current" else f"option.{slug(o['name'])}"
            while ref in used:
                ref += "-2"
            used.add(ref)
            cells = (result.get("cells") or {}).get(o["id"]) or {}
            per = [f"{c.get('ref') or c['name']} {cells[c['id']]:g}" for c in criteria if cells.get(c["id"]) is not None]
            missing = (result.get("missing") or {}).get(o["id"]) or []
            own = (comparison.get("judgments") or {}).get(o["id"]) or {}
            all_mine = bool(judged) and all((own.get(cid) or {}).get("source") == "user" for cid in judged)
            findings.append({
                "ref": ref, "kind": "option_score", "title": f"Option: {o['name']}",
                "detail": "Score per criterion (0-100): " + "; ".join(per)
                          + (f". {len(missing)} judged score(s) missing, so the total is provisional" if missing else ""),
                "figure": f"{total:g} out of 100 (weighted total)",
                "evidence_class": None,
                # Structural fit is a hypothesis until process evidence tests it
                "suggested_grade": "indicated" if all_mine and not missing else "hypothesis",
                "source_note": "Measured criteria from the org file; judged criteria scored "
                               + ("by the designer" if all_mine else "partly by AI suggestion or not yet scored"),
            })

    for f in findings:
        f["grade"] = grades.get(f["ref"]) if grades.get(f["ref"]) in GRADES else f["suggested_grade"]
        f["grade_set_by_you"] = grades.get(f["ref"]) in GRADES
        f["relates_to"] = list(relates.get(f["ref"]) or [])
    return findings


def build_return(engagement_key: Optional[str], findings: List[Dict], country: str = "") -> Dict:
    """compass-return 1.0; `country` is "" for the whole-organization file."""
    return {
        "format": RETURN_FORMAT, "format_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_app": SOURCE_APP, "engagement_key": engagement_key or "",
        "country": country,
        "findings": [
            {"ref": f["ref"], "kind": f["kind"], "title": f["title"], "detail": f["detail"], "grade": f["grade"],
             "figure": f["figure"], "relates_to": f["relates_to"], "source_note": f["source_note"],
             **{k: f[k] for k in OPTIONAL_FINDING_FIELDS if f.get(k)}}
            for f in findings
        ],
    }


ROLE_REASON_SOURCE = "Reason recorded by the designer; head-count from the uploaded org file."


def country_findings(country: str, row: Optional[Dict], role_cells: List[Dict], cluster_ref: Dict[str, str],
                     grades: Dict, relates: Dict) -> List[Dict]:
    """
    Findings for one country's file: the structural baseline computed on that
    country's people (topic role_presence), and one role_reason finding per
    Compass role that has a reason recorded here or nobody in it here.
    role_cells: [{ref, title, holders, compass_status, status_confirmed, reason}] for roles
    whose job-title match is confirmed (roles not matched yet are left out).
    """
    from .compass_roles import people, verb  # roles module depends on nothing here

    out: List[Dict] = []
    if row:
        vs = row["spans_vs_benchmark"]
        base = {"kind": "structural_baseline", "topic": "role_presence", "evidence_class": "OBSERVABLE",
                "suggested_grade": "confirmed",
                "source_note": f"Computed from the uploaded org file ({row['headcount']} people in {country})"}
        out += [
            {**base, "ref": "baseline.layers", "title": f"Layers in the reporting chain ({country})",
             "detail": f"Counted from who reports to whom, for the people whose Country is {country}, "
                       "from the top of the whole organization.",
             "figure": f"{row['layers']} layers"},
            {**base, "ref": "baseline.spans", "title": f"Managers within their span benchmark ({country})",
             "detail": f"{vs['below']} below, {vs['above']} above; {row['single_report_managers']} managers have one "
                       f"direct report. Median span {row['median_span']:g}. A manager's span counts reports in any country.",
             "figure": f"{vs['within']} of {row['managers']} managers"},
            {**base, "ref": "baseline.health", "title": f"Structural health score ({country})",
             "detail": "Weighted from span fit, layers for this size, manager ratio and single-report managers, for this country's people.",
             "figure": f"{row['health_score']} out of 100"},
        ]
    for c in role_cells:
        reason = c.get("reason") or {}
        recorded = bool(reason.get("text") or reason.get("reason_class") not in (None, "", "unknown"))
        if not recorded and c["holders"] != 0:
            continue
        status = {"status": c["compass_status"], "confirmed": c["status_confirmed"] is not False} if c["compass_status"] else None
        cluster = cluster_ref.get(c["ref"], "")
        f = {
            "ref": c["ref"], "kind": "role_reason", "topic": "role_reason",
            "title": f"Why {c['title']} {verb(status, c['holders'])} in {country}",
            "detail": reason.get("text") or "Not recorded yet.",
            "reason_class": reason.get("reason_class") if reason.get("reason_class") in ("required", "chosen", "inherited") else "unknown",
            "figure": people(c["holders"]),
            "evidence_class": None,
            "suggested_grade": "indicated" if reason.get("text") else "hypothesis",
            "relates_to_default": [c["ref"], cluster, f"{cluster}.People"] if cluster else [c["ref"]],
            "source_note": ROLE_REASON_SOURCE,
        }
        if reason.get("compared_with"):
            f["compared_with"] = reason["compared_with"]
        if reason.get("grade") in GRADES:
            f["grade_from_reason"] = reason["grade"]
        out.append(f)

    for f in out:
        mine = grades.get(f["ref"]) if grades.get(f["ref"]) in GRADES else f.pop("grade_from_reason", None)
        f.pop("grade_from_reason", None)
        f["grade"] = mine or f["suggested_grade"]
        f["grade_set_by_you"] = bool(mine)
        f["relates_to"] = list(relates[f["ref"]]) if f["ref"] in relates else f.pop("relates_to_default", [])
        f.pop("relates_to_default", None)
    return out


def return_as_text(ret: Dict) -> str:
    """The same content as the return file, for reading or uploading as a document."""
    kind_titles = {"structural_baseline": "Structural baseline", "role_reason": "Compass roles: why they exist or are missing",
                   "work_activity": "Work activities", "hypothesis": "Operating-model hypotheses", "option_score": "Options compared"}
    reason_words = {"required": "Required", "chosen": "Chosen", "inherited": "Inherited", "unknown": "Not known yet"}
    key = ret.get("engagement_key")
    where = f" ({ret['country']})" if ret.get("country") else ""
    lines = [f"Org Modeling findings for {key or 'this organization'}{where}",
             f"Format {ret['format']} {ret['format_version']}, generated {ret['generated_at']}", ""]
    for kind in FINDING_KINDS:
        items = [f for f in ret["findings"] if f["kind"] == kind]
        if not items:
            continue
        lines += [kind_titles[kind].upper(), ""]
        for f in items:
            ref = f"{key}:{f['ref']}" if key and kind == "hypothesis" else f["ref"]
            lines.append(f"[{ref}] {f['title']}" + (f" — {f['figure']}" if f["figure"] else ""))
            lines.append(f"  Grade: {GRADE_LABELS[f['grade']]}. Rests on: {f['source_note']}")
            if f.get("reason_class"):
                lines.append(f"  Reason: {reason_words[f['reason_class']]}"
                             + (f", compared with {f['compared_with']}" if f.get("compared_with") else ""))
            if f["detail"]:
                lines.append(f"  {f['detail']}")
            if f["relates_to"]:
                lines.append("  Relates to: " + ", ".join(f"{key}:{r}" if key else r for r in f["relates_to"]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
