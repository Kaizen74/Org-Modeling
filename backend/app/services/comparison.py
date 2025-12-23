"""
Scenario Comparison Service.

Compares two organizational scenarios and generates:
- Metric deltas
- Node-level changes (added, removed, modified)
- Cost impact analysis
- Visual diff data for frontend
"""

from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class NodeChange:
    """Represents a change to a single node."""
    change_type: str  # "added", "removed", "modified", "moved"
    node_id: str
    node_name: str
    node_title: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    changes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_title": self.node_title,
            "before": self.before,
            "after": self.after,
            "changes": self.changes,
        }


@dataclass
class MetricDelta:
    """Represents change in a metric."""
    metric_type: str
    baseline_value: float
    target_value: float
    delta: float
    delta_percent: float
    direction: str  # "increase", "decrease", "unchanged"
    is_improvement: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "baseline_value": self.baseline_value,
            "target_value": self.target_value,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "direction": self.direction,
            "is_improvement": self.is_improvement,
        }


@dataclass
class ComparisonResult:
    """Complete comparison between two scenarios."""
    baseline_id: str
    target_id: str
    metric_deltas: List[MetricDelta]
    node_changes: Dict[str, List[NodeChange]]
    cost_impact: Dict[str, Any]
    summary: Dict[str, Any]
    ai_narrative: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "target_id": self.target_id,
            "metric_deltas": [m.to_dict() for m in self.metric_deltas],
            "node_changes": {
                k: [n.to_dict() for n in v]
                for k, v in self.node_changes.items()
            },
            "cost_impact": self.cost_impact,
            "summary": self.summary,
            "ai_narrative": self.ai_narrative,
        }


# Metrics where lower is better
LOWER_IS_BETTER = {
    "hierarchy_depth",
    "leadership_overhead",
    "reporting_complexity",
    "total_cost",
}


class ScenarioComparator:
    """
    Compares two organizational scenarios.

    Features:
    - Metric delta calculation
    - Node-level change detection
    - Cost impact analysis
    - Manager reassignment tracking
    - Function/location migration tracking
    """

    def __init__(self):
        self.lower_is_better = LOWER_IS_BETTER

    def compare(
        self,
        baseline: Dict[str, Any],
        target: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        target_metrics: Dict[str, Any],
    ) -> ComparisonResult:
        """
        Compare two scenarios.

        Args:
            baseline: Baseline scenario data with employees
            target: Target scenario data with employees
            baseline_metrics: Metrics for baseline
            target_metrics: Metrics for target

        Returns:
            ComparisonResult with all comparison data
        """
        # Calculate metric deltas
        metric_deltas = self._calculate_metric_deltas(
            baseline_metrics, target_metrics
        )

        # Detect node changes
        node_changes = self._detect_node_changes(
            baseline.get("employees", []),
            target.get("employees", []),
        )

        # Calculate cost impact
        cost_impact = self._calculate_cost_impact(
            baseline.get("employees", []),
            target.get("employees", []),
            node_changes,
        )

        # Generate summary
        summary = self._generate_summary(
            baseline, target, metric_deltas, node_changes, cost_impact
        )

        return ComparisonResult(
            baseline_id=baseline.get("id", ""),
            target_id=target.get("id", ""),
            metric_deltas=metric_deltas,
            node_changes=node_changes,
            cost_impact=cost_impact,
            summary=summary,
        )

    def _calculate_metric_deltas(
        self,
        baseline_metrics: Dict[str, Any],
        target_metrics: Dict[str, Any],
    ) -> List[MetricDelta]:
        """Calculate changes in metrics between scenarios."""
        deltas = []

        # Get metric values from both
        baseline_values = self._extract_metric_values(baseline_metrics)
        target_values = self._extract_metric_values(target_metrics)

        # All metrics
        all_metrics = set(baseline_values.keys()) | set(target_values.keys())

        for metric_type in all_metrics:
            baseline_val = baseline_values.get(metric_type, 0)
            target_val = target_values.get(metric_type, 0)

            delta = target_val - baseline_val
            delta_percent = (
                (delta / baseline_val * 100) if baseline_val != 0 else 0
            )

            if abs(delta) < 0.001:
                direction = "unchanged"
            elif delta > 0:
                direction = "increase"
            else:
                direction = "decrease"

            # Determine if change is improvement
            is_improvement = None
            if metric_type in self.lower_is_better:
                is_improvement = delta < 0
            elif metric_type in ["span_of_control_avg"]:
                # Optimal range 4-8
                baseline_optimal = 4 <= baseline_val <= 8
                target_optimal = 4 <= target_val <= 8
                is_improvement = target_optimal and not baseline_optimal

            deltas.append(MetricDelta(
                metric_type=metric_type,
                baseline_value=round(baseline_val, 2),
                target_value=round(target_val, 2),
                delta=round(delta, 2),
                delta_percent=round(delta_percent, 2),
                direction=direction,
                is_improvement=is_improvement,
            ))

        return sorted(deltas, key=lambda d: abs(d.delta_percent), reverse=True)

    def _extract_metric_values(
        self, metrics_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract metric values from metrics report."""
        values = {}

        # From summary
        summary = metrics_data.get("summary", {})
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                values[key] = float(value)

        # From metrics list
        for metric in metrics_data.get("metrics", []):
            metric_type = metric.get("metric_type", "")
            value = metric.get("value", 0)
            if isinstance(value, (int, float)):
                values[metric_type] = float(value)

        return values

    def _detect_node_changes(
        self,
        baseline_employees: List[Dict],
        target_employees: List[Dict],
    ) -> Dict[str, List[NodeChange]]:
        """Detect changes at the node level."""
        changes: Dict[str, List[NodeChange]] = {
            "added": [],
            "removed": [],
            "modified": [],
            "moved": [],
        }

        # Create lookup by matching key (employee_id or name)
        baseline_by_key = {}
        for emp in baseline_employees:
            key = emp.get("employee_id") or emp.get("full_name", "")
            baseline_by_key[key] = emp

        target_by_key = {}
        for emp in target_employees:
            key = emp.get("employee_id") or emp.get("full_name", "")
            target_by_key[key] = emp

        baseline_keys = set(baseline_by_key.keys())
        target_keys = set(target_by_key.keys())

        # Find removed nodes
        for key in baseline_keys - target_keys:
            emp = baseline_by_key[key]
            changes["removed"].append(NodeChange(
                change_type="removed",
                node_id=emp.get("id", key),
                node_name=emp.get("full_name", ""),
                node_title=emp.get("job_title", ""),
                before=self._simplify_employee(emp),
            ))

        # Find added nodes
        for key in target_keys - baseline_keys:
            emp = target_by_key[key]
            changes["added"].append(NodeChange(
                change_type="added",
                node_id=emp.get("id", key),
                node_name=emp.get("full_name", ""),
                node_title=emp.get("job_title", ""),
                after=self._simplify_employee(emp),
            ))

        # Find modified nodes
        for key in baseline_keys & target_keys:
            before = baseline_by_key[key]
            after = target_by_key[key]

            field_changes = self._detect_field_changes(before, after)

            if field_changes:
                # Check if it's a move (manager changed)
                manager_changed = any(
                    c["field"] == "manager_id" for c in field_changes
                )

                change = NodeChange(
                    change_type="moved" if manager_changed else "modified",
                    node_id=after.get("id", key),
                    node_name=after.get("full_name", ""),
                    node_title=after.get("job_title", ""),
                    before=self._simplify_employee(before),
                    after=self._simplify_employee(after),
                    changes=field_changes,
                )

                if manager_changed:
                    changes["moved"].append(change)
                else:
                    changes["modified"].append(change)

        return changes

    def _detect_field_changes(
        self,
        before: Dict,
        after: Dict,
    ) -> List[Dict[str, Any]]:
        """Detect changes in specific fields."""
        changes = []

        # Fields to compare
        compare_fields = [
            "job_title",
            "grade",
            "level",
            "function",
            "department",
            "location",
            "manager_id",
            "fte",
            "cost_base_salary",
        ]

        for field in compare_fields:
            before_val = before.get(field)
            after_val = after.get(field)

            if before_val != after_val:
                changes.append({
                    "field": field,
                    "before": before_val,
                    "after": after_val,
                })

        return changes

    def _simplify_employee(self, emp: Dict) -> Dict[str, Any]:
        """Create simplified employee record for comparison output."""
        return {
            "id": emp.get("id"),
            "employee_id": emp.get("employee_id"),
            "full_name": emp.get("full_name"),
            "job_title": emp.get("job_title"),
            "grade": emp.get("grade"),
            "level": emp.get("level"),
            "function": emp.get("function"),
            "location": emp.get("location"),
            "manager_id": emp.get("manager_id"),
            "fte": emp.get("fte"),
            "cost": self._get_employee_cost(emp),
        }

    def _get_employee_cost(self, emp: Dict) -> float:
        """Calculate total cost for an employee."""
        base = emp.get("cost_base_salary", 0) or 0
        variable = emp.get("cost_variable", 0) or 0
        benefits = emp.get("cost_benefits", 0) or 0
        multiplier = emp.get("cost_overhead_multiplier", 1.0) or 1.0
        fte = emp.get("fte", 1.0) or 1.0

        return (base + variable + benefits) * multiplier * fte

    def _calculate_cost_impact(
        self,
        baseline_employees: List[Dict],
        target_employees: List[Dict],
        node_changes: Dict[str, List[NodeChange]],
    ) -> Dict[str, Any]:
        """Calculate cost impact of changes."""
        baseline_total = sum(
            self._get_employee_cost(emp) for emp in baseline_employees
        )
        target_total = sum(
            self._get_employee_cost(emp) for emp in target_employees
        )

        delta = target_total - baseline_total
        delta_percent = (delta / baseline_total * 100) if baseline_total else 0

        # Cost by change type
        added_cost = sum(
            self._get_employee_cost(c.after or {})
            for c in node_changes.get("added", [])
        )
        removed_cost = sum(
            self._get_employee_cost(c.before or {})
            for c in node_changes.get("removed", [])
        )

        # Cost changes from modifications
        modification_cost_delta = 0
        for change in node_changes.get("modified", []) + node_changes.get("moved", []):
            if change.before and change.after:
                before_cost = self._get_employee_cost(change.before)
                after_cost = self._get_employee_cost(change.after)
                modification_cost_delta += after_cost - before_cost

        return {
            "baseline_total": round(baseline_total, 2),
            "target_total": round(target_total, 2),
            "delta": round(delta, 2),
            "delta_percent": round(delta_percent, 2),
            "added_cost": round(added_cost, 2),
            "removed_cost": round(removed_cost, 2),
            "modification_delta": round(modification_cost_delta, 2),
            "is_cost_reduction": delta < 0,
        }

    def _generate_summary(
        self,
        baseline: Dict,
        target: Dict,
        metric_deltas: List[MetricDelta],
        node_changes: Dict[str, List[NodeChange]],
        cost_impact: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comparison summary."""
        baseline_count = len(baseline.get("employees", []))
        target_count = len(target.get("employees", []))

        # Find significant metric changes
        significant_improvements = [
            d for d in metric_deltas
            if d.is_improvement is True and abs(d.delta_percent) > 5
        ]
        significant_concerns = [
            d for d in metric_deltas
            if d.is_improvement is False and abs(d.delta_percent) > 5
        ]

        return {
            "baseline_name": baseline.get("name", ""),
            "target_name": target.get("name", ""),
            "headcount_change": target_count - baseline_count,
            "headcount_change_percent": round(
                (target_count - baseline_count) / baseline_count * 100
                if baseline_count else 0,
                2
            ),
            "total_nodes_changed": (
                len(node_changes.get("added", [])) +
                len(node_changes.get("removed", [])) +
                len(node_changes.get("modified", [])) +
                len(node_changes.get("moved", []))
            ),
            "nodes_added": len(node_changes.get("added", [])),
            "nodes_removed": len(node_changes.get("removed", [])),
            "nodes_modified": len(node_changes.get("modified", [])),
            "nodes_moved": len(node_changes.get("moved", [])),
            "cost_delta": cost_impact.get("delta", 0),
            "cost_delta_percent": cost_impact.get("delta_percent", 0),
            "significant_improvements": [
                {"metric": d.metric_type, "delta_percent": d.delta_percent}
                for d in significant_improvements[:5]
            ],
            "significant_concerns": [
                {"metric": d.metric_type, "delta_percent": d.delta_percent}
                for d in significant_concerns[:5]
            ],
        }


def compare_scenarios(
    baseline: Dict[str, Any],
    target: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    target_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience function to compare scenarios.

    Args:
        baseline: Baseline scenario data
        target: Target scenario data
        baseline_metrics: Metrics for baseline
        target_metrics: Metrics for target

    Returns:
        Dictionary with comparison result
    """
    comparator = ScenarioComparator()
    result = comparator.compare(baseline, target, baseline_metrics, target_metrics)
    return result.to_dict()
