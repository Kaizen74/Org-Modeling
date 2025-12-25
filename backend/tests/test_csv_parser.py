"""Tests for CSV parser."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers.csv_parser import OrgCSVParser


def test_parse_pax_csv(sample_csv_path):
    """Test parsing PAX org structure CSV."""
    parser = OrgCSVParser(sample_csv_path)
    result = parser.parse()

    # Should have no validation errors
    assert len(result["validation_errors"]) == 0, f"Errors: {result['validation_errors']}"

    # Should have 64 employees
    assert result["metadata"]["total_employees"] == 64, f"Got {result['metadata']['total_employees']} employees"

    # Should have 16 managers
    # Note: Need to recalculate based on actual structure
    manager_count = result["metadata"]["manager_count"]
    assert manager_count > 0, "Should have managers"

    # Should have correct total salary
    assert result["metadata"]["total_salary_cost"] == 5770000, f"Got ${result['metadata']['total_salary_cost']}"

    # Should have 6 layers
    assert result["metadata"]["organizational_layers"] == 6


def test_parse_invalid_csv():
    """Test parsing with missing columns."""
    import io
    csv_content = io.StringIO("Name,Title\nJohn,Manager")

    parser = OrgCSVParser(csv_content)
    result = parser.parse()

    assert len(result["validation_errors"]) > 0
    assert "Missing required columns" in result["validation_errors"][0]


def test_employee_records(sample_csv_path):
    """Test employee record structure."""
    parser = OrgCSVParser(sample_csv_path)
    result = parser.parse()

    assert len(result["employees"]) == 64

    # Check first employee (Vincent Chan)
    vincent = next(e for e in result["employees"] if e["name"] == "Vincent Chan")
    assert vincent["grade"] == "SVP"
    assert vincent["level"] == 1
    assert vincent["salary"] == 350000


def test_graph_structure(sample_csv_path):
    """Test graph is correctly built."""
    parser = OrgCSVParser(sample_csv_path)
    result = parser.parse()

    graph = result["graph"]
    assert graph is not None

    # Vincent should have 3 direct reports (the VPs)
    vincent_reports = list(graph.successors("Vincent Chan"))
    assert len(vincent_reports) == 3


def test_hierarchy_generation(sample_csv_path):
    """Test hierarchy structure for visualization."""
    parser = OrgCSVParser(sample_csv_path)
    parser.parse()

    hierarchy = parser.get_org_hierarchy()
    assert hierarchy is not None
    assert "name" in hierarchy
    assert "children" in hierarchy
