"""
Test-only launcher: the real backend with Claude replaced by a deterministic fake.
Used by run_checks.sh step 5 (mock journey); never used by the app itself.

The fake reads each prompt and answers in the shape the real model is asked
for, using names it finds in the prompt (departments, option ids, job titles),
and logs every prompt so the test can check nothing private was sent.
Usage: python fake_claude_server.py <port> <db_path> <prompt_log_path> <backend_dir>
Run it from a scratch folder: saving the API key writes a .env file to the current folder.
"""
import json
import re
import sys

port, db_path, log_path, backend_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
import os
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, backend_dir)

from app.main import app  # noqa: E402
from app.services import ai_analysis_service, work_activities_service, claude_service as cs  # noqa: E402
from app.api import comparison as comparison_api, ai_disposition as disposition_api  # noqa: E402


def _log(kind, prompt):
    with open(log_path, "a") as f:
        f.write(json.dumps({"kind": kind, "prompt": prompt}) + "\n")


def _wrap(obj):
    return "Here is the analysis.\n```json\n" + json.dumps(obj) + "\n```"


def _work_activities(prompt):
    return {
        "executive_summary": "Reporting is duplicated across three departments; peak-season planning is missing; the ramp-to-baggage hand-off lacks an owner.",
        "work_activities_summary": {"total_positions_analyzed": 150, "departments_analyzed": 5, "positions_with_activities": 150, "industry_context": "Aviation ground services"},
        "activity_duplication": {"overall_duplication_score": 55, "severity_assessment": "Medium", "summary": "Stakeholder reporting is produced in three places.",
            "duplications": [{"activity": "Stakeholder reporting", "affected_roles": ["CX Insights Analyst", "Finance Executive"], "affected_departments": ["Customer Experience", "Finance"],
                              "duplication_type": "Partial Overlap", "severity": "High", "business_impact": "Conflicting numbers", "resolution_priority": 1,
                              "recommended_action": "One reporting owner", "evidence": "'stakeholder reporting' in both", "confidence": "High",
                              "confidence_rationale": "verbatim", "dimension": "Process & Systems", "indicator_type": "Leading"}]},
        "missing_activities": {"overall_gap_score": 40, "severity_assessment": "Moderate", "summary": "No peak planning.",
            "gaps": [{"activity": "Peak-season workforce planning", "industry_benchmark": "Central rostering (inferred)", "affected_roles": ["Manager, Ramp Operations"],
                      "affected_departments": ["Ground Operations"], "severity": "Critical", "business_risk": "Overtime spikes", "recommendation": "Add a rostering role",
                      "confidence": "Medium", "confidence_rationale": "model-inferred", "dimension": "People & Skills", "indicator_type": "Leading"}]},
        "coordination_gaps": {"overall_coordination_score": 55, "severity_assessment": "Moderate", "summary": "Turnaround has no owner.",
            "gaps": [{"handoff_point": "Ramp to baggage", "from_department": "Ground Operations", "to_department": "Ground Operations", "from_roles": ["Ramp Team Lead"],
                      "to_roles": ["Baggage Team Lead"], "current_state": "Radio calls", "gap_type": "Unclear Ownership", "severity": "Important",
                      "industry_practice": "Turnaround coordinator", "recommended_interface": "Coordinator role", "confidence": "Medium",
                      "confidence_rationale": "role text", "dimension": "Process & Systems", "indicator_type": "Lagging"}]},
        "departmental_coherence": [{"department": "Ground Operations", "position_count": 90, "coherence_score": 80, "coherence_rationale": "Clear chain",
                                    "synergy_assessment": {"strengths": ["Crew structure"], "gaps": ["Forecasting"], "overlaps": []}, "value_chain_position": "Front-line", "key_activities": ["ramp"]}],
        "overall_coherence": {"organization_coherence_score": 62, "cross_department_synergies": ["CX insight"], "cross_department_gaps": ["Reporting x3"], "integration_assessment": "Side by side"},
        "recommendations": {"quick_wins": ["Name a reporting owner"], "coordination_improvements": [{"recommendation": "Turnaround coordinator", "addresses": "Ramp to baggage", "priority": "High", "effort": "Medium"}]},
        "data_gaps": [{"gap": "Time spent on reporting", "why_it_matters": "Sizes saving", "observable_indicator_to_close": "Time-allocation sample"}],
    }


def _archetype(prompt):
    depts = re.findall(r"^- (.+?): \d+ people", prompt, flags=re.M)
    bd = lambda *v: dict(zip(["industry_match", "size_match", "revenue_model_match", "key_indicators_match", "metrics_match"], v))
    nodes = [{"id": "top", "label": "Chief Executive Officer", "type": "executive", "level": 0, "source_departments": [depts[-1]] if depts else []}]
    for i, d in enumerate(depts[:-1] or depts):
        nodes.append({"id": f"u{i}", "label": d, "type": "department", "level": 1, "source_departments": [d], "is_differentiating": i == 1})
    nodes.append({"id": "ghost", "label": "Marketing", "type": "department", "level": 1, "source_departments": ["Marketing"]})  # invented
    nodes.append({"id": "new", "label": "Turnaround Control", "type": "team", "level": 2, "is_new": True, "source_departments": []})
    diagram = {"title": "Front end / shared back end", "layout_type": "hierarchical", "nodes": nodes,
               "connections": [{"from": "top", "to": n["id"], "type": "reporting"} for n in nodes[1:]]}
    rec = lambda rank, aid, name, b: {"rank": rank, "archetype_id": aid, "archetype": name, "overall_fit_score": 99, "score_breakdown": b,
        "why_it_fits": f"Fits because of {', '.join(depts[:2])}", "expected_benefits": ["One customer owner"], "implementation_challenges": ["Interfaces"],
        "transformation_timeline": "6-12 months", "confidence_level": "Medium", "critical_success_factors": ["Clear interfaces"],
        "differentiating_activities": [{"activity": "Service design", "description": "d", "why_differentiating": "w", "how_archetype_supports": "h", "strategic_importance": "High", "related_roles": ["Service Design Analyst"]}],
        "structure_diagram": diagram}
    return {
        "executive_summary": "Mock archetype analysis.",
        "category_1_industry_trends": {"insights": [{"topic": "Spans", "finding": "Average span 12.1 (2025)", "source": "Gallup research, 2025", "relevance_to_org": "Below trend"}]},
        "category_2_health_diagnosis": {"strengths": ["Frontline spans"], "weaknesses": ["CX layers"], "critical_risks": ["Latency"],
            "pathologies": [{"name": "Frozen Middle", "description": "x", "impact": "y", "severity": "High", "evidence_class": "OBSERVABLE", "supporting_evidence": "single-report managers",
                             "disconfirming_evidence": "Ground Ops healthy", "confidence": "High", "confidence_rationale": "counted", "dimension": "Structure & Accountabilities"}]},
        "category_3_strategy_alignment": {"scores": {k: {"score": 50, "rationale": "r"} for k in ["strategic_clarity", "execution_readiness", "efficiency", "agility"]},
                                          "overall_alignment_score": 50, "alignment_grade": "C", "key_gaps": ["Turnaround owner"]},
        "category_4_recommended_archetypes": {
            "all_archetype_scores": [
                {"archetype_id": "1_functional", "archetype_name": "Functional", "overall_score": 95, "score_breakdown": bd(60, 60, 60, 60, 60), "fit_summary": "AI over-scored", "digital_first_applicable": True},
                {"archetype_id": "3_front_back_hybrid", "archetype_name": "Front-Back Hybrid", "overall_score": 70, "score_breakdown": bd(80, 70, 70, 80, 60), "fit_summary": "s", "digital_first_applicable": True},
                {"archetype_id": "4_process_based", "archetype_name": "Process-Based", "overall_score": 68, "score_breakdown": bd(75, 70, 65, 70, 60), "fit_summary": "s", "digital_first_applicable": True},
            ],
            "recommendations": [rec(1, "1_functional", "Functional Structure", bd(60, 60, 60, 60, 60)), rec(2, "3_front_back_hybrid", "Front-Back Hybrid", bd(80, 70, 70, 80, 60))],
        },
        "action_plan": {"phase_1_quick_wins": ["a"], "phase_2_structural": ["b"], "phase_3_optimization": ["c"]},
        "data_gaps": [{"gap": "Decision cycle time", "why_it_matters": "Agility", "observable_indicator_to_close": "Approval lead times"}],
    }


def _suggest(prompt):
    options = re.findall(r"option_id=(\S+)", prompt)
    criteria = re.findall(r"criterion_id=(\S+):", prompt)
    return {"suggestions": [{"option_id": o, "criterion_id": c, "score": 3 + (i % 2), "rationale": "Cites moves", "evidence_class": "OBSERVABLE", "confidence": "Medium"}
                            for i, (o, c) in enumerate((o, c) for o in options for c in criteria)] + [{"option_id": "ghost", "criterion_id": "x", "score": 5}]}


def _disposition(prompt):
    titles = re.findall(r"job_title='([^']+)'", prompt)
    out = []
    for t in titles:
        low = t.lower()
        disp = "automate" if "analyst" in low or "executive" in low else "keep_human" if "agent" in low or "lead" in low else "augment"
        out.append({"job_title": t, "disposition": disp, "capacity_freed_pct": {"automate": 50, "augment": 20, "keep_human": 5}[disp], "rationale": "mock", "confidence": "Medium"})
    return {"roles": out}


def fake_run_analysis(client, prompt, max_tokens=None):
    if "Score each option on each criterion" in prompt:
        kind, body = "comparison", _suggest(prompt)
    elif "judge the role of AI in its work" in prompt:
        kind, body = "disposition", _disposition(prompt)
    elif "work activity analysis and job design" in prompt:
        kind, body = "work_activities", _work_activities(prompt)
    elif "7 canonical organizational archetypes" in prompt:
        kind, body = "archetype", _archetype(prompt)
    else:
        kind, body = "unknown", {}
    _log(kind, prompt)
    return _wrap(body), {"model_requested": "claude-opus-5-5", "model_served": "claude-opus-5-5", "effort": "high", "stop_reason": "end_turn", "truncated": False}


for module in (ai_analysis_service, work_activities_service, comparison_api, disposition_api):
    module.run_analysis = fake_run_analysis


async def _fake_test_connection():
    return {"success": True, "model": "claude-opus-5-5", "message": "Connection successful (mock)", "tested_at": "now"}

cs.claude_service.test_connection = _fake_test_connection

import uvicorn  # noqa: E402
uvicorn.run(app, host="127.0.0.1", port=int(port), log_level="warning")
