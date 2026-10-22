"""
Ground archetype structure diagrams in the real organization.

The AI names which current departments each diagram unit draws from; this
module checks those names against the actual departments and computes each
unit's headcount and cost from the data (never from the AI). Departments the
diagram leaves out, and names the AI made up, are reported.
"""

from typing import Dict, List


def ground_diagrams(result: Dict, metrics: Dict) -> Dict:
    """Annotate every recommendation's structure_diagram in place (idempotent)."""
    category = result.get("category_4_recommended_archetypes") if isinstance(result, dict) else None
    if not isinstance(category, dict):
        return result
    departments = {d["department"].strip().lower(): d for d in (metrics or {}).get("department_analysis", []) or []}
    if not departments:
        return result

    for rec in category.get("recommendations") or []:
        diagram = rec.get("structure_diagram") if isinstance(rec, dict) else None
        if not isinstance(diagram, dict) or not isinstance(diagram.get("nodes"), list):
            continue
        # A department shared by several units is split between them in whole
        # people (remainder to the first units listed), so totals always match
        claimants: Dict[str, List[str]] = {}
        for node in diagram["nodes"]:
            for name in node.get("source_departments") or []:
                key = str(name).strip().lower()
                if key in departments and node.get("id") not in claimants.setdefault(key, []):
                    claimants[key].append(node.get("id"))
        claims = {k: len(v) for k, v in claimants.items()}
        people_share: Dict[tuple, int] = {}
        for key, node_ids in claimants.items():
            base, extra = divmod(departments[key]["headcount"], len(node_ids))
            for i, nid in enumerate(node_ids):
                people_share[(key, nid)] = base + (1 if i < extra else 0)

        for node in diagram["nodes"]:
            matched, unknown = [], []
            headcount = cost = 0.0
            for name in node.get("source_departments") or []:
                key = str(name).strip().lower()
                dept = departments.get(key)
                if not dept:
                    unknown.append(str(name))
                    continue
                if dept["department"] in matched:
                    continue
                matched.append(dept["department"])
                headcount += people_share.get((key, node.get("id")), 0)
                cost += dept["total_cost"] / claims[key]
            node["source_departments"] = matched
            node["unknown_departments"] = unknown
            node["headcount"] = int(headcount) if matched else None
            node["cost"] = round(cost) if matched else None
            node["shared_departments"] = [d for d in matched if claims[d.strip().lower()] > 1]

        unmapped = [d["department"] for k, d in departments.items() if k not in claims]
        diagram["coverage"] = {
            "mapped_departments": len(claims),
            "total_departments": len(departments),
            "unmapped_departments": unmapped,
            "unmapped_headcount": sum(departments[d.strip().lower()]["headcount"] for d in unmapped),
        }
    return result
