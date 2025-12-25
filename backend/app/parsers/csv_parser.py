"""
CSV Parser for organizational structure data.

TESTED WITH: org_structure_PAX.csv
EXPECTED: 64 employees, 16 managers, avg span 3.94
"""

import pandas as pd
import networkx as nx
from typing import Dict, List, Optional, Any
from pathlib import Path
import io


class OrgCSVParser:
    """
    Parse CSV org structure with validated metrics.

    TESTED WITH: org_structure_PAX.csv
    EXPECTED: 64 employees, 16 managers, avg span 3.94
    """

    REQUIRED_COLUMNS = ["Name", "Job Title", "Grade", "Level", "Line Manager"]
    OPTIONAL_COLUMNS = ["Department", "Employee ID", "Salary"]

    def __init__(self, csv_source):
        """
        Initialize parser with CSV source.

        Args:
            csv_source: Either a file path (str/Path) or file-like object
        """
        self.csv_source = csv_source
        self.df: Optional[pd.DataFrame] = None
        self.graph: Optional[nx.DiGraph] = None

    def parse(self) -> Dict[str, Any]:
        """
        Parse CSV and return structured data.

        Returns:
            {
                'employees': List[Dict],
                'graph': nx.DiGraph,
                'validation_errors': List[str],
                'metadata': Dict
            }
        """
        # Read CSV
        try:
            if isinstance(self.csv_source, (str, Path)):
                self.df = pd.read_csv(self.csv_source)
            else:
                # File-like object
                self.df = pd.read_csv(self.csv_source)
        except Exception as e:
            return {
                "employees": [],
                "graph": None,
                "validation_errors": [f"Failed to read CSV: {str(e)}"],
                "metadata": {}
            }

        # CRITICAL: Remove any completely empty rows
        self.df = self.df.dropna(how="all")

        # Validate columns
        validation_errors = self._validate_columns()
        if validation_errors:
            return {
                "employees": [],
                "graph": None,
                "validation_errors": validation_errors,
                "metadata": {}
            }

        # Clean data
        self.df = self._clean_data()

        # Build employee records
        employees = self._build_employee_records()

        # Build graph
        self.graph = self._build_graph(employees)

        # Detect structural issues
        structural_errors = self._detect_issues()

        # Calculate metadata
        metadata = self._calculate_metadata(employees)

        return {
            "employees": employees,
            "graph": self.graph,
            "validation_errors": structural_errors,
            "metadata": metadata
        }

    def _validate_columns(self) -> List[str]:
        """Validate required columns exist."""
        errors = []
        missing = set(self.REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
        return errors

    def _clean_data(self) -> pd.DataFrame:
        """Clean and normalize the data."""
        df = self.df.copy()

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip()

        # Convert salary (remove commas, handle various formats) - optional column
        if "Salary" in df.columns:
            df["Salary"] = (
                df["Salary"]
                .astype(str)
                .str.replace(",", "")
                .str.replace("$", "")
                .str.strip()
            )
            df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce").fillna(0)
        else:
            df["Salary"] = 0  # Will be populated from grade configuration

        # Convert level to int
        df["Level"] = pd.to_numeric(df["Level"], errors="coerce").fillna(0).astype(int)

        # Fill missing Employee ID with Name
        if "Employee ID" not in df.columns or df["Employee ID"].isna().all():
            df["Employee ID"] = df["Name"]
        else:
            df["Employee ID"] = df["Employee ID"].fillna(df["Name"])

        # Fill missing Department
        if "Department" not in df.columns:
            df["Department"] = "Unknown"
        else:
            df["Department"] = df["Department"].fillna("Unknown")

        return df

    def _build_employee_records(self) -> List[Dict]:
        """Build list of employee dictionaries."""
        employees = []
        for _, row in self.df.iterrows():
            # Skip rows with empty names
            if pd.isna(row["Name"]) or str(row["Name"]).strip() in ["", "nan"]:
                continue

            employees.append({
                "name": str(row["Name"]).strip(),
                "job_title": str(row["Job Title"]).strip() if pd.notna(row["Job Title"]) else "",
                "grade": str(row["Grade"]).strip() if pd.notna(row["Grade"]) else "",
                "department": str(row.get("Department", "Unknown")).strip(),
                "level": int(row["Level"]) if pd.notna(row["Level"]) else 0,
                "manager_name": str(row["Line Manager"]).strip() if pd.notna(row["Line Manager"]) else "",
                "salary": float(row["Salary"]) if pd.notna(row["Salary"]) else 0.0,
                "employee_id": str(row.get("Employee ID", row["Name"])).strip()
            })
        return employees

    def _build_graph(self, employees: List[Dict]) -> nx.DiGraph:
        """Build directed graph of reporting relationships."""
        G = nx.DiGraph()

        # Add all employees as nodes
        for emp in employees:
            G.add_node(emp["name"], **emp)

        # Add edges (manager -> direct report)
        for emp in employees:
            mgr = emp["manager_name"]
            # Skip if no manager or is top of org
            if mgr and mgr not in ["Top of Org", "N/A", "", "nan"] and mgr in G.nodes:
                G.add_edge(mgr, emp["name"])

        return G

    def _detect_issues(self) -> List[str]:
        """Detect structural issues in the org."""
        errors = []

        if not self.graph:
            return errors

        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                cycle_strs = [" -> ".join(c) for c in cycles[:3]]  # Show first 3
                errors.append(f"Circular reporting detected: {'; '.join(cycle_strs)}")
        except Exception:
            pass

        # Check for multiple roots (people with no manager)
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        if len(roots) > 1:
            errors.append(f"Multiple root nodes found ({len(roots)}): {', '.join(roots[:5])}")

        # Check for orphans (manager not in list)
        all_names = set(self.graph.nodes())
        for emp in self.graph.nodes():
            mgr = self.graph.nodes[emp].get("manager_name", "")
            if mgr and mgr not in ["Top of Org", "N/A", "", "nan"] and mgr not in all_names:
                errors.append(f"Manager not found for {emp}: '{mgr}'")

        return errors[:10]  # Limit to first 10 errors

    def _calculate_metadata(self, employees: List[Dict]) -> Dict:
        """Calculate summary metadata."""
        total = len(employees)

        if total == 0:
            return {
                "total_employees": 0,
                "manager_count": 0,
                "ic_count": 0,
                "unique_grades": [],
                "organizational_layers": 0,
                "total_salary_cost": 0.0
            }

        # Count managers (those with direct reports)
        managers = set()
        if self.graph:
            for node in self.graph.nodes():
                if self.graph.out_degree(node) > 0:
                    managers.add(node)

        # Get unique grades
        unique_grades = sorted(list(set(emp["grade"] for emp in employees if emp["grade"])))

        # Get max level
        max_level = max((emp["level"] for emp in employees), default=0)

        # Calculate total salary
        total_salary = sum(emp["salary"] for emp in employees)

        return {
            "total_employees": total,
            "manager_count": len(managers),
            "ic_count": total - len(managers),
            "unique_grades": unique_grades,
            "organizational_layers": max_level,
            "total_salary_cost": round(total_salary, 2)
        }

    def get_employees_by_manager(self) -> Dict[str, List[str]]:
        """Get direct reports for each manager."""
        if not self.graph:
            return {}

        return {
            node: list(self.graph.successors(node))
            for node in self.graph.nodes()
            if self.graph.out_degree(node) > 0
        }

    def get_org_hierarchy(self) -> Dict:
        """Get hierarchical structure for visualization."""
        if not self.graph:
            return {}

        # Find root nodes
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]

        def build_tree(node):
            children = list(self.graph.successors(node))
            node_data = dict(self.graph.nodes[node])
            return {
                "name": node,
                "data": node_data,
                "children": [build_tree(child) for child in children]
            }

        if len(roots) == 1:
            return build_tree(roots[0])
        else:
            return {
                "name": "Organization",
                "data": {},
                "children": [build_tree(root) for root in roots]
            }
