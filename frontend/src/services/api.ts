import axios from 'axios';
import type {
  GradeSalary,
  OrgMetrics,
  AIAnalysisResult,
  UploadResponse,
  APIKeyStatus,
  Employee,
  WorkActivitiesAnalysis,
  QuickWorkActivitiesAnalysis,
  MetricsSummary,
  DesignMove,
  ScenarioDetail,
  ScenarioEvaluation,
  ScenarioHeadline,
  ScenarioListItem,
  ComparisonCriterion,
  ComparisonPayload,
  Disposition,
  DispositionPayload,
  ImplementationPlan
} from '../types';

/** Whole organization when department is empty, otherwise one department. */
export interface AnalysisScope {
  department?: string;
}

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Settings API
export const settingsApi = {
  getStatus: async (): Promise<APIKeyStatus> => {
    const response = await api.get('/settings/claude-api-key/status');
    return response.data;
  },

  setApiKey: async (apiKey: string): Promise<{ message: string; masked_key: string }> => {
    const response = await api.post('/settings/claude-api-key', { api_key: apiKey });
    return response.data;
  },

  testConnection: async (): Promise<{ success: boolean; model: string; message: string }> => {
    const response = await api.post('/settings/claude-api-key/test');
    return response.data;
  },
};

// Grades API
export const gradesApi = {
  list: async (): Promise<GradeSalary[]> => {
    const response = await api.get('/grades/');
    return response.data;
  },

  create: async (grade: Omit<GradeSalary, 'id'>): Promise<GradeSalary> => {
    const response = await api.post('/grades/', grade);
    return response.data;
  },

  update: async (id: string, data: Partial<GradeSalary>): Promise<GradeSalary> => {
    const response = await api.put(`/grades/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/grades/${id}`);
  },

  bulkImport: async (grades: Record<string, number>, currency = 'SGD'): Promise<{ total: number }> => {
    const response = await api.post('/grades/bulk-import', { grades, currency });
    return response.data;
  },

  getOrderMap: async (): Promise<Record<string, number>> => {
    const response = await api.get('/grades/order-map');
    return response.data;
  },

  getStandardHierarchy: async (): Promise<{
    hierarchy: Array<{ seniority: string; grade: string; salary: number; order: number }>;
    seniority_levels: Array<{ name: string; grades: string[]; salary: number }>;
  }> => {
    const response = await api.get('/grades/standard-hierarchy');
    return response.data;
  },

  importStandard: async (): Promise<{ message: string; grades: string[] }> => {
    const response = await api.post('/grades/import-standard');
    return response.data;
  },

  clearAll: async (): Promise<{ message: string }> => {
    const response = await api.delete('/grades/');
    return response.data;
  },
};

// Org Data API
export const orgDataApi = {
  uploadCsv: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/org-data/upload-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getLatest: async (): Promise<{
    employees: Employee[];
    hierarchy: Record<string, unknown>;
    metadata: Record<string, unknown>;
  }> => {
    const response = await api.get('/org-data/latest');
    return response.data;
  },

  listAnalyses: async (): Promise<Array<{
    id: string;
    name: string;
    employee_count: number;
    has_metrics: boolean;
    has_ai_analysis: boolean;
    created_at: string;
  }>> => {
    const response = await api.get('/org-data/analyses');
    return response.data;
  },

  clearAll: async (): Promise<{
    success: boolean;
    message: string;
    deleted_count: number;
  }> => {
    const response = await api.delete('/org-data/clear-all');
    return response.data;
  },
};

// Metrics API
export const metricsApi = {
  calculate: async (employees: Employee[], gradeOrder?: Record<string, number>): Promise<OrgMetrics> => {
    const response = await api.post('/metrics/calculate', {
      employees,
      grade_order: gradeOrder,
    });
    return response.data;
  },

  getLatest: async (forceRecalculate = false): Promise<{
    analysis_id: string;
    analysis_name: string;
    metrics: OrgMetrics;
    cached: boolean;
  }> => {
    const response = await api.get('/metrics/latest', {
      params: { force_recalculate: forceRecalculate }
    });
    return response.data;
  },

  recalculate: async (): Promise<{
    analysis_id: string;
    analysis_name: string;
    metrics: OrgMetrics;
    grade_order_used: Record<string, number>;
    message: string;
  }> => {
    const response = await api.post('/metrics/recalculate');
    return response.data;
  },

  getSummary: async (): Promise<MetricsSummary> => {
    const response = await api.get('/metrics/summary');
    return response.data;
  },
};

// AI Analysis API
export const aiAnalysisApi = {
  analyze: async (analysisId?: string, designCriteria?: string, strategyText?: string, scope?: AnalysisScope): Promise<{
    analysis_id: string;
    ai_analysis: AIAnalysisResult;
  }> => {
    const response = await api.post('/ai-analysis/analyze', {
      analysis_id: analysisId,
      design_criteria: designCriteria,
      strategy_text: strategyText,
      analysis_scope: scope?.department ? 'department' : 'organization',
      department: scope?.department,
    });
    return response.data;
  },

  analyzeWithDocuments: async (
    files: File[],
    designCriteria?: string,
    analysisId?: string,
    scope?: AnalysisScope
  ): Promise<{
    analysis_id: string;
    ai_analysis: AIAnalysisResult;
  }> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('strategy_docs', file);
    });
    if (designCriteria) {
      formData.append('design_criteria', designCriteria);
    }
    if (analysisId) {
      formData.append('analysis_id', analysisId);
    }
    if (scope?.department) {
      formData.append('analysis_scope', 'department');
      formData.append('department', scope.department);
    }
    const response = await api.post('/ai-analysis/analyze-with-documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getQuickAnalysis: async (): Promise<{
    analysis_id: string;
    quick_insights: Array<{
      type: string;
      category: string;
      message: string;
      recommendation: string;
    }>;
    health_score: number;
    health_grade: string;
    warnings: string[];
    recommendations: string[];
  }> => {
    const response = await api.get('/ai-analysis/quick-analysis');
    return response.data;
  },

  getLatest: async (): Promise<{
    analysis_id: string;
    analysis_name: string;
    ai_analysis: AIAnalysisResult;
    created_at: string;
  }> => {
    const response = await api.get('/ai-analysis/latest');
    return response.data;
  },

  // Work Activities Analysis
  analyzeWorkActivities: async (industry?: string, analysisId?: string): Promise<{
    analysis_id: string;
    analysis_name: string;
    work_activities_analysis: WorkActivitiesAnalysis;
  }> => {
    const response = await api.post('/ai-analysis/work-activities', {
      analysis_id: analysisId,
      industry: industry,
    });
    return response.data;
  },

  getQuickWorkActivities: async (): Promise<{
    analysis_id: string;
    analysis_name: string;
  } & QuickWorkActivitiesAnalysis> => {
    const response = await api.get('/ai-analysis/work-activities/quick');
    return response.data;
  },

  getLatestWorkActivities: async (): Promise<{
    analysis_id: string;
    analysis_name: string;
    work_activities_analysis: WorkActivitiesAnalysis;
    created_at: string;
  }> => {
    const response = await api.get('/ai-analysis/work-activities/latest');
    return response.data;
  },
};

export default api;

// Scenario Studio API
export const scenariosApi = {
  list: async (): Promise<{ analysis_id: string; baseline: ScenarioHeadline; scenarios: ScenarioListItem[] }> =>
    (await api.get('/scenarios')).data,
  create: async (name: string, opts: { description?: string; moves?: DesignMove[]; cloneFrom?: string; source?: string } = {}): Promise<ScenarioDetail> =>
    (await api.post('/scenarios', { name, description: opts.description, moves: opts.moves ?? [], clone_from: opts.cloneFrom, source: opts.source ?? 'manual' })).data,
  get: async (id: string): Promise<ScenarioDetail> => (await api.get(`/scenarios/${id}`)).data,
  update: async (id: string, changes: { name?: string; description?: string; moves?: DesignMove[] }): Promise<ScenarioDetail> =>
    (await api.put(`/scenarios/${id}`, changes)).data,
  addMove: async (id: string, move: DesignMove): Promise<ScenarioDetail> => (await api.post(`/scenarios/${id}/moves`, move)).data,
  removeMove: async (id: string, index: number): Promise<ScenarioDetail> => (await api.delete(`/scenarios/${id}/moves/${index}`)).data,
  remove: async (id: string): Promise<void> => { await api.delete(`/scenarios/${id}`); },
  preview: async (moves: DesignMove[]): Promise<ScenarioEvaluation> => (await api.post('/scenarios/preview', { moves })).data,
  implementation: async (id: string): Promise<ImplementationPlan> => (await api.get(`/scenarios/${id}/implementation`)).data,
};

/** URL of the board-ready findings pack (opens in a new tab; print to PDF from there). */
export const packUrl = (scenarioId?: string, includeNames = false) => {
  const q = new URLSearchParams();
  if (scenarioId) q.set('scenario_id', scenarioId);
  if (includeNames) q.set('include_names', 'true');
  return `/api/v1/export/pack${q.toString() ? `?${q}` : ''}`;
};

// Option comparison API
export const comparisonApi = {
  get: async (): Promise<ComparisonPayload> => (await api.get('/comparison')).data,
  saveCriteria: async (criteria: ComparisonCriterion[]): Promise<ComparisonPayload> =>
    (await api.put('/comparison/criteria', { criteria })).data,
  resetCriteria: async (): Promise<ComparisonPayload> => (await api.post('/comparison/criteria/reset')).data,
  judge: async (optionId: string, criterionId: string, score: number | null, rationale?: string): Promise<ComparisonPayload> =>
    (await api.put('/comparison/judgments', { option_id: optionId, criterion_id: criterionId, score, rationale })).data,
  suggest: async (): Promise<ComparisonPayload> => (await api.post('/comparison/suggest')).data,
};

// Optional AI-role overlay API
export const aiDispositionApi = {
  get: async (): Promise<DispositionPayload> => (await api.get('/ai-disposition')).data,
  setEnabled: async (enabled: boolean): Promise<DispositionPayload> => (await api.put('/ai-disposition/enabled', { enabled })).data,
  tag: async (jobTitle: string, disposition: Disposition | null, capacityFreedPct?: number, rationale?: string): Promise<DispositionPayload> =>
    (await api.put('/ai-disposition/role', { job_title: jobTitle, disposition, capacity_freed_pct: capacityFreedPct, rationale })).data,
  suggest: async (industry?: string): Promise<DispositionPayload> => (await api.post('/ai-disposition/suggest', { industry })).data,
};
