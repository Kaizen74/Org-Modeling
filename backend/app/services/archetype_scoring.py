"""
Deterministic archetype scoring.

The AI scores each archetype on five criteria; the overall score is then
computed here from the published weights instead of trusting the AI's own
arithmetic. The AI's figure is kept for transparency, and any disagreement
between the AI's top picks and the weighted ranking is reported.
"""

from typing import Dict, List, Optional

from ..resources.archetypes_reference import SCORING_WEIGHTS

DISCREPANCY_THRESHOLD = 3  # points; smaller differences are rounding


def _criterion_value(value) -> Optional[float]:
    """Breakdown entries are either a number or {"score": n, "rationale": ...}."""
    if isinstance(value, dict):
        value = value.get("score")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def weighted_score(breakdown: Dict) -> Optional[int]:
    """Overall 0-100 score from the five criteria, or None if any criterion is missing."""
    if not isinstance(breakdown, dict):
        return None
    total = 0.0
    for criterion, weight in SCORING_WEIGHTS.items():
        value = _criterion_value(breakdown.get(criterion))
        if value is None:
            return None
        total += max(0.0, min(100.0, value)) * weight
    return round(total / sum(SCORING_WEIGHTS.values()))


def _apply(entry: Dict, score_key: str) -> None:
    """Replace entry[score_key] with the weighted score, keeping the AI's value."""
    computed = weighted_score(entry.get("score_breakdown"))
    if "ai_overall_score" not in entry:
        entry["ai_overall_score"] = entry.get(score_key)
    if computed is None:
        entry["scoring_method"] = "ai_reported"
        return
    entry[score_key] = computed
    entry["scoring_method"] = "weighted"
    ai_value = _criterion_value(entry.get("ai_overall_score"))
    entry["score_discrepancy"] = (
        round(ai_value - computed) if ai_value is not None and abs(ai_value - computed) >= DISCREPANCY_THRESHOLD else 0
    )


def reconcile_archetype_scores(result: Dict) -> Dict:
    """
    Recompute archetype scores in an analysis result in place (idempotent).
    Works on the current object format of category_4 and leaves the legacy
    list format untouched.
    """
    category = result.get("category_4_recommended_archetypes") if isinstance(result, dict) else None
    if not isinstance(category, dict):
        return result

    all_scores: List[Dict] = [s for s in category.get("all_archetype_scores") or [] if isinstance(s, dict)]
    for entry in all_scores:
        _apply(entry, "overall_score")
    all_scores.sort(key=lambda s: s.get("overall_score") or 0, reverse=True)
    for i, entry in enumerate(all_scores, 1):
        entry["weighted_rank"] = i
    if all_scores:
        category["all_archetype_scores"] = all_scores

    recommendations: List[Dict] = [r for r in category.get("recommendations") or [] if isinstance(r, dict)]
    for rec in recommendations:
        _apply(rec, "overall_fit_score")

    # Do the AI's recommended archetypes match the top of the weighted ranking?
    weighted_top = [s.get("archetype_id") for s in all_scores[: len(recommendations)] if s.get("scoring_method") == "weighted"]
    recommended = [r.get("archetype_id") for r in recommendations]
    if weighted_top and recommended and set(weighted_top) != set(recommended):
        names = {s.get("archetype_id"): s.get("archetype_name") for s in all_scores}
        missing = [names.get(a, a) for a in weighted_top if a not in recommended]
        category["ranking_note"] = (
            f"By the weighted criteria, {', '.join(missing)} ranks in the top {len(recommendations)} "
            f"but was not among the AI's detailed recommendations — review its fit before deciding."
        )
    else:
        category.pop("ranking_note", None)

    category["scoring_weights"] = dict(SCORING_WEIGHTS)
    return result
