"""Tests for span benchmarks (frontline operational 10-20, all other managers 5-10) and the health score."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.metrics_service import MetricsCalculator


def _team(manager_title: str, report_title: str, size: int, work_type: str = ""):
    # work_type is the manager's own Work Type tag
    people = [{"name": "Boss", "employee_id": "B", "job_title": manager_title, "grade": "H6",
               "level": 1, "manager_name": "Top of Org", "salary": 100, "department": "D",
               "work_type": work_type}]
    for i in range(size):
        people.append({"name": f"P{i}", "employee_id": f"P{i}", "job_title": report_title, "grade": "AO",
                       "level": 2, "manager_name": "Boss", "salary": 10, "department": "D"})
    return people


def _assessment(people):
    metrics = MetricsCalculator(employees=people).calculate_all_metrics()
    return metrics["span_of_control"]["manager_assessments"][0], metrics


def test_manager_tagged_operational_is_judged_against_10_to_20():
    a, _ = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 18, work_type="operational"))
    assert a["work_type"] == "operational"
    assert a["benchmark_range"] == [10, 20]
    assert a["status"] == "within"
    assert "Work Type column" in a["work_type_basis"]
    a, _ = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 22, work_type="operational"))
    assert a["status"] == "above"


def test_untagged_manager_is_judged_against_5_to_10_whatever_the_titles():
    # No inference from job titles: only the Work Type tag gives the frontline range
    a, _ = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 18))
    assert a["work_type"] == "knowledge"
    assert a["benchmark_range"] == [5, 10]
    assert a["status"] == "above"
    assert "not tagged Operational" in a["work_type_basis"]


def test_frontline_synonym_and_explicit_knowledge_tag():
    a, _ = _assessment(_team("Gate Supervisor", "Gate Agent", 12, work_type="frontline"))
    assert a["benchmark_range"] == [10, 20]
    a, _ = _assessment(_team("Analytics Manager", "Analyst", 8, work_type="knowledge"))
    assert a["benchmark_range"] == [5, 10] and a["status"] == "within"
    assert "'knowledge'" in a["work_type_basis"]


def test_tag_applies_to_managers_of_managers_too():
    people = [{"name": "Head", "employee_id": "H", "job_title": "Head of Ops", "level": 1,
               "manager_name": "Top of Org", "department": "D", "work_type": "operational"}]
    for i in range(3):
        people.append({"name": f"Lead{i}", "employee_id": f"L{i}", "job_title": "Ramp Ops Lead",
                       "level": 2, "manager_name": "Head", "department": "D"})
        people.append({"name": f"Agent{i}", "employee_id": f"A{i}", "job_title": "Ramp Ops Associate",
                       "level": 3, "manager_name": f"Lead{i}", "department": "D"})
    metrics = MetricsCalculator(employees=people).calculate_all_metrics()
    by_name = {a["manager"]: a for a in metrics["span_of_control"]["manager_assessments"]}
    assert by_name["Head"]["benchmark_range"] == [10, 20]
    assert by_name["Lead0"]["benchmark_range"] == [5, 10]  # leads themselves untagged


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
    # One frontline operational manager over 18 ramp agents: span within benchmark, 2 layers, ~5% managers
    _, metrics = _assessment(_team("Ramp Manager", "Ramp Ops Associate", 18, work_type="operational"))
    health = metrics["health_indicators"]
    span_component = next(c for c in health["components"] if c["key"] == "span_fit")
    assert span_component["score"] == 100
    assert health["warnings"] == [] or all("Manager ratio" in w for w in health["warnings"])
