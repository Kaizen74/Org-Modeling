# Project State
*Last updated: 2026-07-10 — update after EVERY increment*

## What this project is
An Organizational Design Analyzer: upload an org-structure CSV, get metrics (spans, layers, costs, health), AI-powered current-state analysis of work activities (duplication, missing activities, coordination gaps), and AI archetype recommendations (7-archetype framework) with visual structure diagrams — all in a web app (FastAPI backend + React frontend).

## Current status
All 23 backend tests pass; frontend builds clean. Evidence-grade analysis discipline (confidence, provenance, disconfirming evidence, data gaps) and research-cited benchmarks are wired into both AI analyses and displayed in the UI.

## This session (2026-07-10)
- [x] Fixed 2 stale test assertions (fixture salary total) — root-caused: fixture data changed, tests hard-coded old total; now derived from fixture
- [x] Added `backend/app/resources/benchmarks_reference.py` — sourced benchmarks (McKinsey, Gallup 2025, Gartner, Deloitte 2026) injected into AI prompts
- [x] Added evidence discipline to both AI prompts: OBSERVABLE/PERCEPTUAL/MODEL-INFERRED tagging, confidence + rationale, disconfirming evidence on pathologies, data_gaps section
- [x] Frontend aligned: new types + confidence/evidence badges on pathologies and duplications, "What the Data Can't Tell Us" section
- [x] Created run_checks.sh, PROJECT_STATE.md, DECISIONS.md, GUIDE.md, API_CONTRACT.md

## Done (all sessions)
- 2024-12: Core app — CSV parser, metrics engine, dashboard, org chart, grades config, Claude API settings
- 2026-07: Work activities analysis (duplication / missing activities / coordination gaps); archetype analysis with all-7 scoring; visual archetype diagrams (auto-layout, differentiating-activity highlighting); multi-encoding CSV support (Windows-1252 etc.); JSON-repair for truncated AI responses; archetype analysis now consumes work-activities (current-state) results and preserves them
- 2026-07-10: Evidence-grade analysis + sourced benchmarks + resilient-build state files (this session)

## Not started yet
- Optional: smoke test that boots the API and exercises one end-to-end path (upload → metrics)
- Optional: export findings pack (markdown/PDF) following facts/interpretation/recommendation structure
- Optional: dashboard hierarchy pass on Metrics page (F-pattern, 40-30-20-10 rule)

## How to resume (write this as if for a stranger)
1. The next task is: whatever the owner asks; nothing is half-done
2. The relevant files are: backend/app/services/*.py (AI logic), backend/app/resources/*.py (reference data), frontend/src/pages/AIAnalysis.tsx and Metrics.tsx (display), frontend/src/types/index.ts (API shapes)
3. Watch out for: environment resets between sessions — run `pip install -r backend/requirements.txt` and `npm install` in frontend/ if tools are missing
4. Run `./run_checks.sh` first — all should pass

## Known issues
- Backend deprecation warnings (Pydantic class-based config; pandas select_dtypes) — cosmetic, not failures
- Frontend bundle >500 kB warning from Vite — cosmetic, consider code-splitting later
