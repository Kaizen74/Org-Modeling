"""Tests for the scenario engine (design moves) and the Scenario Studio API."""

from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scenario_engine import apply_moves, people_impact, headline, delta
from app.services.metrics_service import MetricsCalculator


def _org():
    # CEO > VP Ops > Ops Mgr > Lead > 2 ICs ; CEO > VP Sales > Sales Mgr (no reports)
    def p(i, name, title, mgr, dept, salary=100):
        return {"employee_id": i, "name": name, "job_title": title, "grade": "G", "level": 0,
                "manager_name": mgr, "department": dept, "salary": salary}
    return [
        p("C", "Cara", "CEO", "Top of Org", "Exec", 500),
        p("V1", "Vic", "VP Ops", "Cara", "Ops", 300),
        p("M1", "Max", "Ops Manager", "Vic", "Ops", 200),
        p("L1", "Lee", "Team Lead", "Max", "Ops", 120),
        p("I1", "Ivy", "Agent", "Lee", "Ops", 60),
        p("I2", "Ian", "Agent", "Lee", "Ops", 60),
        p("V2", "Val", "VP Sales", "Cara", "Sales", 300),
        p("M2", "Mo", "Sales Manager", "Val", "Sales", 200),
    ]


def _by_id(emps):
    return {e["employee_id"]: e for e in emps}


def test_baseline_is_never_modified():
    org = _org()
    apply_moves(org, [{"type": "remove_role", "person_id": "M1"}])
    assert len(org) == 8 and "manager_id" not in org[0]


def test_remove_role_moves_reports_up_and_cuts_a_layer():
    emps, log = apply_moves(_org(), [{"type": "remove_role", "person_id": "M1"}])
    by = _by_id(emps)
    assert "M1" not in by
    assert by["L1"]["manager_id"] == "V1"
    assert log[0]["status"] == "applied" and "1 report(s) now report to Vic" in log[0]["message"]
    base = MetricsCalculator(employees=_org()).calculate_all_metrics()
    scen = MetricsCalculator(employees=emps).calculate_all_metrics()
    d = delta(headline(base), headline(scen))
    assert d["layers"] == -1 and d["headcount"] == -1 and d["total_cost"] == -200


def test_reassign_moves_whole_team_and_blocks_loops():
    emps, log = apply_moves(_org(), [
        {"type": "reassign", "person_id": "M1", "new_manager_id": "V2", "department": "Sales"},
        {"type": "reassign", "person_id": "V2", "new_manager_id": "I1"},  # Ivy is now in Val's team
    ])
    by = _by_id(emps)
    assert by["M1"]["manager_id"] == "V2" and by["M1"]["department"] == "Sales"
    assert by["L1"]["manager_id"] == "M1"  # team travels with its manager
    assert log[1]["status"] == "skipped" and "in their own team" in log[1]["message"]


def test_add_role_uses_grade_salary_and_counts():
    emps, log = apply_moves(_org(), [{"type": "add_role", "title": "Turnaround Coordinator", "grade": "H5",
                                      "manager_id": "V1", "count": 2}], grade_salary={"H5": 130})
    new = [e for e in emps if e.get("is_new")]
    assert len(new) == 2 and all(e["salary"] == 130 and e["manager_id"] == "V1" for e in new)
    assert new[0]["employee_id"] != new[1]["employee_id"]
    assert new[0]["department"] == "Ops"  # inherits the manager's department


def test_merge_teams_with_role_removal():
    emps, log = apply_moves(_org(), [{"type": "merge_teams", "from_manager_id": "V2", "into_manager_id": "V1",
                                      "remove_from_manager": True}])
    by = _by_id(emps)
    assert "V2" not in by and by["M2"]["manager_id"] == "V1"
    assert "removed Val's role" in log[0]["message"]


def test_change_role_and_move_department():
    emps, log = apply_moves(_org(), [
        {"type": "change_role", "person_id": "M2", "title": "Commercial Manager", "grade": "H6"},
        {"type": "move_department", "department": "Sales", "new_department": "Commercial"},
    ], grade_salary={"H6": 180})
    by = _by_id(emps)
    assert by["M2"]["job_title"] == "Commercial Manager" and by["M2"]["salary"] == 180
    assert by["V2"]["department"] == "Commercial"
    assert "2 people moved from Sales to Commercial" in log[1]["message"]


def test_invalid_moves_are_skipped_with_reasons_not_errors():
    _, log = apply_moves(_org(), [
        {"type": "remove_role", "person_id": "C"},              # top with reports, no target
        {"type": "reassign", "person_id": "NOPE", "new_manager_id": "C"},
        {"type": "teleport"},
        {"type": "add_role", "manager_id": "C"},                # no title
    ])
    assert [m["status"] for m in log] == ["skipped"] * 4
    assert "without a manager" in log[0]["message"]
    assert "not in this organization" in log[1]["message"]
    assert "Unknown move type" in log[2]["message"]
    assert "needs a job title" in log[3]["message"]


def test_people_impact_lists_who_is_affected():
    base = _org()
    emps, _ = apply_moves(base, [
        {"type": "remove_role", "person_id": "M1"},
        {"type": "add_role", "title": "Coordinator", "manager_id": "V1"},
        {"type": "reassign", "person_id": "M2", "new_manager_id": "V1", "department": "Ops"},
    ])
    impact = people_impact(base, emps)
    assert [r["employee_id"] for r in impact["roles_removed"]] == ["M1"]
    assert len(impact["roles_added"]) == 1
    moved = {m["employee_id"]: m for m in impact["new_manager"]}
    assert moved["L1"]["from"] == "Max" and moved["L1"]["to"] == "Vic"
    assert moved["M2"]["to"] == "Vic"
    assert impact["new_department"][0]["to"] == "Ops"
    assert impact["people_affected"] == 3  # L1, M2 moved + M1 removed
    vic = next(s for s in impact["managers_with_changed_span"] if s["employee_id"] == "V1")
    assert (vic["span_before"], vic["span_after"]) == (1, 3)  # Lee (moved up), new Coordinator, Mo


# ---------- API ----------

async def _upload(client: AsyncClient, path):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", path.read_bytes(), "text/csv")})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_scenario_api_round_trip(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    created = (await client.post("/api/v1/scenarios", json={"name": "Delayer CX"})).json()
    sid = created["id"]
    assert created["delta"]["headcount"] == 0

    # Remove a single-report manager (Rachel Goh manages one person in the fixture)
    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    rachel = next(e for e in org if e["name"] == "Rachel Goh")
    after = (await client.post(f"/api/v1/scenarios/{sid}/moves", json={"type": "remove_role", "person_id": rachel["employee_id"]})).json()
    assert after["move_count"] == 1
    assert after["delta"]["headcount"] == -1
    assert after["delta"]["single_report_managers"] <= 0
    assert after["impact"]["roles_removed"][0]["name"] == "Rachel Goh"
    assert len(after["people"]) == 63 and all("employee_id" in p for p in after["people"])

    listing = (await client.get("/api/v1/scenarios")).json()
    assert listing["scenarios"][0]["name"] == "Delayer CX"
    assert listing["scenarios"][0]["delta"]["headcount"] == -1

    clone = (await client.post("/api/v1/scenarios", json={"name": "Copy", "clone_from": sid})).json()
    assert clone["move_count"] == 1

    removed = (await client.delete(f"/api/v1/scenarios/{sid}/moves/0")).json()
    assert removed["move_count"] == 0 and removed["delta"]["headcount"] == 0

    preview = (await client.post("/api/v1/scenarios/preview", json={"moves": [{"type": "teleport"}]})).json()
    assert preview["move_log"][0]["status"] == "skipped"

    assert (await client.post(f"/api/v1/scenarios/{sid}/moves", json={"type": "teleport"})).status_code == 400
    assert (await client.delete(f"/api/v1/scenarios/{sid}")).status_code == 200
    assert (await client.get(f"/api/v1/scenarios/{sid}")).status_code == 404


@pytest.mark.asyncio
async def test_new_project_clears_scenarios(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    await client.post("/api/v1/scenarios", json={"name": "Temp"})
    await client.delete("/api/v1/org-data/clear-all")
    await _upload(client, sample_csv_path)
    assert (await client.get("/api/v1/scenarios")).json()["scenarios"] == []


@pytest.mark.asyncio
async def test_implementation_plan(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    org = (await client.get("/api/v1/org-data/latest")).json()["employees"]
    by_name = {e["name"]: e for e in org}
    rachel, vincent = by_name["Rachel Goh"], by_name["Vincent Chan"]
    vps = [e for e in org if e["manager_id"] == vincent["employee_id"]]
    moves = [
        {"type": "remove_role", "person_id": rachel["employee_id"], "note": "single-report layer"},
        {"type": "add_role", "title": "Transformation Lead", "manager_id": vincent["employee_id"], "salary": 150000},
        {"type": "merge_teams", "from_manager_id": vps[1]["employee_id"], "into_manager_id": vps[0]["employee_id"]},
        {"type": "teleport"},
    ]
    sid = (await client.post("/api/v1/scenarios", json={"name": "Plan", "moves": moves})).json()["id"]
    plan = (await client.get(f"/api/v1/scenarios/{sid}/implementation")).json()

    assert [w["key"] for w in plan["waves"]] == ["appoint", "move", "remove", "stabilise"]  # appoint before remove
    assert plan["waves"][2]["moves"][0]["note"] == "single-report layer"
    assert plan["cost"]["added_roles"] == 150000
    assert plan["cost"]["removed_roles"] == rachel["salary"]
    assert plan["summary"]["roles_removed"] == 1 and plan["summary"]["roles_added"] == 1
    areas = {r["area"] for r in plan["risks"]}
    assert "Design completeness" in areas  # the skipped 'teleport' move
    assert "People and employee relations" in areas
    assert plan["risks"][0]["severity"] in ("High", "Medium")
    assert plan["change_load"]["managers_gaining"][0]["span_after"] > plan["change_load"]["managers_gaining"][0]["span_before"]
