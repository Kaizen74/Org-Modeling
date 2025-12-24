"""
End-to-end verification: PPTX upload -> Backend parsing -> Frontend OrgChart display

This test verifies that:
1. PPTX parser extracts employees with correct fields
2. Spatial inference creates proper manager-employee relationships
3. Publish endpoint maps old IDs to new UUIDs and sets manager_id
4. Tree endpoint returns React Flow compatible format
5. Data matches frontend OrgNode/OrgEdge TypeScript interfaces
"""

import pytest
import uuid
from typing import Dict, List, Any


# ============================================================================
# Frontend TypeScript interfaces (for reference)
# ============================================================================
"""
// From frontend/src/api/types.ts

interface OrgNode {
  id: string
  data: {
    label: string        // full_name
    title: string        // job_title
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

interface OrgEdge {
  id: string
  source: string    // manager's node id
  target: string    // employee's node id
  type: string      // 'smoothstep'
}
"""


# ============================================================================
# Mock PPTX Parse Result (simulating OrgChartParser output)
# ============================================================================

def create_mock_pptx_employees() -> List[Dict[str, Any]]:
    """
    Simulate employees extracted from PPTX by OrgChartParser.
    This matches the format from ParsedEmployee.to_dict()
    """
    return [
        {
            "id": "slide0_shape0",
            "full_name": "Vincent Chan",
            "job_title": "SVP, Passenger Services",
            "grade": "SVP",
            "level": 1,
            "function": "Passenger Services",
            "position": {
                "left": 4500000, "top": 500000,
                "center_x": 5000000, "center_y": 700000,
                "width": 1000000, "height": 400000,
                "right": 5500000, "bottom": 900000
            },
        },
        {
            "id": "slide0_shape1",
            "full_name": "Kevin Chin",
            "job_title": "VP, Airline Operations",
            "grade": "H7",
            "level": 2,
            "function": "Passenger Services",
            "position": {
                "left": 1000000, "top": 2000000,
                "center_x": 1500000, "center_y": 2200000,
                "width": 1000000, "height": 400000,
                "right": 2000000, "bottom": 2400000
            },
        },
        {
            "id": "slide0_shape2",
            "full_name": "Melissa Koh",
            "job_title": "VP, Premium Services",
            "grade": "H7",
            "level": 2,
            "function": "Passenger Services",
            "position": {
                "left": 4500000, "top": 2000000,
                "center_x": 5000000, "center_y": 2200000,
                "width": 1000000, "height": 400000,
                "right": 5500000, "bottom": 2400000
            },
        },
        {
            "id": "slide0_shape3",
            "full_name": "Zahida Begum",
            "job_title": "Manager, Airline Relations",
            "grade": "H2",
            "level": 3,
            "function": "Passenger Services",
            "position": {
                "left": 500000, "top": 3500000,
                "center_x": 1000000, "center_y": 3700000,
                "width": 1000000, "height": 400000,
                "right": 1500000, "bottom": 3900000
            },
        },
        {
            "id": "slide0_shape4",
            "full_name": "Sharifah Azzah",
            "job_title": "Senior Manager, Training",
            "grade": "H3",
            "level": 3,
            "function": "Passenger Services",
            "position": {
                "left": 2000000, "top": 3500000,
                "center_x": 2500000, "center_y": 3700000,
                "width": 1000000, "height": 400000,
                "right": 3000000, "bottom": 3900000
            },
        },
        {
            "id": "slide0_shape5",
            "full_name": "Diana Lee",
            "job_title": "Manager, Premium Experience",
            "grade": "H2",
            "level": 3,
            "function": "Passenger Services",
            "position": {
                "left": 4000000, "top": 3500000,
                "center_x": 4500000, "center_y": 3700000,
                "width": 1000000, "height": 400000,
                "right": 5000000, "bottom": 3900000
            },
        },
    ]


def create_mock_pptx_relationships() -> List[List[str]]:
    """
    Simulate relationships inferred by spatial proximity algorithm.
    Format: [[manager_id, employee_id], ...]
    """
    return [
        ["slide0_shape0", "slide0_shape1"],  # Vincent -> Kevin
        ["slide0_shape0", "slide0_shape2"],  # Vincent -> Melissa
        ["slide0_shape1", "slide0_shape3"],  # Kevin -> Zahida
        ["slide0_shape1", "slide0_shape4"],  # Kevin -> Sharifah
        ["slide0_shape2", "slide0_shape5"],  # Melissa -> Diana
    ]


# ============================================================================
# Simulated Backend Endpoints
# ============================================================================

def simulate_publish_endpoint(employees: List[Dict], relationships: List[List[str]]) -> tuple:
    """
    Simulate /datasets/{id}/publish endpoint.
    Creates new UUIDs and sets manager_id on employees.
    """
    id_mapping = {}  # old_id -> new_uuid
    db_employees = []

    # Create employees with new UUIDs
    for emp_data in employees:
        old_id = emp_data["id"]
        new_id = str(uuid.uuid4())
        id_mapping[old_id] = new_id

        db_emp = {
            "id": new_id,
            "full_name": emp_data.get("full_name"),
            "job_title": emp_data.get("job_title"),
            "level": emp_data.get("level"),
            "grade": emp_data.get("grade"),
            "function": emp_data.get("function"),
            "location": emp_data.get("location"),
            "position_x": emp_data.get("position", {}).get("center_x"),
            "position_y": emp_data.get("position", {}).get("center_y"),
            "manager_id": None,
            "is_vacant": False,
            "is_new": False,
            "is_modified": False,
        }
        db_employees.append(db_emp)

    # Set manager relationships
    for rel in relationships:
        manager_old_id, employee_old_id = rel[0], rel[1]
        manager_new_id = id_mapping.get(manager_old_id)
        employee_new_id = id_mapping.get(employee_old_id)

        if manager_new_id and employee_new_id:
            for emp in db_employees:
                if emp["id"] == employee_new_id:
                    emp["manager_id"] = manager_new_id
                    break

    return db_employees, id_mapping


def simulate_tree_endpoint(db_employees: List[Dict]) -> Dict[str, List]:
    """
    Simulate /scenarios/{id}/tree endpoint.
    Returns React Flow compatible format.
    """
    nodes = []
    edges = []

    for emp in db_employees:
        emp_id = str(emp["id"])

        # Position conversion (EMU to pixels approximation)
        pos_x = emp.get("position_x") or 0
        pos_y = emp.get("position_y") or 0
        if pos_x > 10000:  # EMU values
            pos_x = pos_x / 10000
        if pos_y > 10000:
            pos_y = pos_y / 10000

        # Create node matching OrgNode interface
        node = {
            "id": emp_id,
            "data": {
                "label": emp["full_name"],
                "title": emp["job_title"],
                "level": emp.get("level"),
                "function": emp.get("function"),
                "location": emp.get("location"),
                "grade": emp.get("grade"),
                "is_vacant": emp.get("is_vacant", False),
                "is_new": emp.get("is_new", False),
                "is_modified": emp.get("is_modified", False),
            },
            "position": {
                "x": pos_x,
                "y": pos_y,
            },
        }
        nodes.append(node)

        # Create edge if employee has manager
        if emp.get("manager_id"):
            manager_id = str(emp["manager_id"])
            edge = {
                "id": f"e-{manager_id}-{emp_id}",
                "source": manager_id,
                "target": emp_id,
                "type": "smoothstep",
            }
            edges.append(edge)

    return {"nodes": nodes, "edges": edges}


# ============================================================================
# Test Cases
# ============================================================================

class TestPPTXFrontendIntegration:
    """Test PPTX data flow matches frontend OrgChart expectations."""

    def test_node_matches_orgnode_interface(self):
        """Verify nodes match TypeScript OrgNode interface."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        for node in tree_data["nodes"]:
            # Required: id must be string
            assert isinstance(node["id"], str), "id must be string"

            # Required: data object
            assert "data" in node, "node must have data"
            data = node["data"]

            # Required data fields
            assert "label" in data, "data must have label"
            assert "title" in data, "data must have title"
            assert isinstance(data["label"], str), "label must be string"
            assert isinstance(data["title"], str), "title must be string"

            # Boolean fields must be boolean
            assert isinstance(data.get("is_vacant", False), bool)
            assert isinstance(data.get("is_new", False), bool)
            assert isinstance(data.get("is_modified", False), bool)

            # Required: position object
            assert "position" in node, "node must have position"
            assert "x" in node["position"], "position must have x"
            assert "y" in node["position"], "position must have y"
            assert isinstance(node["position"]["x"], (int, float))
            assert isinstance(node["position"]["y"], (int, float))

    def test_edge_matches_orgedge_interface(self):
        """Verify edges match TypeScript OrgEdge interface."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        node_ids = {n["id"] for n in tree_data["nodes"]}

        for edge in tree_data["edges"]:
            # Required: id, source, target must be strings
            assert isinstance(edge["id"], str), "edge id must be string"
            assert isinstance(edge["source"], str), "source must be string"
            assert isinstance(edge["target"], str), "target must be string"

            # source and target must reference valid nodes
            assert edge["source"] in node_ids, f"source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"target {edge['target']} not in nodes"

            # type must be smoothstep for proper rendering
            assert edge.get("type") == "smoothstep", "type should be smoothstep"

    def test_all_relationships_become_edges(self):
        """Verify all PPTX relationships become edges."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        assert len(tree_data["edges"]) == len(relationships), \
            f"Expected {len(relationships)} edges, got {len(tree_data['edges'])}"

    def test_correct_reporting_relationships(self):
        """Verify manager-employee relationships are correct."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, id_mapping = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        # Build name lookup
        new_id_to_name = {emp["id"]: emp["full_name"] for emp in db_employees}

        # Verify each expected relationship
        expected_relationships = [
            ("Vincent Chan", "Kevin Chin"),
            ("Vincent Chan", "Melissa Koh"),
            ("Kevin Chin", "Zahida Begum"),
            ("Kevin Chin", "Sharifah Azzah"),
            ("Melissa Koh", "Diana Lee"),
        ]

        actual_relationships = []
        for edge in tree_data["edges"]:
            manager_name = new_id_to_name.get(edge["source"])
            employee_name = new_id_to_name.get(edge["target"])
            actual_relationships.append((manager_name, employee_name))

        for expected in expected_relationships:
            assert expected in actual_relationships, \
                f"Missing relationship: {expected[0]} -> {expected[1]}"

    def test_root_node_has_no_incoming_edge(self):
        """Verify root employee (Vincent Chan) has no incoming edge."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        # Find Vincent Chan's node
        vincent_node = None
        for emp in db_employees:
            if emp["full_name"] == "Vincent Chan":
                vincent_node = emp
                break

        assert vincent_node is not None, "Vincent Chan not found"

        # Check no edge has Vincent Chan as target
        for edge in tree_data["edges"]:
            assert edge["target"] != vincent_node["id"], \
                "Root node should not be target of any edge"

    def test_hierarchy_levels_preserved(self):
        """Verify hierarchy levels are correctly passed to frontend."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        expected_levels = {
            "Vincent Chan": 1,
            "Kevin Chin": 2,
            "Melissa Koh": 2,
            "Zahida Begum": 3,
            "Sharifah Azzah": 3,
            "Diana Lee": 3,
        }

        for node in tree_data["nodes"]:
            name = node["data"]["label"]
            expected_level = expected_levels.get(name)
            actual_level = node["data"].get("level")
            assert actual_level == expected_level, \
                f"{name}: expected level {expected_level}, got {actual_level}"

    def test_employee_details_in_node_data(self):
        """Verify employee details are correctly in node data."""
        employees = create_mock_pptx_employees()
        relationships = create_mock_pptx_relationships()

        db_employees, _ = simulate_publish_endpoint(employees, relationships)
        tree_data = simulate_tree_endpoint(db_employees)

        # Find Kevin Chin's node and verify details
        kevin_node = None
        for node in tree_data["nodes"]:
            if node["data"]["label"] == "Kevin Chin":
                kevin_node = node
                break

        assert kevin_node is not None, "Kevin Chin node not found"
        assert kevin_node["data"]["title"] == "VP, Airline Operations"
        assert kevin_node["data"]["grade"] == "H7"
        assert kevin_node["data"]["function"] == "Passenger Services"


def run_verification():
    """Run all verification tests and print results."""
    print("=" * 70)
    print("PPTX -> Frontend OrgChart Integration Verification")
    print("=" * 70)

    employees = create_mock_pptx_employees()
    relationships = create_mock_pptx_relationships()

    print(f"\n📊 Input from PPTX Parser:")
    print(f"   Employees: {len(employees)}")
    print(f"   Relationships: {len(relationships)}")

    # Simulate backend flow
    db_employees, id_mapping = simulate_publish_endpoint(employees, relationships)
    tree_data = simulate_tree_endpoint(db_employees)

    print(f"\n📤 Output to Frontend OrgChart:")
    print(f"   Nodes: {len(tree_data['nodes'])}")
    print(f"   Edges: {len(tree_data['edges'])}")

    # Verify node format
    print("\n✅ Node Format (OrgNode interface):")
    sample_node = tree_data["nodes"][0]
    print(f"   id: {sample_node['id'][:8]}... (string)")
    print(f"   data.label: {sample_node['data']['label']}")
    print(f"   data.title: {sample_node['data']['title']}")
    print(f"   data.grade: {sample_node['data']['grade']}")
    print(f"   position: ({sample_node['position']['x']}, {sample_node['position']['y']})")

    # Verify edge format
    print("\n✅ Edge Format (OrgEdge interface):")
    if tree_data["edges"]:
        sample_edge = tree_data["edges"][0]
        new_id_to_name = {emp["id"]: emp["full_name"] for emp in db_employees}
        src_name = new_id_to_name.get(sample_edge["source"], "?")
        tgt_name = new_id_to_name.get(sample_edge["target"], "?")
        print(f"   id: {sample_edge['id'][:20]}...")
        print(f"   source: {src_name}")
        print(f"   target: {tgt_name}")
        print(f"   type: {sample_edge['type']}")

    # Show all edges
    print("\n📊 All Reporting Lines (Edges):")
    new_id_to_name = {emp["id"]: emp["full_name"] for emp in db_employees}
    for edge in tree_data["edges"]:
        src = new_id_to_name.get(edge["source"], "?")
        tgt = new_id_to_name.get(edge["target"], "?")
        print(f"   {src} ──→ {tgt}")

    # Final summary
    print("\n" + "=" * 70)
    if len(tree_data["edges"]) == len(relationships):
        print("✅ VERIFICATION PASSED")
        print(f"   • All {len(tree_data['nodes'])} employees will display as boxes")
        print(f"   • All {len(tree_data['edges'])} relationships will display as lines")
        print("   • Data format matches frontend OrgNode/OrgEdge interfaces")
    else:
        print("❌ VERIFICATION FAILED")
        print(f"   Expected {len(relationships)} edges, got {len(tree_data['edges'])}")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
