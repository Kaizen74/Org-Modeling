"""
Compass anchor roles by country: which roles exist where, and why.

Roles (`RL-nnn`) come from the linked Compass packets and are matched by ref
across countries. The designer matches each role to job titles in the org
file; holders per country are counted from those titles. This app never
changes a Compass status: it shows it and raises flags in words where the org
file disagrees. Reasons, matches and grades are the designer's.

A role whose match is not confirmed yet is "not matched": it counts as
neither existing nor absent. A confirmed empty match means "no job title in
this file" and gives 0 holders. A role "to confirm" in the Compass is counted
as "to confirm", never as existing or absent.
"""

import difflib
import re
from typing import Dict, List, Optional

REASON_CLASSES = ["required", "chosen", "inherited", "unknown"]
REASON_LABELS = {"required": "Required", "chosen": "Chosen", "inherited": "Inherited", "unknown": "Not known yet"}
REASON_HELP = {
    "required": "Regulation, a customer contract or the physical site makes it necessary",
    "chosen": "A deliberate local decision someone can state",
    "inherited": "History, an acquisition or habit; nobody decided it",
    "unknown": "Not known yet",
}
MISSING_NOTE = "Why is it missing? Not recorded."
_STOP = {"of", "the", "and", "a", "an", "for", "to", "in"}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _tokens(text: str) -> set:
    return {t for t in _norm(text).split() if t not in _STOP}


def people(n: int) -> str:
    return f"{n} person" if n == 1 else f"{n} people"


def suggest_titles(role_title: str, file_titles: List[str]) -> List[Dict]:
    """Exact and close job-title matches for a role, best first. Suggestions only: the designer confirms."""
    exact = [t for t in file_titles if _norm(t) == _norm(role_title)]
    if exact:
        return [{"title": t, "kind": "exact"} for t in exact]
    scored = []
    rt = _tokens(role_title)
    for t in file_titles:
        ratio = difflib.SequenceMatcher(None, _norm(role_title), _norm(t)).ratio()
        tt = _tokens(t)
        jaccard = len(rt & tt) / len(rt | tt) if rt | tt else 0
        if ratio >= 0.75 or jaccard >= 0.5:
            scored.append((max(ratio, jaccard), t))
    return [{"title": t, "kind": "close"} for _, t in sorted(scored, reverse=True)[:3]]


def role_catalog(packets: List[Dict]) -> List[Dict]:
    """Anchor roles across the linked packets, matched by ref; the first packet naming a ref describes it."""
    seen: Dict[str, Dict] = {}
    for p in packets:
        for r in p.get("roles") or []:
            ref = r.get("ref")
            if ref and ref not in seen:
                seen[ref] = {"ref": ref, "title": r.get("title", ""), "cluster_ref": r.get("cluster_ref", ""),
                             "route": r.get("route", "")}
    return sorted(seen.values(), key=lambda r: r["ref"])


def _status(packet: Dict, ref: str) -> Optional[Dict]:
    r = next((x for x in packet.get("roles") or [] if x.get("ref") == ref), None)
    if not r:
        return None
    return {"status": r.get("status"), "confirmed": r.get("status_confirmed", True) is not False}


def _flag(status: Optional[Dict], holders: Optional[int]) -> Optional[str]:
    """Where the Compass and the org file disagree, in words. The Compass status is never changed here."""
    if status is None or holders is None:
        return None
    if not status["confirmed"]:
        return f"Still to confirm in the Compass; the org file shows {people(holders)}."
    if status["status"] in ("exists", "thin") and holders == 0:
        return "The Compass says this role exists; the org file shows nobody in it."
    if status["status"] == "absent" and holders > 0:
        return f"The Compass says absent; the org file shows {people(holders)}."
    return None


def presence(status: Optional[Dict], holders: Optional[int]) -> str:
    """This app's own summary word: to confirm wins; otherwise from the confirmed match."""
    if status is not None and not status["confirmed"]:
        return "to_confirm"
    if holders is None:
        return "not_matched"
    return "absent" if holders == 0 else "exists"


def verb(status: Optional[Dict], holders: int) -> str:
    """For the finding title: from the Compass status when confirmed, else from holders."""
    if status is not None and status["confirmed"] and status["status"] in ("exists", "thin", "absent"):
        return {"exists": "exists", "thin": "is thin", "absent": "is absent"}[status["status"]]
    return "is absent" if holders == 0 else "exists"


def holders_by_country(employees: List[Dict], titles: List[str], country: str) -> int:
    """People holding any of the titles in that country ("" = everyone)."""
    wanted = {t.strip() for t in titles}
    return sum(1 for e in employees
               if str(e.get("job_title", "")).strip() in wanted and (not country or e.get("country") == country))


def build_roles_view(employees: List[Dict], links: List[Dict], matches: Dict[str, List[str]]) -> Dict:
    """
    links: [{country, key, packet, reasons}] for every linked packet ("" = whole organization).
    matches: {RL ref: [job titles]} confirmed by the designer (an empty list = no job title in this file).
    """
    file_titles = sorted({str(e.get("job_title", "")).strip() for e in employees if e.get("job_title")})
    catalog = role_catalog([l["packet"] for l in links])
    rows = []
    for role in catalog:
        confirmed = role["ref"] in matches
        titles = matches.get(role["ref"], [])
        cells = []
        for l in links:
            status = _status(l["packet"], role["ref"])
            holders = holders_by_country(employees, titles, l["country"]) if confirmed else None
            reason = (l.get("reasons") or {}).get(role["ref"])
            cells.append({
                "country": l["country"],
                "in_packet": status is not None,
                "compass_status": status["status"] if status else None,
                "status_confirmed": status["confirmed"] if status else None,
                "holders": holders,
                "presence": presence(status, holders),
                "flag": _flag(status, holders),
                "reason": reason,
                "missing_note": MISSING_NOTE if holders == 0 and not (reason and reason.get("text")) else None,
            })
        rows.append({**role, "match_confirmed": confirmed, "titles": titles,
                     "suggestions": [] if confirmed else suggest_titles(role["title"], file_titles), "cells": cells})

    matched = {t for ts in matches.values() for t in ts}
    unmatched = [t for t in file_titles if t not in matched]
    summary = {}
    for i, l in enumerate(links):
        counts = {"exists": 0, "absent": 0, "to_confirm": 0, "not_matched": 0}
        for r in rows:
            counts[r["cells"][i]["presence"]] += 1
        summary[l["country"]] = counts
    return {
        "links": [{"country": l["country"], "key": l["key"]} for l in links],
        "roles": rows,
        "file_titles": file_titles,
        "unmatched_titles": len(unmatched),
        "summary": summary,
        "reason_classes": REASON_CLASSES,
        "reason_labels": REASON_LABELS,
        "reason_help": REASON_HELP,
    }
