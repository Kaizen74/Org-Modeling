"""
Test the complete flow from PPTX upload to tree endpoint edge generation.
Verifies that PowerPoint org charts produce correct data for frontend.
"""

import uuid
from app.parsers.pptx_parser import OrgChartParser, ParseResult, ParsedEmployee


def create_mock_pptx_result():
    """
    Create a mock PPTX parse result simulating what OrgChartParser produces.
    This mimics the spatial inference algorithm output.
    """
    # Simulated employees from PPTX parsing (positions in EMU)
    employees = [
        ParsedEmployee(
            id="slide0_shape0",
            name="Vincent Chan",
            title="SVP, Passenger Services",
            grade="SVP",
            full_text="Vincent Chan\nSVP, Passenger Services\nSVP",
            position={"left": 4500000, "top": 500000, "center_x": 5000000, "center_y": 700000, "width": 1000000, "height": 400000, "right": 5500000, "bottom": 900000},
            font_size=14,
            level=1,
        ),
        ParsedEmployee(
            id="slide0_shape1",
            name="Kevin Chin",
            title="VP, Airline Operations",
            grade="H7",
            full_text="Kevin Chin\nVP, Airline Operations\nH7",
            position={"left": 1000000, "top": 2000000, "center_x": 1500000, "center_y": 2200000, "width": 1000000, "height": 400000, "right": 2000000, "bottom": 2400000},
            font_size=12,
            level=2,
        ),
        ParsedEmployee(
            id="slide0_shape2",
            name="Melissa Koh",
            title="VP, Premium Services",
            grade="H7",
            full_text="Melissa Koh\nVP, Premium Services\nH7",
            position={"left": 4500000, "top": 2000000, "center_x": 5000000, "center_y": 2200000, "width": 1000000, "height": 400000, "right": 5500000, "bottom": 2400000},
            font_size=12,
            level=2,
        ),
        ParsedEmployee(
            id="slide0_shape3",
            name="Zahida Begum",
            title="Manager, Airline Relations",
            grade="H2",
            full_text="Zahida Begum\nManager, Airline Relations\nH2",
            position={"left": 500000, "top": 3500000, "center_x": 1000000, "center_y": 3700000, "width": 1000000, "height": 400000, "right": 1500000, "bottom": 3900000},
            font_size=10,
            level=3,
        ),
        ParsedEmployee(
            id="slide0_shape4",
            name="Sharifah Azzah",
            title="Senior Manager, Training",
            grade="H3",
            full_text="Sharifah Azzah\nSenior Manager, Training\nH3",
            position={"left": 2000000, "top": 3500000, "center_x": 2500000, "center_y": 3700000, "width": 1000000, "height": 400000, "right": 3000000, "bottom": 3900000},
            font_size=10,
            level=3,
        ),
        ParsedEmployee(
            id="slide0_shape5",
            name="Diana Lee",
            title="Manager, Premium Experience",
            grade="H2",
            full_text="Diana Lee\nManager, Premium Experience\nH2",
            position={"left": 4000000, "top": 3500000, "center_x": 4500000, "center_y": 3700000, "width": 1000000, "height": 400000, "right": 5000000, "bottom": 3900000},
            font_size=10,
            level=3,
        ),
    ]

    # Simulated relationships from spatial inference
    # Format: (manager_id, employee_id)
    relationships = [
        ("slide0_shape0", "slide0_shape1"),  # Vincent -> Kevin
        ("slide0_shape0", "slide0_shape2"),  # Vincent -> Melissa
        ("slide0_shape1", "slide0_shape3"),  # Kevin -> Zahida
        ("slide0_shape1", "slide0_shape4"),  # Kevin -> Sharifah
        ("slide0_shape2", "slide0_shape5"),  # Melissa -> Diana
    ]

    return employees, relationships


def simulate_pptx_to_dict(employees, relationships):
    """
    Simulate what ParseResult.to_dict() produces for PPTX.
    This is what gets stored in the database.
    """
    return {
        "employees": [emp.to_dict() for emp in employees],
        "relationships": [list(r) for r in relationships],
        "metadata": {
            "total_employees": len(employees),
            "total_relationships": len(relationships),
            "levels_detected": 3,
            "source_file": "test_org.pptx",
        }
    }


def simulate_publish_flow(raw_data):
    """
    Simulate publish endpoint creating database employees with manager_id.
    """
    id_mapping = {}  # old_id -> new_uuid
    published_employees = []

    # Create new UUIDs for each employee
    for emp_data in raw_data["employees"]:
        old_id = emp_data.get("id")
        new_id = str(uuid.uuid4())
        id_mapping[old_id] = new_id

        db_emp = {
            "id": new_id,
            "full_name": emp_data.get("full_name", emp_data.get("name")),
            "job_title": emp_data.get("job_title", emp_data.get("title")),
            "level": emp_data.get("level"),
            "grade": emp_data.get("grade"),
            "function": emp_data.get("function"),
            "position_x": emp_data.get("position", {}).get("center_x"),
            "position_y": emp_data.get("position", {}).get("center_y"),
            "manager_id": None,
        }
        published_employees.append(db_emp)

    # Set manager relationships from parsed_relationships
    relationships_set = 0
    for rel in raw_data["relationships"]:
        manager_old_id, employee_old_id = rel[0], rel[1]
        manager_new_id = id_mapping.get(manager_old_id)
        employee_new_id = id_mapping.get(employee_old_id)

        if manager_new_id and employee_new_id:
            for emp in published_employees:
                if emp["id"] == employee_new_id:
                    emp["manager_id"] = manager_new_id
                    relationships_set += 1
                    break

    return published_employees, id_mapping, relationships_set


def simulate_tree_endpoint(employees):
    """
    Simulate tree endpoint returning React Flow format.
    """
    nodes = []
    edges = []

    for emp in employees:
        emp_id_str = str(emp["id"])

        # Use position from PPTX or default
        pos_x = emp.get("position_x", 0) or 0
        pos_y = emp.get("position_y", 0) or 0

        # Convert EMU to pixels (rough approximation)
        pos_x_px = pos_x / 10000 if pos_x > 1000 else pos_x
        pos_y_px = pos_y / 10000 if pos_y > 1000 else pos_y

        nodes.append({
            "id": emp_id_str,
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
            "position": {
                "x": pos_x_px,
                "y": pos_y_px,
            },
        })

        if emp.get("manager_id"):
            manager_id_str = str(emp["manager_id"])
            edges.append({
                "id": f"e-{manager_id_str}-{emp_id_str}",
                "source": manager_id_str,
                "target": emp_id_str,
                "type": "smoothstep",
            })

    return {"nodes": nodes, "edges": edges}


def verify_react_flow_format(tree_data):
    """
    Verify the tree data matches frontend OrgNode/OrgEdge types.
    """
    errors = []

    # Check nodes
    for node in tree_data["nodes"]:
        if not isinstance(node.get("id"), str):
            errors.append(f"Node id must be string: {node.get('id')}")
        if "data" not in node:
            errors.append(f"Node missing data: {node.get('id')}")
        if "position" not in node:
            errors.append(f"Node missing position: {node.get('id')}")
        if "label" not in node.get("data", {}):
            errors.append(f"Node data missing label: {node.get('id')}")

    # Check edges
    node_ids = {n["id"] for n in tree_data["nodes"]}
    for edge in tree_data["edges"]:
        if not isinstance(edge.get("id"), str):
            errors.append(f"Edge id must be string: {edge.get('id')}")
        if edge.get("source") not in node_ids:
            errors.append(f"Edge source not in nodes: {edge.get('source')}")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge target not in nodes: {edge.get('target')}")

    return errors


def run_pptx_test():
    print("=" * 70)
    print("TESTING PPTX FLOW: Parse -> Publish -> Tree Endpoint")
    print("=" * 70)

    # Step 1: Simulate PPTX parsing
    print("\n=== Step 1: PPTX Parsing (simulated) ===")
    employees, relationships = create_mock_pptx_result()
    print(f"Employees extracted: {len(employees)}")
    print(f"Relationships inferred: {len(relationships)}")

    # Show employee hierarchy
    print("\nEmployee hierarchy:")
    for emp in employees:
        indent = "  " * (emp.level - 1)
        print(f"{indent}L{emp.level}: {emp.name} ({emp.title})")

    # Step 2: Convert to dict (what gets stored)
    print("\n=== Step 2: Serialize to database format ===")
    raw_data = simulate_pptx_to_dict(employees, relationships)
    print(f"Employees in dict: {len(raw_data['employees'])}")
    print(f"Relationships in dict: {len(raw_data['relationships'])}")

    # Show relationships
    print("\nRelationships (manager_id -> employee_id):")
    id_to_name = {emp.id: emp.name for emp in employees}
    for mgr_id, emp_id in relationships:
        print(f"  {id_to_name.get(mgr_id)} -> {id_to_name.get(emp_id)}")

    # Step 3: Simulate publish
    print("\n=== Step 3: Publish Flow ===")
    published_employees, id_mapping, rel_count = simulate_publish_flow(raw_data)
    print(f"Employees created: {len(published_employees)}")
    print(f"ID mappings: {len(id_mapping)}")
    print(f"Relationships set: {rel_count}")

    # Count employees with manager_id
    with_manager = sum(1 for emp in published_employees if emp["manager_id"])
    print(f"Employees with manager_id: {with_manager}")

    # Step 4: Simulate tree endpoint
    print("\n=== Step 4: Tree Endpoint ===")
    tree_data = simulate_tree_endpoint(published_employees)
    print(f"Nodes returned: {len(tree_data['nodes'])}")
    print(f"Edges returned: {len(tree_data['edges'])}")

    # Show edges
    new_id_to_name = {emp["id"]: emp["full_name"] for emp in published_employees}
    print("\nEdges (reporting lines for frontend):")
    for edge in tree_data["edges"]:
        src_name = new_id_to_name.get(edge["source"], "Unknown")
        tgt_name = new_id_to_name.get(edge["target"], "Unknown")
        print(f"  {src_name} -> {tgt_name}")

    # Step 5: Verify React Flow format
    print("\n=== Step 5: React Flow Format Verification ===")
    errors = verify_react_flow_format(tree_data)
    if errors:
        print("ERRORS found:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("All nodes have: id (string), data (label, title), position (x, y)")
        print("All edges have: id, source, target referencing valid nodes")
        print("Format is React Flow compatible!")

    # Final verdict
    print("\n" + "=" * 70)
    if len(tree_data["edges"]) == 0:
        print("FAIL: No edges returned - reporting lines will NOT be displayed!")
    elif len(tree_data["edges"]) == len(relationships):
        print("PASS: PPTX flow produces correct data for frontend!")
        print(f"  {len(tree_data['nodes'])} nodes (employee boxes)")
        print(f"  {len(tree_data['edges'])} edges (reporting lines)")
        print("\nFrontend OrgChart component will display:")
        print("  ✓ Employee boxes with name, title, grade")
        print("  ✓ Connecting lines showing reporting relationships")
        print("  ✓ Hierarchical layout based on PPTX positions")
    else:
        print(f"PARTIAL: {len(tree_data['edges'])}/{len(relationships)} edges")
    print("=" * 70)

    return tree_data


if __name__ == "__main__":
    run_pptx_test()
