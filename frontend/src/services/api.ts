import axios from 'axios';
import type {
  GradeSalary,
  OrgMetrics,
  AIAnalysisResult,
  UploadResponse,
  APIKeyStatus,
  Employee,
  WorkActivitiesAnalysis,
  QuickWorkActivitiesAnalysis
} from '../types';

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

  getSummary: async (): Promise<{
    total_employees: number;
    total_managers: number;
    manager_ratio: number;
    average_span: number;
    average_grade_gap: number;
    total_cost: number;
    layers: number;
    health_score: number;
    health_grade: string;
    warnings: string[];
  }> => {
    const response = await api.get('/metrics/summary');
    return response.data;
  },
};

// AI Analysis API
export const aiAnalysisApi = {
  analyze: async (analysisId?: string, designCriteria?: string, strategyText?: string): Promise<{
    analysis_id: string;
    ai_analysis: AIAnalysisResult;
  }> => {
    const response = await api.post('/ai-analysis/analyze', {
      analysis_id: analysisId,
      design_criteria: designCriteria,
      strategy_text: strategyText,
    });
    return response.data;
  },

  analyzeWithDocuments: async (
    files: File[],
    designCriteria?: string,
    analysisId?: string
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
