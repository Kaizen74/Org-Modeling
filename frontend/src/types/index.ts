// API Types

export interface Employee {
  name: string;
  job_title: string;
  grade: string;
  department: string;
  level: number;
  manager_name: string;
  salary: number;
  employee_id: string;
  work_activities?: string;
  job_description?: string;
}

export interface GradeSalary {
  id: string;
  grade: string;
  median_salary: number;
  currency: string;
  display_order: number;
}

export interface ManagerStats {
  total_managers: number;
  total_ics: number;
  manager_ratio_pct: number;
  ic_ratio_pct: number;
}

export interface ManagerSpanAssessment {
  manager_id: string;
  manager: string;
  job_title: string;
  department: string;
  span: number;
  work_type: 'knowledge' | 'operational';
  work_type_basis: string;
  benchmark_range: [number, number];
  status: 'below' | 'within' | 'above';
}

export interface SpanOfControl {
  average_span: number;
  median_span: number;
  min_span: number;
  max_span: number;
  distribution: Record<string, number>;
  distribution_pct: Record<string, number>;
  manager_assessments?: ManagerSpanAssessment[];
  distribution_vs_benchmark?: Record<'Below benchmark' | 'Within benchmark' | 'Above benchmark', number>;
  single_report_managers?: number;
}

export interface CostAnalysis {
  total_cost: number;
  average_cost_per_employee: number;
  by_level?: Record<string, { count: number; total_cost: number }>;
  by_grade?: Record<string, { count: number; total_cost: number }>;
}

export interface GradeGapAnalysis {
  average_grade_gap: number;
  min_gap: number;
  max_gap: number;
  total_comparisons: number;
}

export interface LayerAnalysis {
  total_layers: number; // from the actual reporting chain
  declared_layers?: number; // highest value in the CSV Level column
  by_level: Record<string, { count: number }>;
  level_mismatches?: {
    count: number;
    examples: Array<{ name: string; declared_level: number; actual_layer: number }>;
  };
  longest_chain?: string[];
}

export interface HealthComponent {
  key: 'span_fit' | 'layers' | 'manager_ratio' | 'single_report';
  label: string;
  score: number;
  weight: number;
  value: string;
  benchmark: string;
  rule: string;
  source: string;
}

export interface HealthIndicators {
  health_score: number;
  health_grade: string;
  components?: HealthComponent[];
  warnings: string[];
  recommendations: string[];
  is_healthy: boolean;
}

export interface DepartmentMetrics {
  department: string;
  headcount: number;
  headcount_pct: number;
  managers: number;
  manager_ratio_pct: number;
  average_span: number;
  median_span: number;
  layers_spanned: number[]; // [top layer, bottom layer]
  layer_count: number;
  total_cost: number;
  cost_pct: number;
  average_cost: number;
  spans_vs_benchmark: { below: number; within: number; above: number };
  operational_teams: number;
  single_report_managers: number;
  reports_from_other_departments: number;
  top_titles: Array<{ title: string; count: number }>;
}

// Which model produced an AI result, and whether it was cut off
export interface LLMCallMeta {
  model_requested: string;
  model_served: string;
  effort: string;
  stop_reason: string;
  truncated: boolean;
}

export interface MetricsSummary {
  total_employees: number;
  total_managers: number;
  manager_ratio: number;
  average_span: number;
  average_grade_gap: number;
  total_cost: number;
  layers: number;
  health_score: number;
  health_grade: string;
  health_components?: HealthComponent[];
  warnings: string[];
  recommendations?: string[];
  departments?: number;
  data_issues?: string[];
}

export interface OrgMetrics {
  total_employees: number;
  manager_stats: ManagerStats;
  span_of_control: SpanOfControl;
  cost_analysis: CostAnalysis;
  grade_gap_analysis: GradeGapAnalysis;
  layer_analysis: LayerAnalysis;
  health_indicators: HealthIndicators;
  data_quality?: { issues: string[] };
  department_analysis?: DepartmentMetrics[];
  metrics_version?: number;
}

// Key gap can be a string or an object with detailed info
export type KeyGap = string | {
  gap: string;
  strategy_reference?: string;
  structural_impact?: string;
};

// Evidence discipline types (facts vs interpretation, provenance, confidence)
export type EvidenceClass = 'OBSERVABLE' | 'PERCEPTUAL' | 'MODEL-INFERRED';

// The five diagnostic dimensions findings are tagged with
export const FIVE_DIMENSIONS = [
  'Structure & Accountabilities',
  'People & Skills',
  'Process & Systems',
  'Mindset & Behaviors',
  'Leadership',
] as const;

export interface DimensionTag {
  dimension?: string;
  indicator_type?: 'Leading' | 'Lagging' | string;
}

export interface DataGap {
  gap: string;
  why_it_matters?: string;
  observable_indicator_to_close?: string;
}

// Practical example for archetype
export interface PracticalExample {
  company_or_scenario: string;
  description: string;
  key_success_factors: string;
  relevance_to_your_org: string;
}

// Archetype Structure Diagram Types
export type DiagramLayoutType = 'hierarchical' | 'matrix' | 'network' | 'hub_spoke' | 'circular';

export type DiagramNodeType = 'executive' | 'department' | 'team' | 'role' | 'external' | 'shared_service';

export type DiagramConnectionType = 'reporting' | 'coordination' | 'advisory' | 'service' | 'dotted_line';

export interface DiagramNode {
  id: string;
  label: string;
  type: DiagramNodeType;
  description?: string;
  is_differentiating?: boolean;
  differentiating_activity?: string;
  x?: number;
  y?: number;
  level?: number;
}

export interface DiagramConnection {
  from: string;
  to: string;
  type: DiagramConnectionType;
  label?: string;
}

export interface StructureDiagram {
  title: string;
  layout_type: DiagramLayoutType;
  nodes: DiagramNode[];
  connections: DiagramConnection[];
  legend?: string;
}

// Differentiating Activity for competitive advantage
export interface DifferentiatingActivity {
  activity: string;
  description: string;
  why_differentiating: string;
  how_archetype_supports: string;
  strategic_importance: 'High' | 'Medium' | 'Low';
  related_roles: string[];
}

// Score breakdown for individual criteria
export interface ScoreBreakdown {
  industry_match: number | { score: number; rationale: string };
  size_match: number | { score: number; rationale: string };
  revenue_model_match: number | { score: number; rationale: string };
  key_indicators_match: number | { score: number; rationale: string };
  metrics_match: number | { score: number; rationale: string };
}

// Summary score for all archetypes
export interface ArchetypeScoreSummary {
  archetype_id: string;
  archetype_name: string;
  overall_score: number;
  score_breakdown: {
    industry_match: number;
    size_match: number;
    revenue_model_match: number;
    key_indicators_match: number;
    metrics_match: number;
  };
  fit_summary: string;
  digital_first_applicable: boolean;
  // Set by the backend: overall_score is computed from the breakdown with the published weights
  ai_overall_score?: number;
  score_discrepancy?: number;
  scoring_method?: 'weighted' | 'ai_reported';
  weighted_rank?: number;
}

// Archetype recommendation
export interface ArchetypeRecommendation {
  rank?: number;
  archetype_id?: string;
  archetype: string;
  overall_fit_score?: number;
  business_model_match_score?: number; // Legacy field
  score_breakdown?: ScoreBreakdown;
  why_it_fits: string;
  expected_benefits: string[];
  implementation_challenges: string[];
  transformation_timeline: string;
  confidence_level: string;
  confidence_rationale?: string;
  critical_success_factors: string[];
  warning_signs_to_monitor?: string[];
  design_criteria_addressed?: string[];
  practical_examples?: PracticalExample[];
  differentiating_activities?: DifferentiatingActivity[];
  structure_diagram?: StructureDiagram;
  ai_overall_score?: number;
  score_discrepancy?: number;
  scoring_method?: 'weighted' | 'ai_reported';
}

// Category 4 can be an array (old format) or object with recommendations (new format)
export type Category4Archetypes = ArchetypeRecommendation[] | {
  design_criteria_analyzed?: string;
  analysis_scope?: string;
  department_analyzed?: string;
  all_archetype_scores?: ArchetypeScoreSummary[];
  recommendations: ArchetypeRecommendation[];
  ranking_note?: string;
  scoring_weights?: Record<string, number>;
};

export interface AIAnalysisResult {
  executive_summary?: string;
  category_1_industry_trends?: {
    insights: Array<{
      topic: string;
      finding: string;
      source: string;
      relevance_to_org: string;
    }>;
  };
  category_2_health_diagnosis?: {
    strengths: string[];
    weaknesses: string[];
    pathologies: Array<{
      name: string;
      description: string;
      impact: string;
      severity: string;
      dimension?: string;
      evidence_class?: EvidenceClass;
      supporting_evidence?: string;
      disconfirming_evidence?: string;
      confidence?: string;
      confidence_rationale?: string;
    }>;
    critical_risks: string[];
  };
  category_3_strategy_alignment?: {
    strategy_documents_analyzed?: string;
    scores: {
      strategic_clarity: { score: number; rationale: string; supporting_evidence?: string };
      execution_readiness: { score: number; rationale: string; supporting_evidence?: string };
      efficiency: { score: number; rationale: string; supporting_evidence?: string };
      agility: { score: number; rationale: string; supporting_evidence?: string };
    };
    overall_alignment_score: number;
    alignment_grade: string;
    key_gaps: KeyGap[];
    alignment_strengths?: string[];
  };
  category_4_recommended_archetypes?: Category4Archetypes;
  action_plan?: {
    phase_1_quick_wins: string[];
    phase_2_structural: string[];
    phase_3_optimization: string[];
  };
  data_gaps?: DataGap[];
  _llm?: LLMCallMeta;
  parse_warning?: string;
  error?: string;
  raw_response?: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  employee_count: number;
  manager_count: number;
  validation_errors: string[];
  metadata: Record<string, unknown>;
}

export interface APIKeyStatus {
  configured: boolean;
  masked_key: string | null;
}

// Work Activities Analysis Types

// Activity Duplication Types
export interface ActivityDuplication extends DimensionTag {
  activity: string;
  affected_roles: string[];
  affected_departments: string[];
  duplication_type: string;
  severity: string;
  business_impact: string;
  resolution_priority: number;
  recommended_action: string;
  evidence?: string;
  confidence?: string;
  confidence_rationale?: string;
}

export interface ActivityDuplicationAnalysis {
  overall_duplication_score: number;
  severity_assessment: string;
  duplications: ActivityDuplication[];
  summary: string;
}

// Missing Activities Types
export interface MissingActivity extends DimensionTag {
  activity: string;
  industry_benchmark: string;
  affected_roles: string[];
  affected_departments: string[];
  severity: string;
  business_risk: string;
  recommendation: string;
  confidence?: string;
  confidence_rationale?: string;
}

export interface MissingActivitiesAnalysis {
  overall_gap_score: number;
  severity_assessment: string;
  gaps: MissingActivity[];
  summary: string;
}

// Coordination Gaps Types
export interface CoordinationGap extends DimensionTag {
  handoff_point: string;
  from_department: string;
  to_department: string;
  from_roles: string[];
  to_roles: string[];
  current_state: string;
  gap_type: string;
  severity: string;
  industry_practice: string;
  recommended_interface: string;
  confidence?: string;
  confidence_rationale?: string;
}

export interface CoordinationGapsAnalysis {
  overall_coordination_score: number;
  severity_assessment: string;
  gaps: CoordinationGap[];
  summary: string;
}

export interface DepartmentCoherence {
  department: string;
  position_count: number;
  coherence_score: number;
  coherence_rationale: string;
  synergy_assessment: {
    strengths: string[];
    gaps: string[];
    overlaps: string[];
  };
  value_chain_position: string;
  internal_dependencies?: string;
  key_activities: string[];
}

export interface WorkTheme {
  theme: string;
  description: string;
  departments_involved: string[];
  position_count: number;
  percentage_of_org: number;
  strategic_importance: string;
}

export interface EmergingActivity {
  activity: string;
  industry_prevalence: string;
  present_in_org: boolean;
  recommendation: string;
}

export interface StructuralRecommendation {
  recommendation: string;
  rationale?: string;
  addresses?: string;
  impact?: string;
  effort?: string;
  priority?: string;
  affected_departments?: string[];
}

export interface RoleOptimization {
  current_role: string;
  recommendation: string;
  rationale: string;
}

export interface CapabilityDevelopment {
  capability: string;
  current_state: string;
  target_state: string;
  priority: string;
}

export interface WorkActivitiesAnalysis {
  work_activities_summary?: {
    total_positions_analyzed: number;
    departments_analyzed: number;
    positions_with_activities: number;
    industry_context: string;
  };
  // New Analysis Areas
  activity_duplication?: ActivityDuplicationAnalysis;
  missing_activities?: MissingActivitiesAnalysis;
  coordination_gaps?: CoordinationGapsAnalysis;
  // Existing Analysis Areas
  departmental_coherence?: DepartmentCoherence[];
  overall_coherence?: {
    organization_coherence_score: number;
    cross_department_synergies: string[];
    cross_department_gaps: string[];
    integration_assessment: string;
  };
  work_themes?: {
    primary_themes: WorkTheme[];
    theme_distribution_assessment: string;
    strategic_alignment_score: number;
    missing_capabilities: string[];
  };
  industry_comparison?: {
    industry_identified: string;
    activity_mix_assessment: {
      alignment_score: number;
      over_represented: string[];
      under_represented: string[];
      unique_strengths: string[];
    };
    role_specialization?: {
      assessment: string;
      rationale: string;
    };
    emerging_industry_activities?: EmergingActivity[];
    competitive_positioning?: {
      potential_advantages: string[];
      potential_disadvantages: string[];
      overall_assessment: string;
    };
  };
  recommendations?: {
    duplication_resolution?: StructuralRecommendation[];
    missing_activity_additions?: StructuralRecommendation[];
    coordination_improvements?: StructuralRecommendation[];
    structural?: StructuralRecommendation[];
    role_optimization?: RoleOptimization[];
    capability_development?: CapabilityDevelopment[];
    quick_wins?: string[];
  };
  executive_summary?: string;
  data_gaps?: DataGap[];
  error?: string;
  message?: string;
  _json_repaired?: boolean;
  parse_warning?: string;
  _llm?: LLMCallMeta;
}

export interface QuickWorkActivitiesAnalysis {
  total_employees: number;
  employees_with_work_activities: number;
  coverage_percentage: number;
  departments_with_activities: number;
  department_breakdown: Array<{
    department: string;
    positions_with_activities: number;
    sample_activities: string[];
  }>;
  potential_duplications_detected?: number;
  potential_duplications?: Array<{
    keyword: string;
    roles_count: number;
    roles: string[];
  }>;
  status: string;
}
