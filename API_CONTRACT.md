# API Contract
*Any change here requires updating BOTH backend and frontend in the SAME session — never leave them misaligned at a checkpoint.*
*Order when an interface changes: this file → backend → frontend types (`frontend/src/types/index.ts`) → frontend pages → tests.*

Base URL: `/api/v1` (frontend client: `frontend/src/services/api.ts`)

AI calls: all go through `backend/app/services/llm_client.py` (model `claude-opus-5-5`, effort `high`, streamed, server-side refusal fallback). Override with env vars `ORG_ANALYZER_MODEL`, `ORG_ANALYZER_EFFORT`, `ORG_ANALYZER_MAX_TOKENS`. Prompts contain job titles and aggregates only — never personal names.

## Org data
### POST /org-data/upload  (multipart: file)
Returns: `{ success, message, employee_count, manager_count, validation_errors[], metadata{} }`
Used by: Upload page (`frontend/src/pages/Upload.tsx`)

### GET /metrics/latest
Returns: `{ analysis_id, analysis_name, metrics: OrgMetrics, cached }`
`OrgMetrics` — `{ metrics_version, total_employees, manager_stats{}, span_of_control{}, cost_analysis{}, grade_gap_analysis{}, layer_analysis{}, health_indicators{}, department_analysis[], data_quality{issues[]} }`
- People are keyed by Employee ID (`employee_id`, resolved `manager_id`); names are display only
- `layer_analysis.total_layers` comes from the actual reporting chain; `declared_layers`, `level_mismatches`, `longest_chain` alongside
- `span_of_control.manager_assessments[]` judges each manager against the benchmark for their team's work type (`work_type`, `work_type_basis`, `benchmark_range`, `status`); plus `distribution_vs_benchmark`, `single_report_managers`
- `health_indicators.components[]` — four weighted parts (`key, label, score, weight, value, benchmark, rule, source`); `health_score` is their weighted average
- `department_analysis[]` — per department: headcount, managers, spans vs benchmark, layers, cost share, top titles, reports from other departments
- Every endpoint goes through `metrics_store.ensure_metrics`: missing salaries filled from the grade table; caches with an older `metrics_version` are recalculated
Used by: Dashboard, Metrics pages

### GET /metrics/summary
Returns headline figures plus `health_components[]` for the Dashboard.

## AI analysis (archetypes)
### POST /ai-analysis/analyze
Body: `{ analysis_id?, design_criteria?, strategy_text?, analysis_scope, department? }`
Returns: `{ analysis_id, analysis_name, ai_analysis: AIAnalysisResult }`
Behavior contract: preserves any existing `work_activities_analysis` inside `ai_analysis`, and passes it into the archetype prompt as current-state context.

### POST /ai-analysis/analyze-with-documents  (multipart: strategy_docs[], design_criteria?, analysis_scope, department?)
Same return + behavior contract as above.

### GET /ai-analysis/latest
Returns: `{ analysis_id, analysis_name, ai_analysis, design_criteria, created_at }`
Used by: AIAnalysis page on load.

`AIAnalysisResult` shape (TypeScript source of truth: `frontend/src/types/index.ts`):
- `executive_summary`
- `category_1_industry_trends.insights[]` — each `source` cites named research (from `backend/app/resources/benchmarks_reference.py`)
- `category_2_health_diagnosis` — `pathologies[]` carry `evidence_class` (OBSERVABLE|PERCEPTUAL|MODEL-INFERRED), `supporting_evidence`, `disconfirming_evidence`, `confidence`, `confidence_rationale`
- `category_3_strategy_alignment` — scores + key_gaps
- `category_4_recommended_archetypes` — `all_archetype_scores[]` (all 7) + `recommendations[]` (top 2, each with `score_breakdown`, `practical_examples[]`, `differentiating_activities[]`, `structure_diagram{nodes[],connections[],layout_type}`). Overall scores are computed by the backend from the breakdown with fixed weights (`scoring_weights`); the AI's own figure is `ai_overall_score`, a difference ≥3 points is `score_discrepancy`, and `ranking_note` appears when the AI's detailed picks differ from the weighted top
- `_llm` — `{ model_requested, model_served, effort, stop_reason, truncated }`; `parse_warning` when the response hit the output limit
- `action_plan{phase_1..3}`
- `data_gaps[]` — `{ gap, why_it_matters, observable_indicator_to_close }`
- `work_activities_analysis` — preserved current-state analysis (see below)

## Work activities (current state)
### POST /ai-analysis/work-activities
Body: `{ analysis_id?, industry? }`
Returns: `{ analysis_id, analysis_name, work_activities_analysis: WorkActivitiesAnalysis }`
Stored inside `ai_analysis.work_activities_analysis`; must survive subsequent archetype runs.

### GET /ai-analysis/work-activities/quick — non-AI coverage stats
### GET /ai-analysis/work-activities/latest — most recent stored analysis
Used by: Metrics page, WorkActivities page.

`WorkActivitiesAnalysis` notable fields: `activity_duplication.duplications[]` (with optional `evidence`, `confidence`, `confidence_rationale`), `missing_activities.gaps[]`, `coordination_gaps.gaps[]` (both with optional `confidence`), `departmental_coherence[]`, `work_themes`, `industry_comparison`, `recommendations`, `data_gaps[]`.

## Scenarios (Scenario Studio)
A scenario = the current upload's employees + an ordered list of design moves. Moves never change the baseline; invalid moves are skipped with a reason in `move_log`.
Move types: `reassign {person_id, new_manager_id, department?}` · `remove_role {person_id, reports_to?}` · `add_role {title, manager_id, grade?, department?, salary?, name?, count?}` · `merge_teams {from_manager_id, into_manager_id, remove_from_manager?}` · `change_role {person_id, title?, grade?, salary?, department?}` · `move_department {department, new_department}`

Evaluation shape (`ScenarioEvaluation`): `{ move_log[{index,type,status,message}], baseline{headline}, scenario{headline}, delta{headline}, departments[{department, headcount_before/after, managers_before/after, cost_before/after, average_span_before/after, status}], impact{roles_removed[], roles_added[], new_manager[], new_department[], managers_with_changed_span[], people_affected, people_affected_pct}, metrics: OrgMetrics }`
Headline keys: `headcount, managers, manager_ratio_pct, average_span, median_span, layers, total_cost, spans_within/below/above_benchmark, single_report_managers, health_score`

- `GET /scenarios` → `{ analysis_id, baseline, scenarios[{id, name, description, source, move_count, scenario, delta, skipped_moves}] }`
- `POST /scenarios` `{name, description?, moves?, clone_from?, source?}` → summary + moves + ScenarioEvaluation
- `GET /scenarios/{id}` · `PUT /scenarios/{id}` `{name?, description?, moves?}` · `DELETE /scenarios/{id}`
- `POST /scenarios/{id}/moves` (one move) · `DELETE /scenarios/{id}/moves/{index}`
- `POST /scenarios/preview` `{moves}` → ScenarioEvaluation without saving
- `GET /scenarios/move-types`
Deleting an upload or starting a new project deletes its scenarios.
Used by: Scenario Studio page (`frontend/src/pages/Scenarios.tsx`).

## Option comparison
One comparison per upload: weighted criteria + judged scores. Options = `current` + every scenario.
- `GET /comparison` → `{ criteria[], measurable{metric:{label,better}}, options[{id,name,source,description,move_count,figures,moves_summary[]}], judgments{option_id:{criterion_id:{score 1-5, rationale, source user|ai, evidence_class?, confidence?}}}, result{cells{option:{criterion:0-100|null}}, totals{}, ranking[], missing{}, complete}, ai_available }`
- `PUT /comparison/criteria` `{criteria[{id,name,kind measured|judged,weight,metric?,better?,description?}]}` (400 with reasons if invalid) · `POST /comparison/criteria/reset`
- `PUT /comparison/judgments` `{option_id, criterion_id, score 1-5|null, rationale?}`
- `POST /comparison/suggest` → AI-suggested judged scores (never overwrites `source: user`); prompt uses job titles, never names
Scoring (backend `comparison_service.score_options`): measured → 0-100 between worst and best option (ties = 100); judged 1-5 → 0-100; total = weighted average of scored criteria; missing judged scores listed.
Scenario `source` may be `archetype:<archetype_id>` to tie a scenario to a recommended archetype.
Used by: Compare page (`frontend/src/pages/Compare.tsx`).

## Optional AI-role overlay
Per job title: `disposition` automate | augment | keep_human, `capacity_freed_pct` 0-100, `rationale`, `source` user|ai. Fully optional: with no tags (or `enabled` off) every other endpoint behaves exactly as before and `ai_capacity_fte` is 0.
- `GET /ai-disposition` → `{ enabled, dispositions{}, roles[{job_title, headcount, departments[], activities[], tag?}], summary{by_disposition, tagged_roles, total_roles, tagged_people_pct, capacity_fte, capacity_cost}, ai_available }`
- `PUT /ai-disposition/role` `{job_title, disposition|null, capacity_freed_pct?, rationale?}` · `PUT /ai-disposition/enabled` `{enabled}`
- `POST /ai-disposition/suggest` `{industry?}` → AI tags for untagged roles (never overwrites user tags; titles and activities only)
Scenario headlines gain `ai_capacity_fte` (FTE freed; never changes headcount); comparison measure `ai_capacity_fte` (higher is better) is available but not in the default criteria.

## Implementation and export
- `GET /scenarios/{id}/implementation` → scenario summary + `baseline/scenario/delta/departments` + `summary{people_affected, people_affected_pct, new_manager, new_department, roles_removed, roles_added, managers_gaining, managers_losing}`, `cost{removed_roles, added_roles, net_change, note}`, `change_load{managers_gaining[], managers_losing[], new_manager[], new_department[], roles_removed[], roles_added[]}`, `risks[{severity, area, risk, mitigation}]`, `waves[{key appoint|move|remove|stabilise, title, guidance, moves[{index,message,note}]}]` — all rule-based, no AI
- `GET /export/pack?scenario_id=&include_names=false` → self-contained HTML findings pack (evidence inventory, facts, diagnosis, options, implementation of the chosen or top-ranked scenario, limits). Names replaced by job titles unless `include_names=true`.
Used by: Implementation page (`frontend/src/pages/Implementation.tsx`).

## Grades
### GET/POST /grades, POST /grades/bulk-import
Returns/accepts `GradeSalary { id, grade, median_salary, currency, display_order }`
Used by: GradeConfig page.

## Settings
### GET /settings/status → `{ configured, masked_key }`
### POST /settings/api-key → stores Anthropic API key
Used by: Settings page; AIAnalysis page checks `configured` before enabling analysis.
