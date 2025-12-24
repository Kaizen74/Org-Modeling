"""
CSV Parser for organizational data.

Supports importing employee data from CSV files with configurable column mappings.
"""

import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class CSVParseResult:
    """Result of parsing a CSV file."""
    employees: List[Dict[str, Any]]
    relationships: List[Tuple[str, str]]
    validation_errors: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employees": self.employees,
            "relationships": [list(r) for r in self.relationships],
            "validation_errors": self.validation_errors,
            "metadata": self.metadata,
        }


# Default column mappings (can be customized by user)
DEFAULT_COLUMN_MAPPINGS = {
    "employee_id": [
        "employee_id", "emp_id", "id", "eid", "employee id", "emp id",
        "employeeid", "staff_id", "staff id", "personnel_id"
    ],
    "full_name": [
        "full_name", "name", "employee_name", "emp_name", "employee name",
        "fullname", "staff_name", "person_name", "display_name"
    ],
    "job_title": [
        "job_title", "title", "position", "role", "job title", "job_title_name",
        "jobtitle", "designation", "job_role", "position_title"
    ],
    "manager_id": [
        "manager_id", "manager", "reports_to", "supervisor_id", "reports to", "manager id",
        "managerid", "reporting_to", "supervisor", "boss_id", "direct_manager_id"
    ],
    "manager_name": [
        "manager_name", "manager name", "supervisor_name", "reports_to_name",
        "line_manager", "line manager", "line mar", "linemanager", "reporting_manager",
        "direct_manager", "boss_name", "manager_full_name"
    ],
    "level": [
        "level", "grade_level", "hierarchy_level", "org_level",
        "hier_level", "reporting_level", "job_level", "position_level"
    ],
    "grade": [
        "grade", "job_grade", "pay_grade", "band", "job grade",
        "salary_grade", "compensation_grade", "level_grade"
    ],
    "function": [
        "function", "department", "division", "org_unit", "business_unit",
        "dept", "departm", "dept_name", "department_name", "team", "unit",
        "business_function", "org_function"
    ],
    "location": [
        "location", "office", "city", "work_location", "site",
        "office_location", "work_city", "base_location", "country"
    ],
    "cost_center": [
        "cost_center", "cc", "cost center", "cost_center_code",
        "costcenter", "cost_centre", "cc_code"
    ],
    "fte": [
        "fte", "full_time_equivalent", "headcount_fte",
        "fulltime_equivalent", "fte_count", "headcount"
    ],
    "salary": [
        "salary", "base_salary", "annual_salary", "base_pay", "compensation",
        "pay", "wage", "annual_pay", "yearly_salary", "base_compensation"
    ],
}


class CSVParser:
    """
    Parses CSV files containing organizational employee data.

    Features:
    - Flexible column mapping (auto-detect or user-specified)
    - Relationship inference from manager_id or manager_name
    - Validation of required fields
    - Support for various CSV formats (comma, semicolon, tab)
    """

    def __init__(
        self,
        column_mappings: Optional[Dict[str, str]] = None,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ):
        """
        Initialize the CSV parser.

        Args:
            column_mappings: Custom column name mappings
            delimiter: CSV delimiter character
            encoding: File encoding
        """
        self.custom_mappings = column_mappings or {}
        self.delimiter = delimiter
        self.encoding = encoding

    def parse(self, file_content: str) -> CSVParseResult:
        """
        Parse CSV content and extract employee data.

        Args:
            file_content: CSV file content as string

        Returns:
            CSVParseResult with employees, relationships, and metadata
        """
        validation_errors = []
        employees = []
        relationships = []

        try:
            # Detect delimiter if not specified
            if not self.delimiter:
                self.delimiter = self._detect_delimiter(file_content)

            # Parse CSV
            reader = csv.DictReader(
                io.StringIO(file_content),
                delimiter=self.delimiter
            )

            # Map columns
            headers = reader.fieldnames or []
            column_map = self._create_column_map(headers)

            if not column_map.get("full_name"):
                validation_errors.append({
                    "error_type": "missing_column",
                    "severity": "error",
                    "message": "Required column 'name' or 'full_name' not found",
                    "affected_nodes": [],
                })
                return CSVParseResult(
                    employees=[],
                    relationships=[],
                    validation_errors=validation_errors,
                    metadata={"total_rows": 0, "headers": headers},
                )

            # Process rows
            name_to_id = {}  # For manager_name resolution
            rows_with_manager_name = []

            def normalize_name(name: str) -> str:
                """Normalize name for matching - lowercase, strip, collapse whitespace."""
                if not name:
                    return ""
                return " ".join(name.lower().strip().split())

            def get_name_variants(name: str) -> List[str]:
                """Generate multiple variants of a name for fuzzy matching."""
                if not name:
                    return []
                normalized = normalize_name(name)
                parts = normalized.split()
                variants = [normalized]

                if len(parts) >= 2:
                    # First name only
                    variants.append(parts[0])
                    # Last name only
                    variants.append(parts[-1])
                    # First + Last (skip middle)
                    if len(parts) > 2:
                        variants.append(f"{parts[0]} {parts[-1]}")
                    # First initial + last name pattern
                    variants.append(f"{parts[0][0]} {parts[-1]}" if parts[0] else "")
                    # First name + last initial
                    variants.append(f"{parts[0]} {parts[-1][0]}" if parts[-1] else "")

                return [v for v in variants if v]  # Filter empty strings

            for row_idx, row in enumerate(reader):
                try:
                    employee = self._parse_row(row, row_idx, column_map)
                    if employee:
                        employees.append(employee)
                        # Store normalized name and all variants for lookup
                        for variant in get_name_variants(employee["full_name"]):
                            if variant not in name_to_id:
                                name_to_id[variant] = employee["id"]

                        # Track if we need to resolve manager by name
                        if employee.get("_manager_name"):
                            rows_with_manager_name.append(employee)

                except Exception as e:
                    validation_errors.append({
                        "error_type": "parse_error",
                        "severity": "warning",
                        "message": f"Error parsing row {row_idx + 2}: {str(e)}",
                        "affected_nodes": [f"row_{row_idx}"],
                    })

            logger.info(f"Parsed {len(employees)} employees, name_to_id has {len(name_to_id)} entries")

            # Resolve manager relationships
            for emp in employees:
                manager_id = emp.get("manager_id")

                # Try to resolve manager_name to ID
                if emp.get("_manager_name") and not manager_id:
                    manager_name_raw = emp["_manager_name"]

                    # Try all variants of the manager name
                    for manager_variant in get_name_variants(manager_name_raw):
                        manager_id = name_to_id.get(manager_variant)
                        if manager_id:
                            break

                    # Try partial match if no exact variant matched
                    if not manager_id:
                        manager_name = normalize_name(manager_name_raw)
                        for stored_name, stored_id in name_to_id.items():
                            # Check if either is a prefix of the other
                            if stored_name.startswith(manager_name) or manager_name.startswith(stored_name):
                                manager_id = stored_id
                                break
                            # Check if they share the same first name
                            stored_first = stored_name.split()[0] if stored_name else ""
                            mgr_first = manager_name.split()[0] if manager_name else ""
                            if stored_first and mgr_first and stored_first == mgr_first:
                                manager_id = stored_id
                                break

                    if manager_id:
                        emp["manager_id"] = manager_id
                        logger.debug(f"Resolved manager '{manager_name_raw}' -> {manager_id}")
                    else:
                        logger.warning(f"Could not resolve manager '{manager_name_raw}' for employee '{emp.get('full_name')}'")

                # Remove temporary field
                emp.pop("_manager_name", None)

                # Add relationship
                if manager_id and manager_id != emp["id"]:
                    relationships.append((manager_id, emp["id"]))

            logger.info(f"Created {len(relationships)} relationships from CSV")

            # Validate relationships
            employee_ids = {e["id"] for e in employees}
            for mgr_id, emp_id in relationships:
                if mgr_id not in employee_ids:
                    validation_errors.append({
                        "error_type": "missing_manager",
                        "severity": "warning",
                        "message": f"Manager '{mgr_id}' not found for employee",
                        "affected_nodes": [emp_id],
                    })

            # Calculate levels if not provided
            if employees and not any(e.get("level") for e in employees):
                self._infer_levels(employees, relationships)

        except Exception as e:
            validation_errors.append({
                "error_type": "file_error",
                "severity": "error",
                "message": f"Failed to parse CSV: {str(e)}",
                "affected_nodes": [],
            })

        return CSVParseResult(
            employees=employees,
            relationships=relationships,
            validation_errors=validation_errors,
            metadata={
                "total_rows": len(employees),
                "total_relationships": len(relationships),
                "columns_mapped": list(column_map.keys()),
            },
        )

    def _detect_delimiter(self, content: str) -> str:
        """Auto-detect CSV delimiter."""
        first_line = content.split("\n")[0]
        for delim in [",", ";", "\t", "|"]:
            if delim in first_line:
                return delim
        return ","

    def _create_column_map(self, headers: List[str]) -> Dict[str, str]:
        """Create mapping from standard fields to actual column names."""
        column_map = {}
        headers_lower = [h.lower().strip() for h in headers]

        for field, possible_names in DEFAULT_COLUMN_MAPPINGS.items():
            # Check custom mapping first
            if field in self.custom_mappings:
                custom = self.custom_mappings[field]
                if custom.lower() in headers_lower:
                    idx = headers_lower.index(custom.lower())
                    column_map[field] = headers[idx]
                    continue

            # Check default names (exact match)
            found = False
            for name in possible_names:
                if name.lower() in headers_lower:
                    idx = headers_lower.index(name.lower())
                    column_map[field] = headers[idx]
                    found = True
                    break

            # If not found, try partial/prefix matching for truncated headers
            if not found:
                for header_idx, header in enumerate(headers_lower):
                    for name in possible_names:
                        # Check if header is a prefix of name (e.g., "line mar" matches "line manager")
                        if len(header) >= 3 and name.lower().startswith(header):
                            column_map[field] = headers[header_idx]
                            found = True
                            break
                        # Check if name is a prefix of header
                        if len(name) >= 3 and header.startswith(name.lower()):
                            column_map[field] = headers[header_idx]
                            found = True
                            break
                    if found:
                        break

        return column_map

    def _parse_row(
        self,
        row: Dict[str, str],
        row_idx: int,
        column_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Parse a single CSV row into an employee dict."""

        def get_value(field: str) -> Optional[str]:
            col = column_map.get(field)
            if col and col in row:
                val = row[col].strip()
                return val if val else None
            return None

        name = get_value("full_name")
        if not name:
            return None

        employee_id = get_value("employee_id") or f"csv_row_{row_idx}"

        employee = {
            "id": employee_id,
            "employee_id": employee_id,
            "full_name": name,
            "job_title": get_value("job_title") or "Unknown",
            "manager_id": get_value("manager_id"),
            "_manager_name": get_value("manager_name"),  # Temporary, resolved later
            "grade": get_value("grade"),
            "function": get_value("function"),
            "location": get_value("location"),
            "cost_center": get_value("cost_center"),
            "source_row": row_idx + 2,  # Account for header row
        }

        # Parse numeric fields
        level = get_value("level")
        if level:
            try:
                employee["level"] = int(level)
            except ValueError:
                pass

        fte = get_value("fte")
        if fte:
            try:
                employee["fte"] = float(fte)
            except ValueError:
                employee["fte"] = 1.0
        else:
            employee["fte"] = 1.0

        salary = get_value("salary")
        if salary:
            try:
                # Remove currency symbols and commas
                salary_clean = salary.replace("$", "").replace(",", "").replace(" ", "")
                employee["cost_base_salary"] = float(salary_clean)
            except ValueError:
                pass

        return employee

    def _infer_levels(
        self,
        employees: List[Dict],
        relationships: List[Tuple[str, str]]
    ) -> None:
        """Infer hierarchy levels from relationships."""
        import networkx as nx

        G = nx.DiGraph()
        for emp in employees:
            G.add_node(emp["id"])

        for mgr_id, emp_id in relationships:
            if mgr_id in G and emp_id in G:
                G.add_edge(mgr_id, emp_id)

        # Find roots and calculate depths
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]

        for root in roots:
            try:
                depths = nx.single_source_shortest_path_length(G, root)
                for node, depth in depths.items():
                    for emp in employees:
                        if emp["id"] == node:
                            emp["level"] = depth + 1
                            break
            except nx.NetworkXError:
                pass

        # Set default level for unassigned
        for emp in employees:
            if "level" not in emp:
                emp["level"] = 99  # Unknown level


def parse_csv_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        Dictionary with parsed employee data
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    parser = CSVParser()
    result = parser.parse(content)
    return result.to_dict()
