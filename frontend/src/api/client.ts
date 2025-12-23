import axios, { AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth tokens (future use)
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token')
    }
    return Promise.reject(error)
  }
)

// API Functions

// Health
export const checkHealth = async () => {
  const response = await apiClient.get('/health')
  return response.data
}

// Projects
export const getProjects = async (archived = false, search?: string) => {
  const params = new URLSearchParams()
  params.set('archived', String(archived))
  if (search) params.set('search', search)
  const response = await apiClient.get(`/projects?${params}`)
  return response.data
}

export const getProject = async (projectId: string) => {
  const response = await apiClient.get(`/projects/${projectId}`)
  return response.data
}

export const createProject = async (data: { name: string; client_name: string; description?: string }) => {
  const response = await apiClient.post('/projects', data)
  return response.data
}

export const updateProject = async (projectId: string, data: Partial<{ name: string; client_name: string; description: string; archived: boolean }>) => {
  const response = await apiClient.patch(`/projects/${projectId}`, data)
  return response.data
}

export const deleteProject = async (projectId: string) => {
  const response = await apiClient.delete(`/projects/${projectId}`)
  return response.data
}

// Datasets
export const uploadDataset = async (projectId: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post(`/projects/${projectId}/datasets`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const getDataset = async (datasetId: string) => {
  const response = await apiClient.get(`/datasets/${datasetId}`)
  return response.data
}

export const getDatasetPreview = async (datasetId: string) => {
  const response = await apiClient.get(`/datasets/${datasetId}/preview`)
  return response.data
}

export const validateDataset = async (datasetId: string) => {
  const response = await apiClient.post(`/datasets/${datasetId}/validate`)
  return response.data
}

export const applyCorrections = async (datasetId: string, corrections: any[]) => {
  const response = await apiClient.patch(`/datasets/${datasetId}/corrections`, { corrections })
  return response.data
}

export const publishDataset = async (datasetId: string, scenarioName: string, description?: string, isBaseline = false) => {
  const formData = new FormData()
  formData.append('scenario_name', scenarioName)
  if (description) formData.append('scenario_description', description)
  formData.append('is_baseline', String(isBaseline))
  const response = await apiClient.post(`/datasets/${datasetId}/publish`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// Scenarios
export const getScenarios = async (projectId: string, status?: string) => {
  const params = status ? `?status=${status}` : ''
  const response = await apiClient.get(`/projects/${projectId}/scenarios${params}`)
  return response.data
}

export const getScenario = async (scenarioId: string) => {
  const response = await apiClient.get(`/scenarios/${scenarioId}`)
  return response.data
}

export const createScenario = async (projectId: string, data: { name: string; description?: string; is_baseline?: boolean }) => {
  const response = await apiClient.post(`/projects/${projectId}/scenarios`, data)
  return response.data
}

export const cloneScenario = async (scenarioId: string, newName: string, description?: string) => {
  const response = await apiClient.post(`/scenarios/${scenarioId}/clone`, {
    new_name: newName,
    description,
  })
  return response.data
}

export const getScenarioEmployees = async (scenarioId: string) => {
  const response = await apiClient.get(`/scenarios/${scenarioId}/employees`)
  return response.data
}

export const getScenarioTree = async (scenarioId: string) => {
  const response = await apiClient.get(`/scenarios/${scenarioId}/tree`)
  return response.data
}

// Employees
export const createEmployee = async (scenarioId: string, data: any) => {
  const response = await apiClient.post(`/scenarios/${scenarioId}/employees`, data)
  return response.data
}

export const updateEmployee = async (scenarioId: string, employeeId: string, data: any) => {
  const response = await apiClient.patch(`/scenarios/${scenarioId}/employees/${employeeId}`, data)
  return response.data
}

export const deleteEmployee = async (scenarioId: string, employeeId: string) => {
  const response = await apiClient.delete(`/scenarios/${scenarioId}/employees/${employeeId}`)
  return response.data
}

// Metrics
export const calculateMetrics = async (scenarioId: string) => {
  const response = await apiClient.post(`/scenarios/${scenarioId}/calculate-metrics`)
  return response.data
}

export const getMetrics = async (scenarioId: string) => {
  const response = await apiClient.get(`/scenarios/${scenarioId}/metrics`)
  return response.data
}

// Analysis
export const analyzeScenario = async (scenarioId: string, apiKey?: string) => {
  const params = apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ''
  const response = await apiClient.post(`/scenarios/${scenarioId}/analyze${params}`)
  return response.data
}

// Comparison
export const compareScenarios = async (baselineId: string, targetId: string, includeNarrative = true, apiKey?: string) => {
  const params = apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ''
  const response = await apiClient.post(`/scenarios/compare${params}`, {
    baseline_scenario_id: baselineId,
    target_scenario_id: targetId,
    include_ai_narrative: includeNarrative,
  })
  return response.data
}

// API Key
export const testApiKey = async (apiKey: string) => {
  const response = await apiClient.post('/api-key/test', { api_key: apiKey })
  return response.data
}

export const saveApiKey = async (apiKey: string, projectId?: string) => {
  const params = projectId ? `?project_id=${projectId}` : ''
  const response = await apiClient.post(`/api-key/save${params}`, { api_key: apiKey })
  return response.data
}

export const getApiKey = async (projectId?: string) => {
  const params = projectId ? `?project_id=${projectId}` : ''
  const response = await apiClient.get(`/api-key${params}`)
  return response.data
}
