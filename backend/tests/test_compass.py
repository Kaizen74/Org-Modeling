"""Tests for the Capability Compass hand-off import, shared grades, hypotheses and the return file."""

import copy
import json
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import compass_service as cs
from app.services.comparison_service import DEFAULT_CRITERIA, validate_criteria

SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "meridian_compass_handoff.json").read_text())
NAMES = ["Vincent Chan", "Daniel Boy"]  # people in the org fixture


def broken(**changes):
    """A deliberately broken copy of the sample file."""
    p = copy.deepcopy(SAMPLE)
    if "format" in changes:
        p["format"] = changes["format"]
    if changes.get("no_key"):
        p["engagement"]["key"] = ""
    if changes.get("dangling"):
        p["roles"][0]["cluster_ref"] = "CAP-99"
    if changes.get("not_ready"):
        p["readiness"] = {"ready": False, "verdict": "Not ready", "open": ["CAP-02 not scored"]}
    return p


def test_sample_packet_is_valid_and_fits_the_criteria_contract():
    assert cs.validate_packet(SAMPLE) == ([], [])
    criteria = cs.packet_criteria(SAMPLE)
    assert [c["ref"] for c in criteria] == ["DC-1", "DC-2", "DC-3", "DC-4", "DC-5", "DC-6"]
    assert validate_criteria(criteria) == []
    refs = {r["ref"] for r in cs.known_refs(SAMPLE)}
    assert {"CAP-03", "CAP-04.People", "VS-01", "LV-02", "RL-014", "DC-1", "P1", "C8", "LG-5", "DEC-06"} <= refs


def test_broken_packets_are_rejected_or_warned_in_plain_language():
    errors, _ = cs.validate_packet(broken(format="something-else"))
    assert "not a Capability Compass hand-off file" in errors[0] and "something-else" in errors[0]
    errors, _ = cs.validate_packet(broken(no_key=True))
    assert any("no engagement key" in e for e in errors)
    errors, warnings = cs.validate_packet(broken(dangling=True))
    assert errors == [] and any("RL-001" in w and "CAP-99" in w for w in warnings)
    errors, warnings = cs.validate_packet(broken(not_ready=True))
    assert errors == [] and any("not ready" in w and "CAP-02 not scored" in w for w in warnings)
    assert cs.validate_packet([1, 2])[0]
    newer = copy.deepcopy(SAMPLE)
    newer.update(format_version="1.7", something_new={"x": 1})
    assert cs.validate_packet(newer) == ([], [])  # any 1.x; unknown fields ignored
    newer["format_version"] = "2.0"
    assert cs.validate_packet(newer)[0]


def test_suggested_grades_follow_the_shared_mapping():
    assert [cs.suggested_grade(e) for e in ("OBSERVABLE", "PERCEPTUAL", "MODEL-INFERRED", None)] == \
        ["confirmed", "indicated", "hypothesis", None]


async def _upload(client, path):
    r = await client.post("/api/v1/org-data/upload-csv", files={"file": ("pax.csv", path.read_bytes(), "text/csv")})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_app_works_with_no_packet(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    state = (await client.get("/api/v1/compass")).json()
    assert state["engagement"] is None and state["refs"] == [] and state["hypotheses"] == []
    assert [f["ref"] for f in state["findings"]][:3] == ["baseline.layers", "baseline.spans", "baseline.health"]
    ret = (await client.get("/api/v1/compass/return")).json()
    assert ret["format"] == "compass-return" and ret["engagement_key"] == ""
    assert (await client.get("/api/v1/export/pack")).status_code == 200


@pytest.mark.asyncio
async def test_preview_applies_nothing_and_import_sets_criteria_strategy_and_key(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    pre = (await client.post("/api/v1/compass/preview", json={"packet": SAMPLE})).json()
    assert pre["ok"] and pre["engagement"]["key"] == "MERIDIAN"
    assert pre["criteria"]["action"] == "set" and pre["strategy"]["action"] == "set"
    assert pre["context"] == {"structure_findings": 6, "clusters": 6, "ids": len(cs.known_refs(SAMPLE))}
    # nothing applied yet
    assert (await client.get("/api/v1/compass")).json()["engagement"] is None
    assert [c["id"] for c in (await client.get("/api/v1/comparison")).json()["criteria"]] == [c["id"] for c in DEFAULT_CRITERIA]

    done = (await client.post("/api/v1/compass/import", json={"packet": SAMPLE})).json()
    assert done["engagement"]["key"] == "MERIDIAN"
    assert done["strategy_draft"].startswith("Who we serve:")
    assert [l["ref"] for l in done["context"]["structure_lens"]][0] == "CAP-01.Structure"
    comp = (await client.get("/api/v1/comparison")).json()
    assert [(c["ref"], c["weight"]) for c in comp["criteria"]] == \
        [("DC-1", 25), ("DC-2", 20), ("DC-3", 15), ("DC-4", 15), ("DC-5", 15), ("DC-6", 10)]
    assert comp["result"]["totals"]["current"] is not None  # measured criteria score straight away
    # Compass context never sets a score
    assert comp["judgments"] == {}


@pytest.mark.asyncio
async def test_import_never_overwrites_what_the_designer_typed_without_asking(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    mine = [{"id": "mine", "name": "My criterion", "kind": "judged", "weight": 100}]
    assert (await client.put("/api/v1/comparison/criteria", json={"criteria": mine})).status_code == 200
    await client.put("/api/v1/compass/strategy-draft", json={"text": "My own strategy"})

    pre = (await client.post("/api/v1/compass/preview", json={"packet": SAMPLE})).json()
    assert pre["criteria"]["action"] == "ask" and pre["strategy"]["action"] == "ask"

    kept = (await client.post("/api/v1/compass/import", json={"packet": SAMPLE})).json()
    assert kept["strategy_draft"] == "My own strategy"
    assert [c["id"] for c in (await client.get("/api/v1/comparison")).json()["criteria"]] == ["mine"]
    assert "Your comparison criteria were kept" in kept["applied"]

    replaced = (await client.post("/api/v1/compass/import", json={
        "packet": SAMPLE, "replace_criteria": True, "replace_strategy": True})).json()
    assert replaced["strategy_draft"].startswith("Who we serve:")
    assert len((await client.get("/api/v1/comparison")).json()["criteria"]) == 6


@pytest.mark.asyncio
async def test_broken_files_through_the_api(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    pre = (await client.post("/api/v1/compass/preview", json={"packet": broken(format="nope")})).json()
    assert pre["ok"] is False and "not a Capability Compass hand-off file" in pre["errors"][0]
    r = await client.post("/api/v1/compass/import", json={"packet": broken(no_key=True)})
    assert r.status_code == 400 and "no engagement key" in r.json()["detail"]
    assert (await client.get("/api/v1/compass")).json()["engagement"] is None
    # warnings don't block
    done = (await client.post("/api/v1/compass/import", json={"packet": broken(dangling=True, not_ready=True)})).json()
    assert done["engagement"]["key"] == "MERIDIAN" and len(done["warnings"]) == 2


@pytest.mark.asyncio
async def test_hypothesis_numbers_are_never_reused(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    h = {"statement": "Station heads decide turnaround trade-offs", "refuted_by": "Event records show ops control deciding"}
    await client.post("/api/v1/compass/hypotheses", json=h)
    await client.post("/api/v1/compass/hypotheses", json={**h, "statement": "Second"})
    assert (await client.delete("/api/v1/compass/hypotheses/H2")).status_code == 200
    state = (await client.post("/api/v1/compass/hypotheses", json={**h, "statement": "Third"})).json()
    assert [x["ref"] for x in state["hypotheses"]] == ["H1", "H3"]
    state = (await client.put("/api/v1/compass/hypotheses/H1", json={**h, "status": "supported", "note": "5 cases"})).json()
    assert state["hypotheses"][0]["status"] == "supported"
    assert (await client.post("/api/v1/compass/hypotheses", json={"statement": " "})).status_code == 400
    assert (await client.put("/api/v1/compass/hypotheses/H1", json={**h, "status": "maybe"})).status_code == 400
    assert (await client.put("/api/v1/compass/hypotheses/H9", json=h)).status_code == 404


@pytest.mark.asyncio
async def test_grades_links_and_the_return_file(client: AsyncClient, sample_csv_path):
    await _upload(client, sample_csv_path)
    # no packet yet: nothing to relate to
    r = await client.put("/api/v1/compass/relates", json={"ref": "baseline.layers", "relates_to": ["CAP-01"]})
    assert r.status_code == 400 and "Import a Capability Compass file first" in r.json()["detail"]

    await client.post("/api/v1/compass/import", json={"packet": SAMPLE})
    await client.post("/api/v1/compass/hypotheses", json={
        "statement": "Vincent Chan should own bid decisions", "refuted_by": "A different role decides in 1 case in 5"})
    await client.post("/api/v1/scenarios", json={"name": "Flatter option"})
    await client.put("/api/v1/comparison/judgments", json={"option_id": "current", "criterion_id": SAMPLE["charter"]["design_criteria"][0]["id"], "score": 4})

    state = (await client.get("/api/v1/compass")).json()
    by_ref = {f["ref"]: f for f in state["findings"]}
    assert by_ref["baseline.layers"]["grade"] == "confirmed" and by_ref["H1"]["grade"] == "hypothesis"
    assert by_ref["option.flatter-option"]["grade"] == "hypothesis"  # judged scores missing: fit not yet tested

    assert (await client.put("/api/v1/compass/grades", json={"ref": "baseline.layers", "grade": "sure"})).status_code == 400
    await client.put("/api/v1/compass/grades", json={"ref": "H1", "grade": "indicated"})
    r = await client.put("/api/v1/compass/relates", json={"ref": "H1", "relates_to": ["CAP-04.People", "RL-014", "CAP-77"]})
    assert r.status_code == 400 and "CAP-77" in r.json()["detail"]
    await client.put("/api/v1/compass/relates", json={"ref": "H1", "relates_to": ["CAP-04.People", "VS-01", "RL-014"]})

    ret = (await client.get("/api/v1/compass/return")).json()
    assert (ret["format"], ret["format_version"], ret["source_app"], ret["engagement_key"]) == \
        ("compass-return", "1.0", "org-modeling", "MERIDIAN")
    assert {f["kind"] for f in ret["findings"]} == {"structural_baseline", "hypothesis", "option_score"}
    for f in ret["findings"]:
        assert set(f) == {"ref", "kind", "title", "detail", "grade", "figure", "relates_to", "source_note"}
        assert f["grade"] in cs.GRADES
    h1 = next(f for f in ret["findings"] if f["ref"] == "H1")
    assert h1["grade"] == "indicated" and h1["relates_to"] == ["CAP-04.People", "VS-01", "RL-014"]
    option = next(f for f in ret["findings"] if f["ref"] == "option.current")
    assert "DC-1 75" in option["detail"] and "DC-4" in option["detail"] and "out of 100" in option["figure"]
    # the only ID this app mints is Hn; Compass IDs are untouched
    own = [f["ref"] for f in ret["findings"]]
    assert all(re_ok for re_ok in (r == "H1" or "." in r for r in own))
    # no names, no key, no strategy text
    dumped = json.dumps(ret)
    assert not any(n in dumped for n in NAMES) and "Who we serve" not in dumped and "sk-ant" not in dumped

    text = (await client.get("/api/v1/compass/return.txt")).text
    assert "[MERIDIAN:H1]" in text and "Relates to: MERIDIAN:CAP-04.People, MERIDIAN:VS-01, MERIDIAN:RL-014" in text
    assert "Grade: Indicated" in text and not any(n in text for n in NAMES)

    pack = (await client.get("/api/v1/export/pack")).text
    assert "MERIDIAN" in pack and "DC-1" in pack and "H1" in pack and "CAP-04.People" in pack
    assert not any(n in pack for n in NAMES)

    # grade back to suggested; new project clears the engagement
    state = (await client.put("/api/v1/compass/grades", json={"ref": "H1", "grade": None})).json()
    assert next(f for f in state["findings"] if f["ref"] == "H1")["grade"] == "hypothesis"
    await client.delete("/api/v1/org-data/clear-all")
    await _upload(client, sample_csv_path)
    fresh = (await client.get("/api/v1/compass")).json()
    assert fresh["engagement"] is None and fresh["hypotheses"] == []


@pytest.mark.asyncio
async def test_work_activity_findings_are_graded_and_exported(client: AsyncClient, monkeypatch):
    from app.services import work_activities_service
    from app.api import ai_analysis as api
    meta = {"model_requested": "m", "model_served": "m", "effort": "high", "stop_reason": "end_turn", "truncated": False}
    answer = {"executive_summary": "x",
              "activity_duplication": {"duplications": [{"activity": "Stakeholder reporting", "business_impact": "Conflicting numbers", "affected_departments": ["A", "B"]}]},
              "missing_activities": {"gaps": [{"activity": "Peak planning", "business_risk": "Overtime"}]},
              "coordination_gaps": {"gaps": [{"handoff_point": "Ramp to baggage", "from_department": "A", "to_department": "B", "evidence_class": "OBSERVABLE"}]}}
    monkeypatch.setattr(work_activities_service, "run_analysis", lambda _c, _p, max_tokens=None: (json.dumps(answer), meta))
    monkeypatch.setattr(api.claude_service, "is_configured", lambda: True)
    monkeypatch.setattr(api.claude_service, "api_key", "k", raising=False)
    csv = ("Name,Job Title,Grade,Level,Line Manager,Employee ID,Work Activities\n"
           "Ana Lee,CEO,SVP,1,Top of Org,E1,Sets strategy\nBo Lim,Analyst,AO,2,Ana Lee,E2,Reporting\n")
    await client.post("/api/v1/org-data/upload-csv", files={"file": ("org.csv", csv.encode(), "text/csv")})
    assert (await client.post("/api/v1/ai-analysis/work-activities", json={})).status_code == 200
    work = {f["ref"]: f for f in (await client.get("/api/v1/compass")).json()["findings"] if f["kind"] == "work_activity"}
    assert work["work.duplication.stakeholder-reporting"]["grade"] == "indicated"
    assert work["work.missing.peak-planning"]["grade"] == "hypothesis"
    assert work["work.handoff.ramp-to-baggage"]["grade"] == "confirmed"  # its own evidence class wins
