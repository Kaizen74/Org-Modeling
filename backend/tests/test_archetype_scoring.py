"""Tests for deterministic weighted archetype scoring."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.archetype_scoring import reconcile_archetype_scores, weighted_score


def _summary(aid, name, ai_overall, breakdown):
    return {"archetype_id": aid, "archetype_name": name, "overall_score": ai_overall,
            "score_breakdown": breakdown, "fit_summary": "", "digital_first_applicable": True}


FUNCTIONAL = {"industry_match": 80, "size_match": 70, "revenue_model_match": 60, "key_indicators_match": 90, "metrics_match": 50}
HYBRID = {"industry_match": 60, "size_match": 60, "revenue_model_match": 60, "key_indicators_match": 60, "metrics_match": 60}
PROCESS = {"industry_match": 90, "size_match": 90, "revenue_model_match": 90, "key_indicators_match": 90, "metrics_match": 90}


def test_weighted_score_uses_published_weights():
    # 80*.30 + 70*.15 + 60*.20 + 90*.25 + 50*.10 = 24 + 10.5 + 12 + 22.5 + 5 = 74
    assert weighted_score(FUNCTIONAL) == 74
    assert weighted_score({"industry_match": {"score": 100, "rationale": "x"}, "size_match": 100,
                           "revenue_model_match": 100, "key_indicators_match": 100, "metrics_match": 100}) == 100


def test_missing_criterion_falls_back_to_ai_score():
    result = {"category_4_recommended_archetypes": {"all_archetype_scores": [
        _summary("1_functional", "Functional", 66, {"industry_match": 80})]}}
    reconcile_archetype_scores(result)
    entry = result["category_4_recommended_archetypes"]["all_archetype_scores"][0]
    assert entry["overall_score"] == 66
    assert entry["scoring_method"] == "ai_reported"


def test_ai_arithmetic_is_overridden_and_discrepancy_recorded():
    result = {"category_4_recommended_archetypes": {"all_archetype_scores": [
        _summary("1_functional", "Functional", 90, FUNCTIONAL)]}}
    reconcile_archetype_scores(result)
    entry = result["category_4_recommended_archetypes"]["all_archetype_scores"][0]
    assert entry["overall_score"] == 74
    assert entry["ai_overall_score"] == 90
    assert entry["score_discrepancy"] == 16
    assert entry["scoring_method"] == "weighted"


def test_ranking_reordered_and_mismatch_with_recommendations_flagged():
    result = {"category_4_recommended_archetypes": {
        "all_archetype_scores": [
            _summary("1_functional", "Functional", 95, FUNCTIONAL),   # weighted 74
            _summary("3_front_back_hybrid", "Front-Back", 94, HYBRID),  # weighted 60
            _summary("4_process_based", "Process-Based", 50, PROCESS),  # weighted 90
        ],
        "recommendations": [
            {"rank": 1, "archetype_id": "1_functional", "archetype": "Functional", "overall_fit_score": 95,
             "score_breakdown": FUNCTIONAL},
            {"rank": 2, "archetype_id": "3_front_back_hybrid", "archetype": "Front-Back", "overall_fit_score": 94,
             "score_breakdown": HYBRID},
        ]}}
    reconcile_archetype_scores(result)
    cat = result["category_4_recommended_archetypes"]
    assert [s["archetype_id"] for s in cat["all_archetype_scores"]] == ["4_process_based", "1_functional", "3_front_back_hybrid"]
    assert cat["all_archetype_scores"][0]["weighted_rank"] == 1
    assert cat["recommendations"][0]["overall_fit_score"] == 74
    assert "Process-Based" in cat["ranking_note"]
    assert cat["scoring_weights"]["industry_match"] == 30


def test_reconcile_is_idempotent_and_keeps_original_ai_value():
    result = {"category_4_recommended_archetypes": {"all_archetype_scores": [
        _summary("1_functional", "Functional", 90, FUNCTIONAL)]}}
    reconcile_archetype_scores(result)
    reconcile_archetype_scores(result)
    entry = result["category_4_recommended_archetypes"]["all_archetype_scores"][0]
    assert entry["ai_overall_score"] == 90
    assert entry["overall_score"] == 74


def test_legacy_and_empty_results_untouched():
    assert reconcile_archetype_scores({"category_4_recommended_archetypes": [{"archetype": "x"}]}) == \
        {"category_4_recommended_archetypes": [{"archetype": "x"}]}
    assert reconcile_archetype_scores({"error": "no key"}) == {"error": "no key"}


def test_real_department_names_map_to_guidance():
    from app.resources.archetypes_reference import match_department_key
    assert match_department_key("Ground Operations") == "manufacturing_operations"
    assert match_department_key("Finance") == "finance"
    assert match_department_key("Human Resources") == "hr"
    assert match_department_key("Passenger Services") == "passenger_services"
    assert match_department_key("Digital & Technology") == "it_digital"
    assert match_department_key("Customer Experience") == "service_delivery"
    assert match_department_key("Strategic Communications") == ""  # no guidance: say nothing rather than guess


def test_department_scope_prompt_includes_guidance(sample_employees):
    from app.services.ai_analysis_service import AIAnalysisService
    from app.services.metrics_service import MetricsCalculator
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    prompt = AIAnalysisService(api_key=None)._build_prompt(metrics, sample_employees, None, None, "department", "Sales")
    assert "DEPARTMENT-SPECIFIC GUIDANCE FOR SALES" in prompt
