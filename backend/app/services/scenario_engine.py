"""
Scenario engine: apply design moves to a copy of the current organization
and measure what changes.

A scenario is the baseline employee list plus an ordered list of moves.
Moves never touch the baseline; each is validated and either applied or
reported as skipped with a plain-language reason, so a scenario can always
be computed.

Move types (all reference people by Employee ID):
- reassign        {person_id, new_manager_id, department?}  — move a person (and their whole team) under another manager
- remove_role     {person_id, reports_to?}                   — delete a position; its direct reports move up (to reports_to or the person's manager)
- add_role        {title, grade?, department?, manager_id, salary?, name?, count?} — add one or more new positions
- merge_teams     {from_manager_id, into_manager_id, remove_from_manager?} — move every direct report of one manager to another
- change_role     {person_id, title?, grade?, salary?, department?} — redesign a role in place
- move_department {department, new_department}               — rename a department or fold it into another
"""

import copy
import itertools
from typing import Dict, List, Optional, Tuple

from .org_graph import normalize_employees

MOVE_TYPES = ["reassign", "remove_role", "add_role", "merge_teams", "change_role", "move_department"]


class MoveError(Exception):
    """A move that cannot be applied; the message is shown to the user."""


def _index(employees: List[Dict]) -> Dict[str, Dict]:
    return {e["employee_id"]: e for e in employees}


def _would_create_loop(by_id: Dict[str, Dict], person_id: str, new_manager_id: str) -> bool:
    """True if new_manager_id is the person or sits anywhere below them."""
    cur: Optional[str] = new_manager_id
    seen = set()
    while cur and cur not in seen:
        if cur == person_id:
            return True
        seen.add(cur)
        cur = by_id.get(cur, {}).get("manager_id")
    return False


def _name(by_id: Dict[str, Dict], pid: Optional[str]) -> str:
    return by_id.get(pid, {}).get("name", pid or "top of the organization") if pid else "top of the organization"


def _require(by_id: Dict[str, Dict], pid: Optional[str], role: str) -> Dict:
    if not pid or pid not in by_id:
        raise MoveError(f"{role} '{pid}' is not in this organization")
    return by_id[pid]


def apply_move(employees: List[Dict], move: Dict, grade_salary: Dict[str, float], new_ids: "itertools.count") -> str:
    """Apply one move in place; return a one-line description of what happened."""
    by_id = _index(employees)
    kind = move.get("type")

    if kind == "reassign":
        person = _require(by_id, move.get("person_id"), "Person")
        new_mgr = _require(by_id, move.get("new_manager_id"), "New manager")
        if _would_create_loop(by_id, person["employee_id"], new_mgr["employee_id"]):
            raise MoveError(f"{person['name']} can't report to {new_mgr['name']}, who is in their own team")
        old = _name(by_id, person.get("manager_id"))
        person["manager_id"] = new_mgr["employee_id"]
        person["manager_name"] = new_mgr["name"]
        if move.get("department"):
            person["department"] = move["department"]
        return f"{person['name']} (and team) moved from {old} to {new_mgr['name']}"

    if kind == "remove_role":
        person = _require(by_id, move.get("person_id"), "Person")
        target = move.get("reports_to") or person.get("manager_id")
        if target and target not in by_id:
            raise MoveError(f"Reports can't move to '{target}', who is not in this organization")
        if target == person["employee_id"]:
            raise MoveError("A role's reports can't move to the role being removed")
        reports = [e for e in employees if e.get("manager_id") == person["employee_id"]]
        if not target and reports:
            raise MoveError(f"Removing {person['name']} would leave {len(reports)} people without a manager — choose who they report to")
        for r in reports:
            r["manager_id"] = target
            r["manager_name"] = _name(by_id, target)
        employees.remove(person)
        moved = f"; {len(reports)} report(s) now report to {_name(by_id, target)}" if reports else ""
        return f"Removed {person['name']} ({person.get('job_title', '')}){moved}"

    if kind == "add_role":
        manager = _require(by_id, move.get("manager_id"), "Manager")
        title = (move.get("title") or "").strip()
        if not title:
            raise MoveError("A new role needs a job title")
        count = int(move.get("count") or 1)
        if not 1 <= count <= 500:
            raise MoveError("Add between 1 and 500 positions at a time")
        grade = move.get("grade") or ""
        salary = move.get("salary")
        if salary in (None, ""):
            salary = grade_salary.get(grade, 0)
        for _ in range(count):
            new_id = f"NEW-{next(new_ids):03d}"
            employees.append({
                "employee_id": new_id,
                "name": move.get("name") or f"New: {title}",
                "job_title": title,
                "grade": grade,
                "department": move.get("department") or manager.get("department", ""),
                "level": (manager.get("level") or 0) + 1,
                "manager_id": manager["employee_id"],
                "manager_name": manager["name"],
                "salary": float(salary or 0),
                "work_type": move.get("work_type", ""),
                "work_activities": move.get("work_activities", ""),
                "is_new": True,
            })
        return f"Added {count} × {title} reporting to {manager['name']}"

    if kind == "merge_teams":
        source = _require(by_id, move.get("from_manager_id"), "Team to merge")
        dest = _require(by_id, move.get("into_manager_id"), "Receiving manager")
        if source["employee_id"] == dest["employee_id"]:
            raise MoveError("Choose two different managers to merge")
        if _would_create_loop(by_id, source["employee_id"], dest["employee_id"]):
            raise MoveError(f"{dest['name']} is inside {source['name']}'s team; merge the other way round")
        reports = [e for e in employees if e.get("manager_id") == source["employee_id"]]
        for r in reports:
            r["manager_id"] = dest["employee_id"]
            r["manager_name"] = dest["name"]
        summary = f"Merged {source['name']}'s team ({len(reports)}) into {dest['name']}'s"
        if move.get("remove_from_manager"):
            employees.remove(source)
            summary += f"; removed {source['name']}'s role"
        return summary

    if kind == "change_role":
        person = _require(by_id, move.get("person_id"), "Person")
        changes = []
        for field, label in (("title", "title"), ("grade", "grade"), ("department", "department")):
            if move.get(field):
                key = "job_title" if field == "title" else field
                changes.append(f"{label} {person.get(key, '')} → {move[field]}")
                person[key] = move[field]
        if move.get("salary") not in (None, ""):
            person["salary"] = float(move["salary"])
            changes.append(f"salary → {move['salary']}")
        elif move.get("grade") and move["grade"] in grade_salary:
            person["salary"] = grade_salary[move["grade"]]
        if not changes:
            raise MoveError("Nothing to change — give a new title, grade, salary or department")
        return f"{person['name']}: " + "; ".join(changes)

    if kind == "move_department":
        old, new = (move.get("department") or "").strip(), (move.get("new_department") or "").strip()
        if not old or not new:
            raise MoveError("Give both the department and its new name")
        affected = [e for e in employees if e.get("department") == old]
        if not affected:
            raise MoveError(f"No one is in a department called '{old}'")
        for e in affected:
            e["department"] = new
        return f"{len(affected)} people moved from {old} to {new}"

    raise MoveError(f"Unknown move type '{kind}' (expected one of: {', '.join(MOVE_TYPES)})")


def apply_moves(baseline: List[Dict], moves: List[Dict], grade_salary: Optional[Dict[str, float]] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Apply moves in order to a copy of the baseline. Returns (employees,
    log) where each log entry is {index, type, status: applied|skipped, message}.
    """
    employees, _ = normalize_employees(copy.deepcopy(baseline))
    new_ids = itertools.count(1)
    log = []
    for i, move in enumerate(moves or []):
        try:
            message = apply_move(employees, move, grade_salary or {}, new_ids)
            log.append({"index": i, "type": move.get("type"), "status": "applied", "message": message})
        except MoveError as e:
            log.append({"index": i, "type": move.get("type"), "status": "skipped", "message": str(e)})
    return employees, log


# Headline figures compared between baseline and scenario
def headline(metrics: Dict) -> Dict:
    span = metrics.get("span_of_control", {})
    vs = span.get("distribution_vs_benchmark", {})
    health = metrics.get("health_indicators", {})
    return {
        "headcount": metrics.get("total_employees", 0),
        "managers": metrics.get("manager_stats", {}).get("total_managers", 0),
        "manager_ratio_pct": metrics.get("manager_stats", {}).get("manager_ratio_pct", 0),
        "average_span": span.get("average_span", 0),
        "median_span": span.get("median_span", 0),
        "layers": metrics.get("layer_analysis", {}).get("total_layers", 0),
        "total_cost": metrics.get("cost_analysis", {}).get("total_cost", 0),
        "spans_within_benchmark": vs.get("Within benchmark", 0),
        "spans_below_benchmark": vs.get("Below benchmark", 0),
        "spans_above_benchmark": vs.get("Above benchmark", 0),
        "single_report_managers": span.get("single_report_managers", 0),
        "health_score": health.get("health_score", 0),
    }


def delta(base: Dict, scenario: Dict) -> Dict:
    """Scenario minus baseline for every headline figure."""
    out = {}
    for k, v in scenario.items():
        b = base.get(k, 0) or 0
        out[k] = round((v or 0) - b, 2) if isinstance(v, (int, float)) else None
    return out


def department_deltas(base_metrics: Dict, scenario_metrics: Dict) -> List[Dict]:
    """Per-department headcount, managers and cost, before and after."""
    base = {d["department"]: d for d in base_metrics.get("department_analysis", [])}
    scen = {d["department"]: d for d in scenario_metrics.get("department_analysis", [])}
    rows = []
    for dept in sorted(set(base) | set(scen)):
        b, s = base.get(dept, {}), scen.get(dept, {})
        rows.append({
            "department": dept,
            "headcount_before": b.get("headcount", 0), "headcount_after": s.get("headcount", 0),
            "managers_before": b.get("managers", 0), "managers_after": s.get("managers", 0),
            "cost_before": b.get("total_cost", 0), "cost_after": s.get("total_cost", 0),
            "average_span_before": b.get("average_span", 0), "average_span_after": s.get("average_span", 0),
            "status": "new" if not b else "removed" if not s else "changed"
            if (b.get("headcount"), b.get("total_cost")) != (s.get("headcount"), s.get("total_cost")) else "unchanged",
        })
    return rows


def people_impact(baseline: List[Dict], scenario: List[Dict]) -> Dict:
    """
    Who is affected: roles removed and added, people with a new manager or
    department, and managers whose team size changed. Feeds the
    implementation view.
    """
    base_norm, _ = normalize_employees(copy.deepcopy(baseline))
    before = _index(base_norm)
    after = _index(scenario)

    def span_map(emps: Dict[str, Dict]) -> Dict[str, int]:
        spans: Dict[str, int] = {}
        for e in emps.values():
            m = e.get("manager_id")
            if m:
                spans[m] = spans.get(m, 0) + 1
        return spans

    removed = [before[i] for i in before if i not in after]
    added = [after[i] for i in after if i not in before]
    new_manager, new_department = [], []
    for pid, e in after.items():
        b = before.get(pid)
        if not b:
            continue
        if b.get("manager_id") != e.get("manager_id"):
            new_manager.append({
                "employee_id": pid, "name": e.get("name"), "job_title": e.get("job_title"),
                "from": _name(before, b.get("manager_id")), "to": _name(after, e.get("manager_id")),
            })
        if (b.get("department") or "") != (e.get("department") or ""):
            new_department.append({"employee_id": pid, "name": e.get("name"), "from": b.get("department"), "to": e.get("department")})

    spans_before, spans_after = span_map(before), span_map(after)
    span_changes = []
    for mid in set(spans_before) | set(spans_after):
        if mid in after and spans_before.get(mid, 0) != spans_after.get(mid, 0):
            span_changes.append({
                "employee_id": mid, "name": after[mid].get("name"),
                "span_before": spans_before.get(mid, 0), "span_after": spans_after.get(mid, 0),
            })

    brief = lambda e: {"employee_id": e["employee_id"], "name": e.get("name"), "job_title": e.get("job_title"),
                       "department": e.get("department"), "salary": e.get("salary", 0)}
    affected = {p["employee_id"] for p in new_manager} | {p["employee_id"] for p in new_department}
    return {
        "roles_removed": [brief(e) for e in removed],
        "roles_added": [brief(e) for e in added],
        "new_manager": new_manager,
        "new_department": new_department,
        "managers_with_changed_span": sorted(span_changes, key=lambda s: -abs(s["span_after"] - s["span_before"])),
        "people_affected": len(affected) + len(removed),
        "people_affected_pct": round((len(affected) + len(removed)) / len(before) * 100, 1) if before else 0.0,
    }
