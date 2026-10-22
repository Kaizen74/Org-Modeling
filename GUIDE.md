# Organizational Design Analyzer — Owner's Guide
*Updated: 2026-10-22*

## What this app does
You upload a spreadsheet (CSV) of your organization — names, job titles, grades, who reports to whom, salaries, and optionally each role's work activities. The app then:
1. Calculates the health of your structure: how many people each manager supervises, how many layers exist, what it all costs
2. Uses AI to analyze the current state of work: duplicated activities across roles, activities missing versus industry practice, and weak handoffs between departments
3. Recommends the two best-fitting organizational structures (from seven research-based archetypes), with a visual diagram of each, informed by the current-state findings and your strategy
4. Tells you how confident each finding is, what evidence supports it, and what your data cannot show — so you know what to verify before acting

## How to start it (click by click)
1. Open a terminal in the project folder
2. Start the backend: `cd backend && uvicorn app.main:app --reload` — you'll know it worked when you see "Uvicorn running on http://127.0.0.1:8000"
3. In a second terminal, start the frontend: `cd frontend && npm run dev` — you'll know it worked when you see a local address like http://localhost:5173
4. Open your browser to that address

## How to use it
1. **Settings** — paste your Anthropic API key (needed for all AI analysis)
2. **Grade Config** — enter your salary grades so costs can be calculated
3. **Upload** — upload your org CSV (required: Name, Job Title, Grade, Level, Line Manager; recommended: Employee ID, Department, Salary; optional: Line Manager ID, Work Type, Work Activities, Job Description). Give everyone a unique Employee ID — people who share a name are then kept apart. If two managers share a name, add a Line Manager ID column. Work Type ("Operational" or "Knowledge") lets you state which span benchmark applies instead of letting the app infer it from job titles
4. **Metrics** — see spans, layers, costs, and run the Work Activities analysis (current state)
5. **AI Analysis** — add your design criteria and strategy (text or documents), then run the archetype analysis. Read the confidence badges: findings marked "Inferred from research" come from industry knowledge, not your data
6. **What the Data Can't Tell Us** — at the bottom of the AI analysis; lists what to measure next to firm up the findings

## How to check everything still works
Type `./run_checks.sh` and press Enter. You want to see "ALL CHECKS PASSED ✅". It runs the automated tests, checks and builds the screens, then opens the app in a hidden browser and confirms the main pages load with a sample org. If anything is red, stop and fix before trusting new changes.

## What changed recently
- 2026-10-22: New look matching the OrgDesign Playbook, with the menu laid out as the engagement flow (01 Diagnose, 02 Design). The Overview leads with the health score and what drives it. Structure lists every manager against the right benchmark and compares departments side by side. The org chart opens two layers deep, colours by department / span / cost / grade, and flags managers with a single report. Work Activities now holds the whole current-state analysis, with each finding tagged by your five dimensions
- 2026-10-22: Accuracy fixes. People who share a name are no longer merged. Layers are counted from who actually reports to whom (your Level column is checked against it). Each manager's span is judged against the right benchmark for their team's kind of work (frontline 15–25, knowledge work 5–10). The health score now shows its four parts and how each is calculated. Archetype scores are calculated from the stated weights rather than taken from the AI. The AI now sees your departments and roles (never names) and uses the current Claude model. The previous AI setup would have stopped working from 21 Oct 2026, because a setting it sent is no longer accepted
- 2026-07-10: Analysis findings now carry confidence levels, the evidence behind them, and counter-evidence where a pattern only half-fits. Benchmarks quoted in the analysis now come from named research (McKinsey, Gallup, Gartner, Deloitte) instead of the AI's memory. A new "What the Data Can't Tell Us" section lists the measurements that would strengthen the analysis. Two long-failing tests were fixed — the full check suite is green for the first time
- 2026-07: Archetype diagrams no longer overlap or truncate; archetype recommendations now use the current-state (work activities) findings

## If something goes wrong
- CSV won't upload → make sure the required columns exist; the app accepts Excel's default encoding
- AI analysis shows an error about API key → set the key in Settings
- Analysis output looks cut off → run the analysis again (long responses are auto-repaired, but a retry gives a clean result)
- To stop the app: press Ctrl+C in each terminal

## Glossary
- **Span of control**: how many people report directly to one manager
- **Layers**: the number of reporting levels from top to bottom
- **Archetype**: a research-based template for how organizations can be structured (e.g., Functional, Front-Back Hybrid)
- **Observable evidence**: something counted directly from your uploaded data
- **Model-inferred**: something the AI knows from industry research, not from your data — treat as hypothesis to verify
