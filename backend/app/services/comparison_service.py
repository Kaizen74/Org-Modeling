"""
Option comparison: score the current state and each scenario against the
designer's weighted criteria.

Two kinds of criteria:
- measured: scored from scenario figures (cost, layers, spans within
  benchmark, share of people affected...). Options are placed 0-100 between
  the worst and best value among the options compared.
- judged: scored 1-5 by the designer (or suggested by the AI, which the
  designer can override); 1 → 0, 5 → 100.

All arithmetic happens here, so totals and rankings are repeatable.
"""

from typing import Dict, List, Optional

# Figures a measured criterion can use, and which direction is better by default
MEASURABLE = {
    "total_cost": {"label": "People cost", "better": "lower"},
    "layers": {"label": "Layers", "better": "lower"},
    "spans_within_benchmark": {"label": "Managers within span benchmark", "better": "higher"},
    "single_report_managers": {"label": "Single-report managers", "better": "lower"},
    "health_score": {"label": "Structural health", "better": "higher"},
    "manager_ratio_pct": {"label": "Manager ratio %", "better": "lower"},
    "headcount": {"label": "People", "better": "lower"},
    "people_affected_pct": {"label": "Share of people affected", "better": "lower"},
    "ai_capacity_fte": {"label": "Capacity freed by AI (FTE, optional overlay)", "better": "higher"},
}

DEFAULT_CRITERIA = [
    {"id": "strategy_fit", "name": "Fit with the strategy", "kind": "judged", "weight": 25,
     "description": "How directly the structure enables the stated strategic priorities"},
    {"id": "cost", "name": "Cost efficiency", "kind": "measured", "metric": "total_cost", "better": "lower", "weight": 20},
    {"id": "decision_speed", "name": "Decision speed (fewer layers)", "kind": "measured", "metric": "layers", "better": "lower", "weight": 15},
    {"id": "manager_capacity", "name": "Manager capacity (spans fit the work)", "kind": "measured", "metric": "spans_within_benchmark", "better": "higher", "weight": 15},
    {"id": "customer_focus", "name": "Customer and service focus", "kind": "judged", "weight": 15,
     "description": "How clearly accountability for customer outcomes is placed"},
    {"id": "disruption", "name": "Low disruption", "kind": "measured", "metric": "people_affected_pct", "better": "lower", "weight": 10},
]


def validate_criteria(criteria: List[Dict]) -> List[str]:
    """Plain-language problems with a criteria set (empty list = valid)."""
    problems = []
    ids = set()
    for c in criteria:
        name = c.get("name") or c.get("id") or "A criterion"
        if not c.get("id"):
            problems.append(f"{name} needs an id")
        elif c["id"] in ids:
            problems.append(f"Two criteria share the id '{c['id']}'")
        ids.add(c.get("id"))
        if c.get("kind") not in ("measured", "judged"):
            problems.append(f"{name}: kind must be 'measured' or 'judged'")
        if c.get("kind") == "measured" and c.get("metric") not in MEASURABLE:
            problems.append(f"{name}: unknown measure '{c.get('metric')}'")
        if c.get("kind") == "measured" and c.get("better", MEASURABLE.get(c.get("metric"), {}).get("better")) not in ("higher", "lower"):
            problems.append(f"{name}: 'better' must be 'higher' or 'lower'")
        try:
            if float(c.get("weight", 0)) < 0:
                problems.append(f"{name}: weight can't be negative")
        except (TypeError, ValueError):
            problems.append(f"{name}: weight must be a number")
    if criteria and sum(float(c.get("weight", 0) or 0) for c in criteria) <= 0:
        problems.append("At least one criterion needs a weight above zero")
    return problems


def _measured_scores(values: Dict[str, Optional[float]], better: str) -> Dict[str, Optional[float]]:
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {k: None for k in values}
    lo, hi = min(present.values()), max(present.values())
    out: Dict[str, Optional[float]] = {}
    for k, v in values.items():
        if v is None:
            out[k] = None
        elif hi == lo:
            out[k] = 100.0  # no difference between options on this measure
        else:
            frac = (v - lo) / (hi - lo)
            out[k] = round(100 * (frac if better == "higher" else 1 - frac), 1)
    return out


def score_options(options: List[Dict], criteria: List[Dict], judgments: Dict[str, Dict[str, Dict]]) -> Dict:
    """
    options: [{id, name, figures: {metric: value}}]
    judgments: {option_id: {criterion_id: {score: 1-5, rationale, source}}}
    Returns per-option criterion scores (0-100), weighted totals, ranking and
    which judged scores are still missing.
    """
    cells: Dict[str, Dict[str, Optional[float]]] = {o["id"]: {} for o in options}
    for c in criteria:
        if c["kind"] == "measured":
            better = c.get("better") or MEASURABLE[c["metric"]]["better"]
            per_option = _measured_scores({o["id"]: o["figures"].get(c["metric"]) for o in options}, better)
            for oid, s in per_option.items():
                cells[oid][c["id"]] = s
        else:
            for o in options:
                j = (judgments.get(o["id"]) or {}).get(c["id"]) or {}
                raw = j.get("score")
                cells[o["id"]][c["id"]] = round((float(raw) - 1) * 25, 1) if raw not in (None, "") else None

    totals, missing = {}, {}
    for o in options:
        num = den = 0.0
        missing[o["id"]] = []
        for c in criteria:
            w = float(c.get("weight", 0) or 0)
            s = cells[o["id"]].get(c["id"])
            if s is None:
                if w > 0:
                    missing[o["id"]].append(c["id"])
                continue
            num += w * s
            den += w
        totals[o["id"]] = round(num / den, 1) if den else None

    ranked = sorted([o["id"] for o in options if totals[o["id"]] is not None], key=lambda oid: -totals[oid])
    return {
        "cells": cells,
        "totals": totals,
        "ranking": ranked,
        "missing": missing,
        "complete": all(not m for m in missing.values()),
    }
