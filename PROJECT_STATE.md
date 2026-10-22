# Project State
*Last updated: 2026-10-22 — update after EVERY increment*

## What this project is
An Organizational Design Analyzer for an OD practitioner: upload an org-structure CSV, diagnose the current state (spans, layers, costs, health, work activities), ideate and compare potential structures (7-archetype framework, scenarios) against the business strategy, and surface implementation implications — in a web app (FastAPI backend + React frontend) styled after the owner's OrgDesign Playbook.

## Current status
Owner approved the 5-phase plan on 2026-10-22. Phase 1 in progress — P1.1 done (36/36 tests).

## This session (2026-10-22) — approved plan, in order
Phase 1 — Accuracy fixes
- [x] P1.1 Key people by Employee ID, not name (duplicate names no longer merge)
- [ ] P1.2 Compute layers from the actual reporting chain; flag Level-column mismatches
- [ ] P1.3 Role-aware span benchmarks + transparent health score
- [ ] P1.4 Deterministic weighted archetype scoring (code applies the 30/15/20/25/10 weights)
- [ ] P1.5 Org composition in AI prompts; remove employee names from AI calls; one model setting
Phase 2 — Current-state depth (visual foundation first so new screens are built in the Playbook style)
- [ ] P2.0 Playbook visual foundation: tokens, fonts, app shell, shared UI pieces
- [ ] P2.1 Department-level metrics + department scope in AI analysis
- [ ] P2.2 Org chart with span/cost/department overlays and layer-removal flags
- [ ] P2.3 One Work Activities page + findings tagged by the five dimensions
Phase 3 — Scenario Studio
- [ ] P3.1 Scenario engine (design moves → metric deltas)
- [ ] P3.2 Scenario Studio screen
- [ ] P3.3 Option comparison matrix vs weighted design criteria
- [ ] P3.4 Archetype diagrams using the organization's real units
- [ ] P3.5 Optional AI-disposition tagging (automate / augment / keep human) — never blocks the workflow
Phase 4
- [ ] P4 Implementation implications view + board-ready export pack
Phase 5
- [ ] P5 Restyle remaining pages in the Playbook style

## Done (all sessions)
- 2024-12: Core app — CSV parser, metrics engine, dashboard, org chart, grades config, Claude API settings
- 2026-07: Work activities analysis (duplication / missing activities / coordination gaps); archetype analysis with all-7 scoring; visual archetype diagrams; multi-encoding CSV support; JSON-repair for truncated AI responses; archetype analysis consumes and preserves work-activities results
- 2026-07-10: Evidence-grade analysis + sourced benchmarks + resilient-build state files + AI pipeline mock tests

## How to resume (write this as if for a stranger)
1. The next task is: the first unchecked item above
2. The relevant files are: backend/app/parsers/csv_parser.py, backend/app/services/metrics_service.py, backend/app/services/ai_analysis_service.py, frontend/src/pages/*.tsx, frontend/src/types/index.ts
3. Watch out for: in this container `pip` installs into a different Python than the app uses — always install with `python -m pip install -r backend/requirements.txt`; run `npm install` in frontend/ if node_modules is missing
4. Run `./run_checks.sh` first — all should pass

## Known issues
- Backend deprecation warnings (Pydantic class-based config; pandas select_dtypes) — cosmetic, not failures
- Frontend bundle >500 kB warning from Vite — cosmetic, consider code-splitting later
