"""
Tests for CSV parser with various column formats.
"""

import pytest
from app.parsers.csv_parser import CSVParser, DEFAULT_COLUMN_MAPPINGS


class TestCSVParser:
    """Test CSV parsing with different column naming conventions."""

    def test_standard_columns(self):
        """Test parsing with standard column names."""
        csv_content = """employee_id,name,job_title,department,manager_id,salary
CEO001,John Smith,CEO,Executive,,150000
VP001,Jane Doe,VP Sales,Sales,CEO001,120000
MGR001,Bob Johnson,Sales Manager,Sales,VP001,80000"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert len(result.employees) == 3
        assert result.employees[0]["full_name"] == "John Smith"
        assert result.employees[0]["job_title"] == "CEO"
        assert result.employees[0]["function"] == "Executive"

    def test_truncated_column_headers(self):
        """Test parsing with truncated headers like 'Line Mar' and 'Departm'."""
        csv_content = """Name,Job Title,Grade,Departm,Level,Line Mar,Salary,Employee ID
Lim Ah Kow,VP Passenger Services,E1,Passenger Services,2,Ong Beng Seng,180000,PS001
Tan Wei Ming,Manager Ground Handling,M1,Ground Operations,3,Lim Ah Kow,85000,PS002
Sarah Chen,Supervisor Check-in,S1,Check-in Services,4,Tan Wei Ming,55000,PS003"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert len(result.employees) == 3
        assert result.employees[0]["full_name"] == "Lim Ah Kow"
        assert result.employees[0]["job_title"] == "VP Passenger Services"
        assert result.employees[0]["grade"] == "E1"
        assert result.employees[0]["function"] == "Passenger Services"
        assert result.employees[0]["level"] == 2

    def test_manager_name_resolution(self):
        """Test that manager relationships are resolved by name."""
        csv_content = """Name,Job Title,Line Manager
Alice Boss,Director,
Bob Worker,Engineer,Alice Boss
Carol Helper,Assistant,Bob Worker"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert len(result.employees) == 3
        # Check relationships were created (Alice->Bob, Bob->Carol)
        assert len(result.relationships) >= 1

    def test_various_column_variations(self):
        """Test various column name variations are recognized."""
        # Test employee_id variations
        csv_content_emp_id = """emp_id,name,position
E001,John,Manager"""
        parser = CSVParser()
        result = parser.parse(csv_content_emp_id)
        assert result.employees[0]["employee_id"] == "E001"

        # Test with staff_id
        csv_content_staff = """staff_id,name,designation
S001,Jane,Developer"""
        result = parser.parse(csv_content_staff)
        assert result.employees[0]["employee_id"] == "S001"

    def test_salary_parsing(self):
        """Test salary parsing with various formats."""
        csv_content = """name,salary
John,150000
Jane,120000
Bob,85000"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert result.employees[0]["cost_base_salary"] == 150000.0
        assert result.employees[1]["cost_base_salary"] == 120000.0
        assert result.employees[2]["cost_base_salary"] == 85000.0

    def test_salary_parsing_with_currency_symbols(self):
        """Test salary parsing with currency symbols.

        Note: Comma-separated values like $120,000 need to be quoted in CSV
        to avoid confusion with CSV delimiter.
        """
        csv_content = """name,salary
John,$150000
Jane,"$120,000"
Bob,$85000.50"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert result.employees[0]["cost_base_salary"] == 150000.0
        assert result.employees[1]["cost_base_salary"] == 120000.0
        assert result.employees[2]["cost_base_salary"] == 85000.50

    def test_fte_parsing(self):
        """Test FTE field parsing."""
        csv_content = """name,fte
John,1.0
Jane,0.5
Bob,0.8"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert result.employees[0]["fte"] == 1.0
        assert result.employees[1]["fte"] == 0.5
        assert result.employees[2]["fte"] == 0.8

    def test_missing_name_column_error(self):
        """Test error when name column is missing."""
        csv_content = """employee_id,job_title
1,CEO
2,VP"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert len(result.employees) == 0
        assert len(result.validation_errors) > 0
        assert result.validation_errors[0]["error_type"] == "missing_column"

    def test_semicolon_delimiter(self):
        """Test parsing with semicolon delimiter."""
        csv_content = """name;job_title;department
John;CEO;Executive
Jane;VP;Sales"""

        parser = CSVParser(delimiter=";")
        result = parser.parse(csv_content)

        assert len(result.employees) == 2
        assert result.employees[0]["full_name"] == "John"

    def test_tab_delimiter_auto_detect(self):
        """Test auto-detection of tab delimiter."""
        csv_content = "name\tjob_title\tdepartment\nJohn\tCEO\tExecutive"

        parser = CSVParser(delimiter="")
        result = parser.parse(csv_content)

        # Should auto-detect tab as delimiter
        assert len(result.employees) >= 1

    def test_empty_rows_skipped(self):
        """Test that empty rows are properly skipped."""
        csv_content = """name,job_title
John,CEO

Jane,VP
"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        # Should have 2 employees, empty row skipped
        assert len(result.employees) == 2

    def test_custom_column_mapping(self):
        """Test custom column mappings override defaults."""
        csv_content = """person,role
John,CEO
Jane,VP"""

        parser = CSVParser(column_mappings={"full_name": "person", "job_title": "role"})
        result = parser.parse(csv_content)

        assert len(result.employees) == 2
        assert result.employees[0]["full_name"] == "John"
        assert result.employees[0]["job_title"] == "CEO"

    def test_level_inference_from_relationships(self):
        """Test that levels are inferred when not provided."""
        csv_content = """employee_id,name,manager_id
CEO001,Alice CEO,
VP001,Bob VP,CEO001
MGR001,Carol Manager,VP001"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        # Levels should be inferred from hierarchy
        assert result.employees[0].get("level") is not None

    def test_prefix_matching_for_truncated_headers(self):
        """Test prefix matching for truncated column names."""
        # Test 'dept' matching 'department'
        csv_content = """name,dept
John,Engineering"""

        parser = CSVParser()
        result = parser.parse(csv_content)

        assert result.employees[0]["function"] == "Engineering"


class TestColumnMappings:
    """Test the default column mapping configurations."""

    def test_manager_name_variations_exist(self):
        """Verify manager name variations include truncated forms."""
        manager_mappings = DEFAULT_COLUMN_MAPPINGS["manager_name"]
        assert "line manager" in manager_mappings
        assert "line mar" in manager_mappings
        assert "line_manager" in manager_mappings

    def test_function_variations_exist(self):
        """Verify function/department variations include truncated forms."""
        function_mappings = DEFAULT_COLUMN_MAPPINGS["function"]
        assert "department" in function_mappings
        assert "departm" in function_mappings
        assert "dept" in function_mappings

    def test_all_required_fields_have_mappings(self):
        """Ensure all commonly used fields have mappings."""
        required_fields = [
            "employee_id", "full_name", "job_title", "manager_id",
            "manager_name", "level", "grade", "function", "location",
            "cost_center", "fte", "salary"
        ]
        for field in required_fields:
            assert field in DEFAULT_COLUMN_MAPPINGS
            assert len(DEFAULT_COLUMN_MAPPINGS[field]) > 0


class TestCSVParseResult:
    """Test the CSVParseResult dataclass."""

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        csv_content = """name,job_title
John,CEO"""

        parser = CSVParser()
        result = parser.parse(csv_content)
        result_dict = result.to_dict()

        assert "employees" in result_dict
        assert "relationships" in result_dict
        assert "validation_errors" in result_dict
        assert "metadata" in result_dict
        assert isinstance(result_dict["employees"], list)
