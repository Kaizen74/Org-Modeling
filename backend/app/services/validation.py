"""
Organizational Structure Validation Service.

Validates parsed org data for structural issues:
- Cycle detection (reporting loops)
- Orphan detection (disconnected nodes)
- Duplicate detection
- Missing manager references
- Level consistency
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import networkx as nx
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation issue."""
    error_type: str
    severity: str  # "error", "warning", "info"
    message: str
    affected_nodes: List[str]
    suggested_fix: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "severity": self.severity,
            "message": self.message,
            "affected_nodes": self.affected_nodes,
            "suggested_fix": self.suggested_fix,
            "details": self.details,
        }


@dataclass
class ValidationResult:
    """Result of validation process."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    info: List[ValidationError]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "summary": self.summary,
        }

    @property
    def all_issues(self) -> List[ValidationError]:
        return self.errors + self.warnings + self.info


class OrgValidator:
    """
    Validates organizational structure for common issues.

    Checks for:
    - Cycles (reporting loops)
    - Orphans (nodes with no path to root)
    - Duplicates (same ID or name)
    - Missing managers (referenced but not found)
    - Level inconsistencies
    - Span of control issues
    - Deep hierarchies
    """

    def __init__(
        self,
        max_span_warning: int = 12,
        max_span_error: int = 25,
        max_depth_warning: int = 8,
        max_depth_error: int = 12,
    ):
        """
        Initialize validator with thresholds.

        Args:
            max_span_warning: Warn if span of control exceeds this
            max_span_error: Error if span of control exceeds this
            max_depth_warning: Warn if hierarchy depth exceeds this
            max_depth_error: Error if hierarchy depth exceeds this
        """
        self.max_span_warning = max_span_warning
        self.max_span_error = max_span_error
        self.max_depth_warning = max_depth_warning
        self.max_depth_error = max_depth_error

    def validate(
        self,
        employees: List[Dict[str, Any]],
        relationships: List[Tuple[str, str]],
    ) -> ValidationResult:
        """
        Run all validation checks on the org structure.

        Args:
            employees: List of employee dicts with 'id' field
            relationships: List of (manager_id, employee_id) tuples

        Returns:
            ValidationResult with all found issues
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        info: List[ValidationError] = []

        # Build graph for analysis
        G = self._build_graph(employees, relationships)

        # Run all checks
        errors.extend(self._check_duplicates(employees))
        errors.extend(self._check_cycles(G))
        errors.extend(self._check_missing_managers(employees, relationships))

        orphan_issues = self._check_orphans(G)
        for issue in orphan_issues:
            if issue.severity == "error":
                errors.append(issue)
            else:
                warnings.append(issue)

        span_issues = self._check_span_of_control(G)
        for issue in span_issues:
            if issue.severity == "error":
                errors.append(issue)
            else:
                warnings.append(issue)

        depth_issues = self._check_depth(G)
        for issue in depth_issues:
            if issue.severity == "error":
                errors.append(issue)
            else:
                warnings.append(issue)

        level_issues = self._check_level_consistency(G)
        warnings.extend(level_issues)

        # Info-level observations
        info.extend(self._generate_observations(G, employees))

        # Determine overall validity (no errors = valid)
        is_valid = len(errors) == 0

        # Summary statistics
        summary = self._generate_summary(G, employees, relationships)

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            summary=summary,
        )

    def _build_graph(
        self,
        employees: List[Dict[str, Any]],
        relationships: List[Tuple[str, str]],
    ) -> nx.DiGraph:
        """Build NetworkX graph from employees and relationships."""
        G = nx.DiGraph()

        # Add nodes
        for emp in employees:
            G.add_node(emp["id"], **emp)

        # Add edges (manager → employee)
        for manager_id, employee_id in relationships:
            if manager_id in G and employee_id in G:
                G.add_edge(manager_id, employee_id)

        return G

    def _check_duplicates(
        self, employees: List[Dict[str, Any]]
    ) -> List[ValidationError]:
        """Check for duplicate employee IDs or names."""
        errors = []

        # Check ID duplicates
        id_counts: Dict[str, int] = {}
        for emp in employees:
            emp_id = emp.get("id", "")
            id_counts[emp_id] = id_counts.get(emp_id, 0) + 1

        for emp_id, count in id_counts.items():
            if count > 1:
                errors.append(ValidationError(
                    error_type="duplicate_id",
                    severity="error",
                    message=f"Duplicate employee ID '{emp_id}' found {count} times",
                    affected_nodes=[emp_id],
                    suggested_fix="Assign unique IDs to each employee",
                    details={"count": count},
                ))

        # Check name duplicates (warning only)
        name_counts: Dict[str, List[str]] = {}
        for emp in employees:
            name = emp.get("full_name", "").lower().strip()
            if name:
                if name not in name_counts:
                    name_counts[name] = []
                name_counts[name].append(emp.get("id", "unknown"))

        for name, ids in name_counts.items():
            if len(ids) > 1:
                # This is a warning, not an error - same names can be valid
                pass  # Could add as info if needed

        return errors

    def _check_cycles(self, G: nx.DiGraph) -> List[ValidationError]:
        """Detect reporting cycles (loops) in the org structure."""
        errors = []

        try:
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                cycle_path = " → ".join(cycle + [cycle[0]])
                errors.append(ValidationError(
                    error_type="cycle",
                    severity="error",
                    message=f"Reporting cycle detected: {cycle_path}",
                    affected_nodes=cycle,
                    suggested_fix="Remove one of the reporting relationships to break the cycle",
                    details={"cycle_path": cycle},
                ))
        except nx.NetworkXError as e:
            logger.warning(f"Cycle detection failed: {e}")

        return errors

    def _check_orphans(self, G: nx.DiGraph) -> List[ValidationError]:
        """Detect orphaned nodes (no path to any root)."""
        issues = []

        # Find root nodes (no incoming edges)
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        if not roots:
            issues.append(ValidationError(
                error_type="no_root",
                severity="error",
                message="No root node found (everyone reports to someone - circular structure?)",
                affected_nodes=list(G.nodes())[:10],
                suggested_fix="Ensure at least one person has no manager (CEO/top leader)",
            ))
            return issues

        # Find all nodes reachable from roots
        reachable = set()
        for root in roots:
            reachable.add(root)
            try:
                descendants = nx.descendants(G, root)
                reachable.update(descendants)
            except nx.NetworkXError:
                pass

        # Identify orphans
        all_nodes = set(G.nodes())
        orphans = all_nodes - reachable

        if orphans:
            orphan_list = list(orphans)
            # Get names for display
            orphan_names = [
                G.nodes[node].get("full_name", node)
                for node in orphan_list[:5]
            ]
            name_str = ", ".join(orphan_names)
            if len(orphans) > 5:
                name_str += f" (+{len(orphans) - 5} more)"

            issues.append(ValidationError(
                error_type="orphan",
                severity="warning",
                message=f"{len(orphans)} disconnected employee(s): {name_str}",
                affected_nodes=orphan_list,
                suggested_fix="Assign a manager to connect these employees to the org structure",
                details={"count": len(orphans)},
            ))

        return issues

    def _check_missing_managers(
        self,
        employees: List[Dict[str, Any]],
        relationships: List[Tuple[str, str]],
    ) -> List[ValidationError]:
        """Check for references to non-existent managers."""
        errors = []

        employee_ids = {emp["id"] for emp in employees}
        missing_managers: Dict[str, List[str]] = {}

        for manager_id, employee_id in relationships:
            if manager_id not in employee_ids:
                if manager_id not in missing_managers:
                    missing_managers[manager_id] = []
                missing_managers[manager_id].append(employee_id)

        for manager_id, affected in missing_managers.items():
            errors.append(ValidationError(
                error_type="missing_manager",
                severity="error",
                message=f"Manager '{manager_id}' not found (referenced by {len(affected)} employee(s))",
                affected_nodes=affected,
                suggested_fix=f"Add manager '{manager_id}' to the org or reassign affected employees",
                details={"manager_id": manager_id, "affected_count": len(affected)},
            ))

        return errors

    def _check_span_of_control(self, G: nx.DiGraph) -> List[ValidationError]:
        """Check for excessively wide or narrow spans of control."""
        issues = []

        for node in G.nodes():
            direct_reports = list(G.successors(node))
            span = len(direct_reports)

            if span > self.max_span_error:
                issues.append(ValidationError(
                    error_type="excessive_span",
                    severity="error",
                    message=f"'{G.nodes[node].get('full_name', node)}' has {span} direct reports (max: {self.max_span_error})",
                    affected_nodes=[node] + direct_reports,
                    suggested_fix="Consider adding an intermediate management layer",
                    details={"span": span, "threshold": self.max_span_error},
                ))
            elif span > self.max_span_warning:
                issues.append(ValidationError(
                    error_type="wide_span",
                    severity="warning",
                    message=f"'{G.nodes[node].get('full_name', node)}' has {span} direct reports (recommended: <{self.max_span_warning})",
                    affected_nodes=[node],
                    suggested_fix="Consider restructuring for better manageability",
                    details={"span": span, "threshold": self.max_span_warning},
                ))

        return issues

    def _check_depth(self, G: nx.DiGraph) -> List[ValidationError]:
        """Check for excessively deep hierarchies."""
        issues = []

        # Find roots
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        for root in roots:
            try:
                depths = nx.single_source_shortest_path_length(G, root)
                max_depth = max(depths.values()) if depths else 0

                if max_depth > self.max_depth_error:
                    deepest = [node for node, d in depths.items() if d == max_depth]
                    issues.append(ValidationError(
                        error_type="excessive_depth",
                        severity="error",
                        message=f"Hierarchy depth of {max_depth + 1} levels exceeds maximum ({self.max_depth_error + 1})",
                        affected_nodes=deepest[:5],
                        suggested_fix="Consider flattening the organization by removing intermediate layers",
                        details={"depth": max_depth + 1, "threshold": self.max_depth_error + 1, "root": root},
                    ))
                elif max_depth > self.max_depth_warning:
                    issues.append(ValidationError(
                        error_type="deep_hierarchy",
                        severity="warning",
                        message=f"Hierarchy has {max_depth + 1} levels (recommended: <{self.max_depth_warning + 1})",
                        affected_nodes=[root],
                        suggested_fix="Review if all management layers add value",
                        details={"depth": max_depth + 1, "threshold": self.max_depth_warning + 1},
                    ))
            except nx.NetworkXError:
                pass

        return issues

    def _check_level_consistency(self, G: nx.DiGraph) -> List[ValidationError]:
        """Check if employee levels are consistent with hierarchy position."""
        issues = []

        for edge in G.edges():
            manager_id, employee_id = edge
            manager_level = G.nodes[manager_id].get("level")
            employee_level = G.nodes[employee_id].get("level")

            if manager_level is not None and employee_level is not None:
                if employee_level <= manager_level:
                    issues.append(ValidationError(
                        error_type="level_inconsistency",
                        severity="warning",
                        message=(
                            f"'{G.nodes[employee_id].get('full_name', employee_id)}' (Level {employee_level}) "
                            f"reports to '{G.nodes[manager_id].get('full_name', manager_id)}' (Level {manager_level})"
                        ),
                        affected_nodes=[manager_id, employee_id],
                        suggested_fix="Verify level assignments reflect actual hierarchy",
                        details={
                            "manager_level": manager_level,
                            "employee_level": employee_level,
                        },
                    ))

        return issues

    def _generate_observations(
        self, G: nx.DiGraph, employees: List[Dict]
    ) -> List[ValidationError]:
        """Generate informational observations about the org."""
        info = []

        # Count individual contributors (no direct reports)
        ics = [node for node in G.nodes() if G.out_degree(node) == 0]
        if len(ics) > len(G.nodes()) * 0.8:
            info.append(ValidationError(
                error_type="high_ic_ratio",
                severity="info",
                message=f"{len(ics)} of {len(G.nodes())} employees ({100*len(ics)//len(G.nodes())}%) are individual contributors",
                affected_nodes=[],
                details={"ic_count": len(ics), "total": len(G.nodes())},
            ))

        # Check for multiple roots
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]
        if len(roots) > 1:
            root_names = [G.nodes[r].get("full_name", r) for r in roots]
            info.append(ValidationError(
                error_type="multiple_roots",
                severity="info",
                message=f"Multiple top-level leaders: {', '.join(root_names[:5])}",
                affected_nodes=roots,
                details={"root_count": len(roots)},
            ))

        return info

    def _generate_summary(
        self,
        G: nx.DiGraph,
        employees: List[Dict],
        relationships: List[Tuple[str, str]],
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]
        ics = [node for node in G.nodes() if G.out_degree(node) == 0]
        managers = [node for node in G.nodes() if G.out_degree(node) > 0]

        # Calculate max depth
        max_depth = 0
        for root in roots:
            try:
                depths = nx.single_source_shortest_path_length(G, root)
                if depths:
                    max_depth = max(max_depth, max(depths.values()))
            except nx.NetworkXError:
                pass

        # Calculate average span
        spans = [G.out_degree(node) for node in managers]
        avg_span = sum(spans) / len(spans) if spans else 0

        return {
            "total_employees": len(employees),
            "total_relationships": len(relationships),
            "root_count": len(roots),
            "manager_count": len(managers),
            "ic_count": len(ics),
            "max_depth": max_depth + 1,
            "avg_span_of_control": round(avg_span, 2),
            "max_span_of_control": max(spans) if spans else 0,
        }


def validate_org_structure(
    employees: List[Dict[str, Any]],
    relationships: List[Tuple[str, str]],
) -> Dict[str, Any]:
    """
    Convenience function to validate org structure.

    Args:
        employees: List of employee dicts
        relationships: List of (manager_id, employee_id) tuples

    Returns:
        Dictionary with validation results
    """
    validator = OrgValidator()
    result = validator.validate(employees, relationships)
    return result.to_dict()
