"""
API journey: every step of the workflow against the backend with the fake
Claude (fake_claude_server.py), on the sample org from make_org.py.
Expectations are computed independently from the CSV wherever possible.
Needs a fresh database and no saved API key. Run by run_checks.sh step 5.
Usage: python journey_api.py <api_base> <csv_path> <prompt_log>
"""
import csv
import io
import json
import sys

import httpx

BASE, CSV_PATH, PROMPT_LOG = sys.argv[1], sys.argv[2], sys.argv[3]
c = httpx.Client(base_url=BASE + "/api/v1", timeout=60)
results = []


def check(step, cond, detail=""):
    results.append((step, bool(cond), "" if cond else str(detail)[:300]))


def ok(r):
    if r.status_code >= 400:
        raise AssertionError(f"{r.request.method} {r.request.url.path} -> {r.status_code}: {r.text[:300]}")
    return r.json()


# ---- independent expectations from the raw file ----
raw = list(csv.DictReader(io.StringIO(open(CSV_PATH, "rb").read().decode("cp1252"))))
DISTINCT = ["Alicia Seah", "Tan Boon Hock", "Jasmine Lim", "Conor O’Brien", "Rachel Ng", "Kumar Raj", "Wei Tan", "Mei Lin"]
depts = {}
for r in raw:
    depts[r["Department"]] = depts.get(r["Department"], 0) + 1


def step(name, fn):
    try:
        fn()
    except Exception as e:  # keep going; record the failure
        check(name, False, f"{type(e).__name__}: {e}")


ctx = {}

# 1. Reset and settings
def s1():
    ok(c.delete("/org-data/clear-all"))
    check("settings: no key at start", ok(c.get("/settings/claude-api-key/status"))["configured"] is False)
    ok(c.post("/settings/claude-api-key", json={"api_key": "sk-ant-mock-key-0000"}))
    st = ok(c.get("/settings/claude-api-key/status"))
    check("settings: key saved and masked", st["configured"] and "0000" in (st["masked_key"] or "") and "mock-key" not in (st["masked_key"] or ""), st)
    check("settings: connection test", ok(c.post("/settings/claude-api-key/test"))["success"])
step("settings", s1)

# 2. Upload the Windows-1252 file
def s2():
    r = c.post("/org-data/upload-csv", files={"file": ("acme_org.csv", open(CSV_PATH, "rb").read(), "text/csv")})
    up = ok(r)
    check("upload: Excel encoding accepted", up["success"])
    check("upload: every row read", up["employee_count"] == len(raw), (up["employee_count"], len(raw)))
    w = " | ".join(up["validation_errors"])
    check("upload: shared names reported", "shared by more than one person" in w, w)
    check("upload: ambiguous Kumar Raj reported, not guessed", "'Kumar Raj' matches 2 people and could not be resolved" in w, w)
    check("upload: Level mismatch reported", "Level doesn't match" in w, w)
    org = ok(c.get("/org-data/latest"))
    ctx["org"] = org["employees"]
    by_name = {}
    for e in org["employees"]:
        by_name.setdefault(e["name"], []).append(e)
    check("upload: curly apostrophe decoded", "Conor O’Brien" in by_name, [n for n in by_name if "Brien" in n])
    check("upload: two Kumar Raj kept apart", len(by_name.get("Kumar Raj", [])) == 2)
    mei = by_name["Mei Lin"][0]
    hrbp = next(e for e in by_name["Wei Tan"] if e["job_title"] == "HR Business Partner")
    check("upload: Line Manager given as Employee ID resolves", mei["manager_id"] == hrbp["employee_id"], (mei["manager_id"], hrbp["employee_id"]))
    head = next(e for e in by_name["Wei Tan"] if e["job_title"] == "Head, People")
    check("upload: shared name resolved by level", hrbp["manager_id"] == head["employee_id"])
    check("upload: hierarchy keyed by id", org["hierarchy"].get("id") is not None)
step("upload", s2)

# 3. Grades and metrics
def s3():
    grades = {g["grade"]: g for g in ok(c.get("/grades/"))}
    check("grades: auto-imported from upload", {"SVP", "H8", "H6", "H5", "TL", "AO"} <= set(grades), list(grades))
    check("grades: H6 median ignores blank salaries", grades["H6"]["median_salary"] > 0, grades["H6"])
    m = ok(c.get("/metrics/latest"))["metrics"]
    ctx["metrics"] = m
    check("metrics: version current", m.get("metrics_version", 0) >= 3)
    check("metrics: headcount", m["total_employees"] == len(raw))
    # expected cost: CSV salaries, blanks filled with the grade median
    exp_cost = sum(float(r["Salary"]) if r["Salary"] else grades[r["Grade"]]["median_salary"] for r in raw)
    check("metrics: cost = CSV salaries + grade medians for blanks", abs(m["cost_analysis"]["total_cost"] - exp_cost) < 1, (m["cost_analysis"]["total_cost"], exp_cost))
    comps = m["health_indicators"]["components"]
    check("metrics: health is weighted sum of its 4 parts", m["health_indicators"]["health_score"] == round(sum(x["score"] * x["weight"] for x in comps) / 100) and sum(x["weight"] for x in comps) == 100)
    d = {x["department"]: x for x in m["department_analysis"]}
    check("metrics: department headcounts match CSV", {k: v["headcount"] for k, v in d.items()} == depts, ({k: v["headcount"] for k, v in d.items()}, depts))
    check("metrics: cost shares add to 100%", abs(sum(x["cost_pct"] for x in d.values()) - 100) < 0.6)
    a = {x["manager"]: x for x in m["span_of_control"]["manager_assessments"]}
    check("metrics: manager tagged Operational judged against 10-20", a["Ramp Lead 0"]["benchmark_range"] == [10, 20] and a["Ramp Lead 0"]["status"] == "within", a["Ramp Lead 0"])
    check("metrics: untagged managers judged against 5-10", a["Manager Ramp"]["benchmark_range"] == [5, 10] and a["Tan Boon Hock"]["benchmark_range"] == [5, 10] and a["Mgr CX Insights"]["benchmark_range"] == [5, 10])
    check("metrics: every manager has 10-20 only if tagged", all((x["benchmark_range"] == [10, 20]) == ("Lead" in x["manager"]) for x in a.values()))
    check("metrics: Level mismatch listed", any(x["name"] == "Mei Lin" for x in m["layer_analysis"]["level_mismatches"]["examples"]), m["layer_analysis"]["level_mismatches"])
    s = ok(c.get("/metrics/summary"))
    check("summary: agrees with metrics", s["health_score"] == m["health_indicators"]["health_score"] and s["total_employees"] == len(raw) and s["departments"] == len(depts))
step("metrics", s3)

# 4. Work activities (fake AI)
def s4():
    q = ok(c.get("/ai-analysis/work-activities/quick"))
    check("work activities: coverage 100%", q["coverage_percentage"] == 100.0, q["coverage_percentage"])
    wa = ok(c.post("/ai-analysis/work-activities", json={"industry": "Aviation ground services"}))["work_activities_analysis"]
    check("work activities: analysis stored", wa["activity_duplication"]["duplications"][0]["dimension"] == "Process & Systems")
    check("work activities: model recorded", wa.get("_llm", {}).get("model_served") == "claude-opus-5-5")
    check("work activities: latest returns it", ok(c.get("/ai-analysis/work-activities/latest"))["work_activities_analysis"]["executive_summary"] == wa["executive_summary"])
step("work activities", s4)

# 5. Archetype analysis (fake AI)
def s5():
    ai = ok(c.post("/ai-analysis/analyze", json={"design_criteria": "Faster frontline decisions", "strategy_text": "Grow on-time performance"}))["ai_analysis"]
    cat = ai["category_4_recommended_archetypes"]
    fn = next(x for x in cat["all_archetype_scores"] if x["archetype_id"] == "1_functional")
    check("archetypes: overall recomputed from weights (AI said 95)", fn["overall_score"] == 60 and fn["ai_overall_score"] == 95, fn)
    check("archetypes: ranking re-sorted", cat["all_archetype_scores"][0]["archetype_id"] == "3_front_back_hybrid")
    check("archetypes: mismatch with AI picks flagged", "Process-Based" in (cat.get("ranking_note") or ""), cat.get("ranking_note"))
    diag = cat["recommendations"][1]["structure_diagram"]
    nodes = {n["id"]: n for n in diag["nodes"]}
    check("diagrams: invented department not counted", nodes["ghost"]["headcount"] is None and nodes["ghost"]["unknown_departments"] == ["Marketing"])
    real = sum(n["headcount"] or 0 for n in diag["nodes"])
    check("diagrams: unit headcounts add up to the organization", real == len(raw), (real, len(raw)))
    check("diagrams: new unit marked", nodes["new"]["headcount"] is None and nodes["new"]["is_new"])
    check("archetypes: work-activities analysis preserved", ai.get("work_activities_analysis", {}).get("executive_summary"))
    latest = ok(c.get("/ai-analysis/latest"))["ai_analysis"]
    check("archetypes: saved result reloads with scoring", latest["category_4_recommended_archetypes"]["all_archetype_scores"][0]["archetype_id"] == "3_front_back_hybrid")
    ok(c.post("/ai-analysis/analyze", json={"analysis_scope": "department", "department": "Finance"}))
step("archetypes", s5)

# 6. Optional AI-role overlay
def s6():
    d0 = ok(c.get("/ai-disposition"))
    check("AI overlay: off until used", d0["enabled"] is False and d0["summary"]["capacity_fte"] == 0)
    ok(c.put("/ai-disposition/role", json={"job_title": "Finance Executive", "disposition": "keep_human", "capacity_freed_pct": 0}))
    d1 = ok(c.post("/ai-disposition/suggest", json={"industry": "Aviation"}))
    tags = {r["job_title"]: r["tag"] for r in d1["roles"] if r["tag"]}
    check("AI overlay: suggestions added", d1["suggestions_added"] >= 10, d1["suggestions_added"])
    check("AI overlay: your tag kept over the AI's", tags["Finance Executive"]["disposition"] == "keep_human" and tags["Finance Executive"]["source"] == "user")
    exp_fte = sum((tags.get(r["Job Title"], {}) or {}).get("capacity_freed_pct", 0) / 100 for r in raw)
    check("AI overlay: capacity = sum of tagged shares", abs(d1["summary"]["capacity_fte"] - round(exp_fte, 1)) < 0.11, (d1["summary"]["capacity_fte"], exp_fte))
    ctx["capacity"] = d1["summary"]["capacity_fte"]
step("AI overlay", s6)

# 7. Scenarios: every move type, plus an invalid one
def s7():
    org = {e["name"]: e for e in ctx["org"] if e["name"] not in ("Kumar Raj", "Wei Tan")}
    sm = org["Senior CX Insights"]; mm = org["Mgr CX Insights"]; vp_cx = org["Jasmine Lim"]
    m_cargo = org["Manager Cargo"]; m_bag = org["Manager Baggage"]; vp_go = org["Tan Boon Hock"]; ceo = org["Alicia Seah"]
    moves = [
        {"type": "add_role", "title": "Turnaround Coordinator", "manager_id": vp_go["employee_id"], "grade": "H5", "count": 2, "note": "own the hand-off"},
        {"type": "remove_role", "person_id": sm["employee_id"], "note": "single-report layer"},
        {"type": "merge_teams", "from_manager_id": m_cargo["employee_id"], "into_manager_id": m_bag["employee_id"], "remove_from_manager": True},
        {"type": "reassign", "person_id": mm["employee_id"], "new_manager_id": vp_cx["employee_id"]},
        {"type": "change_role", "person_id": org["Conor O’Brien"]["employee_id"], "title": "Head, Corporate Affairs & Communications"},
        {"type": "move_department", "department": "People", "new_department": "People & Culture"},
        {"type": "reassign", "person_id": ceo["employee_id"], "new_manager_id": vp_go["employee_id"]},  # loop: must be skipped
    ]
    sc = ok(c.post("/scenarios", json={"name": "Integrated option", "moves": moves}))
    ctx["sid"] = sc["id"]
    status = [m["status"] for m in sc["move_log"]]
    check("scenario: six valid moves applied, loop skipped", status == ["applied"] * 6 + ["skipped"], sc["move_log"])
    imp = sc["impact"]
    added_cost = sum(r["salary"] for r in imp["roles_added"]); removed_cost = sum(r["salary"] for r in imp["roles_removed"])
    check("scenario: headcount change = added - removed", sc["delta"]["headcount"] == len(imp["roles_added"]) - len(imp["roles_removed"]) == 2 - 2, sc["delta"]["headcount"])
    check("scenario: cost change = added - removed salaries", abs(sc["delta"]["total_cost"] - (added_cost - removed_cost)) < 1, (sc["delta"]["total_cost"], added_cost, removed_cost))
    check("scenario: new roles priced from grade table", all(r["salary"] > 0 for r in imp["roles_added"]))
    check("scenario: department fold counted", any(d["department"] == "People & Culture" and d["status"] == "new" for d in sc["departments"]))
    check("scenario: baseline unchanged by moves", ok(c.get("/metrics/latest"))["metrics"]["total_employees"] == len(raw))
    check("scenario: AI capacity carried", sc["baseline"]["ai_capacity_fte"] == ctx["capacity"], (sc["baseline"]["ai_capacity_fte"], ctx["capacity"]))
    quick_ids = [a["manager_id"] for a in ctx["metrics"]["span_of_control"]["manager_assessments"] if a["span"] == 1]
    q = ok(c.post("/scenarios", json={"name": "Remove single-report managers", "moves": [{"type": "remove_role", "person_id": i} for i in quick_ids if i != ceo["employee_id"]]}))
    check("scenario: removing single-report managers leaves none", q["scenario"]["single_report_managers"] == 0, q["scenario"]["single_report_managers"])
    cl = ok(c.post("/scenarios", json={"name": "Copy", "clone_from": sc["id"]}))
    check("scenario: duplicate keeps moves", cl["move_count"] == len(moves))
    ok(c.delete(f"/scenarios/{cl['id']}/moves/6"))
    check("scenario: removing a move recalculates", ok(c.get(f"/scenarios/{cl['id']}"))["move_count"] == 6)
    ok(c.delete(f"/scenarios/{cl['id']}"))
    check("scenario: list has two", len(ok(c.get("/scenarios"))["scenarios"]) == 2)
step("scenarios", s7)

# 8. Comparison
def s8():
    comp = ok(c.get("/comparison"))
    check("compare: current + two scenarios", [o["id"] for o in comp["options"]][0] == "current" and len(comp["options"]) == 3)
    ok(c.put("/comparison/judgments", json={"option_id": ctx["sid"], "criterion_id": "strategy_fit", "score": 5, "rationale": "Owns turnaround"}))
    comp = ok(c.post("/comparison/suggest"))
    j = comp["judgments"]
    check("compare: your score kept over the AI's", j[ctx["sid"]]["strategy_fit"]["source"] == "user" and j[ctx["sid"]]["strategy_fit"]["score"] == 5)
    check("compare: invented option ignored", "ghost" not in j)
    check("compare: all judged cells now scored", comp["result"]["complete"], comp["result"]["missing"])
    # recompute one total by hand
    w = {c_["id"]: c_["weight"] for c_ in comp["criteria"]}
    cells = comp["result"]["cells"][ctx["sid"]]
    manual = round(sum(cells[k] * w[k] for k in w) / sum(w.values()), 1)
    check("compare: total = weighted average of cells", comp["result"]["totals"][ctx["sid"]] == manual, (comp["result"]["totals"][ctx["sid"]], manual))
    bad = c.put("/comparison/criteria", json={"criteria": [{"id": "x", "name": "X", "kind": "measured", "metric": "nope", "weight": 1}]})
    check("compare: invalid criteria refused with reason", bad.status_code == 400 and "unknown measure" in bad.text)
step("comparison", s8)

# 9. Implementation and board pack
def s9():
    plan = ok(c.get(f"/scenarios/{ctx['sid']}/implementation"))
    keys = [w["key"] for w in plan["waves"]]
    check("implementation: appoint before move before remove", keys == ["appoint", "move", "remove", "stabilise"], keys)
    check("implementation: cost lines add up", plan["cost"]["net_change"] == plan["cost"]["added_roles"] - plan["cost"]["removed_roles"], plan["cost"])
    check("implementation: skipped move flagged as risk", any(r["area"] == "Design completeness" for r in plan["risks"]))
    pack = c.get("/export/pack")
    check("pack: renders", pack.status_code == 200 and "Evidence inventory" in pack.text and "Transition sequence" in pack.text)
    leaked = [n for n in DISTINCT if n in pack.text]
    check("pack: no personal names by default", not leaked, leaked)
    named = c.get(f"/export/pack?scenario_id={ctx['sid']}&include_names=true").text
    check("pack: names of affected people when asked", "Senior CX Insights" in named and "Senior CX Insights" not in pack.text)
step("implementation", s9)

# 10. Grade edit flows into costs
def s10():
    g = next(x for x in ok(c.get("/grades/")) if x["grade"] == "H6")
    before = ok(c.get("/metrics/latest"))["metrics"]["cost_analysis"]["total_cost"]
    blanks = sum(1 for r in raw if r["Grade"] == "H6" and not r["Salary"])
    ok(c.put(f"/grades/{g['id']}", json={**g, "median_salary": g["median_salary"] + 10000}))
    after = ok(c.post("/metrics/recalculate"))["metrics"]["cost_analysis"]["total_cost"]
    check("grades: salary edit changes cost for blank-salary people only", abs((after - before) - blanks * 10000) < 1, (after - before, blanks))
step("grades", s10)

# 11. Privacy across every AI call
def s11():
    prompts = [json.loads(l) for l in open(PROMPT_LOG)]
    kinds = sorted({p["kind"] for p in prompts})
    check("AI calls: all four kinds exercised", kinds == ["archetype", "comparison", "disposition", "work_activities"], kinds)
    leaks = {n for p in prompts for n in DISTINCT if n in p["prompt"]}
    check("AI calls: no personal names in any prompt", not leaks, leaks)
    arch = [p["prompt"] for p in prompts if p["kind"] == "archetype"]
    check("AI calls: archetype prompt has real departments", all(f"- {d}:" in arch[0] for d in depts))
    check("AI calls: department scope prompt", "All roles in Finance" in arch[-1] and "GUIDANCE FOR FINANCE" in arch[-1])
step("privacy", s11)

# 12. New project clears everything
def s12():
    ok(c.delete("/org-data/clear-all"))
    check("new project: metrics gone", c.get("/metrics/latest").status_code == 404)
    check("new project: scenarios gone", c.get("/scenarios").status_code == 404)
    check("new project: key kept", ok(c.get("/settings/claude-api-key/status"))["configured"])
step("new project", s12)

passed = sum(1 for r in results if r[1])
for name, good, detail in results:
    print(("PASS  " if good else "FAIL  ") + name + (f"\n        {detail}" if not good else ""))
print(f"\n{passed} of {len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
