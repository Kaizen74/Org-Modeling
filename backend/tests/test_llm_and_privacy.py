"""
Tests for the shared Claude call path, name removal from AI prompts, and the
org-composition context — all with a fake client (no network, no cost).
"""

import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import llm_client
from app.services.llm_client import run_analysis, AnalysisRefused
from app.services.ai_analysis_service import AIAnalysisService
from app.services.work_activities_service import WorkActivitiesAnalysisService
from app.services.metrics_service import MetricsCalculator


class _Stream:
    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._message


class FakeClient:
    """Records the request and returns a canned message with a thinking block first."""

    def __init__(self, text="{}", stop_reason="end_turn", category=None):
        self.calls = []
        message = SimpleNamespace(
            model="claude-opus-5-5",
            stop_reason=stop_reason,
            stop_details=SimpleNamespace(category=category) if category else None,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        )
        outer = self

        class _Messages:
            def stream(self, **kwargs):
                outer.calls.append(kwargs)
                return _Stream(message)

        self.beta = SimpleNamespace(messages=_Messages())


def test_run_analysis_uses_configured_model_and_skips_thinking():
    client = FakeClient(text='{"ok": true}')
    text, meta = run_analysis(client, "prompt")
    assert text == '{"ok": true}'
    call = client.calls[0]
    assert call["model"] == llm_client.MODEL == "claude-opus-5-5"
    assert call["output_config"] == {"effort": llm_client.EFFORT}
    assert call["fallbacks"] == "default"
    assert llm_client.FALLBACK_BETA in call["betas"]
    assert "temperature" not in call  # rejected by the API since 2026-10-21
    assert meta["truncated"] is False


def test_refusal_raises_and_truncation_is_flagged():
    try:
        run_analysis(FakeClient(stop_reason="refusal", category="cyber"), "prompt")
        assert False, "expected AnalysisRefused"
    except AnalysisRefused as e:
        assert "cyber" in str(e)
    _, meta = run_analysis(FakeClient(stop_reason="max_tokens"), "prompt")
    assert meta["truncated"] is True


def test_work_activities_reads_answer_after_thinking_block(sample_employees):
    employees = [dict(e, work_activities="planning and reporting") for e in sample_employees]
    service = WorkActivitiesAnalysisService()
    service.client = FakeClient(text='```json\n{"executive_summary": "ok"}\n```')
    result = asyncio.run(service.analyze_work_activities(employees))
    assert result["executive_summary"] == "ok"
    assert result["_llm"]["model_served"] == "claude-opus-5-5"


def test_archetype_analysis_end_to_end_with_fake_client(sample_employees):
    service = AIAnalysisService(api_key=None)
    payload = {"executive_summary": "ok", "category_4_recommended_archetypes": {"all_archetype_scores": [
        {"archetype_id": "1_functional", "archetype_name": "Functional", "overall_score": 99,
         "score_breakdown": {"industry_match": 50, "size_match": 50, "revenue_model_match": 50,
                             "key_indicators_match": 50, "metrics_match": 50}}]}}
    service.client = FakeClient(text=json.dumps(payload))
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    result = asyncio.run(service.analyze_organization(metrics=metrics, employees=sample_employees))
    assert result["executive_summary"] == "ok"
    # weighted scoring applied on the live path
    assert result["category_4_recommended_archetypes"]["all_archetype_scores"][0]["overall_score"] == 50


def test_no_personal_names_in_any_ai_prompt(sample_employees):
    employees = [dict(e, name=f"Person Zeta{i}", work_activities="budgeting, hiring")
                 for i, e in enumerate(sample_employees)]
    for i, e in enumerate(employees):
        if i:
            e["manager_name"] = "Person Zeta0"
    metrics = MetricsCalculator(employees=employees).calculate_all_metrics()

    archetype_prompt = AIAnalysisService(api_key=None)._build_prompt(
        metrics, employees, None, None, "department", "Sales", None)
    wa_prompt = WorkActivitiesAnalysisService()._build_prompt(employees, industry=None)
    for prompt in (archetype_prompt, wa_prompt):
        assert "Zeta" not in prompt


def test_archetype_prompt_includes_actual_departments_and_roles(sample_employees):
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    prompt = AIAnalysisService(api_key=None)._build_prompt(
        metrics, sample_employees, None, None, "department", "Sales", None)
    assert "ORGANIZATION COMPOSITION" in prompt
    assert "- Sales: 5 people" in prompt  # VP Sales, Sales Manager, Team Lead, 2 Associates
    assert "Operations" in prompt
    assert "Sales Manager" in prompt  # role titles, not names
    assert "All roles in Sales" in prompt


def test_department_analysis_in_metrics(sample_employees):
    depts = {d["department"]: d for d in MetricsCalculator(employees=sample_employees).calculate_all_metrics()["department_analysis"]}
    assert depts["Sales"]["headcount"] == 5  # VP1, Mgr1, Lead1, IC1, IC2
    assert depts["Sales"]["managers"] == 3  # VP1, Mgr1, Lead1
    # VP1 (Sales) reports to the CEO in Executive
    assert depts["Sales"]["reports_from_other_departments"] == 1
    assert sum(d["headcount"] for d in depts.values()) == 8


def test_prompts_request_five_dimension_tags(sample_employees):
    from app.resources.benchmarks_reference import FIVE_DIMENSIONS
    employees = [dict(e, work_activities="planning") for e in sample_employees]
    wa_prompt = WorkActivitiesAnalysisService()._build_prompt(employees, industry=None)
    assert all(d in wa_prompt for d in FIVE_DIMENSIONS)
    assert '"indicator_type": "Leading/Lagging"' in wa_prompt
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    archetype_prompt = AIAnalysisService(api_key=None)._build_prompt(metrics, sample_employees, None, None)
    assert '"dimension": "One of: Structure & Accountabilities' in archetype_prompt
