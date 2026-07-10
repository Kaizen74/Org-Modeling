# API Contract
*Any change here requires updating BOTH backend and frontend in the SAME session — never leave them misaligned at a checkpoint.*
*Order when an interface changes: this file → backend → frontend types (`frontend/src/types/index.ts`) → frontend pages → tests.*

Base URL: `/api/v1` (frontend client: `frontend/src/services/api.ts`)

## Org data
### POST /org-data/upload  (multipart: file)
Returns: `{ success, message, employee_count, manager_count, validation_errors[], metadata{} }`
Used by: Upload page (`frontend/src/pages/Upload.tsx`)

### GET /metrics/latest
Returns: `OrgMetrics` — `{ total_employees, manager_stats{}, span_of_control{}, cost_analysis{}, grade_gap_analysis{}, layer_analysis{}, health_indicators{} }`
Used by: Dashboard, Metrics pages

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
- `category_4_recommended_archetypes` — `all_archetype_scores[]` (all 7) + `recommendations[]` (top 2, each with `score_breakdown`, `practical_examples[]`, `differentiating_activities[]`, `structure_diagram{nodes[],connections[],layout_type}`)
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

## Grades
### GET/POST /grades, POST /grades/bulk-import
Returns/accepts `GradeSalary { id, grade, median_salary, currency, display_order }`
Used by: GradeConfig page.

## Settings
### GET /settings/status → `{ configured, masked_key }`
### POST /settings/api-key → stores Anthropic API key
Used by: Settings page; AIAnalysis page checks `configured` before enabling analysis.
