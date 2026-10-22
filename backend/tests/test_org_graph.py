"""Tests for ID-keyed org graph construction (duplicate names, manager resolution)."""

import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers.csv_parser import OrgCSVParser
from app.services.metrics_service import MetricsCalculator
from app.services.org_graph import normalize_employees, build_org_graph


def _parse(csv_text: str):
    return OrgCSVParser(io.BytesIO(csv_text.encode("utf-8"))).parse()


HEADER = "Name,Job Title,Grade,Level,Line Manager,Employee ID,Department,Salary\n"


def test_two_people_with_same_name_stay_separate():
    csv = HEADER + (
        "Ana Lee,CEO,SVP,1,Top of Org,E1,Exec,300000\n"
        "John Tan,VP Ops,H8,2,Ana Lee,E2,Ops,200000\n"
        "John Tan,VP Sales,H8,2,Ana Lee,E3,Sales,200000\n"
    )
    result = _parse(csv)
    assert result["metadata"]["total_employees"] == 3
    assert result["graph"].number_of_nodes() == 3
    assert len(list(result["graph"].successors("E1"))) == 2
    assert any("shared by more than one person" in i for i in result["validation_errors"])


def test_shared_manager_name_resolved_by_level():
    # Two "John Tan"s at different levels; the report sits one level below the VP
    csv = HEADER + (
        "Ana Lee,CEO,SVP,1,Top of Org,E1,Exec,300000\n"
        "John Tan,VP Ops,H8,2,Ana Lee,E2,Ops,200000\n"
        "John Tan,Analyst,AO,4,Mei Ng,E9,Ops,60000\n"
        "Mei Ng,Manager,H6,3,John Tan,E4,Ops,150000\n"
    )
    result = _parse(csv)
    mei = next(e for e in result["employees"] if e["name"] == "Mei Ng")
    assert mei["manager_id"] == "E2"  # the level-2 John Tan, not the level-4 one
    assert any("matched by level" in i for i in result["validation_errors"])


def test_line_manager_id_column_takes_precedence():
    csv = (
        "Name,Job Title,Grade,Level,Line Manager,Line Manager ID,Employee ID\n"
        "Ana Lee,CEO,SVP,1,Top of Org,,E1\n"
        "John Tan,VP,H8,2,Ana Lee,E1,E2\n"
        "John Tan,VP,H8,2,Ana Lee,E1,E3\n"
        "Mei Ng,Manager,H6,3,John Tan,E3,E4\n"
    )
    result = _parse(csv)
    mei = next(e for e in result["employees"] if e["name"] == "Mei Ng")
    assert mei["manager_id"] == "E3"
    assert not any("could not be resolved" in i for i in result["validation_errors"])


def test_line_manager_value_can_be_an_employee_id():
    csv = HEADER + (
        "Ana Lee,CEO,SVP,1,Top of Org,E1,Exec,1\n"
        "Bo Lim,VP,H8,2,E1,E2,Ops,1\n"
    )
    result = _parse(csv)
    assert list(result["graph"].successors("E1")) == ["E2"]


def test_records_without_ids_fall_back_to_names(sample_employees, sample_grade_order):
    # Older saved uploads have no employee_id/manager_id; metrics must still work
    metrics = MetricsCalculator(employees=sample_employees, grade_order=sample_grade_order).calculate_all_metrics()
    assert metrics["total_employees"] == 8
    assert metrics["manager_stats"]["total_managers"] == 5


def test_duplicate_employee_ids_are_made_unique_and_reported():
    employees, issues = normalize_employees([
        {"name": "A", "employee_id": "X1", "manager_name": "Top of Org", "level": 1},
        {"name": "B", "employee_id": "X1", "manager_name": "A", "level": 2},
    ])
    ids = [e["employee_id"] for e in employees]
    assert len(set(ids)) == 2
    assert any("Duplicate Employee ID" in i for i in issues)
    assert build_org_graph(employees).number_of_edges() == 1


def test_hierarchy_carries_id_and_display_name(sample_csv_path):
    parser = OrgCSVParser(sample_csv_path)
    parser.parse()
    tree = parser.get_org_hierarchy()
    assert tree["id"] == "E001"
    assert tree["name"] == "Vincent Chan"


def test_layers_come_from_reporting_chain_not_level_column():
    # Level column claims 3 layers, but the chain is 4 deep (Ana > Bo > Cy > Di)
    csv = HEADER + (
        "Ana Lee,CEO,SVP,1,Top of Org,E1,Exec,1\n"
        "Bo Lim,VP,H8,2,Ana Lee,E2,Ops,1\n"
        "Cy Ong,Mgr,H6,3,Bo Lim,E3,Ops,1\n"
        "Di Koh,Lead,TL,3,Cy Ong,E4,Ops,1\n"
    )
    result = _parse(csv)
    assert result["metadata"]["organizational_layers"] == 4
    assert any("Level doesn't match" in i for i in result["validation_errors"])

    metrics = MetricsCalculator(employees=result["employees"]).calculate_all_metrics()
    layers = metrics["layer_analysis"]
    assert layers["total_layers"] == 4
    assert layers["declared_layers"] == 3
    assert layers["level_mismatches"]["count"] == 1
    assert layers["level_mismatches"]["examples"][0] == {"name": "Di Koh", "declared_level": 3, "actual_layer": 4}
    assert layers["longest_chain"] == ["Ana Lee", "Bo Lim", "Cy Ong", "Di Koh"]
    # Cost by layer uses the actual layer
    assert 4 in metrics["cost_analysis"]["by_level"]


def test_fixture_level_column_matches_chain(sample_csv_path):
    result = OrgCSVParser(sample_csv_path).parse()
    metrics = MetricsCalculator(employees=result["employees"]).calculate_all_metrics()
    assert metrics["layer_analysis"]["total_layers"] == 6
    assert metrics["layer_analysis"]["level_mismatches"]["count"] == 0


def test_people_under_unresolved_manager_get_no_layer():
    # Two "Kim Ho"s at the same level: the analyst's manager can't be resolved.
    # The analyst is not really at the top, so they must not be reported as
    # "Level 4, actually layer 1" — the unresolved manager is reported instead.
    csv = HEADER + (
        "Ana Lee,CEO,SVP,1,Top of Org,E1,Exec,1\n"
        "Kim Ho,Manager,H6,2,Ana Lee,E2,Fin,1\n"
        "Kim Ho,Analyst,AO,2,Ana Lee,E3,Fin,1\n"
        "Bo Lim,Exec,AO,3,Kim Ho,E4,Fin,1\n"
        "Cy Ong,Clerk,AO,4,Bo Lim,E5,Fin,1\n"
    )
    result = _parse(csv)
    assert any("could not be resolved" in i for i in result["validation_errors"])
    assert not any("Level doesn't match" in i for i in result["validation_errors"])

    metrics = MetricsCalculator(employees=result["employees"]).calculate_all_metrics()
    layers = metrics["layer_analysis"]
    assert layers["level_mismatches"]["count"] == 0
    assert layers["total_layers"] == 2
    # Without a chain position they are counted at their typed Level
    assert metrics["cost_analysis"]["by_level"][3]["count"] == 1
    assert metrics["cost_analysis"]["by_level"][4]["count"] == 1
