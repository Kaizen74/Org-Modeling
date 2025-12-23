import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { getProjects, getScenarios, compareScenarios } from '../api/client'
import type { Project, Scenario, ComparisonResult } from '../api/types'
import {
  GitCompare,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  DollarSign,
  Plus,
  Trash2,
  Edit,
  Move,
} from 'lucide-react'

export default function ComparisonPage() {
  const { apiKey, setLoading, setError } = useAppStore()

  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [baselineId, setBaselineId] = useState<string>('')
  const [targetId, setTargetId] = useState<string>('')
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [isComparing, setIsComparing] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      loadScenarios()
    }
  }, [selectedProject])

  const loadProjects = async () => {
    try {
      const data = await getProjects(false)
      setProjects(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load projects')
    }
  }

  const loadScenarios = async () => {
    if (!selectedProject) return
    try {
      const data = await getScenarios(selectedProject)
      setScenarios(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load scenarios')
    }
  }

  const handleCompare = async () => {
    if (!baselineId || !targetId) return

    setIsComparing(true)
    try {
      const result = await compareScenarios(baselineId, targetId, !!apiKey, apiKey || undefined)
      setComparison(result)
    } catch (err: any) {
      setError(err.message || 'Failed to compare scenarios')
    } finally {
      setIsComparing(false)
    }
  }

  const formatDelta = (value: number) => {
    if (value > 0) return `+${value.toLocaleString()}`
    return value.toLocaleString()
  }

  const formatPercent = (value: number) => {
    if (value > 0) return `+${value.toFixed(1)}%`
    return `${value.toFixed(1)}%`
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Scenario Comparison</h1>
        <p className="text-slate-500">Compare two organizational scenarios to analyze changes</p>
      </div>

      {/* Selection */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
          {/* Project Selection */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Project
            </label>
            <select
              value={selectedProject}
              onChange={(e) => {
                setSelectedProject(e.target.value)
                setBaselineId('')
                setTargetId('')
                setComparison(null)
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} - {p.client_name}
                </option>
              ))}
            </select>
          </div>

          {/* Baseline Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Baseline (As-Is)
            </label>
            <select
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
              disabled={!selectedProject}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="">Select baseline</option>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} {s.is_baseline && '(Baseline)'}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-center">
            <ArrowRight className="h-6 w-6 text-slate-400" />
          </div>

          {/* Target Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Target (To-Be)
            </label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              disabled={!selectedProject}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="">Select target</option>
              {scenarios
                .filter((s) => s.id !== baselineId)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleCompare}
            disabled={!baselineId || !targetId || isComparing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isComparing ? (
              <>
                <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                <GitCompare className="h-5 w-5" />
                Compare Scenarios
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {comparison && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 text-slate-500 mb-2">
                <Users className="h-5 w-5" />
                <span className="text-sm">Headcount Change</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">
                  {formatDelta(comparison.summary.headcount_change)}
                </span>
                <span
                  className={`text-sm ${
                    comparison.summary.headcount_change_percent < 0
                      ? 'text-green-600'
                      : comparison.summary.headcount_change_percent > 0
                      ? 'text-red-600'
                      : 'text-slate-500'
                  }`}
                >
                  {formatPercent(comparison.summary.headcount_change_percent)}
                </span>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 text-slate-500 mb-2">
                <DollarSign className="h-5 w-5" />
                <span className="text-sm">Cost Impact</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">
                  ${Math.abs(comparison.cost_impact.delta / 1000).toFixed(0)}K
                </span>
                <span
                  className={`text-sm ${
                    comparison.cost_impact.is_cost_reduction
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {comparison.cost_impact.is_cost_reduction ? 'Savings' : 'Increase'}
                </span>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 text-slate-500 mb-2">
                <Plus className="h-5 w-5 text-green-500" />
                <span className="text-sm">Added</span>
              </div>
              <span className="text-2xl font-bold text-green-600">
                {comparison.summary.nodes_added}
              </span>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center gap-2 text-slate-500 mb-2">
                <Trash2 className="h-5 w-5 text-red-500" />
                <span className="text-sm">Removed</span>
              </div>
              <span className="text-2xl font-bold text-red-600">
                {comparison.summary.nodes_removed}
              </span>
            </div>
          </div>

          {/* Metric Deltas */}
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="font-semibold mb-4">Metric Changes</h3>
            <div className="space-y-3">
              {comparison.metric_deltas.slice(0, 10).map((delta) => (
                <div
                  key={delta.metric_type}
                  className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
                >
                  <div className="flex items-center gap-2">
                    {delta.direction === 'increase' && (
                      <TrendingUp className="h-4 w-4 text-blue-500" />
                    )}
                    {delta.direction === 'decrease' && (
                      <TrendingDown className="h-4 w-4 text-orange-500" />
                    )}
                    {delta.direction === 'unchanged' && (
                      <Minus className="h-4 w-4 text-slate-400" />
                    )}
                    <span className="text-slate-700">
                      {delta.metric_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-slate-500">{delta.baseline_value}</span>
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                    <span className="font-medium">{delta.target_value}</span>
                    <span
                      className={`text-sm px-2 py-0.5 rounded ${
                        delta.is_improvement === true
                          ? 'bg-green-100 text-green-700'
                          : delta.is_improvement === false
                          ? 'bg-red-100 text-red-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {formatPercent(delta.delta_percent)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Node Changes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Added */}
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Plus className="h-5 w-5 text-green-500" />
                Added Positions ({comparison.node_changes.added.length})
              </h3>
              <div className="space-y-2 max-h-64 overflow-auto">
                {comparison.node_changes.added.map((node) => (
                  <div key={node.node_id} className="p-2 bg-green-50 rounded">
                    <p className="font-medium text-slate-900">{node.node_name}</p>
                    <p className="text-sm text-slate-500">{node.node_title}</p>
                  </div>
                ))}
                {comparison.node_changes.added.length === 0 && (
                  <p className="text-slate-500 text-sm">No positions added</p>
                )}
              </div>
            </div>

            {/* Removed */}
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Trash2 className="h-5 w-5 text-red-500" />
                Removed Positions ({comparison.node_changes.removed.length})
              </h3>
              <div className="space-y-2 max-h-64 overflow-auto">
                {comparison.node_changes.removed.map((node) => (
                  <div key={node.node_id} className="p-2 bg-red-50 rounded">
                    <p className="font-medium text-slate-900">{node.node_name}</p>
                    <p className="text-sm text-slate-500">{node.node_title}</p>
                  </div>
                ))}
                {comparison.node_changes.removed.length === 0 && (
                  <p className="text-slate-500 text-sm">No positions removed</p>
                )}
              </div>
            </div>
          </div>

          {/* AI Narrative */}
          {comparison.ai_narrative && (
            <div className="bg-purple-50 rounded-lg border border-purple-200 p-6">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-purple-900">
                <GitCompare className="h-5 w-5" />
                AI-Generated Summary
              </h3>
              <p className="text-purple-800 whitespace-pre-line">{comparison.ai_narrative}</p>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!comparison && !isComparing && (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
          <GitCompare className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Select two scenarios to compare</p>
        </div>
      )}
    </div>
  )
}
