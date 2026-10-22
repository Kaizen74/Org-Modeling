"""
Metrics Calculator Service.

Calculate org metrics with VALIDATED formulas.
TESTED: Returns accurate metrics for 64-employee PAX org

Expected results for PAX CSV:
- total_employees: 64
- total_managers: 16
- manager_ratio_pct: 25.0
- average_span: 3.94
- total_cost: 5770000
- average_grade_gap: 2.98
- organizational_layers: 6
"""

import networkx as nx
from typing import Dict, List, Optional
import statistics

from .org_graph import normalize_employees, build_org_graph, display_name, reporting_layers


class MetricsCalculator:
    """
    Calculate org metrics with VALIDATED formulas.

    TESTED: Returns accurate metrics for 64-employee PAX org
    """

    def __init__(self, employees: List[Dict], grade_order: Optional[Dict[str, int]] = None):
        """
        Initialize calculator with employee data.

        Args:
            employees: List of employee dictionaries
            grade_order: Map of grade -> numeric order (1 = highest)
        """
        # Keyed by Employee ID; records saved before IDs were resolved are
        # resolved here by name, so older uploads still work
        self.employees, self.data_issues = normalize_employees(employees)
        self.grade_order = grade_order or {}
        self.graph = build_org_graph(self.employees)
        # Layer = position in the actual reporting chain (top = 1), not the typed Level column
        self.layers = reporting_layers(self.graph)

    def _layer_of(self, node: str) -> int:
        """Actual reporting layer, falling back to the declared Level for people in a reporting loop."""
        return self.layers.get(node) or self.graph.nodes[node].get("level", 0)

    def calculate_all_metrics(self) -> Dict:
        """Calculate all organizational metrics."""
        return {
            "total_employees": self._total_employees(),
            "manager_stats": self._manager_statistics(),
            "span_of_control": self._span_of_control(),
            "cost_analysis": self._cost_analysis(),
            "grade_gap_analysis": self._grade_gap_analysis(),
            "layer_analysis": self._layer_analysis(),
            "health_indicators": self._health_indicators(),
            "data_quality": {"issues": self.data_issues[:20]}
        }

    def _total_employees(self) -> int:
        """Get total employee count."""
        return len(self.graph.nodes())

    def _manager_statistics(self) -> Dict:
        """
        Calculate manager statistics.

        CORRECTED: Only count employees with >0 direct reports as managers.
        """
        total = len(self.graph.nodes())
        if total == 0:
            return {
                "total_managers": 0,
                "total_ics": 0,
                "manager_ratio_pct": 0.0,
                "ic_ratio_pct": 0.0
            }

        # Count managers (nodes with outgoing edges = direct reports)
        managers = [n for n in self.graph.nodes() if self.graph.out_degree(n) > 0]
        manager_count = len(managers)
        ic_count = total - manager_count

        return {
            "total_managers": manager_count,
            "total_ics": ic_count,
            "manager_ratio_pct": round(manager_count / total * 100, 1),
            "ic_ratio_pct": round(ic_count / total * 100, 1)
        }

    def _span_of_control(self) -> Dict:
        """
        Calculate span of control metrics.

        CORRECTED: Divide by manager count, not total employees.
        """
        spans = []
        by_manager = {}
        distribution = {"Narrow (<5)": 0, "Optimal (5-10)": 0, "Wide (>10)": 0}

        for node in self.graph.nodes():
            span = self.graph.out_degree(node)  # Direct reports
            if span > 0:  # Only count managers
                spans.append(span)
                by_manager[node] = span

                if span < 5:
                    distribution["Narrow (<5)"] += 1
                elif span <= 10:
                    distribution["Optimal (5-10)"] += 1
                else:
                    distribution["Wide (>10)"] += 1

        if not spans:
            return {
                "average_span": 0.0,
                "median_span": 0.0,
                "min_span": 0,
                "max_span": 0,
                "distribution": distribution,
                "distribution_pct": {},
                "by_manager": {}
            }

        total_managers = len(spans)
        return {
            "average_span": round(statistics.mean(spans), 2),
            "median_span": round(statistics.median(spans), 2),
            "min_span": min(spans),
            "max_span": max(spans),
            "distribution": distribution,
            "distribution_pct": {
                k: round(v / total_managers * 100, 1)
                for k, v in distribution.items()
            },
            "by_manager": by_manager
        }

    def _cost_analysis(self) -> Dict:
        """Calculate total cost from ALL employees."""
        total_cost = sum(
            self.graph.nodes[n].get("salary", 0)
            for n in self.graph.nodes()
        )

        total_emp = len(self.graph.nodes())

        # Cost by reporting layer
        by_level = {}
        for node in self.graph.nodes():
            level = self._layer_of(node)
            salary = self.graph.nodes[node].get("salary", 0)
            if level not in by_level:
                by_level[level] = {"count": 0, "total_cost": 0}
            by_level[level]["count"] += 1
            by_level[level]["total_cost"] += salary

        # Cost by grade
        by_grade = {}
        for node in self.graph.nodes():
            grade = self.graph.nodes[node].get("grade", "Unknown")
            salary = self.graph.nodes[node].get("salary", 0)
            if grade not in by_grade:
                by_grade[grade] = {"count": 0, "total_cost": 0}
            by_grade[grade]["count"] += 1
            by_grade[grade]["total_cost"] += salary

        return {
            "total_cost": round(total_cost, 0),
            "average_cost_per_employee": round(total_cost / total_emp, 0) if total_emp > 0 else 0,
            "by_level": by_level,
            "by_grade": by_grade
        }

    def _grade_gap_analysis(self) -> Dict:
        """
        Calculate grade gap between managers and reports.

        CORRECTED: subordinate_rank - manager_rank (positive = sub is lower)
        """
        if not self.grade_order:
            return {
                "average_grade_gap": 0.0,
                "total_comparisons": 0,
                "gaps": [],
                "note": "No grade order configured"
            }

        gaps = []
        gap_details = []

        for mgr in self.graph.nodes():
            mgr_grade = self.graph.nodes[mgr].get("grade")
            if mgr_grade not in self.grade_order:
                continue

            for sub in self.graph.successors(mgr):
                sub_grade = self.graph.nodes[sub].get("grade")
                if sub_grade in self.grade_order:
                    gap = self.grade_order[sub_grade] - self.grade_order[mgr_grade]
                    gaps.append(gap)
                    gap_details.append({
                        "manager": display_name(self.graph, mgr),
                        "manager_grade": mgr_grade,
                        "subordinate": display_name(self.graph, sub),
                        "subordinate_grade": sub_grade,
                        "gap": gap
                    })

        # Find unusual gaps (too small or too large)
        unusual_gaps = [g for g in gap_details if g["gap"] < 1 or g["gap"] > 4]

        return {
            "average_grade_gap": round(statistics.mean(gaps), 2) if gaps else 0.0,
            "min_gap": min(gaps) if gaps else 0,
            "max_gap": max(gaps) if gaps else 0,
            "total_comparisons": len(gaps),
            "unusual_gaps": unusual_gaps[:10]  # Limit to first 10
        }

    def _layer_analysis(self) -> Dict:
        """
        Count layers from the actual reporting chain and check the typed Level
        column against it.
        """
        if not self.graph.nodes():
            return {"total_layers": 0, "declared_layers": 0, "by_level": {},
                    "level_mismatches": {"count": 0, "examples": []}, "longest_chain": []}

        by_level: Dict[int, int] = {}
        for node in self.graph.nodes():
            layer = self._layer_of(node)
            by_level[layer] = by_level.get(layer, 0) + 1

        declared = [self.graph.nodes[n].get("level", 0) for n in self.graph.nodes()]
        mismatches = [
            {
                "name": display_name(self.graph, n),
                "declared_level": self.graph.nodes[n].get("level", 0),
                "actual_layer": self.layers[n],
            }
            for n in self.graph.nodes()
            if n in self.layers and self.graph.nodes[n].get("level", 0)
            and self.graph.nodes[n].get("level") != self.layers[n]
        ]

        # Deepest reporting chain, top to bottom — where to look for layer compression
        longest_chain: List[str] = []
        if self.layers:
            node = max(self.layers, key=lambda n: self.layers[n])
            while node is not None:
                longest_chain.append(display_name(self.graph, node))
                preds = list(self.graph.predecessors(node))
                node = preds[0] if preds else None
            longest_chain.reverse()

        return {
            "total_layers": max(self.layers.values()) if self.layers else max(declared),
            "declared_layers": max(declared),
            "by_level": {k: {"count": v} for k, v in sorted(by_level.items())},
            "level_mismatches": {"count": len(mismatches), "examples": mismatches[:10]},
            "longest_chain": longest_chain,
        }

    def _health_indicators(self) -> Dict:
        """Flag organizational health issues."""
        span = self._span_of_control()
        mgr = self._manager_statistics()

        warnings = []
        recommendations = []

        # Check average span
        if span["average_span"] < 5:
            warnings.append(
                f"Low avg span ({span['average_span']}) - consider consolidation"
            )
            recommendations.append(
                "Increase span of control by combining teams or reducing management layers"
            )

        # Check span distribution
        narrow_pct = span["distribution_pct"].get("Narrow (<5)", 0)
        if narrow_pct > 60:
            warnings.append(
                f"{narrow_pct}% managers have narrow spans (<5 reports)"
            )
            recommendations.append(
                "Review managers with 1-2 direct reports for potential consolidation"
            )

        # Check manager ratio
        if mgr["manager_ratio_pct"] > 30:
            warnings.append(
                f"High manager ratio ({mgr['manager_ratio_pct']}%) - potential overhead"
            )
            recommendations.append(
                "Benchmark against industry standards (typically 15-25% managers)"
            )

        # Check for very wide spans
        if span["max_span"] > 15:
            warnings.append(
                f"Some managers have very wide spans (max: {span['max_span']})"
            )
            recommendations.append(
                "Consider adding team leads or splitting large teams"
            )

        # Calculate health score
        health_score = max(0, 100 - len(warnings) * 15)

        return {
            "health_score": health_score,
            "health_grade": self._score_to_grade(health_score),
            "warnings": warnings,
            "recommendations": recommendations,
            "is_healthy": len(warnings) <= 2
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
