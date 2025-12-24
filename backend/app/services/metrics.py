"""
Organizational Metrics Calculator.

Calculates key org health metrics based on Kates-Kesler and McKinsey frameworks:
- Span of Control (average, distribution)
- Layer Count / Hierarchy Depth
- Manager to IC Ratio
- Complexity Indices
- Cost Analysis
- Function/Location Distribution
"""

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
from dataclasses import dataclass, field
from statistics import mean, median, stdev
from collections import Counter
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    """A single calculated metric."""
    metric_type: str
    metric_category: str
    value: float
    value_formatted: str
    breakdown: Dict[str, Any] = field(default_factory=dict)
    benchmark_value: Optional[float] = None
    benchmark_source: Optional[str] = None
    status: str = "info"  # "healthy", "warning", "critical", "info"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "metric_category": self.metric_category,
            "value": self.value,
            "value_formatted": self.value_formatted,
            "breakdown": self.breakdown,
            "benchmark_value": self.benchmark_value,
            "benchmark_source": self.benchmark_source,
            "status": self.status,
            "description": self.description,
        }


@dataclass
class MetricsReport:
    """Complete metrics report for a scenario."""
    metrics: List[MetricResult]
    summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


# Industry Benchmarks (McKinsey, Kates-Kesler research)
BENCHMARKS = {
    "span_of_control_avg": {
        "healthy_min": 4,
        "healthy_max": 8,
        "source": "McKinsey Organizational Design Benchmarks",
    },
    "manager_to_ic_ratio": {
        "healthy_min": 0.10,
        "healthy_max": 0.25,
        "source": "Kates-Kesler Framework",
    },
    "hierarchy_depth": {
        "healthy_max": 7,
        "source": "McKinsey 2020 Study",
    },
    "leadership_overhead": {
        "healthy_max": 0.20,
        "source": "BCG Org Efficiency Research",
    },
}


class MetricsCalculator:
    """
    Calculates organizational health metrics.

    Categories:
    - Structure: span of control, layers, manager ratio
    - Cost: total cost, cost per function, overhead
    - Complexity: reporting complexity, geographic spread
    - Health: benchmark comparisons, pathology indicators
    """

    def __init__(self):
        self.benchmarks = BENCHMARKS

    def calculate_all(
        self,
        employees: List[Dict[str, Any]],
        relationships: List[Tuple[str, str]],
    ) -> MetricsReport:
        """
        Calculate all metrics for the given org structure.

        Args:
            employees: List of employee dicts
            relationships: List of (manager_id, employee_id) tuples

        Returns:
            MetricsReport with all calculated metrics
        """
        # Build graph
        G = self._build_graph(employees, relationships)

        metrics: List[MetricResult] = []

        # Structure metrics
        metrics.append(self._calc_headcount(employees))
        metrics.append(self._calc_fte(employees))
        metrics.extend(self._calc_span_of_control(G, employees))
        metrics.append(self._calc_hierarchy_depth(G))
        metrics.append(self._calc_manager_ratio(G))
        metrics.append(self._calc_leadership_overhead(G, employees))

        # Cost metrics
        metrics.extend(self._calc_cost_metrics(employees))

        # Distribution metrics
        metrics.extend(self._calc_function_distribution(employees))
        metrics.extend(self._calc_location_distribution(employees))
        metrics.extend(self._calc_grade_distribution(employees))

        # Grade differential metric
        metrics.append(self._calc_grade_differential(G, employees))

        # Cost by job grades metric
        metrics.append(self._calc_cost_by_grade(employees))

        # Complexity metrics
        metrics.append(self._calc_reporting_complexity(G))

        # Generate summary
        summary = self._generate_summary(metrics, employees, G)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)

        return MetricsReport(
            metrics=metrics,
            summary=summary,
            recommendations=recommendations,
        )

    def _build_graph(
        self,
        employees: List[Dict[str, Any]],
        relationships: List[Tuple[str, str]],
    ) -> nx.DiGraph:
        """Build NetworkX graph from org data."""
        G = nx.DiGraph()

        for emp in employees:
            G.add_node(emp.get("id", ""), **emp)

        for manager_id, employee_id in relationships:
            if manager_id in G and employee_id in G:
                G.add_edge(manager_id, employee_id)

        return G

    def _calc_headcount(self, employees: List[Dict]) -> MetricResult:
        """Calculate total headcount."""
        total = len(employees)
        return MetricResult(
            metric_type="total_headcount",
            metric_category="structure",
            value=total,
            value_formatted=f"{total:,}",
            description="Total number of employees in the organization",
        )

    def _calc_fte(self, employees: List[Dict]) -> MetricResult:
        """Calculate total FTE."""
        total_fte = sum(emp.get("fte", 1.0) for emp in employees)
        return MetricResult(
            metric_type="total_fte",
            metric_category="structure",
            value=round(total_fte, 1),
            value_formatted=f"{total_fte:,.1f}",
            description="Total Full-Time Equivalent (FTE) positions",
        )

    def _calc_span_of_control(
        self, G: nx.DiGraph, employees: List[Dict]
    ) -> List[MetricResult]:
        """Calculate span of control metrics."""
        metrics = []

        # Get managers and their spans
        managers = [node for node in G.nodes() if G.out_degree(node) > 0]
        spans = [G.out_degree(node) for node in managers]

        if not spans:
            return [MetricResult(
                metric_type="span_of_control_avg",
                metric_category="structure",
                value=0,
                value_formatted="N/A",
                status="info",
                description="Average span of control (no managers found)",
            )]

        avg_span = mean(spans)
        median_span = median(spans)
        max_span = max(spans)
        min_span = min(spans)

        # Determine status based on benchmarks
        benchmark = self.benchmarks["span_of_control_avg"]
        if avg_span < benchmark["healthy_min"]:
            status = "warning"
        elif avg_span > benchmark["healthy_max"]:
            status = "warning"
        else:
            status = "healthy"

        # Average span
        metrics.append(MetricResult(
            metric_type="span_of_control_avg",
            metric_category="structure",
            value=round(avg_span, 2),
            value_formatted=f"{avg_span:.1f}:1",
            benchmark_value=(benchmark["healthy_min"] + benchmark["healthy_max"]) / 2,
            benchmark_source=benchmark["source"],
            status=status,
            description="Average number of direct reports per manager",
            breakdown={
                "median": round(median_span, 1),
                "max": max_span,
                "min": min_span,
                "manager_count": len(managers),
            },
        ))

        # Span distribution
        distribution = Counter(spans)
        distribution_breakdown = {str(k): v for k, v in sorted(distribution.items())}

        metrics.append(MetricResult(
            metric_type="span_distribution",
            metric_category="structure",
            value=len(distribution),
            value_formatted=f"{len(distribution)} distinct spans",
            description="Distribution of span of control across managers",
            breakdown={
                "distribution": distribution_breakdown,
                "narrow_span_count": sum(1 for s in spans if s < 4),
                "optimal_span_count": sum(1 for s in spans if 4 <= s <= 8),
                "wide_span_count": sum(1 for s in spans if s > 8),
            },
        ))

        return metrics

    def _calc_hierarchy_depth(self, G: nx.DiGraph) -> MetricResult:
        """Calculate maximum hierarchy depth."""
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        max_depth = 0
        depth_by_root = {}

        for root in roots:
            try:
                depths = nx.single_source_shortest_path_length(G, root)
                if depths:
                    root_max = max(depths.values())
                    depth_by_root[root] = root_max
                    max_depth = max(max_depth, root_max)
            except nx.NetworkXError:
                pass

        layers = max_depth + 1  # Convert depth to layer count

        # Status based on benchmark
        benchmark = self.benchmarks["hierarchy_depth"]
        status = "healthy" if layers <= benchmark["healthy_max"] else "warning"

        return MetricResult(
            metric_type="hierarchy_depth",
            metric_category="structure",
            value=layers,
            value_formatted=f"{layers} layers",
            benchmark_value=benchmark["healthy_max"],
            benchmark_source=benchmark["source"],
            status=status,
            description="Number of hierarchical layers from CEO to front-line",
            breakdown={
                "max_depth": max_depth,
                "root_count": len(roots),
            },
        )

    def _calc_manager_ratio(self, G: nx.DiGraph) -> MetricResult:
        """Calculate manager to IC ratio."""
        managers = [node for node in G.nodes() if G.out_degree(node) > 0]
        ics = [node for node in G.nodes() if G.out_degree(node) == 0]

        total = len(G.nodes())
        if total == 0:
            return MetricResult(
                metric_type="manager_to_ic_ratio",
                metric_category="structure",
                value=0,
                value_formatted="N/A",
                status="info",
            )

        ratio = len(managers) / total if total > 0 else 0

        benchmark = self.benchmarks["manager_to_ic_ratio"]
        if ratio < benchmark["healthy_min"]:
            status = "warning"  # Too few managers
        elif ratio > benchmark["healthy_max"]:
            status = "warning"  # Too many managers
        else:
            status = "healthy"

        return MetricResult(
            metric_type="manager_to_ic_ratio",
            metric_category="structure",
            value=round(ratio, 3),
            value_formatted=f"{ratio:.1%}",
            benchmark_value=(benchmark["healthy_min"] + benchmark["healthy_max"]) / 2,
            benchmark_source=benchmark["source"],
            status=status,
            description="Percentage of employees who are people managers",
            breakdown={
                "manager_count": len(managers),
                "ic_count": len(ics),
                "total": total,
            },
        )

    def _calc_leadership_overhead(
        self, G: nx.DiGraph, employees: List[Dict]
    ) -> MetricResult:
        """Calculate leadership overhead (managers as % of total headcount)."""
        # Convert employee IDs to strings for consistent comparison
        manager_ids = {str(node) for node in G.nodes() if G.out_degree(node) > 0}

        # Count managers and ICs using headcount
        manager_count = 0
        ic_count = 0
        total_count = len(employees)

        for emp in employees:
            emp_id = str(emp.get("id", ""))
            if emp_id in manager_ids:
                manager_count += 1
            else:
                ic_count += 1

        if total_count == 0:
            overhead = 0
        else:
            overhead = manager_count / total_count

        benchmark = self.benchmarks["leadership_overhead"]
        status = "healthy" if overhead <= benchmark["healthy_max"] else "warning"

        return MetricResult(
            metric_type="leadership_overhead",
            metric_category="structure",
            value=round(overhead, 3),
            value_formatted=f"{overhead:.1%}",
            benchmark_value=benchmark["healthy_max"],
            benchmark_source=benchmark["source"],
            status=status,
            description="Percentage of employees who are people managers",
            breakdown={
                "manager_count": manager_count,
                "ic_count": ic_count,
                "total_count": total_count,
            },
        )

    def _calc_cost_metrics(self, employees: List[Dict]) -> List[MetricResult]:
        """Calculate cost-related metrics."""
        metrics = []

        # Total cost
        total_cost = sum(self._get_employee_cost(emp) for emp in employees)

        metrics.append(MetricResult(
            metric_type="total_cost",
            metric_category="cost",
            value=round(total_cost, 2),
            value_formatted=f"${total_cost:,.0f}",
            description="Total loaded employment cost",
        ))

        # Average cost per employee
        if employees:
            avg_cost = total_cost / len(employees)
            metrics.append(MetricResult(
                metric_type="avg_cost_per_employee",
                metric_category="cost",
                value=round(avg_cost, 2),
                value_formatted=f"${avg_cost:,.0f}",
                description="Average cost per employee",
            ))

        # Cost by function
        cost_by_function: Dict[str, float] = {}
        for emp in employees:
            func = emp.get("function", "Unknown")
            cost_by_function[func] = cost_by_function.get(func, 0) + self._get_employee_cost(emp)

        if cost_by_function:
            metrics.append(MetricResult(
                metric_type="cost_by_function",
                metric_category="cost",
                value=len(cost_by_function),
                value_formatted=f"{len(cost_by_function)} functions",
                description="Cost distribution across functions",
                breakdown={
                    func: round(cost, 2)
                    for func, cost in sorted(
                        cost_by_function.items(),
                        key=lambda x: -x[1]
                    )
                },
            ))

        return metrics

    def _calc_function_distribution(
        self, employees: List[Dict]
    ) -> List[MetricResult]:
        """Calculate distribution across functions."""
        functions = Counter(emp.get("function", "Unknown") for emp in employees)

        return [MetricResult(
            metric_type="function_distribution",
            metric_category="distribution",
            value=len(functions),
            value_formatted=f"{len(functions)} functions",
            description="Headcount distribution across business functions",
            breakdown=dict(functions.most_common()),
        )]

    def _calc_location_distribution(
        self, employees: List[Dict]
    ) -> List[MetricResult]:
        """Calculate distribution across locations."""
        locations = Counter(emp.get("location", "Unknown") for emp in employees)

        return [MetricResult(
            metric_type="location_distribution",
            metric_category="distribution",
            value=len(locations),
            value_formatted=f"{len(locations)} locations",
            description="Headcount distribution across geographic locations",
            breakdown=dict(locations.most_common()),
        )]

    def _calc_grade_distribution(
        self, employees: List[Dict]
    ) -> List[MetricResult]:
        """Calculate distribution across grades/levels."""
        grades = Counter(emp.get("grade", "Unknown") for emp in employees)
        levels = Counter(emp.get("level", 0) for emp in employees)

        return [
            MetricResult(
                metric_type="grade_distribution",
                metric_category="distribution",
                value=len(grades),
                value_formatted=f"{len(grades)} grades",
                description="Headcount distribution across job grades",
                breakdown=dict(grades.most_common()),
            ),
            MetricResult(
                metric_type="level_distribution",
                metric_category="distribution",
                value=len(levels),
                value_formatted=f"{len(levels)} levels",
                description="Headcount distribution across hierarchy levels",
                breakdown={str(k): v for k, v in sorted(levels.items())},
            ),
        ]

    def _calc_grade_differential(
        self, G: nx.DiGraph, employees: List[Dict]
    ) -> MetricResult:
        """
        Calculate average reporting grade differential.

        This measures the average job grade difference between managers
        and their direct reports.
        """
        # Create grade hierarchy mapping (numeric values for comparison)
        # Common grade patterns: E1>E2>E3, L1>L2>L3, VP>Director>Manager, etc.
        grade_order = {}

        # Extract unique grades and try to establish order
        all_grades = set()
        for emp in employees:
            grade = emp.get("grade")
            if grade:
                all_grades.add(grade)

        # Try to infer numeric ordering from grades
        # Strategy: Use level if available, otherwise try parsing grade string
        emp_by_id = {emp.get("id"): emp for emp in employees}

        differentials = []
        differential_details = []

        for manager_id in G.nodes():
            if G.out_degree(manager_id) == 0:
                continue  # Not a manager

            manager = emp_by_id.get(manager_id, {})
            manager_grade = manager.get("grade")
            manager_level = manager.get("level")

            if not manager_grade and not manager_level:
                continue

            # Get direct reports
            for report_id in G.successors(manager_id):
                report = emp_by_id.get(report_id, {})
                report_grade = report.get("grade")
                report_level = report.get("level")

                # Calculate differential using grade or level
                differential = None

                # Try using explicit levels first
                if manager_level is not None and report_level is not None:
                    try:
                        differential = int(report_level) - int(manager_level)
                    except (ValueError, TypeError):
                        pass

                # Try parsing numeric grades (E1, L2, M3, etc.)
                if differential is None and manager_grade and report_grade:
                    try:
                        # Extract numbers from grades
                        import re
                        mgr_num = re.search(r'\d+', str(manager_grade))
                        rep_num = re.search(r'\d+', str(report_grade))
                        if mgr_num and rep_num:
                            # Higher number typically = lower grade in most systems
                            differential = int(rep_num.group()) - int(mgr_num.group())
                    except (ValueError, TypeError):
                        pass

                if differential is not None:
                    differentials.append(differential)
                    differential_details.append({
                        "manager": manager.get("full_name", manager_id),
                        "manager_grade": manager_grade,
                        "report": report.get("full_name", report_id),
                        "report_grade": report_grade,
                        "differential": differential,
                    })

        if not differentials:
            return MetricResult(
                metric_type="grade_differential_avg",
                metric_category="structure",
                value=0,
                value_formatted="N/A",
                status="info",
                description="Average job grade difference between managers and subordinates (insufficient data)",
            )

        avg_differential = mean(differentials)

        # Ideal differential is 1-2 levels
        if 0.5 <= avg_differential <= 2.5:
            status = "healthy"
        elif avg_differential < 0.5:
            status = "warning"  # Managers too close in grade to reports
        else:
            status = "warning"  # Too large a gap

        return MetricResult(
            metric_type="grade_differential_avg",
            metric_category="structure",
            value=round(avg_differential, 2),
            value_formatted=f"{avg_differential:.1f} levels",
            status=status,
            description="Average job grade difference between managers and their direct reports",
            breakdown={
                "total_relationships_analyzed": len(differentials),
                "min_differential": min(differentials) if differentials else 0,
                "max_differential": max(differentials) if differentials else 0,
                "distribution": dict(Counter(differentials)),
            },
        )

    def _calc_cost_by_grade(self, employees: List[Dict]) -> MetricResult:
        """
        Calculate total cost organized by job grades.

        This provides a breakdown of employee costs by grade level.
        """
        cost_by_grade: Dict[str, Dict[str, Any]] = {}

        for emp in employees:
            grade = emp.get("grade", "Unknown") or "Unknown"
            emp_cost = self._get_employee_cost(emp)

            if grade not in cost_by_grade:
                cost_by_grade[grade] = {
                    "headcount": 0,
                    "total_fte": 0,
                    "total_cost": 0,
                    "avg_cost": 0,
                }

            cost_by_grade[grade]["headcount"] += 1
            cost_by_grade[grade]["total_fte"] += emp.get("fte", 1.0)
            cost_by_grade[grade]["total_cost"] += emp_cost

        # Calculate averages
        for grade in cost_by_grade:
            if cost_by_grade[grade]["headcount"] > 0:
                cost_by_grade[grade]["avg_cost"] = round(
                    cost_by_grade[grade]["total_cost"] / cost_by_grade[grade]["headcount"],
                    2
                )
            cost_by_grade[grade]["total_cost"] = round(cost_by_grade[grade]["total_cost"], 2)
            cost_by_grade[grade]["total_fte"] = round(cost_by_grade[grade]["total_fte"], 1)

        # Sort by total cost descending
        sorted_grades = sorted(
            cost_by_grade.items(),
            key=lambda x: x[1]["total_cost"],
            reverse=True
        )

        total_cost = sum(g["total_cost"] for g in cost_by_grade.values())

        return MetricResult(
            metric_type="cost_by_grade",
            metric_category="cost",
            value=total_cost,
            value_formatted=f"${total_cost:,.0f}",
            description="Total employee cost organized by job grades",
            breakdown={
                grade: data
                for grade, data in sorted_grades
            },
        )

    def _calc_reporting_complexity(self, G: nx.DiGraph) -> MetricResult:
        """Calculate reporting relationship complexity."""
        total_relationships = G.number_of_edges()
        total_nodes = G.number_of_nodes()

        # Complexity = edges / nodes (1.0 = simple tree)
        if total_nodes > 0:
            complexity = total_relationships / total_nodes
        else:
            complexity = 0

        return MetricResult(
            metric_type="reporting_complexity",
            metric_category="complexity",
            value=round(complexity, 3),
            value_formatted=f"{complexity:.2f}",
            description="Ratio of reporting relationships to employees (1.0 = simple hierarchy)",
            breakdown={
                "total_relationships": total_relationships,
                "total_nodes": total_nodes,
            },
        )

    def _get_employee_cost(self, emp: Dict) -> float:
        """Calculate total loaded cost for an employee."""
        base = emp.get("cost_base_salary", 0) or 0
        variable = emp.get("cost_variable", 0) or 0
        benefits = emp.get("cost_benefits", 0) or 0
        multiplier = emp.get("cost_overhead_multiplier", 1.0) or 1.0
        fte = emp.get("fte", 1.0) or 1.0

        return (base + variable + benefits) * multiplier * fte

    def _generate_summary(
        self,
        metrics: List[MetricResult],
        employees: List[Dict],
        G: nx.DiGraph,
    ) -> Dict[str, Any]:
        """Generate summary of key metrics."""
        summary = {
            "total_headcount": len(employees),
            "total_fte": round(sum(emp.get("fte", 1.0) for emp in employees), 1),
            "total_cost": round(sum(self._get_employee_cost(emp) for emp in employees), 2),
        }

        # Add key metrics
        for metric in metrics:
            if metric.metric_type in [
                "span_of_control_avg",
                "hierarchy_depth",
                "manager_to_ic_ratio",
            ]:
                summary[metric.metric_type] = metric.value

        # Health score (0-100)
        healthy_count = sum(1 for m in metrics if m.status == "healthy")
        warning_count = sum(1 for m in metrics if m.status == "warning")
        critical_count = sum(1 for m in metrics if m.status == "critical")

        if critical_count > 0:
            health_score = max(0, 50 - critical_count * 10)
        elif warning_count > 0:
            health_score = max(50, 80 - warning_count * 5)
        else:
            health_score = min(100, 80 + healthy_count * 2)

        summary["health_score"] = health_score
        summary["health_status"] = (
            "critical" if health_score < 50 else
            "warning" if health_score < 70 else
            "healthy"
        )

        return summary

    def _generate_recommendations(
        self, metrics: List[MetricResult]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on metrics."""
        recommendations = []

        for metric in metrics:
            if metric.status in ["warning", "critical"]:
                rec = self._get_recommendation_for_metric(metric)
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _get_recommendation_for_metric(
        self, metric: MetricResult
    ) -> Optional[Dict[str, Any]]:
        """Get recommendation for a specific metric issue."""
        recommendations = {
            "span_of_control_avg": {
                "title": "Optimize Span of Control",
                "description": (
                    "Average span of control is outside the optimal range (4-8). "
                    "Consider restructuring to balance manager workloads."
                ),
                "priority": "medium",
                "framework": "Kates-Kesler",
            },
            "hierarchy_depth": {
                "title": "Flatten Organization Structure",
                "description": (
                    "Deep hierarchy may slow decision-making and increase costs. "
                    "Consider removing intermediate management layers."
                ),
                "priority": "high",
                "framework": "McKinsey",
            },
            "manager_to_ic_ratio": {
                "title": "Review Manager Ratio",
                "description": (
                    "Manager-to-IC ratio suggests potential over-management or under-management. "
                    "Review role definitions and career paths."
                ),
                "priority": "medium",
                "framework": "Kates-Kesler",
            },
            "leadership_overhead": {
                "title": "Reduce Leadership Overhead",
                "description": (
                    "Management costs exceed recommended levels. "
                    "Consider consolidating leadership roles or expanding spans."
                ),
                "priority": "high",
                "framework": "BCG",
            },
        }

        return recommendations.get(metric.metric_type)


def calculate_metrics(
    employees: List[Dict[str, Any]],
    relationships: List[Tuple[str, str]],
) -> Dict[str, Any]:
    """
    Convenience function to calculate all metrics.

    Args:
        employees: List of employee dicts
        relationships: List of (manager_id, employee_id) tuples

    Returns:
        Dictionary with metrics report
    """
    calculator = MetricsCalculator()
    report = calculator.calculate_all(employees, relationships)
    return report.to_dict()
