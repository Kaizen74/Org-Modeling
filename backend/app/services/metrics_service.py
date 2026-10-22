"""
Metrics Calculator Service.

Calculate org metrics with VALIDATED formulas.
Reference results for the PAX test fixture (a deliberately bottom-heavy org):
64 employees, 34 managers (53.1%), average span 1.85, 6 layers from the
reporting chain, total cost = sum of the fixture's Salary column.
"""

import networkx as nx
from typing import Dict, List, Optional
import statistics

from .org_graph import normalize_employees, build_org_graph, display_name, reporting_layers
from ..resources.benchmarks_reference import (
    SPAN_TARGETS,
    MANAGER_RATIO_RANGE,
    LAYER_PLANNING_SPAN,
    OPERATIONAL_TITLE_KEYWORDS,
    MANAGER_RATIO_BENCHMARKS,
    LAYERS_BENCHMARKS,
)
import math

# Bump when the shape or meaning of calculated metrics changes, so cached
# metrics from older uploads are recalculated instead of shown stale
METRICS_VERSION = 3


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
            "metrics_version": METRICS_VERSION,
            "total_employees": self._total_employees(),
            "manager_stats": self._manager_statistics(),
            "span_of_control": self._span_of_control(),
            "cost_analysis": self._cost_analysis(),
            "grade_gap_analysis": self._grade_gap_analysis(),
            "layer_analysis": self._layer_analysis(),
            "health_indicators": self._health_indicators(),
            "department_analysis": self._department_analysis(),
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
        if getattr(self, "_span_cache", None) is None:
            self._span_cache = self._compute_span_of_control()
        return self._span_cache

    def _compute_span_of_control(self) -> Dict:
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
                "by_manager": {},
                "manager_assessments": [],
                "distribution_vs_benchmark": {"Below benchmark": 0, "Within benchmark": 0, "Above benchmark": 0},
                "single_report_managers": 0,
            }

        total_managers = len(spans)
        assessments = [self._assess_manager_span(m) for m in by_manager]
        vs_benchmark = {"Below benchmark": 0, "Within benchmark": 0, "Above benchmark": 0}
        for a in assessments:
            vs_benchmark[{"below": "Below benchmark", "within": "Within benchmark", "above": "Above benchmark"}[a["status"]]] += 1

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
            "by_manager": by_manager,
            # Each manager judged against the benchmark for the kind of work their team does
            "manager_assessments": sorted(assessments, key=lambda a: (a["status"] != "below", a["span"])),
            "distribution_vs_benchmark": vs_benchmark,
            "single_report_managers": sum(1 for s in spans if s == 1),
        }

    def _team_work_type(self, manager: str) -> Dict:
        """
        Decide which span benchmark applies to a manager's team, and say why.
        Order: explicit Work Type column on the reports, then managers-of-managers,
        then operational domain words in the reports' job titles, else knowledge work.
        """
        reports = list(self.graph.successors(manager))
        declared = [self.graph.nodes[r].get("work_type", "") for r in reports]
        declared = [d for d in declared if d in SPAN_TARGETS]
        if declared:
            kind = max(set(declared), key=declared.count)
            return {"work_type": kind, "basis": "Work Type column"}

        reports_who_manage = sum(1 for r in reports if self.graph.out_degree(r) > 0)
        if reports_who_manage * 2 > len(reports):
            return {"work_type": "knowledge", "basis": "team is mostly managers (manager of managers)"}

        matched = []
        for r in reports:
            title = str(self.graph.nodes[r].get("job_title", "")).lower()
            if any(k in title for k in OPERATIONAL_TITLE_KEYWORDS):
                matched.append(self.graph.nodes[r].get("job_title", ""))
        if matched and len(matched) * 2 >= len(reports):
            return {"work_type": "operational", "basis": f"direct reports' job titles (e.g. '{matched[0]}')"}
        return {"work_type": "knowledge", "basis": "no operational job titles among direct reports (default)"}

    def _assess_manager_span(self, manager: str) -> Dict:
        span = self.graph.out_degree(manager)
        kind = self._team_work_type(manager)
        low, high = SPAN_TARGETS[kind["work_type"]]["range"]
        status = "below" if span < low else "above" if span > high else "within"
        return {
            "manager_id": manager,
            "manager": display_name(self.graph, manager),
            "job_title": self.graph.nodes[manager].get("job_title", ""),
            "department": self.graph.nodes[manager].get("department", ""),
            "span": span,
            "work_type": kind["work_type"],
            "work_type_basis": kind["basis"],
            "benchmark_range": [low, high],
            "status": status,
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

    def _department_analysis(self) -> List[Dict]:
        """
        The same structural lenses per department: size, cost, managers, spans
        against benchmark, layers, the most common roles, and how many people
        report to a manager in a different department.
        """
        assessments = {a["manager_id"]: a for a in self._span_of_control().get("manager_assessments", [])}
        total_people = self._total_employees() or 1
        total_cost = sum(self.graph.nodes[n].get("salary", 0) or 0 for n in self.graph.nodes()) or 0

        by_dept: Dict[str, List[str]] = {}
        for n in self.graph.nodes():
            dept = str(self.graph.nodes[n].get("department") or "Unknown").strip() or "Unknown"
            by_dept.setdefault(dept, []).append(n)

        result = []
        for dept, people in by_dept.items():
            managers = [n for n in people if self.graph.out_degree(n) > 0]
            spans = [self.graph.out_degree(n) for n in managers]
            layers = sorted({self._layer_of(n) for n in people})
            cost = sum(self.graph.nodes[n].get("salary", 0) or 0 for n in people)

            titles: Dict[str, int] = {}
            for n in people:
                t = str(self.graph.nodes[n].get("job_title", "")).strip()
                if t:
                    titles[t] = titles.get(t, 0) + 1

            vs = {"below": 0, "within": 0, "above": 0}
            for m in managers:
                if m in assessments:
                    vs[assessments[m]["status"]] += 1
            operational_teams = sum(1 for m in managers if assessments.get(m, {}).get("work_type") == "operational")

            cross_reports = 0
            for n in people:
                mgr = next(iter(self.graph.predecessors(n)), None)
                if mgr is not None and str(self.graph.nodes[mgr].get("department") or "Unknown").strip() != dept:
                    cross_reports += 1

            result.append({
                "department": dept,
                "headcount": len(people),
                "headcount_pct": round(len(people) / total_people * 100, 1),
                "managers": len(managers),
                "manager_ratio_pct": round(len(managers) / len(people) * 100, 1),
                "average_span": round(statistics.mean(spans), 2) if spans else 0.0,
                "median_span": round(statistics.median(spans), 2) if spans else 0.0,
                "layers_spanned": [layers[0], layers[-1]] if layers else [],
                "layer_count": len(layers),
                "total_cost": round(cost, 0),
                "cost_pct": round(cost / total_cost * 100, 1) if total_cost else 0.0,
                "average_cost": round(cost / len(people), 0),
                "spans_vs_benchmark": vs,
                "operational_teams": operational_teams,
                "single_report_managers": sum(1 for x in spans if x == 1),
                "reports_from_other_departments": cross_reports,
                "top_titles": [
                    {"title": t, "count": c}
                    for t, c in sorted(titles.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
                ],
            })
        return sorted(result, key=lambda d: -d["headcount"])

    # Weights of the health score components (must sum to 100)
    HEALTH_WEIGHTS = {"span_fit": 35, "layers": 25, "manager_ratio": 20, "single_report": 20}

    def _health_indicators(self) -> Dict:
        """
        Structural health as four visible components, each scored 0-100 with
        the value, the benchmark and the rule used, then weighted together.
        """
        span = self._span_of_control()
        mgr = self._manager_statistics()
        layers = self._layer_analysis()
        total = self._total_employees()
        managers = mgr["total_managers"]
        components = []

        # 1. Span fit: share of managers within the benchmark for their team's kind of work
        within = span.get("distribution_vs_benchmark", {}).get("Within benchmark", 0)
        span_fit = round(within / managers * 100) if managers else 100
        below = span.get("distribution_vs_benchmark", {}).get("Below benchmark", 0)
        above = span.get("distribution_vs_benchmark", {}).get("Above benchmark", 0)
        components.append({
            "key": "span_fit", "label": "Spans fit the work",
            "score": span_fit, "weight": self.HEALTH_WEIGHTS["span_fit"],
            "value": f"{within} of {managers} managers within benchmark ({below} below, {above} above)",
            "benchmark": "Knowledge work 5-10, operational work 15-25 direct reports",
            "rule": "Score = % of managers whose span is within the benchmark for their team's kind of work",
            "source": f"{SPAN_TARGETS['knowledge']['source']}; {SPAN_TARGETS['operational']['source']}",
        })

        # 2. Layers vs the minimum this headcount needs at a planning span
        actual_layers = layers["total_layers"]
        needed = max(1, math.ceil(math.log(total, LAYER_PLANNING_SPAN)) + 1) if total > 1 else 1
        excess = max(0, actual_layers - needed)
        layer_score = max(0, 100 - excess * 20)
        components.append({
            "key": "layers", "label": "Layers for this size",
            "score": layer_score, "weight": self.HEALTH_WEIGHTS["layers"],
            "value": f"{actual_layers} layers; about {needed} needed for {total} people at a span of {LAYER_PLANNING_SPAN}",
            "benchmark": LAYERS_BENCHMARKS["typical_guidance"]["range"],
            "rule": f"Minimum layers = ceil(log_{LAYER_PLANNING_SPAN}(headcount)) + 1; minus 20 points per extra layer",
            "source": LAYERS_BENCHMARKS["typical_guidance"]["source"],
        })

        # 3. Manager ratio vs the typical range
        ratio = mgr["manager_ratio_pct"]
        lo, hi = MANAGER_RATIO_RANGE
        distance = lo - ratio if ratio < lo else ratio - hi if ratio > hi else 0
        ratio_score = max(0, round(100 - distance * 4))
        components.append({
            "key": "manager_ratio", "label": "Manager ratio",
            "score": ratio_score, "weight": self.HEALTH_WEIGHTS["manager_ratio"],
            "value": f"{ratio}% of people manage others",
            "benchmark": f"{lo}-{hi}% of the workforce",
            "rule": "Minus 4 points per percentage point outside the range",
            "source": MANAGER_RATIO_BENCHMARKS["typical_range"]["source"],
        })

        # 4. Managers with a single direct report (classic layer-compression signal)
        singles = span.get("single_report_managers", 0)
        single_pct = round(singles / managers * 100, 1) if managers else 0
        single_score = max(0, round(100 - single_pct * 3))
        components.append({
            "key": "single_report", "label": "Single-report managers",
            "score": single_score, "weight": self.HEALTH_WEIGHTS["single_report"],
            "value": f"{singles} of {managers} managers ({single_pct}%) have one direct report",
            "benchmark": "As few as possible — each is a candidate for removing a layer",
            "rule": "Minus 3 points per percentage point of managers with one direct report",
            "source": "Spans-and-layers practice",
        })

        health_score = round(sum(c["score"] * c["weight"] for c in components) / 100)

        warnings, recommendations = [], []
        if span_fit < 70:
            if below >= above:
                warnings.append(f"{below} of {managers} managers have spans below the benchmark for their kind of work")
                recommendations.append("Review the narrowest teams for consolidation, starting with the manager list below")
            else:
                warnings.append(f"{above} of {managers} managers have spans above the benchmark for their kind of work")
                recommendations.append("Consider team leads or splitting the widest teams to protect manager capacity")
        if excess > 0:
            warnings.append(f"{actual_layers} layers where about {needed} would suffice for {total} people")
            recommendations.append("Examine the longest reporting chain for layers that can be removed")
        if ratio_score < 70:
            warnings.append(f"Manager ratio of {ratio}% is outside the typical {lo}-{hi}% range")
            recommendations.append("Check whether manager roles are justified by span and complexity")
        if single_score < 70:
            warnings.append(f"{singles} managers have only one direct report")
            recommendations.append("Single-report managers are the first candidates for layer compression")

        return {
            "health_score": health_score,
            "health_grade": self._score_to_grade(health_score),
            "components": components,
            "warnings": warnings,
            "recommendations": recommendations,
            "is_healthy": health_score >= 70,
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
