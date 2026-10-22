"""
Implementation implications of a scenario, derived by rule from its design
moves and measured effects (no AI): cost, change load, risks, and a
transition sequence.

Sequencing principle: appoint before you remove. New roles are filled first,
then people and teams move, then roles are removed once their reports have a
new home, then the structure is stabilised.
"""

from typing import Dict, List

WAVES = [
    ("appoint", "Appoint and prepare", "Create and fill new roles; redesign changed roles; brief the managers who will receive people.",
     {"add_role", "change_role"}),
    ("move", "Move people and teams", "Re-point reporting lines, merge teams and move units, with each affected person told by their new manager.",
     {"reassign", "merge_teams", "move_department"}),
    ("remove", "Remove roles", "Remove roles only once their reports have a new manager; handle each affected person individually.",
     {"remove_role"}),
]

OVERLOAD_MARGIN = 1.0  # a span above the benchmark's upper bound counts as overload


def _headline_change(ev: Dict, key: str) -> float:
    return (ev.get("delta") or {}).get(key) or 0


def build_plan(ev: Dict, moves: List[Dict]) -> Dict:
    """ev is a scenario evaluation (see api.scenarios.evaluate)."""
    impact = ev["impact"]
    log = ev["move_log"]

    removed_cost = sum(r.get("salary") or 0 for r in impact["roles_removed"])
    added_cost = sum(r.get("salary") or 0 for r in impact["roles_added"])

    # Change load per manager: people joining or leaving their team
    span_changes = impact["managers_with_changed_span"]
    gaining = [m for m in span_changes if m["span_after"] > m["span_before"]]
    losing = [m for m in span_changes if m["span_after"] < m["span_before"]]

    # Spans after the change, against each manager's benchmark
    assessments = {a["manager_id"]: a for a in ev["metrics"]["span_of_control"].get("manager_assessments", [])}
    risks: List[Dict] = []
    for m in gaining:
        a = assessments.get(m["employee_id"])
        if a and a["span"] > a["benchmark_range"][1] * OVERLOAD_MARGIN:
            risks.append({
                "severity": "High", "area": "Manager capacity",
                "risk": f"{m['name']} goes from {m['span_before']} to {m['span_after']} direct reports, above the {a['benchmark_range'][0]}–{a['benchmark_range'][1]} benchmark for {a['work_type']} work",
                "mitigation": "Add a team lead, phase the transfer, or move part of the team elsewhere",
            })
    for m in losing:
        if m["span_before"] >= 3 and m["span_after"] <= m["span_before"] / 2:
            risks.append({
                "severity": "Medium", "area": "Role viability",
                "risk": f"{m['name']}'s team shrinks from {m['span_before']} to {m['span_after']}; the role may no longer be needed at its current level",
                "mitigation": "Review the role's scope and grade alongside this change",
            })
    if impact["people_affected_pct"] >= 20:
        risks.append({
            "severity": "High", "area": "Change load",
            "risk": f"{impact['people_affected_pct']}% of people are affected — a large change to run at once",
            "mitigation": "Sequence by department, and build manager capability to lead the conversations",
        })
    elif impact["people_affected_pct"] >= 10:
        risks.append({
            "severity": "Medium", "area": "Change load",
            "risk": f"{impact['people_affected_pct']}% of people are affected",
            "mitigation": "Give each affected manager a briefing pack and a clear timeline",
        })
    if impact["roles_removed"]:
        risks.append({
            "severity": "Medium", "area": "People and employee relations",
            "risk": f"{len(impact['roles_removed'])} roles are removed",
            "mitigation": "Plan redeployment first; consult per local employment practice before announcing",
        })
    if _headline_change(ev, "spans_above_benchmark") > 0:
        risks.append({
            "severity": "Medium", "area": "Manager capacity",
            "risk": f"{int(_headline_change(ev, 'spans_above_benchmark'))} more managers end up above their span benchmark",
            "mitigation": "Check these teams before finalising the design",
        })
    if _headline_change(ev, "layers") == 0 and any(m.get("type") == "remove_role" for m in moves):
        risks.append({
            "severity": "Low", "area": "Design intent",
            "risk": "Roles are removed but the number of layers is unchanged",
            "mitigation": "If delayering is the goal, check the longest reporting chain",
        })
    skipped = [m for m in log if m["status"] == "skipped"]
    if skipped:
        risks.append({
            "severity": "Medium", "area": "Design completeness",
            "risk": f"{len(skipped)} design move(s) could not be applied and are not reflected in the figures",
            "mitigation": "Fix or remove them in the Scenario Studio",
        })
    order = {"High": 0, "Medium": 1, "Low": 2}
    risks.sort(key=lambda r: order[r["severity"]])

    # Transition waves from the applied moves
    waves = []
    for key, title, guidance, types in WAVES:
        items = [
            {"index": m["index"], "message": m["message"], "note": (moves[m["index"]] or {}).get("note")}
            for m in log if m["status"] == "applied" and m["type"] in types
        ]
        if items:
            waves.append({"key": key, "title": title, "guidance": guidance, "moves": items})
    waves.append({
        "key": "stabilise", "title": "Stabilise",
        "guidance": "Re-run the structure diagnostics against the new organization; confirm spans, decision rights and hand-offs are working; close open roles.",
        "moves": [],
    })

    return {
        "summary": {
            "people_affected": impact["people_affected"],
            "people_affected_pct": impact["people_affected_pct"],
            "new_manager": len(impact["new_manager"]),
            "new_department": len(impact["new_department"]),
            "roles_removed": len(impact["roles_removed"]),
            "roles_added": len(impact["roles_added"]),
            "managers_gaining": len(gaining),
            "managers_losing": len(losing),
        },
        "cost": {
            "removed_roles": round(removed_cost),
            "added_roles": round(added_cost),
            "net_change": round(_headline_change(ev, "total_cost")),
            "note": "Annual salary base. Excludes one-off costs (severance, recruitment, transition support).",
        },
        "change_load": {
            "managers_gaining": sorted(gaining, key=lambda m: -(m["span_after"] - m["span_before"])),
            "managers_losing": sorted(losing, key=lambda m: m["span_after"] - m["span_before"]),
            "new_manager": impact["new_manager"],
            "new_department": impact["new_department"],
            "roles_removed": impact["roles_removed"],
            "roles_added": impact["roles_added"],
        },
        "risks": risks,
        "waves": waves,
    }
