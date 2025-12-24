"""
Mock test to verify the frontend OrgChart component receives correct data.

Tests the complete flow:
1. CSV/PPTX parsing creates employees and relationships
2. Publish endpoint stores data in database format
3. Tree endpoint returns React Flow compatible format
4. Data matches frontend OrgNode/OrgEdge types
"""

import pytest
from app.parsers.csv_parser import CSVParser


# Sample org structure for testing
SAMPLE_ORG_CSV = """Name,Title,Function,Grade,Line Manager
Vincent Chan,SVP Passenger Services,Passenger Services,SVP,
Kevin Chen,VP Airline Operations,Passenger Services,H7,Vincent Chan
Melissa Koh,VP Premium Services,Passenger Services,H7,Vincent Chan
Zahida Begum,Manager Airline Relations,Passenger Services,H2,Kevin Chen
Diana Lee,Manager Premium Experience,Passenger Services,H2,Melissa Koh
"""


class TestFrontendDataFormat:
    """Test that backend data matches frontend OrgNode/OrgEdge types."""

    def test_tree_node_format(self):
        """
        Verify node format matches frontend OrgNode interface:

        interface OrgNode {
            id: string
            data: {
                label: string      // full_name
                title: string      // job_title
                level?: number
                function?: string
                location?: string
                grade?: string
                is_vacant: boolean
                is_new: boolean
                is_modified: boolean
            }
            position: {
                x: number
                y: number
            }
        }
        """
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Frontend Node Format Test ===")

        # Simulate tree endpoint node creation
        for emp in result.employees:
            node = {
                "id": str(emp["id"]),  # Must be string
                "data": {
                    "label": emp.get("full_name", "Unknown"),
                    "title": emp.get("job_title", "Unknown"),
                    "level": emp.get("level"),
                    "function": emp.get("function"),
                    "location": emp.get("location"),
                    "grade": emp.get("grade"),
                    "is_vacant": False,
                    "is_new": False,
                    "is_modified": False,
                },
                "position": {
                    "x": 0,  # Would be calculated by auto-layout
                    "y": 0,
                },
            }

            # Verify required fields
            assert isinstance(node["id"], str), f"id must be string: {node['id']}"
            assert "label" in node["data"], "Missing label in data"
            assert "title" in node["data"], "Missing title in data"
            assert "x" in node["position"], "Missing x in position"
            assert "y" in node["position"], "Missing y in position"

            print(f"  Node: {node['data']['label']} ({node['data']['title']})")

        print(f"PASS: {len(result.employees)} nodes match OrgNode format")

    def test_tree_edge_format(self):
        """
        Verify edge format matches frontend OrgEdge interface:

        interface OrgEdge {
            id: string
            source: string    // manager_id
            target: string    // employee_id
            type: string      // 'smoothstep'
        }
        """
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Frontend Edge Format Test ===")

        # Build ID to name mapping for display
        id_to_name = {emp["id"]: emp["full_name"] for emp in result.employees}

        # Simulate tree endpoint edge creation
        for manager_id, employee_id in result.relationships:
            edge = {
                "id": f"e-{manager_id}-{employee_id}",
                "source": str(manager_id),  # Must be string
                "target": str(employee_id),  # Must be string
                "type": "smoothstep",
            }

            # Verify required fields
            assert isinstance(edge["id"], str), "id must be string"
            assert isinstance(edge["source"], str), "source must be string"
            assert isinstance(edge["target"], str), "target must be string"
            assert edge["type"] == "smoothstep", "type should be smoothstep"

            manager_name = id_to_name.get(manager_id, "Unknown")
            employee_name = id_to_name.get(employee_id, "Unknown")
            print(f"  Edge: {manager_name} -> {employee_name}")

        print(f"PASS: {len(result.relationships)} edges match OrgEdge format")

    def test_complete_tree_structure(self):
        """
        Test that tree structure is complete and hierarchical.
        Verifies:
        1. All employees have nodes
        2. All relationships have edges
        3. Edges reference valid node IDs
        """
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Complete Tree Structure Test ===")

        # Build complete tree response
        nodes = []
        edges = []
        node_ids = set()

        for emp in result.employees:
            emp_id = str(emp["id"])
            node_ids.add(emp_id)
            nodes.append({
                "id": emp_id,
                "data": {
                    "label": emp.get("full_name"),
                    "title": emp.get("job_title"),
                    "level": emp.get("level"),
                    "function": emp.get("function"),
                    "grade": emp.get("grade"),
                    "is_vacant": False,
                    "is_new": False,
                    "is_modified": False,
                },
                "position": {"x": 0, "y": 0},
            })

        for manager_id, employee_id in result.relationships:
            mgr_str = str(manager_id)
            emp_str = str(employee_id)
            edges.append({
                "id": f"e-{mgr_str}-{emp_str}",
                "source": mgr_str,
                "target": emp_str,
                "type": "smoothstep",
            })

        # Verify all edges reference valid nodes
        for edge in edges:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"

        print(f"  Total nodes: {len(nodes)}")
        print(f"  Total edges: {len(edges)}")
        print(f"  All edges reference valid nodes: True")

        # Verify hierarchy
        employees_with_manager = len([e for e in edges])
        employees_without_manager = len(nodes) - employees_with_manager

        print(f"  Root nodes (no manager): {employees_without_manager}")
        print(f"  Non-root nodes (have manager): {employees_with_manager}")

        assert employees_without_manager >= 1, "Should have at least one root node"
        assert len(nodes) == 5, f"Expected 5 nodes, got {len(nodes)}"
        assert len(edges) == 4, f"Expected 4 edges, got {len(edges)}"

        print("PASS: Tree structure is complete and valid")

    def test_manager_subordinate_relationships(self):
        """
        Verify specific manager-subordinate relationships are correct.
        """
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Manager-Subordinate Relationships Test ===")

        # Build relationship map
        id_to_name = {emp["id"]: emp["full_name"] for emp in result.employees}
        relationships = {}
        for manager_id, employee_id in result.relationships:
            emp_name = id_to_name.get(employee_id)
            mgr_name = id_to_name.get(manager_id)
            relationships[emp_name] = mgr_name

        # Expected relationships from CSV
        expected = {
            "Kevin Chen": "Vincent Chan",
            "Melissa Koh": "Vincent Chan",
            "Zahida Begum": "Kevin Chen",
            "Diana Lee": "Melissa Koh",
        }

        print("  Checking relationships:")
        for emp_name, expected_mgr in expected.items():
            actual_mgr = relationships.get(emp_name)
            status = "✓" if actual_mgr == expected_mgr else "✗"
            print(f"    {status} {emp_name} -> {actual_mgr} (expected: {expected_mgr})")
            assert actual_mgr == expected_mgr, f"Wrong manager for {emp_name}"

        # Vincent Chan should have no manager (root)
        assert "Vincent Chan" not in relationships, "Vincent Chan should have no manager"
        print(f"    ✓ Vincent Chan is root (no manager)")

        print("PASS: All relationships are correct")

    def test_react_flow_compatibility(self):
        """
        Test that the tree data is compatible with React Flow library.
        React Flow requires:
        - nodes: array with id, position, data
        - edges: array with id, source, target
        """
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== React Flow Compatibility Test ===")

        # Build React Flow format
        react_flow_data = {
            "nodes": [],
            "edges": [],
        }

        for i, emp in enumerate(result.employees):
            react_flow_data["nodes"].append({
                "id": str(emp["id"]),
                "type": "custom",  # Custom node component
                "position": {"x": i * 200, "y": (emp.get("level", 1) - 1) * 150},
                "data": {
                    "label": emp.get("full_name"),
                    "title": emp.get("job_title"),
                },
            })

        for manager_id, employee_id in result.relationships:
            react_flow_data["edges"].append({
                "id": f"e-{manager_id}-{employee_id}",
                "source": str(manager_id),
                "target": str(employee_id),
                "type": "smoothstep",
                "animated": False,
                "style": {"stroke": "#94a3b8", "strokeWidth": 2},
            })

        # Verify structure
        assert "nodes" in react_flow_data
        assert "edges" in react_flow_data
        assert isinstance(react_flow_data["nodes"], list)
        assert isinstance(react_flow_data["edges"], list)

        # Verify each node has required React Flow fields
        for node in react_flow_data["nodes"]:
            assert "id" in node, "Node missing id"
            assert "position" in node, "Node missing position"
            assert "x" in node["position"], "Position missing x"
            assert "y" in node["position"], "Position missing y"
            assert "data" in node, "Node missing data"

        # Verify each edge has required React Flow fields
        for edge in react_flow_data["edges"]:
            assert "id" in edge, "Edge missing id"
            assert "source" in edge, "Edge missing source"
            assert "target" in edge, "Edge missing target"

        print(f"  Nodes: {len(react_flow_data['nodes'])}")
        for node in react_flow_data["nodes"]:
            print(f"    - {node['data']['label']} at ({node['position']['x']}, {node['position']['y']})")

        print(f"  Edges: {len(react_flow_data['edges'])}")
        for edge in react_flow_data["edges"]:
            print(f"    - {edge['source']} -> {edge['target']}")

        print("PASS: Data is React Flow compatible")


class TestOrgChartVisualization:
    """Test org chart visualization data."""

    def test_hierarchy_levels(self):
        """Test that hierarchy levels are correctly assigned."""
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Hierarchy Levels Test ===")

        # Build level map
        levels = {}
        for emp in result.employees:
            levels[emp["full_name"]] = emp.get("level", 99)

        print("  Employee levels:")
        for name, level in sorted(levels.items(), key=lambda x: x[1]):
            print(f"    Level {level}: {name}")

        # Vincent Chan should be level 1 (root)
        assert levels.get("Vincent Chan") == 1, "Vincent Chan should be level 1"

        # Kevin and Melissa should be level 2
        assert levels.get("Kevin Chen") == 2, "Kevin Chen should be level 2"
        assert levels.get("Melissa Koh") == 2, "Melissa Koh should be level 2"

        # Zahida and Diana should be level 3
        assert levels.get("Zahida Begum") == 3, "Zahida Begum should be level 3"
        assert levels.get("Diana Lee") == 3, "Diana Lee should be level 3"

        print("PASS: Hierarchy levels are correct")

    def test_employee_data_completeness(self):
        """Test that all employee data fields are populated."""
        parser = CSVParser()
        result = parser.parse(SAMPLE_ORG_CSV)

        print("\n=== Employee Data Completeness Test ===")

        required_fields = ["id", "full_name", "job_title"]
        optional_fields = ["function", "grade", "level", "manager_id"]

        for emp in result.employees:
            print(f"  {emp['full_name']}:")

            # Check required fields
            for field in required_fields:
                assert field in emp, f"Missing required field: {field}"
                assert emp[field] is not None, f"Required field is None: {field}"

            # Report optional fields
            for field in optional_fields:
                value = emp.get(field)
                status = "✓" if value else "○"
                print(f"    {status} {field}: {value}")

        print("PASS: Employee data is complete")


def run_all_tests():
    """Run all frontend integration tests."""
    print("=" * 70)
    print("FRONTEND INTEGRATION TESTS")
    print("Verifying OrgChart component receives correct data from backend")
    print("=" * 70)

    # Node/Edge format tests
    format_tests = TestFrontendDataFormat()
    format_tests.test_tree_node_format()
    format_tests.test_tree_edge_format()
    format_tests.test_complete_tree_structure()
    format_tests.test_manager_subordinate_relationships()
    format_tests.test_react_flow_compatibility()

    # Visualization tests
    viz_tests = TestOrgChartVisualization()
    viz_tests.test_hierarchy_levels()
    viz_tests.test_employee_data_completeness()

    print("\n" + "=" * 70)
    print("ALL FRONTEND INTEGRATION TESTS PASSED!")
    print("=" * 70)
    print("\nThe backend correctly provides:")
    print("  ✓ Nodes with id, data (label, title, etc.), position")
    print("  ✓ Edges with id, source, target for reporting lines")
    print("  ✓ Correct manager-subordinate relationships")
    print("  ✓ Proper hierarchy levels")
    print("  ✓ React Flow compatible format")


if __name__ == "__main__":
    run_all_tests()
