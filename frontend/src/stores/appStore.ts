import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Project, Scenario, Employee, Metric, ApiKeyConfig } from '../api/types'

interface AppState {
  // Current context
  currentProject: Project | null
  currentScenario: Scenario | null

  // Data caches
  projects: Project[]
  scenarios: Scenario[]
  employees: Employee[]
  metrics: Metric[]

  // API Key
  apiKey: string | null
  apiKeyConfig: ApiKeyConfig | null

  // UI State
  isLoading: boolean
  error: string | null
  sidebarCollapsed: boolean

  // Actions
  setCurrentProject: (project: Project | null) => void
  setCurrentScenario: (scenario: Scenario | null) => void
  setProjects: (projects: Project[]) => void
  setScenarios: (scenarios: Scenario[]) => void
  setEmployees: (employees: Employee[]) => void
  setMetrics: (metrics: Metric[]) => void
  setApiKey: (apiKey: string | null) => void
  setApiKeyConfig: (config: ApiKeyConfig | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  toggleSidebar: () => void
  clearState: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      currentProject: null,
      currentScenario: null,
      projects: [],
      scenarios: [],
      employees: [],
      metrics: [],
      apiKey: null,
      apiKeyConfig: null,
      isLoading: false,
      error: null,
      sidebarCollapsed: false,

      // Actions
      setCurrentProject: (project) => set({ currentProject: project }),
      setCurrentScenario: (scenario) => set({ currentScenario: scenario }),
      setProjects: (projects) => set({ projects }),
      setScenarios: (scenarios) => set({ scenarios }),
      setEmployees: (employees) => set({ employees }),
      setMetrics: (metrics) => set({ metrics }),
      setApiKey: (apiKey) => set({ apiKey }),
      setApiKeyConfig: (apiKeyConfig) => set({ apiKeyConfig }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      clearState: () => set({
        currentProject: null,
        currentScenario: null,
        projects: [],
        scenarios: [],
        employees: [],
        metrics: [],
        error: null,
      }),
    }),
    {
      name: 'orgdesign-storage',
      partialize: (state) => ({
        apiKey: state.apiKey,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)
