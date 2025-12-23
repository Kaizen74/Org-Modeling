// API Types for Organizational Design Workbench

export type StatusEnum = 'pending' | 'validated' | 'rejected' | 'draft' | 'baseline' | 'active' | 'archived'
export type SourceTypeEnum = 'pptx' | 'csv' | 'excel' | 'hris_api' | 'manual'

// Project
export interface Project {
  id: string
  name: string
  client_name: string
  description?: string
  created_at: string
  updated_at?: string
  archived: boolean
  settings?: Record<string, any>
  dataset_count?: number
  scenario_count?: number
}

export interface ProjectCreate {
  name: string
  client_name: string
  description?: string
}

// Dataset
export interface Dataset {
  id: string
  project_id: string
  source_type: SourceTypeEnum
  source_filename: string
  uploaded_at: string
  validation_status: StatusEnum
  validation_errors?: ValidationError[]
  parsed_employees?: Employee[]
  parsed_relationships?: [string, string][]
}

export interface DatasetPreview {
  id: string
  source_filename: string
  total_employees: number
  total_relationships: number
  levels_detected: number
  outside_canvas_count: number
  validation_errors: ValidationError[]
  sample_employees: any[]
}

export interface ValidationError {
  error_type: string
  severity: 'error' | 'warning' | 'info'
  message: string
  affected_nodes: string[]
  suggested_fix?: string
}

// Scenario
export interface Scenario {
  id: string
  project_id: string
  name: string
  description?: string
  parent_scenario_id?: string
  status: StatusEnum
  created_at: string
  last_modified_at: string
  is_baseline: boolean
  metadata?: Record<string, any>
  employee_count?: number
}

// Employee
export interface Employee {
  id: string
  scenario_id: string
  employee_id?: string
  full_name: string
  job_title: string
  level?: number
  grade?: string
  manager_id?: string
  dotted_line_managers?: string[]
  function?: string
  department?: string
  location?: string
  cost_center?: string
  fte: number
  cost_base_salary?: number
  cost_variable?: number
  cost_benefits?: number
  cost_overhead_multiplier: number
  currency: string
  position_x?: number
  position_y?: number
  is_vacant: boolean
  is_new: boolean
  is_modified: boolean
  is_deleted: boolean
  direct_report_count?: number
}

// React Flow types for org chart
export interface OrgNode {
  id: string
  data: {
    label: string
    title: string
    level?: number
    function?: string
    location?: string
    grade?: string
    is_vacant: boolean
    is_new: boolean
    is_modified: boolean
  }
  position: {
    x: number
    y: number
  }
}

export interface OrgEdge {
  id: string
  source: string
  target: string
  type: string
}

export interface OrgTree {
  nodes: OrgNode[]
  edges: OrgEdge[]
}

// Metrics
export interface Metric {
  id: string
  scenario_id: string
  metric_type: string
  metric_category?: string
  value: number
  value_formatted?: string
  breakdown?: Record<string, any>
  benchmark_value?: number
  benchmark_source?: string
  status?: 'healthy' | 'warning' | 'critical' | 'info'
  calculated_at: string
}

export interface MetricsSummary {
  total_headcount: number
  total_fte: number
  total_cost: number
  avg_span_of_control: number
  max_layers: number
  functions: string[]
  locations: string[]
  grade_distribution: Record<string, number>
  metrics: Metric[]
}

// Analysis
export interface AnalysisResult {
  analysis_type: string
  success: boolean
  findings: Finding[]
  recommendations: Recommendation[]
  narrative?: string
  error?: string
  tokens_used: number
  generated_at: string
}

export interface Finding {
  category: string
  title: string
  description: string
  severity: 'low' | 'medium' | 'high'
  evidence: string[]
}

export interface Recommendation {
  priority: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  rationale: string
  framework_reference: string
  implementation_steps: string[]
  expected_impact: {
    cost_reduction?: string
    efficiency_gain?: string
    risk_mitigation?: string
  }
  effort: 'low' | 'medium' | 'high'
  timeline: 'immediate' | 'short-term' | 'medium-term' | 'long-term'
}

// Comparison
export interface ComparisonResult {
  baseline_id: string
  target_id: string
  metric_deltas: MetricDelta[]
  node_changes: {
    added: NodeChange[]
    removed: NodeChange[]
    modified: NodeChange[]
    moved: NodeChange[]
  }
  cost_impact: CostImpact
  summary: ComparisonSummary
  ai_narrative?: string
}

export interface MetricDelta {
  metric_type: string
  baseline_value: number
  target_value: number
  delta: number
  delta_percent: number
  direction: 'increase' | 'decrease' | 'unchanged'
  is_improvement?: boolean
}

export interface NodeChange {
  change_type: 'added' | 'removed' | 'modified' | 'moved'
  node_id: string
  node_name: string
  node_title: string
  before?: Partial<Employee>
  after?: Partial<Employee>
  changes: { field: string; before: any; after: any }[]
}

export interface CostImpact {
  baseline_total: number
  target_total: number
  delta: number
  delta_percent: number
  added_cost: number
  removed_cost: number
  modification_delta: number
  is_cost_reduction: boolean
}

export interface ComparisonSummary {
  baseline_name: string
  target_name: string
  headcount_change: number
  headcount_change_percent: number
  total_nodes_changed: number
  nodes_added: number
  nodes_removed: number
  nodes_modified: number
  nodes_moved: number
  cost_delta: number
  cost_delta_percent: number
  significant_improvements: { metric: string; delta_percent: number }[]
  significant_concerns: { metric: string; delta_percent: number }[]
}

// API Key
export interface ApiKeyConfig {
  id: string
  provider: string
  api_key_hint: string
  is_valid: boolean
  last_validated_at?: string
  total_requests: number
  total_tokens_used: number
}

export interface ApiKeyTestResult {
  is_valid: boolean
  message: string
  model_available?: string
}

// Health
export interface HealthStatus {
  status: string
  version: string
  database: string
  claude_api: string
}
