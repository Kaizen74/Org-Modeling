"""Tests for metrics calculator."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.metrics_service import MetricsCalculator
from app.parsers.csv_parser import OrgCSVParser


def test_metrics_with_sample_employees(sample_employees, sample_grade_order):
    """Test metrics calculation with sample data."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    assert metrics["total_employees"] == 8
    assert metrics["manager_stats"]["total_managers"] == 5  # CEO, VP1, VP2, Mgr1, Lead1
    assert metrics["manager_stats"]["total_ics"] == 3  # Mgr2, IC1, IC2 (Mgr2 has no reports)


def test_span_of_control(sample_employees, sample_grade_order):
    """Test span of control calculation."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    span = metrics["span_of_control"]
    assert "average_span" in span
    assert "distribution" in span
    assert span["average_span"] > 0


def test_cost_analysis(sample_employees, sample_grade_order):
    """Test cost analysis calculation."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    cost = metrics["cost_analysis"]
    # Sum of all salaries: 350k + 250k + 250k + 180k + 180k + 90k + 60k + 60k = 1,420,000
    assert cost["total_cost"] == 1420000
    assert cost["average_cost_per_employee"] == 1420000 / 8


def test_grade_gap_analysis(sample_employees, sample_grade_order):
    """Test grade gap calculation."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    gap = metrics["grade_gap_analysis"]
    assert "average_grade_gap" in gap
    assert gap["total_comparisons"] > 0


def test_layer_analysis(sample_employees, sample_grade_order):
    """Test layer analysis."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    layers = metrics["layer_analysis"]
    assert layers["total_layers"] == 5  # Levels 1-5


def test_health_indicators(sample_employees, sample_grade_order):
    """Test health indicators."""
    calculator = MetricsCalculator(
        employees=sample_employees,
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    health = metrics["health_indicators"]
    assert "health_score" in health
    assert "health_grade" in health
    assert "warnings" in health
    assert health["health_score"] >= 0 and health["health_score"] <= 100


def test_pax_metrics_accuracy(sample_csv_path, sample_grade_order):
    """Test metrics accuracy against known PAX data."""
    # Parse CSV
    parser = OrgCSVParser(sample_csv_path)
    result = parser.parse()

    # Calculate metrics
    calculator = MetricsCalculator(
        employees=result["employees"],
        grade_order=sample_grade_order
    )
    metrics = calculator.calculate_all_metrics()

    # Validate against expected — total cost derived from the fixture so the
    # assertion can't go stale if fixture salaries change
    import pandas as pd
    expected_salary = pd.read_csv(sample_csv_path)["Salary"].sum()
    assert metrics["total_employees"] == 64
    assert metrics["cost_analysis"]["total_cost"] == expected_salary
    assert metrics["layer_analysis"]["total_layers"] == 6
