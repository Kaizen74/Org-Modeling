"""
Optional overlay: the role of AI in each role's work.

Each job title can be tagged automate / augment / keep_human with an
estimated share of the role's time that AI could free up. The overlay is
entirely optional: nothing else in the app depends on it. When it is used,
scenarios and comparisons show the capacity it frees (in full-time
equivalents) — it never changes headcount by itself; the designer decides
what to do with freed capacity through design moves.
"""

from typing import Dict, List, Optional, Tuple

DISPOSITIONS = {
    "automate": "AI can do most of this work; people supervise",
    "augment": "People keep the work; AI speeds it up or improves it",
    "keep_human": "Judgement, relationships or physical work that stays with people",
}


def role_inventory(employees: List[Dict]) -> List[Dict]:
    """One row per job title: headcount, departments, sample activities. No names."""
    roles: Dict[str, Dict] = {}
    for e in employees:
        title = str(e.get("job_title") or "").strip()
        if not title:
            continue
        r = roles.setdefault(title, {"job_title": title, "headcount": 0, "departments": set(), "activities": []})
        r["headcount"] += 1
        if e.get("department"):
            r["departments"].add(e["department"])
        act = str(e.get("work_activities") or "").strip()
        if act and act not in r["activities"] and len(r["activities"]) < 3:
            r["activities"].append(act[:300])
    out = []
    for r in roles.values():
        out.append({**r, "departments": sorted(r["departments"])})
    return sorted(out, key=lambda r: -r["headcount"])


def capacity_freed(employees: List[Dict], roles: Dict[str, Dict]) -> Tuple[float, float]:
    """(FTE, cost) freed across these employees, from each title's capacity share."""
    fte = cost = 0.0
    for e in employees:
        tag = roles.get(str(e.get("job_title") or "").strip())
        if not tag:
            continue
        share = max(0.0, min(100.0, float(tag.get("capacity_freed_pct") or 0))) / 100
        fte += share
        cost += share * float(e.get("salary") or 0)
    return round(fte, 1), round(cost, 0)


def summarize(employees: List[Dict], roles: Dict[str, Dict]) -> Dict:
    inventory = role_inventory(employees)
    by_disposition = {k: {"roles": 0, "people": 0} for k in DISPOSITIONS}
    tagged_people = 0
    for r in inventory:
        tag = roles.get(r["job_title"])
        if tag and tag.get("disposition") in by_disposition:
            by_disposition[tag["disposition"]]["roles"] += 1
            by_disposition[tag["disposition"]]["people"] += r["headcount"]
            tagged_people += r["headcount"]
    fte, cost = capacity_freed(employees, roles)
    total = sum(r["headcount"] for r in inventory) or 1
    return {
        "by_disposition": by_disposition,
        "tagged_roles": sum(1 for r in inventory if r["job_title"] in roles),
        "total_roles": len(inventory),
        "tagged_people_pct": round(tagged_people / total * 100, 1),
        "capacity_fte": fte,
        "capacity_cost": cost,
    }


def validate_tag(disposition: Optional[str], capacity_freed_pct: Optional[float]) -> Optional[str]:
    if disposition not in DISPOSITIONS:
        return f"Disposition must be one of: {', '.join(DISPOSITIONS)}"
    if capacity_freed_pct is not None and not 0 <= capacity_freed_pct <= 100:
        return "Capacity freed must be between 0 and 100%"
    return None


def build_prompt(inventory: List[Dict], industry: Optional[str] = None) -> str:
    lines = []
    for r in inventory[:80]:
        acts = " | ".join(r["activities"]) or "no activities listed"
        lines.append(f"- job_title={r['job_title']!r} ({r['headcount']} people; {', '.join(r['departments'])}): {acts}")
    return f"""You are an expert in work design and AI-enabled operating models. For each role below, judge the role of AI in its work.

INDUSTRY: {industry or 'Infer from the roles'}

ROLES (job titles and activities only; no personal names):
{chr(10).join(lines)}

For each role give:
- disposition: "automate" (AI can do most of the work; people supervise), "augment" (people keep the work; AI speeds it up or improves it) or "keep_human" (judgement, relationships, physical work)
- capacity_freed_pct: realistic share of the role's time AI could free within 2-3 years (0-100), considering only current, proven capabilities
- rationale: one sentence naming the specific activities driving the judgement
- confidence: High/Medium/Low (Medium at most when no activities are listed)

Return only JSON:
```json
{{"roles": [{{"job_title": "exact title as given", "disposition": "augment", "capacity_freed_pct": 20, "rationale": "...", "confidence": "Medium"}}]}}
```"""
