import type { AnalysisResult, Finding, Recommendation } from '../api/types'
import {
  Brain,
  AlertTriangle,
  CheckCircle,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Settings,
  TrendingUp,
  Clock,
} from 'lucide-react'
import { useState } from 'react'

interface AnalysisPanelProps {
  analysis: Record<string, AnalysisResult> | null
  onAnalyze: () => void
  isAnalyzing: boolean
  hasApiKey: boolean
}

function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false)

  const severityColors = {
    low: 'bg-blue-100 text-blue-700',
    medium: 'bg-yellow-100 text-yellow-700',
    high: 'bg-red-100 text-red-700',
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className={`h-5 w-5 flex-shrink-0 ${
              finding.severity === 'high'
                ? 'text-red-500'
                : finding.severity === 'medium'
                ? 'text-yellow-500'
                : 'text-blue-500'
            }`}
          />
          <div>
            <h4 className="font-medium text-slate-900">{finding.title}</h4>
            <span
              className={`inline-block px-2 py-0.5 text-xs rounded mt-1 ${
                severityColors[finding.severity]
              }`}
            >
              {finding.severity}
            </span>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-400 hover:text-slate-600"
        >
          {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 pl-8 space-y-2">
          <p className="text-sm text-slate-600">{finding.description}</p>
          {finding.evidence.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Evidence:</p>
              <ul className="list-disc list-inside text-sm text-slate-600">
                {finding.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const [expanded, setExpanded] = useState(false)

  const priorityColors = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
  }

  const effortColors = {
    low: 'text-green-600',
    medium: 'text-yellow-600',
    high: 'text-red-600',
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Lightbulb className="h-5 w-5 text-yellow-500 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-slate-900">{recommendation.title}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`px-2 py-0.5 text-xs rounded ${
                  priorityColors[recommendation.priority]
                }`}
              >
                {recommendation.priority}
              </span>
              <span className="text-xs text-slate-500">
                {recommendation.framework_reference}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-400 hover:text-slate-600"
        >
          {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 pl-8 space-y-3">
          <p className="text-sm text-slate-600">{recommendation.description}</p>

          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Rationale:</p>
            <p className="text-sm text-slate-600">{recommendation.rationale}</p>
          </div>

          {recommendation.implementation_steps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Implementation Steps:</p>
              <ol className="list-decimal list-inside text-sm text-slate-600">
                {recommendation.implementation_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>
          )}

          <div className="flex items-center gap-4 text-sm">
            <span className={`flex items-center gap-1 ${effortColors[recommendation.effort]}`}>
              <TrendingUp className="h-4 w-4" />
              {recommendation.effort} effort
            </span>
            <span className="flex items-center gap-1 text-slate-500">
              <Clock className="h-4 w-4" />
              {recommendation.timeline}
            </span>
          </div>

          {recommendation.expected_impact && (
            <div className="p-2 bg-slate-50 rounded text-sm">
              <p className="font-medium text-slate-700 mb-1">Expected Impact:</p>
              {recommendation.expected_impact.cost_reduction && (
                <p className="text-slate-600">
                  Cost: {recommendation.expected_impact.cost_reduction}
                </p>
              )}
              {recommendation.expected_impact.efficiency_gain && (
                <p className="text-slate-600">
                  Efficiency: {recommendation.expected_impact.efficiency_gain}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AnalysisPanel({
  analysis,
  onAnalyze,
  isAnalyzing,
  hasApiKey,
}: AnalysisPanelProps) {
  const [activeSection, setActiveSection] = useState<'findings' | 'recommendations'>('findings')

  if (!hasApiKey) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 p-6">
        <Settings className="h-12 w-12 mb-4 text-slate-300" />
        <p className="text-center mb-4">
          Configure your Claude API key in Settings to enable AI-powered analysis
        </p>
        <a
          href="/settings"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Go to Settings
        </a>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 p-6">
        <Brain className="h-12 w-12 mb-4 text-slate-300" />
        <p className="text-center mb-4">
          Run AI analysis to get insights about your organization structure
        </p>
        <button
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {isAnalyzing ? (
            <>
              <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Brain className="h-5 w-5" />
              Start Analysis
            </>
          )}
        </button>
      </div>
    )
  }

  const structuralAnalysis = analysis.structural
  const pathologyAnalysis = analysis.pathology
  const recommendations = analysis.recommendations

  const allFindings = [
    ...(structuralAnalysis?.findings || []),
    ...(pathologyAnalysis?.findings || []),
  ]

  const allRecommendations = recommendations?.recommendations || []

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="flex gap-4 p-4 border-b border-slate-200">
        <button
          onClick={() => setActiveSection('findings')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'findings'
              ? 'bg-purple-100 text-purple-700'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <AlertTriangle className="h-5 w-5" />
          Findings ({allFindings.length})
        </button>
        <button
          onClick={() => setActiveSection('recommendations')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            activeSection === 'recommendations'
              ? 'bg-purple-100 text-purple-700'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Lightbulb className="h-5 w-5" />
          Recommendations ({allRecommendations.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeSection === 'findings' && (
          <div className="space-y-4">
            {structuralAnalysis?.narrative && (
              <div className="bg-slate-50 rounded-lg p-4 mb-4">
                <h4 className="font-medium text-slate-900 mb-2">Overall Assessment</h4>
                <p className="text-sm text-slate-600">{structuralAnalysis.narrative}</p>
              </div>
            )}

            {allFindings.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                <p>No significant issues found</p>
              </div>
            ) : (
              allFindings.map((finding, i) => <FindingCard key={i} finding={finding} />)
            )}
          </div>
        )}

        {activeSection === 'recommendations' && (
          <div className="space-y-4">
            {allRecommendations.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Lightbulb className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p>No recommendations generated</p>
              </div>
            ) : (
              allRecommendations.map((rec, i) => (
                <RecommendationCard key={i} recommendation={rec} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
