"""Tests for work-type-aware span benchmarks and the component-based health score."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.metrics_service import MetricsCalculator


def _team(manager_title: str, report_title: str, size: int, work_type: str = ""):
    people = [{"name": "Boss", "employee_id": "B", "job_title": manager_title, "grade": "H6",
               "level": 1, "manager_name": "Top of Org", "salary": 100, "department": "D"}]
    for i in range(size):
        people.append({"name": f"P{i}", "employee_id": f"P{i}", "job_title": report_title, "grade": "AO",
                       "level": 2, "manager_name": "Boss", "salary": 10, "department": "D",
                       "work_type": work_type})
    return people


def _assessment(people):
    metrics = MetricsCalculator(employees=people).calculate_all_metrics()
    return metrics["span_of_control"]["manager_assessments"][0], metrics


def test_operational_team_of_18_is_within_benchmark():
    a, _ = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 18))
    assert a["work_type"] == "operational"
    assert a["benchmark_range"] == [15, 25]
    assert a["status"] == "within"
    assert "Ramp Ops Associate" in a["work_type_basis"]


def test_knowledge_team_of_18_is_above_benchmark():
    a, _ = _assessment(_team("Analytics Manager", "SQ Analytics Associate", 18))
    assert a["work_type"] == "knowledge"
    assert a["benchmark_range"] == [5, 10]
    assert a["status"] == "above"


def test_work_type_column_overrides_title_inference():
    a, _ = _assessment(_team("Analytics Manager", "SQ Analytics Associate", 18, work_type="operational"))
    assert a["work_type"] == "operational"
    assert a["work_type_basis"] == "Work Type column"
    assert a["status"] == "within"


def test_manager_of_managers_uses_knowledge_benchmark():
    people = [{"name": "Head", "employee_id": "H", "job_title": "Head of Ops", "level": 1,
               "manager_name": "Top of Org", "department": "D"}]
    for i in range(3):
        people.append({"name": f"Lead{i}", "employee_id": f"L{i}", "job_title": "Ramp Ops Lead",
                       "level": 2, "manager_name": "Head", "department": "D"})
        people.append({"name": f"Agent{i}", "employee_id": f"A{i}", "job_title": "Ramp Ops Associate",
                       "level": 3, "manager_name": f"Lead{i}", "department": "D"})
    metrics = MetricsCalculator(employees=people).calculate_all_metrics()
    head = next(a for a in metrics["span_of_control"]["manager_assessments"] if a["manager"] == "Head")
    assert head["work_type"] == "knowledge"
    assert "manager of managers" in head["work_type_basis"]


def test_health_score_is_weighted_sum_of_visible_components(sample_csv_path):
    from app.parsers.csv_parser import OrgCSVParser
    employees = OrgCSVParser(sample_csv_path).parse()["employees"]
    health = MetricsCalculator(employees=employees).calculate_all_metrics()["health_indicators"]

    components = health["components"]
    assert {c["key"] for c in components} == {"span_fit", "layers", "manager_ratio", "single_report"}
    assert sum(c["weight"] for c in components) == 100
    expected = round(sum(c["score"] * c["weight"] for c in components) / 100)
    assert health["health_score"] == expected
    for c in components:
        assert 0 <= c["score"] <= 100
        assert c["value"] and c["benchmark"] and c["rule"] and c["source"]


def test_fixture_is_correctly_diagnosed_as_bottom_heavy(sample_csv_path):
    # 34 of 64 people manage someone, every span is 4 or fewer, 12 managers have one report
    from app.parsers.csv_parser import OrgCSVParser
    employees = OrgCSVParser(sample_csv_path).parse()["employees"]
    metrics = MetricsCalculator(employees=employees).calculate_all_metrics()
    span = metrics["span_of_control"]
    assert span["distribution_vs_benchmark"]["Within benchmark"] == 0
    assert span["single_report_managers"] == 12
    health = metrics["health_indicators"]
    assert health["health_score"] < 50
    assert any("only one direct report" in w for w in health["warnings"])


def test_healthy_operational_org_scores_well():
    # One manager over 18 ramp agents: span within benchmark, 2 layers, ~5% managers
    _, metrics = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 18))
    health = metrics["health_indicators"]
    span_component = next(c for c in health["components"] if c["key"] == "span_fit")
    assert span_component["score"] == 100
    assert health["warnings"] == [] or all("Manager ratio" in w for w in health["warnings"])
