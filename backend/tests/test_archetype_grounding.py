"""Tests: archetype diagram units are grounded in the real departments."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.archetype_grounding import ground_diagrams
from app.services.metrics_service import MetricsCalculator


def _result(nodes):
    return {"category_4_recommended_archetypes": {"recommendations": [
        {"archetype": "Front-Back Hybrid", "structure_diagram": {"title": "t", "layout_type": "hierarchical",
                                                                 "nodes": nodes, "connections": []}}]}}


def test_nodes_get_real_headcount_and_coverage(sample_employees):
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()  # Sales 5, Operations 2, Executive 1
    result = _result([
        {"id": "front", "label": "Sales front end", "source_departments": ["sales"]},  # case-insensitive
        {"id": "ops", "label": "Shared Operations", "source_departments": ["Operations", "Marketing"]},  # Marketing doesn't exist
        {"id": "new", "label": "Digital Hub", "source_departments": [], "is_new": True},
    ])
    ground_diagrams(result, metrics)
    diagram = result["category_4_recommended_archetypes"]["recommendations"][0]["structure_diagram"]
    nodes = {n["id"]: n for n in diagram["nodes"]}
    assert nodes["front"]["headcount"] == 5 and nodes["front"]["source_departments"] == ["Sales"]
    assert nodes["ops"]["headcount"] == 2 and nodes["ops"]["unknown_departments"] == ["Marketing"]
    assert nodes["new"]["headcount"] is None
    assert diagram["coverage"]["unmapped_departments"] == ["Executive"]
    assert diagram["coverage"]["unmapped_headcount"] == 1


def test_shared_department_is_split_between_units(sample_employees):
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    result = _result([
        {"id": "a", "label": "A", "source_departments": ["Sales"]},
        {"id": "b", "label": "B", "source_departments": ["Sales", "Operations"]},
    ])
    ground_diagrams(result, metrics)
    nodes = {n["id"]: n for n in result["category_4_recommended_archetypes"]["recommendations"][0]["structure_diagram"]["nodes"]}
    # Sales (5) split in whole people: 3 to the first unit, 2 to the second; Operations (2) to B
    assert (nodes["a"]["headcount"], nodes["b"]["headcount"]) == (3, 4)
    assert nodes["b"]["shared_departments"] == ["Sales"]


def test_grounding_is_idempotent_and_safe_on_odd_input(sample_employees):
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    result = _result([{"id": "a", "label": "A", "source_departments": ["Sales"]}])
    ground_diagrams(result, metrics)
    ground_diagrams(result, metrics)
    assert result["category_4_recommended_archetypes"]["recommendations"][0]["structure_diagram"]["nodes"][0]["headcount"] == 5
    assert ground_diagrams({"error": "x"}, metrics) == {"error": "x"}
    assert ground_diagrams(_result([{"id": "a"}]), {}) is not None


def test_prompt_asks_for_real_units(sample_employees):
    from app.services.ai_analysis_service import AIAnalysisService
    metrics = MetricsCalculator(employees=sample_employees).calculate_all_metrics()
    prompt = AIAnalysisService(api_key=None)._build_prompt(metrics, sample_employees, None, None)
    assert "source_departments" in prompt and "actual department names" in prompt
