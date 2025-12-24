import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import {
  getScenario,
  getScenarioTree,
  calculateMetrics,
  analyzeScenario,
} from '../api/client'
import type { Scenario, OrgTree, MetricsSummary, AnalysisResult } from '../api/types'
import OrgChart from '../components/OrgChart'
import MetricsDashboard from '../components/MetricsDashboard'
import AnalysisPanel from '../components/AnalysisPanel'
import {
  ArrowLeft,
  BarChart3,
  Network,
  Brain,
  RefreshCw,
} from 'lucide-react'

type TabType = 'chart' | 'metrics' | 'analysis'

export default function ScenarioPage() {
  const { scenarioId } = useParams<{ scenarioId: string }>()
  const { setCurrentScenario, apiKey, setLoading, setError } = useAppStore()

  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [orgTree, setOrgTree] = useState<OrgTree | null>(null)
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null)
  const [analysis, setAnalysis] = useState<Record<string, AnalysisResult> | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('chart')
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  useEffect(() => {
    if (scenarioId) {
      loadScenario()
      loadOrgTree()
    }
  }, [scenarioId])

  const loadScenario = async () => {
    if (!scenarioId) return
    try {
      const data = await getScenario(scenarioId)
      setScenario(data)
      setCurrentScenario(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load scenario')
    }
  }

  const loadOrgTree = async () => {
    if (!scenarioId) return
    try {
      const data = await getScenarioTree(scenarioId)
      setOrgTree(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load org chart')
    }
  }

  const handleCalculateMetrics = async () => {
    if (!scenarioId) return
    setLoading(true)
    try {
      const data = await calculateMetrics(scenarioId)
      setMetrics(data)
      setActiveTab('metrics')
    } catch (err: any) {
      setError(err.message || 'Failed to calculate metrics')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async () => {
    if (!scenarioId) return

    if (!apiKey) {
      setError('Please configure your Claude API key in Settings')
      return
    }

    setIsAnalyzing(true)
    try {
      const result = await analyzeScenario(scenarioId, apiKey)
      if (result.success) {
        setAnalysis(result.analyses)
        setActiveTab('analysis')
      } else {
        setError('Analysis failed')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to analyze scenario')
    } finally {
      setIsAnalyzing(false)
    }
  }

  if (!scenario) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading scenario...</div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to={`/projects/${scenario.project_id}`}
              className="text-slate-500 hover:text-slate-700"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-900">{scenario.name}</h1>
              <p className="text-sm text-slate-500">
                {scenario.employee_count || 0} employees
                {scenario.is_baseline && (
                  <span className="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                    Baseline
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCalculateMetrics}
              className="flex items-center gap-2 px-3 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <BarChart3 className="h-5 w-5" />
              Calculate Metrics
            </button>
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              {isAnalyzing ? (
                <RefreshCw className="h-5 w-5 animate-spin" />
              ) : (
                <Brain className="h-5 w-5" />
              )}
              AI Analysis
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mt-4">
          <button
            onClick={() => setActiveTab('chart')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'chart'
                ? 'bg-blue-100 text-blue-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Network className="h-5 w-5" />
            Org Chart
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'metrics'
                ? 'bg-blue-100 text-blue-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <BarChart3 className="h-5 w-5" />
            Metrics
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'analysis'
                ? 'bg-blue-100 text-blue-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Brain className="h-5 w-5" />
            Analysis
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chart' && orgTree && (
          <OrgChart nodes={orgTree.nodes} edges={orgTree.edges} />
        )}
        {activeTab === 'metrics' && (
          <MetricsDashboard metrics={metrics} onRefresh={handleCalculateMetrics} />
        )}
        {activeTab === 'analysis' && (
          <AnalysisPanel
            analysis={analysis}
            onAnalyze={handleAnalyze}
            isAnalyzing={isAnalyzing}
            hasApiKey={!!apiKey}
          />
        )}
      </div>
    </div>
  )
}
