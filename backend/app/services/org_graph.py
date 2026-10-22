"""
Shared org-graph construction.

People are keyed by Employee ID, never by name, so two people who share a
name stay two people. The parser and the metrics engine both build their
graph through this module so they can never disagree about who reports to
whom.

Line Manager resolution order for each person:
1. an explicit Line Manager ID (optional CSV column)
2. a Line Manager value that matches an Employee ID
3. a Line Manager value that matches exactly one person's name
4. a name matching several people: pick the one exactly one level above;
   if that is still ambiguous, leave the person unattached and report it
"""

from typing import Dict, List, Optional, Tuple
import networkx as nx

ROOT_MARKERS = {"", "top of org", "n/a", "na", "nan", "none", "-", "null"}


def _is_root_marker(value: Optional[str]) -> bool:
    return value is None or str(value).strip().lower() in ROOT_MARKERS


def normalize_employees(employees: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    Return copies of the employee records with a unique `employee_id` and a
    resolved `manager_id` (None for top-of-org or unresolvable), plus a list
    of plain-language data issues found along the way.
    """
    issues: List[str] = []
    normalized: List[Dict] = []
    seen_ids: Dict[str, int] = {}

    # Pass 1: unique IDs
    for emp in employees:
        record = dict(emp)
        name = str(record.get("name", "")).strip()
        raw_id = str(record.get("employee_id") or "").strip()
        if _is_root_marker(raw_id):
            raw_id = name
        emp_id = raw_id
        if emp_id in seen_ids:
            seen_ids[emp_id] += 1
            emp_id = f"{raw_id}#{seen_ids[raw_id]}"
            issues.append(
                f"Duplicate Employee ID '{raw_id}' (for {name}) — treated as a separate person; "
                f"give each person a unique Employee ID for reliable reporting lines"
            )
        else:
            seen_ids[emp_id] = 1
        record["employee_id"] = emp_id
        normalized.append(record)

    ids = {r["employee_id"] for r in normalized}
    by_name: Dict[str, List[Dict]] = {}
    for r in normalized:
        by_name.setdefault(str(r.get("name", "")).strip(), []).append(r)

    duplicate_names = {n for n, rs in by_name.items() if len(rs) > 1 and n}
    if duplicate_names:
        issues.append(
            f"{len(duplicate_names)} name(s) are shared by more than one person "
            f"({', '.join(sorted(duplicate_names)[:5])}) — kept as separate people by Employee ID"
        )

    # Pass 2: resolve managers
    for r in normalized:
        r["manager_id"] = _resolve_manager(r, ids, by_name, issues)

    return normalized, issues


def _resolve_manager(record: Dict, ids: set, by_name: Dict[str, List[Dict]], issues: List[str]) -> Optional[str]:
    name = record.get("name", "")
    explicit = record.get("manager_id")
    if explicit is not None and not _is_root_marker(explicit):
        explicit = str(explicit).strip()
        if explicit in ids and explicit != record["employee_id"]:
            return explicit
        issues.append(f"Line Manager ID '{explicit}' for {name} does not match any Employee ID")
        return None

    mgr_value = record.get("manager_name", "")
    if _is_root_marker(mgr_value):
        return None
    mgr_value = str(mgr_value).strip()

    if mgr_value in ids and mgr_value != record["employee_id"]:
        return mgr_value

    candidates = [c for c in by_name.get(mgr_value, []) if c["employee_id"] != record["employee_id"]]
    if len(candidates) == 1:
        return candidates[0]["employee_id"]
    if not candidates:
        issues.append(f"Manager not found for {name}: '{mgr_value}'")
        return None

    # Several people share the manager's name: use the one a level above
    level = record.get("level")
    one_up = [c for c in candidates if level and c.get("level") == level - 1]
    if len(one_up) == 1:
        issues.append(
            f"Line Manager '{mgr_value}' for {name} matches {len(candidates)} people — "
            f"matched by level; add a 'Line Manager ID' column to remove the guesswork"
        )
        return one_up[0]["employee_id"]
    issues.append(
        f"Line Manager '{mgr_value}' for {name} matches {len(candidates)} people and could not be "
        f"resolved — add a 'Line Manager ID' column"
    )
    return None


def build_org_graph(employees: List[Dict]) -> nx.DiGraph:
    """Build a manager -> direct-report graph from normalized employee records."""
    G = nx.DiGraph()
    for emp in employees:
        G.add_node(emp["employee_id"], **emp)
    for emp in employees:
        mgr = emp.get("manager_id")
        if mgr and mgr in G and mgr != emp["employee_id"]:
            G.add_edge(mgr, emp["employee_id"])
    return G


def display_name(G: nx.DiGraph, node_id: str) -> str:
    """Human-readable name for a node, falling back to its ID."""
    return G.nodes[node_id].get("name") or node_id
