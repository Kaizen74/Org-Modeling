"""
Test the complete flow from CSV upload to tree endpoint edge generation.
This simulates what happens when a user uploads a CSV and views the org chart.
"""

import asyncio
import uuid
from datetime import datetime
from app.parsers.csv_parser import CSVParser


# Real-world org structure similar to user's data
SATS_ORG_CSV = """Name,Title,Function,Grade,Line Manager
Vincent Chan,SVP Passenger Services,Passenger Services,SVP,
Kevin Chin,VP Airline Operations,Passenger Services,H7,Vincent Chan
Melissa Koh,VP Premium Services,Passenger Services,H7,Vincent Chan
Zahida Begum,Manager Airline Relations,Passenger Services,H2,Kevin Chin
Sharifah Azzah,Senior Manager Training,Passenger Services,H3,Kevin Chin
Diana Lee,Manager Premium Experience,Passenger Services,H2,Melissa Koh
AO20,Airline Relations,Passenger Services,AO,Zahida Begum
AO21,Airline Relations,Passenger Services,AO,Zahida Begum
AO22,Airline Relations,Passenger Services,AO,Zahida Begum
AO23,Airline Relations,Passenger Services,AO,Diana Lee
AO24,Airline Relations,Passenger Services,AO,Diana Lee
AO25,Airline Relations,Passenger Services,AO,Sharifah Azzah
AO26,Training,Passenger Services,AO,Sharifah Azzah
AO27,Quality,Passenger Services,AO,Sharifah Azzah
AO28,Lounge,Passenger Services,AO,Diana Lee
"""


def simulate_tree_endpoint(employees, relationships, id_mapping):
    """
    Simulate what the /scenarios/{id}/tree endpoint does.

    This is the exact logic from routes.py lines 738-779
    """
    nodes = []
    edges = []

    for emp in employees:
        emp_id_str = str(emp["id"])

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
                "x": 0,
                "y": (emp.get("level", 1) - 1) * 150,
            },
        })

        # This is the critical part - checking manager_id
        manager_id = emp.get("manager_id")
        if manager_id:
            # In real endpoint, manager_id is a UUID
            # Here we simulate by looking up the new ID
            manager_id_str = str(manager_id)
            edges.append({
                "id": f"e-{manager_id_str}-{emp_id_str}",
                "source": manager_id_str,
                "target": emp_id_str,
                "type": "smoothstep",
            })

    return {"nodes": nodes, "edges": edges}


def simulate_publish_flow(parse_result):
    """
    Simulate what the /datasets/{id}/publish endpoint does.

    This creates the id_mapping and sets manager_id on employees.
    """
    id_mapping = {}  # old_id -> new_uuid
    employees_with_manager_id = []

    # Create new UUIDs for each employee (simulating database insert)
    published_employees = []
    for emp_data in parse_result.employees:
        old_id = emp_data.get("id")
        new_id = str(uuid.uuid4())
        id_mapping[old_id] = new_id

        # Create "database" employee record
        db_emp = {
            "id": new_id,
            "full_name": emp_data.get("full_name"),
            "job_title": emp_data.get("job_title"),
            "level": emp_data.get("level"),
            "function": emp_data.get("function"),
            "grade": emp_data.get("grade"),
            "manager_id": None,  # Will be set below
        }
        published_employees.append(db_emp)

        # Track employees with manager_id in parsed data
        if emp_data.get("manager_id"):
            employees_with_manager_id.append((new_id, emp_data.get("manager_id")))

    print(f"\n=== Publish Flow Simulation ===")
    print(f"Total employees: {len(published_employees)}")
    print(f"ID mapping entries: {len(id_mapping)}")
    print(f"Employees with manager_id in parsed data: {len(employees_with_manager_id)}")
    print(f"Parsed relationships: {len(parse_result.relationships)}")

    # Set manager relationships from parsed_relationships
    relationships_set = 0
    for rel in parse_result.relationships:
        manager_old_id, employee_old_id = rel[0], rel[1]
        manager_new_id = id_mapping.get(manager_old_id)
        employee_new_id = id_mapping.get(employee_old_id)

        if manager_new_id and employee_new_id:
            # Find employee and set manager_id
            for emp in published_employees:
                if emp["id"] == employee_new_id:
                    emp["manager_id"] = manager_new_id
                    relationships_set += 1
                    break

    print(f"Relationships set from parsed_relationships: {relationships_set}")

    # Also set from employee's manager_id field (backup)
    csv_relationships_set = 0
    for new_employee_id, old_manager_id in employees_with_manager_id:
        manager_new_id = id_mapping.get(old_manager_id)
        if manager_new_id:
            for emp in published_employees:
                if emp["id"] == new_employee_id and not emp["manager_id"]:
                    emp["manager_id"] = manager_new_id
                    csv_relationships_set += 1
                    break

    print(f"Additional relationships from manager_id field: {csv_relationships_set}")

    # Count final manager_id relationships
    final_count = sum(1 for emp in published_employees if emp["manager_id"])
    print(f"Final employees with manager_id: {final_count}")

    return published_employees, id_mapping


def run_test():
    print("=" * 70)
    print("TESTING COMPLETE FLOW: CSV -> Publish -> Tree Endpoint")
    print("=" * 70)

    # Step 1: Parse CSV
    print("\n=== Step 1: Parse CSV ===")
    parser = CSVParser()
    result = parser.parse(SATS_ORG_CSV)

    print(f"Employees parsed: {len(result.employees)}")
    print(f"Relationships parsed: {len(result.relationships)}")

    # Show parsed relationships
    print("\nParsed relationships (manager_old_id -> employee_old_id):")
    id_to_name = {emp["id"]: emp["full_name"] for emp in result.employees}
    for mgr_id, emp_id in result.relationships[:5]:
        print(f"  {id_to_name.get(mgr_id)} -> {id_to_name.get(emp_id)}")
    if len(result.relationships) > 5:
        print(f"  ... and {len(result.relationships) - 5} more")

    # Show manager_id on employees
    print("\nEmployees with manager_id field set:")
    for emp in result.employees[:5]:
        mgr_id = emp.get("manager_id")
        if mgr_id:
            mgr_name = id_to_name.get(mgr_id, "Unknown")
            print(f"  {emp['full_name']} -> {mgr_name}")

    # Step 2: Simulate publish
    print("\n" + "=" * 70)
    published_employees, id_mapping = simulate_publish_flow(result)

    # Step 3: Simulate tree endpoint
    print("\n=== Step 3: Tree Endpoint Simulation ===")
    tree_data = simulate_tree_endpoint(published_employees, result.relationships, id_mapping)

    print(f"Nodes returned: {len(tree_data['nodes'])}")
    print(f"Edges returned: {len(tree_data['edges'])}")

    # Verify edges
    print("\nEdges (reporting lines):")
    new_id_to_name = {emp["id"]: emp["full_name"] for emp in published_employees}
    for edge in tree_data["edges"][:5]:
        src_name = new_id_to_name.get(edge["source"], "Unknown")
        tgt_name = new_id_to_name.get(edge["target"], "Unknown")
        print(f"  {src_name} -> {tgt_name}")
    if len(tree_data["edges"]) > 5:
        print(f"  ... and {len(tree_data['edges']) - 5} more")

    # Final verdict
    print("\n" + "=" * 70)
    if len(tree_data["edges"]) == 0:
        print("FAIL: No edges returned - reporting lines will NOT be displayed!")
        print("Root cause: manager_id is not being set on employees")
    elif len(tree_data["edges"]) == len(result.relationships):
        print("PASS: All edges returned correctly!")
        print(f"  {len(tree_data['nodes'])} nodes (employee boxes)")
        print(f"  {len(tree_data['edges'])} edges (reporting lines)")
    else:
        print(f"PARTIAL: {len(tree_data['edges'])}/{len(result.relationships)} edges returned")
    print("=" * 70)

    return tree_data


if __name__ == "__main__":
    run_test()
