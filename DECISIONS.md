# Decisions Log
| Date | Decision | Why | Alternative rejected |
|---|---|---|---|
| 2024-12 | FastAPI + async SQLAlchemy + SQLite backend | Free, no server needed, fits single-user app | Cloud database (overkill, monthly cost) |
| 2024-12 | React + TypeScript + Vite + Tailwind frontend | Fast dev loop, typed API contract | Server-rendered templates (weaker interactivity) |
| 2026-07 | CSV parser tries multiple encodings (UTF-8, cp1252, latin-1) | Excel exports commonly use Windows-1252; hard failures blocked uploads | Requiring users to re-save as UTF-8 (bad UX) |
| 2026-07 | AI responses parsed with JSON-repair fallback | Long analyses occasionally truncate; repairing salvages most of the result | Failing the whole analysis on one truncated bracket |
| 2026-07 | Archetype analysis consumes and preserves work-activities analysis | Recommendations must reflect current state; previously it was overwritten | Keeping the two analyses independent (produced disconnected advice) |
| 2026-07-10 | Fixed stale salary assertions by deriving expected total from the fixture CSV | Fixture data had changed ($5.77M → $6.62M); parser was correct, tests were stale. Deriving from the file prevents future drift | Hard-coding the new number (would go stale again) |
| 2026-07-10 | Benchmarks live in `benchmarks_reference.py` with named sources, injected into prompts | Stops the AI inventing benchmark figures; updates happen in one file (McKinsey spans-by-archetype, Gallup 2025, Gartner, Deloitte 2026) | Letting the model recall benchmarks from memory (unsourced, drifts) |
| 2026-07-10 | Evidence discipline in AI prompts: OBSERVABLE/PERCEPTUAL/MODEL-INFERRED, confidence capped at Medium for purely inferred findings, disconfirming evidence required on pathologies, data_gaps section | Separates facts from interpretation; prevents anecdote-as-pattern and perceptual laundering (OD evidence-synthesis practice) | Free-form AI narrative (unauditable claims) |
| 2026-07-10 | New AI-output fields are optional in TypeScript types | Backward compatible with previously stored analyses in the DB | Required fields (would break rendering of old analyses) |
