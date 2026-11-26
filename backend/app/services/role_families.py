"""
Role families: every job title in the org file grouped into families, defined
once for the whole file, so a family means the same thing in every unit.

- Suggestions come from a deterministic rule: a title's leading key words,
  with generic role words (Head, Manager, Officer…) set aside. Titles that
  share their first key word are suggested together. Nothing is applied until
  the designer confirms it; no AI is involved.
- A family gets its ID (RF-nn) when first confirmed. Renaming keeps the ID;
  merging two keeps the older ID and retires the other; a retired ID is never
  reused.
- Head-count per family per unit is counted from the file; the designer
  records why a family is, or isn't, in a unit.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional

from .compass_roles import people as people_word

REASON_CLASSES = ["required", "chosen", "inherited", "unknown"]

# Words that say how senior or what kind of job, not which work: set aside when suggesting
GENERIC_WORDS = {
    "head", "lead", "leader", "manager", "management", "officer", "director", "vp", "svp", "evp", "agent",
    "supervisor", "controller", "analyst", "executive", "specialist", "senior", "junior", "assistant",
    "associate", "chief", "global", "regional", "general", "group", "deputy", "principal", "staff", "team",
    "coordinator", "administrator", "admin", "user", "super", "certified", "of", "the", "and", "for", "to",
    "in", "on", "a", "an",
    # Common abbreviations and grade markers in HRIS titles ("Asst Mgr", "AVP", "Snr Exec", "Officer II")
    "asst", "ast", "mgr", "mngr", "mgt", "avp", "snr", "sr", "jr", "exec", "dy", "dep", "assoc", "hod", "gm",
    "agm", "dgm", "acting", "interim", "trainee", "intern", "i", "ii", "iii", "iv",
}
_SEGMENT_SPLIT = re.compile(r"\s*(?:/|,|—|–|\(|\)|-(?=\s)|\s-\s)\s*")


def _key_phrase(title: str) -> str:
    """The first part of a title that names the work, e.g. 'Head of Pricing / Revenue Management' → 'Pricing'."""
    for segment in _SEGMENT_SPLIT.split(title or ""):
        words = [w for w in re.findall(r"[A-Za-z0-9&]+", segment) if w.lower() not in GENERIC_WORDS]
        while words and words[0] == "&":
            words.pop(0)
        while words and words[-1] == "&":
            words.pop()
        if words:
            phrase = " ".join(words)
            return phrase[0].upper() + phrase[1:].lower() if not any(w.isupper() and len(w) > 1 for w in words) else phrase
    return (title or "").strip()


def suggestion_key(title: str) -> str:
    phrase = _key_phrase(title)
    first = re.findall(r"[A-Za-z0-9]+", phrase.lower())
    return first[0] if first else phrase.lower()


def suggest(titles: List[str]) -> List[Dict]:
    """Suggested families for titles not yet in a family: [{name, titles}], titles sharing their first key word together."""
    groups: Dict[str, List[str]] = {}
    for t in sorted(titles):
        groups.setdefault(suggestion_key(t), []).append(t)
    out = []
    for titles_ in groups.values():
        name = min((_key_phrase(t) for t in titles_), key=len)
        out.append({"name": name, "titles": titles_})
    return sorted(out, key=lambda g: g["name"].lower())


def active(families: List[Dict]) -> List[Dict]:
    return [f for f in families or [] if not f.get("retired")]


def next_ref(seq: int) -> str:
    return f"RF-{seq:02d}"


def ref_number(ref: str) -> int:
    m = re.match(r"RF-(\d+)$", ref or "")
    return int(m.group(1)) if m else 0


def headcounts(employees: List[Dict], titles: List[str]) -> Dict[str, Dict]:
    """Per unit: people holding any of the titles, and how many distinct titles they hold."""
    wanted = {t.strip() for t in titles}
    out: Dict[str, Dict] = {}
    for e in employees:
        t = str(e.get("job_title", "")).strip()
        if t in wanted:
            u = out.setdefault(e.get("country") or "", {"headcount": 0, "titles": set()})
            u["headcount"] += 1
            u["titles"].add(t)
    return {u: {"headcount": v["headcount"], "job_titles": len(v["titles"])} for u, v in out.items()}


def presence(by_unit: Dict[str, int], units: List[str]) -> Dict:
    """In every unit, in some, only in one, or in none."""
    present = [u for u in units if by_unit.get(u, 0) > 0]
    if not units:
        return {"presence": "", "only_in": None}
    if len(present) == len(units):
        return {"presence": "every", "only_in": None}
    if len(present) == 1:
        return {"presence": "only", "only_in": present[0]}
    return {"presence": "none" if not present else "some", "only_in": None}


def view(employees: List[Dict], families: List[Dict], reasons: Dict, units: List[str]) -> Dict:
    """Everything the Role families screen shows."""
    all_titles: Dict[str, Dict[str, int]] = {}
    for e in employees:
        t = str(e.get("job_title", "")).strip()
        if t:
            u = all_titles.setdefault(t, {})
            u[e.get("country") or ""] = u.get(e.get("country") or "", 0) + 1
    title_family = {t: f["ref"] for f in active(families) for t in f.get("titles", [])}
    rows = []
    for f in active(families):
        counts = headcounts(employees, f.get("titles", []))
        by_unit = {u: counts.get(u, {}).get("headcount", 0) for u in units} if units else {}
        rows.append({**{k: f.get(k) for k in ("ref", "name", "titles", "relates_to", "confirmed_at")},
                     "headcount": sum(c["headcount"] for c in counts.values()),
                     "by_unit": by_unit, **presence(by_unit, units),
                     "reasons": (reasons or {}).get(f["ref"], {})})
    unassigned = [t for t in all_titles if t not in title_family]
    return {
        "units": units,
        "families": sorted(rows, key=lambda r: ref_number(r["ref"])),
        "retired": [{"ref": f["ref"], "name": f.get("name"), "merged_into": f.get("merged_into")} for f in families or [] if f.get("retired")],
        "titles": [{"title": t, "headcount": sum(c.values()), "by_unit": c, "family": title_family.get(t)}
                   for t, c in sorted(all_titles.items())],
        "suggestions": suggest(unassigned),
        "unassigned": len(unassigned),
        "reason_classes": REASON_CLASSES,
    }


# ------------------------------------------------------------------ changes (pure functions on the stored list)

def _clean_titles(titles: List[str], file_titles: set) -> List[str]:
    cleaned = list(dict.fromkeys(t.strip() for t in titles or [] if t and t.strip()))
    unknown = [t for t in cleaned if t not in file_titles]
    if unknown:
        raise ValueError(f"Not a job title in the org file: {', '.join(unknown)}")
    return cleaned


def _take_titles(families: List[Dict], titles: List[str], keep_ref: Optional[str] = None) -> None:
    """A title belongs to one family: moving it takes it out of any other."""
    for f in active(families):
        if f["ref"] != keep_ref:
            f["titles"] = [t for t in f.get("titles", []) if t not in titles]


def confirm(families: List[Dict], seq: int, name: str, titles: List[str], file_titles: set):
    """A new family from the designer's confirmation; its RF number is the next never used."""
    name = (name or "").strip()
    if not name:
        raise ValueError("A family needs a name.")
    titles = _clean_titles(titles, file_titles)
    if not titles:
        raise ValueError("Choose at least one job title for the family.")
    if any(f["name"].lower() == name.lower() for f in active(families)):
        raise ValueError(f"A family called '{name}' already exists; add the titles to it instead.")
    families = [dict(f) for f in families or []]
    _take_titles(families, titles)
    seq += 1
    families.append({"ref": next_ref(seq), "name": name, "titles": titles, "relates_to": [], "retired": False,
                     "merged_into": None, "confirmed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"})
    return families, seq


def update(families: List[Dict], ref: str, file_titles: set, *, name: Optional[str] = None,
           titles: Optional[List[str]] = None, relates_to: Optional[List[str]] = None, valid_refs: Optional[set] = None):
    """Rename (the ID stays), change titles, or link the Compass clusters a family serves."""
    families = [dict(f) for f in families or []]
    target = next((f for f in active(families) if f["ref"] == ref), None)
    if not target:
        raise LookupError(f"No family {ref}")
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("A family needs a name.")
        if any(f["name"].lower() == name.lower() and f["ref"] != ref for f in active(families)):
            raise ValueError(f"A family called '{name}' already exists.")
        target["name"] = name
    if titles is not None:
        titles = _clean_titles(titles, file_titles)
        _take_titles(families, titles, keep_ref=ref)
        target["titles"] = titles
    if relates_to is not None:
        unknown = [r for r in relates_to if valid_refs is not None and r not in valid_refs]
        if unknown:
            raise ValueError(f"Not in the linked Compass files: {', '.join(unknown)}")
        target["relates_to"] = list(dict.fromkeys(relates_to))
    return families


def merge(families: List[Dict], reasons: Dict, a: str, b: str):
    """Merge two families: the older ID (lower number) stays, the other is retired and never reused."""
    families = [dict(f) for f in families or []]
    fa = next((f for f in active(families) if f["ref"] == a), None)
    fb = next((f for f in active(families) if f["ref"] == b), None)
    if not fa or not fb or a == b:
        raise LookupError("Choose two different families to merge.")
    keep, retire = (fa, fb) if ref_number(a) < ref_number(b) else (fb, fa)
    keep["titles"] = list(dict.fromkeys(keep.get("titles", []) + retire.get("titles", [])))
    keep["relates_to"] = list(dict.fromkeys(keep.get("relates_to", []) + retire.get("relates_to", [])))
    retire.update(retired=True, merged_into=keep["ref"], titles=[])
    reasons = {k: dict(v) for k, v in (reasons or {}).items()}
    for unit, r in reasons.pop(retire["ref"], {}).items():
        reasons.setdefault(keep["ref"], {}).setdefault(unit, r)  # the kept family's own reasons win
    return families, reasons, keep["ref"]


def retire(families: List[Dict], reasons: Dict, ref: str):
    """Stop using a family; its titles go back to unassigned and its ID is never reused."""
    families = [dict(f) for f in families or []]
    target = next((f for f in active(families) if f["ref"] == ref), None)
    if not target:
        raise LookupError(f"No family {ref}")
    target.update(retired=True, titles=[])
    reasons = {k: v for k, v in (reasons or {}).items() if k != ref}
    return families, reasons


def unit_findings(unit: str, employees: List[Dict], families: List[Dict], reasons: Dict, unit_people: int) -> List[Dict]:
    """One role_family finding per family for a unit's file, including families with nobody there (0 = absent)."""
    out = []
    for f in sorted(active(families), key=lambda x: ref_number(x["ref"])):
        counts = headcounts(employees, f.get("titles", [])).get(unit, {"headcount": 0, "job_titles": 0})
        r = ((reasons or {}).get(f["ref"]) or {}).get(unit) or {}
        finding = {
            "ref": f["ref"], "kind": "role_family", "topic": "role_presence", "title": f["name"],
            "detail": r.get("text", "") if r else "",
            "figure": people_word(counts["headcount"]),
            "metrics": {"headcount": counts["headcount"], "job_titles": counts["job_titles"]},
            "evidence_class": "OBSERVABLE", "suggested_grade": "confirmed",
            "relates_to_default": list(f.get("relates_to") or []),
            "source_note": f"Grouped from job titles in the uploaded org file ({unit_people} people in {unit}).",
        }
        if r.get("reason_class") in REASON_CLASSES:
            finding["reason_class"] = r["reason_class"]
            if r.get("compared_with"):
                finding["compared_with"] = r["compared_with"]
        out.append(finding)
    return out
