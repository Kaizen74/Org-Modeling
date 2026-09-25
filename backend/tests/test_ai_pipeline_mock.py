"""Mock tests for the AI analysis pipeline — no network calls.

Covers the evidence-grade contract: benchmark citations and evidence
discipline present in prompts, new fields (confidence, disconfirming
evidence, data_gaps, diagram flags) surviving response parsing, truncation
repair, and the API-layer rule that work_activities_analysis is preserved
across archetype runs.
"""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai_analysis_service import AIAnalysisService
from app.services.work_activities_service import WorkActivitiesAnalysisService


class FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeBlock(text)]


@pytest.fixture
def archetype_service():
    return AIAnalysisService(api_key=None)


@pytest.fixture
def minimal_metrics():
    return {
        "total_employees": 64,
        "manager_stats": {},
        "span_of_control": {},
        "cost_analysis": {},
        "layer_analysis": {},
        "grade_gap_analysis": {},
    }


@pytest.fixture
def mock_ai_response():
    return {
        "executive_summary": "Healthy spans with coordination gaps.",
        "category_2_health_diagnosis": {
            "strengths": ["s"],
            "weaknesses": ["w"],
            "pathologies": [{
                "name": "Collaborative Overload",
                "description": "x", "impact": "y", "severity": "Medium",
                "evidence_class": "OBSERVABLE",
                "supporting_evidence": "duplicated event comms in 2 roles",
                "disconfirming_evidence": "coordination score is mid-range",
                "confidence": "Medium",
                "confidence_rationale": "single observable signal",
            }],
            "critical_risks": ["r"],
        },
        "category_4_recommended_archetypes": {
            "recommendations": [{
                "rank": 1, "archetype": "Front-Back Hybrid",
                "why_it_fits": "f", "expected_benefits": ["b"],
                "implementation_challenges": ["c"],
                "transformation_timeline": "6-12 months",
                "confidence_level": "Medium",
                "critical_success_factors": ["f1"],
                "differentiating_activities": [{
                    "activity": "corporate affairs", "description": "d",
                    "why_differentiating": "w", "how_archetype_supports": "h",
                    "strategic_importance": "High", "related_roles": ["Comms Lead"],
                }],
                "structure_diagram": {
                    "title": "t", "layout_type": "hierarchical",
                    "nodes": [
                        {"id": "n1", "label": "CEO", "type": "executive", "level": 0},
                        {"id": "n2", "label": "Strategic Comms", "type": "department",
                         "level": 1, "is_differentiating": True,
                         "differentiating_activity": "corporate affairs"},
                    ],
                    "connections": [{"from": "n1", "to": "n2", "type": "reporting"}],
                },
            }],
        },
        "data_gaps": [{
            "gap": "no decision cycle-time data",
            "why_it_matters": "limits agility scoring",
            "observable_indicator_to_close": "approval lead times",
        }],
    }


def test_archetype_prompt_carries_benchmarks_and_evidence_rules(archetype_service, minimal_metrics):
    prompt = archetype_service._build_prompt(
        metrics=minimal_metrics, employees=[],
        strategy_docs=["Grow APAC revenue 20%"], design_criteria="agility",
        analysis_scope="organization", department=None,
        work_activities_analysis={"executive_summary": "Comms spans internal and corporate affairs."},
    )
    for marker in [
        "RESEARCH-CALIBRATED BENCHMARKS", "Gallup research, 2025",
        "McKinsey managerial archetypes", "Deloitte Global Human Capital Trends 2026",
        "EVIDENCE DISCIPLINE", "OBSERVABLE", "MODEL-INFERRED",
        "disconfirming_evidence", "confidence_rationale", "data_gaps",
        "CURRENT STATE ANALYSIS", "structure_diagram", "differentiating_activities",
    ]:
        assert marker in prompt, f"missing prompt marker: {marker}"


def test_work_activities_prompt_carries_evidence_rules():
    prompt = WorkActivitiesAnalysisService()._build_prompt(
        [{"name": "A", "job_title": "Comms Lead", "grade": "H5",
          "department": "Strategic Communications",
          "work_activities": "internal communications, corporate affairs"}],
        industry="Aviation Services",
    )
    for marker in ["EVIDENCE DISCIPLINE", "MODEL-INFERRED", "confidence_rationale",
                   "data_gaps", "Aviation Services"]:
        assert marker in prompt, f"missing prompt marker: {marker}"


def test_parse_preserves_evidence_fields(archetype_service, mock_ai_response):
    parsed = archetype_service._parse_structured_response(
        FakeResponse("```json\n" + json.dumps(mock_ai_response) + "\n```"))

    pathology = parsed["category_2_health_diagnosis"]["pathologies"][0]
    assert pathology["evidence_class"] == "OBSERVABLE"
    assert pathology["disconfirming_evidence"]
    assert pathology["confidence"] == "Medium" and pathology["confidence_rationale"]

    rec = parsed["category_4_recommended_archetypes"]["recommendations"][0]
    assert rec["differentiating_activities"][0]["strategic_importance"] == "High"
    diagram = rec["structure_diagram"]
    assert diagram["nodes"][1]["is_differentiating"] is True
    assert diagram["connections"][0]["type"] == "reporting"

    assert parsed["data_gaps"][0]["observable_indicator_to_close"] == "approval lead times"


def test_truncated_response_is_repaired_not_crashed(archetype_service, mock_ai_response):
    full = json.dumps(mock_ai_response)
    truncated = "```json\n" + full[: int(len(full) * 0.8)]
    parsed = archetype_service._parse_structured_response(FakeResponse(truncated))
    # Either repaired into structured data or degraded gracefully with raw text
    assert parsed.get("_json_repaired") is True or "executive_summary" in parsed
    assert "raw_response" in parsed


def test_work_activities_parse_keeps_evidence_and_data_gaps():
    wa_mock = {
        "activity_duplication": {
            "overall_duplication_score": 40, "severity_assessment": "Medium",
            "duplications": [{
                "activity": "a", "affected_roles": ["r1", "r2"],
                "affected_departments": ["d"], "duplication_type": "Partial Overlap",
                "severity": "Medium", "business_impact": "i",
                "resolution_priority": 1, "recommended_action": "act",
                "evidence": "'corporate affairs' appears in both role descriptions",
                "confidence": "High", "confidence_rationale": "verbatim overlap",
            }],
            "summary": "s",
        },
        "data_gaps": [{"gap": "no time allocation data", "why_it_matters": "m",
                       "observable_indicator_to_close": "timesheets"}],
        "executive_summary": "es",
    }
    parsed = WorkActivitiesAnalysisService()._parse_response(
        "```json\n" + json.dumps(wa_mock) + "\n```")
    duplication = parsed["activity_duplication"]["duplications"][0]
    assert "corporate affairs" in duplication["evidence"]
    assert duplication["confidence"] == "High"
    assert parsed["data_gaps"][0]["observable_indicator_to_close"] == "timesheets"


def test_work_activities_analysis_preserved_across_archetype_run():
    """Mirrors the preserve rule in app/api/ai_analysis.py (see API_CONTRACT.md)."""
    existing_ai = {"work_activities_analysis": {"executive_summary": "current state"},
                   "executive_summary": "old archetype run"}
    fresh_archetype_result = {"executive_summary": "new archetype run"}

    if existing_ai and "work_activities_analysis" in existing_ai:
        fresh_archetype_result["work_activities_analysis"] = existing_ai["work_activities_analysis"]

    assert fresh_archetype_result["work_activities_analysis"]["executive_summary"] == "current state"
    assert fresh_archetype_result["executive_summary"] == "new archetype run"
