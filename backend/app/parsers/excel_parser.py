"""
Excel Parser for organizational data.

Supports importing employee data from Excel (.xlsx, .xls) files.
Uses openpyxl for reading Excel files.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl not installed. Excel parsing will be unavailable.")


@dataclass
class ExcelParseResult:
    """Result of parsing an Excel file."""
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


# Default column mappings (same as CSV parser)
DEFAULT_COLUMN_MAPPINGS = {
    "employee_id": ["employee_id", "emp_id", "id", "eid", "employee id", "emp id"],
    "full_name": ["full_name", "name", "employee_name", "emp_name", "employee name"],
    "job_title": ["job_title", "title", "position", "role", "job title", "job_title_name"],
    "manager_id": ["manager_id", "manager", "reports_to", "supervisor_id", "reports to", "manager id"],
    "manager_name": ["manager_name", "manager name", "supervisor_name", "reports_to_name"],
    "level": ["level", "grade_level", "hierarchy_level", "org_level"],
    "grade": ["grade", "job_grade", "pay_grade", "band", "job grade"],
    "function": ["function", "department", "division", "org_unit", "business_unit"],
    "location": ["location", "office", "city", "work_location", "site"],
    "cost_center": ["cost_center", "cc", "cost center", "cost_center_code"],
    "fte": ["fte", "full_time_equivalent", "headcount_fte"],
    "salary": ["salary", "base_salary", "annual_salary", "base_pay", "compensation"],
}


class ExcelParser:
    """
    Parses Excel files containing organizational employee data.

    Features:
    - Support for .xlsx and .xlsm files (via openpyxl)
    - Multiple sheet support
    - Flexible column mapping
    - Relationship inference from manager columns
    """

    def __init__(
        self,
        sheet_name: Optional[str] = None,
        column_mappings: Optional[Dict[str, str]] = None,
        header_row: int = 1,
    ):
        """
        Initialize the Excel parser.

        Args:
            sheet_name: Specific sheet to parse (None = first sheet)
            column_mappings: Custom column name mappings
            header_row: Row number containing headers (1-indexed)
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required for Excel parsing")

        self.sheet_name = sheet_name
        self.custom_mappings = column_mappings or {}
        self.header_row = header_row

    def parse(self, file_content: bytes) -> ExcelParseResult:
        """
        Parse Excel content and extract employee data.

        Args:
            file_content: Excel file content as bytes

        Returns:
            ExcelParseResult with employees, relationships, and metadata
        """
        validation_errors = []
        employees = []
        relationships = []

        try:
            # Load workbook
            wb = load_workbook(BytesIO(file_content), data_only=True)

            # Select sheet
            if self.sheet_name:
                if self.sheet_name in wb.sheetnames:
                    ws = wb[self.sheet_name]
                else:
                    validation_errors.append({
                        "error_type": "sheet_not_found",
                        "severity": "error",
                        "message": f"Sheet '{self.sheet_name}' not found. Available: {wb.sheetnames}",
                        "affected_nodes": [],
                    })
                    return ExcelParseResult(
                        employees=[],
                        relationships=[],
                        validation_errors=validation_errors,
                        metadata={"sheets": wb.sheetnames},
                    )
            else:
                ws = wb.active

            # Get headers
            headers = []
            for cell in ws[self.header_row]:
                if cell.value:
                    headers.append(str(cell.value))
                else:
                    headers.append(f"column_{cell.column}")

            # Create column map
            column_map = self._create_column_map(headers)

            if not column_map.get("full_name"):
                validation_errors.append({
                    "error_type": "missing_column",
                    "severity": "error",
                    "message": "Required column 'name' or 'full_name' not found",
                    "affected_nodes": [],
                })
                return ExcelParseResult(
                    employees=[],
                    relationships=[],
                    validation_errors=validation_errors,
                    metadata={"headers": headers, "sheets": wb.sheetnames},
                )

            # Process rows
            name_to_id = {}

            for row_idx, row in enumerate(ws.iter_rows(min_row=self.header_row + 1), start=1):
                try:
                    # Convert row to dict
                    row_data = {}
                    for col_idx, cell in enumerate(row):
                        if col_idx < len(headers):
                            value = cell.value
                            if value is not None:
                                row_data[headers[col_idx]] = str(value).strip()

                    employee = self._parse_row(row_data, row_idx, column_map)
                    if employee:
                        employees.append(employee)
                        name_to_id[employee["full_name"].lower()] = employee["id"]

                except Exception as e:
                    validation_errors.append({
                        "error_type": "parse_error",
                        "severity": "warning",
                        "message": f"Error parsing row {row_idx + self.header_row}: {str(e)}",
                        "affected_nodes": [f"row_{row_idx}"],
                    })

            # Resolve manager relationships
            for emp in employees:
                manager_id = emp.get("manager_id")

                # Try to resolve manager_name to ID
                if emp.get("_manager_name") and not manager_id:
                    manager_name = emp["_manager_name"].lower()
                    manager_id = name_to_id.get(manager_name)
                    if manager_id:
                        emp["manager_id"] = manager_id

                emp.pop("_manager_name", None)

                if manager_id and manager_id != emp["id"]:
                    relationships.append((manager_id, emp["id"]))

            # Validate relationships
            employee_ids = {e["id"] for e in employees}
            for mgr_id, emp_id in relationships:
                if mgr_id not in employee_ids:
                    validation_errors.append({
                        "error_type": "missing_manager",
                        "severity": "warning",
                        "message": f"Manager '{mgr_id}' not found",
                        "affected_nodes": [emp_id],
                    })

            # Infer levels if needed
            if employees and not any(e.get("level") for e in employees):
                self._infer_levels(employees, relationships)

            wb.close()

        except Exception as e:
            validation_errors.append({
                "error_type": "file_error",
                "severity": "error",
                "message": f"Failed to parse Excel file: {str(e)}",
                "affected_nodes": [],
            })

        return ExcelParseResult(
            employees=employees,
            relationships=relationships,
            validation_errors=validation_errors,
            metadata={
                "total_rows": len(employees),
                "total_relationships": len(relationships),
                "columns_mapped": list(column_map.keys()),
                "sheet_name": self.sheet_name or "Active",
            },
        )

    def _create_column_map(self, headers: List[str]) -> Dict[str, str]:
        """Create mapping from standard fields to actual column names."""
        column_map = {}
        headers_lower = [h.lower().strip() for h in headers]

        for field, possible_names in DEFAULT_COLUMN_MAPPINGS.items():
            if field in self.custom_mappings:
                custom = self.custom_mappings[field]
                if custom.lower() in headers_lower:
                    idx = headers_lower.index(custom.lower())
                    column_map[field] = headers[idx]
                    continue

            for name in possible_names:
                if name.lower() in headers_lower:
                    idx = headers_lower.index(name.lower())
                    column_map[field] = headers[idx]
                    break

        return column_map

    def _parse_row(
        self,
        row: Dict[str, str],
        row_idx: int,
        column_map: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Parse a single Excel row into an employee dict."""

        def get_value(field: str) -> Optional[str]:
            col = column_map.get(field)
            if col and col in row:
                val = row[col]
                return val if val else None
            return None

        name = get_value("full_name")
        if not name:
            return None

        employee_id = get_value("employee_id") or f"excel_row_{row_idx}"

        employee = {
            "id": employee_id,
            "employee_id": employee_id,
            "full_name": name,
            "job_title": get_value("job_title") or "Unknown",
            "manager_id": get_value("manager_id"),
            "_manager_name": get_value("manager_name"),
            "grade": get_value("grade"),
            "function": get_value("function"),
            "location": get_value("location"),
            "cost_center": get_value("cost_center"),
            "source_row": row_idx + self.header_row,
        }

        # Parse numeric fields
        level = get_value("level")
        if level:
            try:
                employee["level"] = int(float(level))
            except (ValueError, TypeError):
                pass

        fte = get_value("fte")
        if fte:
            try:
                employee["fte"] = float(fte)
            except (ValueError, TypeError):
                employee["fte"] = 1.0
        else:
            employee["fte"] = 1.0

        salary = get_value("salary")
        if salary:
            try:
                salary_clean = str(salary).replace("$", "").replace(",", "").replace(" ", "")
                employee["cost_base_salary"] = float(salary_clean)
            except (ValueError, TypeError):
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

        roots = [n for n in G.nodes() if G.in_degree(n) == 0]

        for root in roots:
            try:
                depths = nx.single_source_shortest_path_length(G, root)
                for node, depth in depths.items():
                    for emp in employees:
                        if emp["id"] == node:
                            emp["level"] = depth + 1
                            break
            except Exception:
                pass

        for emp in employees:
            if "level" not in emp:
                emp["level"] = 99


def parse_excel_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse an Excel file.

    Args:
        file_path: Path to the Excel file

    Returns:
        Dictionary with parsed employee data
    """
    with open(file_path, "rb") as f:
        content = f.read()

    parser = ExcelParser()
    result = parser.parse(content)
    return result.to_dict()
