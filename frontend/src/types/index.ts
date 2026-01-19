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

export interface SpanOfControl {
  average_span: number;
  median_span: number;
  min_span: number;
  max_span: number;
  distribution: Record<string, number>;
  distribution_pct: Record<string, number>;
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
  total_layers: number;
  by_level: Record<string, { count: number }>;
}

export interface HealthIndicators {
  health_score: number;
  health_grade: string;
  warnings: string[];
  recommendations: string[];
  is_healthy: boolean;
}

export interface OrgMetrics {
  total_employees: number;
  manager_stats: ManagerStats;
  span_of_control: SpanOfControl;
  cost_analysis: CostAnalysis;
  grade_gap_analysis: GradeGapAnalysis;
  layer_analysis: LayerAnalysis;
  health_indicators: HealthIndicators;
}

// Key gap can be a string or an object with detailed info
export type KeyGap = string | {
  gap: string;
  strategy_reference?: string;
  structural_impact?: string;
};

// Archetype recommendation
export interface ArchetypeRecommendation {
  archetype: string;
  business_model_match_score: number;
  why_it_fits: string;
  expected_benefits: string[];
  implementation_challenges: string[];
  transformation_timeline: string;
  confidence_level: string;
  critical_success_factors: string[];
  design_criteria_addressed?: string[];
}

// Category 4 can be an array (old format) or object with recommendations (new format)
export type Category4Archetypes = ArchetypeRecommendation[] | {
  design_criteria_analyzed?: string;
  recommendations: ArchetypeRecommendation[];
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
