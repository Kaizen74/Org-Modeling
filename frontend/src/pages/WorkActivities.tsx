import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Loader2, AlertTriangle, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';
import { aiAnalysisApi, settingsApi } from '../services/api';
import type { WorkActivitiesAnalysis, QuickWorkActivitiesAnalysis } from '../types';

export default function WorkActivities() {
  const [analysis, setAnalysis] = useState<WorkActivitiesAnalysis | null>(null);
  const [quickAnalysis, setQuickAnalysis] = useState<QuickWorkActivitiesAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [industry, setIndustry] = useState('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    coherence: true,
    themes: true,
    industry: true,
    recommendations: true,
  });

  useEffect(() => {
    checkApiStatus();
    loadQuickAnalysis();
    loadExistingAnalysis();
  }, []);

  const checkApiStatus = async () => {
    try {
      const status = await settingsApi.getStatus();
      setApiConfigured(status.configured);
    } catch (err) {
      console.error('Failed to check API status:', err);
    }
  };

  const loadQuickAnalysis = async () => {
    try {
      const result = await aiAnalysisApi.getQuickWorkActivities();
      setQuickAnalysis(result);
    } catch (err) {
      // No quick analysis available
    }
  };

  const loadExistingAnalysis = async () => {
    try {
      const result = await aiAnalysisApi.getLatestWorkActivities();
      setAnalysis(result.work_activities_analysis);
    } catch (err) {
      // No existing analysis
    }
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await aiAnalysisApi.analyzeWorkActivities(industry || undefined);
      setAnalysis(result.work_activities_analysis);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to run work activities analysis');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Show quick analysis stats
  const QuickStats = () => {
    if (!quickAnalysis) return null;

    return (
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4">Work Activities Coverage</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <p className="text-2xl font-bold text-primary-600">{quickAnalysis.total_employees}</p>
            <p className="text-sm text-gray-600">Total Employees</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <p className="text-2xl font-bold text-green-600">{quickAnalysis.employees_with_work_activities}</p>
            <p className="text-sm text-gray-600">With Activities</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <p className="text-2xl font-bold text-blue-600">{quickAnalysis.coverage_percentage}%</p>
            <p className="text-sm text-gray-600">Coverage</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <p className="text-2xl font-bold text-purple-600">{quickAnalysis.departments_with_activities}</p>
            <p className="text-sm text-gray-600">Departments</p>
          </div>
        </div>

        {quickAnalysis.status !== 'complete' && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-700">
              <AlertTriangle className="w-4 h-4 inline mr-1" />
              {quickAnalysis.status === 'minimal'
                ? 'Limited work activities data available. Consider adding more activities to the CSV for better analysis.'
                : 'Some positions are missing work activities. Full coverage is recommended for comprehensive analysis.'}
            </p>
          </div>
        )}
      </div>
    );
  };

  if (!apiConfigured) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Work Activities Analysis</h1>
        <QuickStats />
        <div className="card text-center py-8">
          <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-600 mb-2">Claude API Not Configured</h2>
          <p className="text-gray-500 mb-4">
            Configure your Anthropic API key to enable AI-powered work activities analysis.
          </p>
          <Link to="/settings" className="btn btn-primary inline-flex items-center gap-2">
            Configure API Key <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Work Activities Analysis</h1>

      {/* Quick Stats */}
      <QuickStats />

      {/* Input Section */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4">Analysis Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="label">Industry Context (Optional)</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="input"
              placeholder="E.g., Airlines, Technology, Financial Services, Healthcare..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Providing industry context improves benchmark comparisons
            </p>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={loading || (quickAnalysis !== null && quickAnalysis.employees_with_work_activities === 0)}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing (this may take 30-60 seconds)...
              </>
            ) : (
              <>
                <Briefcase className="w-5 h-5" />
                Run Work Activities Analysis
              </>
            )}
          </button>

          {quickAnalysis && quickAnalysis.employees_with_work_activities === 0 && (
            <p className="text-sm text-red-600">
              No work activities found. Please upload a CSV with a "Work Activities" column.
            </p>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-red-200 mb-6">
          <div className="flex items-center gap-2 text-red-700">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">{error}</span>
          </div>
        </div>
      )}

      {/* Results */}
      {analysis && !analysis.error && (
        <div className="space-y-6">
          {/* Executive Summary */}
          {analysis.executive_summary && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-3">Executive Summary</h2>
              <div className="prose prose-sm max-w-none text-gray-600">
                {analysis.executive_summary}
              </div>
            </div>
          )}

          {/* Departmental Coherence */}
          {analysis.departmental_coherence && analysis.departmental_coherence.length > 0 && (
            <CollapsibleSection
              title="Departmental Coherence & Synergy"
              isOpen={expandedSections.coherence}
              onToggle={() => toggleSection('coherence')}
            >
              {/* Overall Coherence Score */}
              {analysis.overall_coherence && (
                <div className="mb-6 p-4 bg-primary-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-primary-800">Organization Coherence Score</span>
                    <span className="text-3xl font-bold text-primary-600">
                      {analysis.overall_coherence.organization_coherence_score}/100
                    </span>
                  </div>
                  <p className="text-sm text-primary-700">{analysis.overall_coherence.integration_assessment}</p>

                  {analysis.overall_coherence.cross_department_synergies?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-green-700">Cross-Department Synergies:</p>
                      <ul className="text-sm text-green-600">
                        {analysis.overall_coherence.cross_department_synergies.map((s, i) => (
                          <li key={i}>&#10003; {s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {analysis.overall_coherence.cross_department_gaps?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-sm font-medium text-red-700">Cross-Department Gaps:</p>
                      <ul className="text-sm text-red-600">
                        {analysis.overall_coherence.cross_department_gaps.map((g, i) => (
                          <li key={i}>&#10007; {g}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Department Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.departmental_coherence.map((dept, i) => (
                  <div key={i} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold">{dept.department}</h4>
                      <span className={`text-xl font-bold ${
                        dept.coherence_score >= 70 ? 'text-green-600' :
                        dept.coherence_score >= 50 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {dept.coherence_score}/100
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mb-2">{dept.position_count} positions</p>
                    <p className="text-sm text-gray-600 mb-3">{dept.coherence_rationale}</p>

                    <div className="flex flex-wrap gap-2 mb-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        {dept.value_chain_position}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                        Dependencies: {dept.internal_dependencies}
                      </span>
                    </div>

                    {dept.synergy_assessment?.strengths?.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-green-700">Strengths:</p>
                        <ul className="text-xs text-green-600">
                          {dept.synergy_assessment.strengths.slice(0, 2).map((s, j) => (
                            <li key={j}>&#10003; {s}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {dept.synergy_assessment?.gaps?.length > 0 && (
                      <div className="mt-1">
                        <p className="text-xs font-medium text-red-700">Gaps:</p>
                        <ul className="text-xs text-red-600">
                          {dept.synergy_assessment.gaps.slice(0, 2).map((g, j) => (
                            <li key={j}>&#10007; {g}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Work Themes */}
          {analysis.work_themes && (
            <CollapsibleSection
              title="Work Theme Synthesis"
              isOpen={expandedSections.themes}
              onToggle={() => toggleSection('themes')}
            >
              {/* Strategic Alignment Score */}
              <div className="mb-4 p-3 bg-blue-50 rounded-lg flex items-center justify-between">
                <span className="font-medium text-blue-800">Strategic Alignment Score</span>
                <span className="text-2xl font-bold text-blue-600">
                  {analysis.work_themes.strategic_alignment_score}/100
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-4">
                {analysis.work_themes.theme_distribution_assessment}
              </p>

              {/* Theme Cards */}
              {analysis.work_themes.primary_themes && (
                <div className="space-y-3">
                  {analysis.work_themes.primary_themes.map((theme, i) => (
                    <div key={i} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold">{theme.theme}</h4>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-500">
                            {theme.percentage_of_org}% of org
                          </span>
                          <span className={`px-2 py-1 text-xs rounded ${
                            theme.strategic_importance === 'High' ? 'bg-green-100 text-green-700' :
                            theme.strategic_importance === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {theme.strategic_importance} Importance
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{theme.description}</p>
                      <p className="text-xs text-gray-500 mt-2">
                        Departments: {theme.departments_involved?.join(', ')}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Missing Capabilities */}
              {analysis.work_themes.missing_capabilities && analysis.work_themes.missing_capabilities.length > 0 && (
                <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                  <p className="font-medium text-yellow-800 mb-2">Missing Capabilities</p>
                  <ul className="text-sm text-yellow-700">
                    {analysis.work_themes.missing_capabilities.map((cap, i) => (
                      <li key={i}>&#9888; {cap}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Industry Comparison */}
          {analysis.industry_comparison && (
            <CollapsibleSection
              title="Industry Benchmark Comparison"
              isOpen={expandedSections.industry}
              onToggle={() => toggleSection('industry')}
            >
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-700">
                  <span className="font-medium">Industry Identified:</span>{' '}
                  {analysis.industry_comparison.industry_identified}
                </p>
              </div>

              {/* Activity Mix */}
              {analysis.industry_comparison.activity_mix_assessment && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">Activity Mix Alignment</span>
                      <span className="text-xl font-bold text-primary-600">
                        {analysis.industry_comparison.activity_mix_assessment.alignment_score}/100
                      </span>
                    </div>

                    {analysis.industry_comparison.activity_mix_assessment.unique_strengths?.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-green-700">Unique Strengths:</p>
                        <ul className="text-xs text-green-600">
                          {analysis.industry_comparison.activity_mix_assessment.unique_strengths.map((s, i) => (
                            <li key={i}>&#10003; {s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="p-4 border rounded-lg">
                    <span className="font-medium">Role Specialization</span>
                    <p className={`text-lg font-semibold mt-1 ${
                      analysis.industry_comparison.role_specialization?.assessment === 'Well balanced'
                        ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {analysis.industry_comparison.role_specialization?.assessment}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {analysis.industry_comparison.role_specialization?.rationale}
                    </p>
                  </div>
                </div>
              )}

              {/* Competitive Positioning */}
              {analysis.industry_comparison.competitive_positioning && (
                <div className="p-4 bg-indigo-50 rounded-lg">
                  <h4 className="font-medium text-indigo-800 mb-3">Competitive Positioning</h4>
                  <p className="text-sm text-indigo-700 mb-3">
                    {analysis.industry_comparison.competitive_positioning.overall_assessment}
                  </p>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-medium text-green-700">Potential Advantages:</p>
                      <ul className="text-xs text-green-600">
                        {analysis.industry_comparison.competitive_positioning.potential_advantages?.map((a, i) => (
                          <li key={i}>&#10003; {a}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-red-700">Potential Disadvantages:</p>
                      <ul className="text-xs text-red-600">
                        {analysis.industry_comparison.competitive_positioning.potential_disadvantages?.map((d, i) => (
                          <li key={i}>&#10007; {d}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Recommendations */}
          {analysis.recommendations && (
            <CollapsibleSection
              title="Recommendations"
              isOpen={expandedSections.recommendations}
              onToggle={() => toggleSection('recommendations')}
            >
              {/* Quick Wins */}
              {analysis.recommendations.quick_wins && analysis.recommendations.quick_wins.length > 0 && (
                <div className="mb-4 p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-2">Quick Wins</h4>
                  <ul className="space-y-1">
                    {analysis.recommendations.quick_wins.map((win, i) => (
                      <li key={i} className="text-sm text-green-700">&#10003; {win}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Structural Recommendations */}
              {analysis.recommendations.structural && analysis.recommendations.structural.length > 0 && (
                <div className="mb-4">
                  <h4 className="font-medium mb-3">Structural Recommendations</h4>
                  <div className="space-y-3">
                    {analysis.recommendations.structural.map((rec, i) => (
                      <div key={i} className="p-3 border rounded-lg">
                        <p className="font-medium">{rec.recommendation}</p>
                        <p className="text-sm text-gray-600 mt-1">{rec.rationale}</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className={`px-2 py-1 text-xs rounded ${
                            rec.impact === 'High' ? 'bg-green-100 text-green-700' :
                            rec.impact === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            Impact: {rec.impact}
                          </span>
                          <span className={`px-2 py-1 text-xs rounded ${
                            rec.effort === 'Low' ? 'bg-green-100 text-green-700' :
                            rec.effort === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            Effort: {rec.effort}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Capability Development */}
              {analysis.recommendations.capability_development && analysis.recommendations.capability_development.length > 0 && (
                <div className="mb-4">
                  <h4 className="font-medium mb-3">Capability Development</h4>
                  <div className="space-y-3">
                    {analysis.recommendations.capability_development.map((cap, i) => (
                      <div key={i} className="p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-blue-800">{cap.capability}</p>
                          <span className={`px-2 py-1 text-xs rounded ${
                            cap.priority === 'High' ? 'bg-red-100 text-red-700' :
                            cap.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            Priority: {cap.priority}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
                          <div>
                            <p className="text-xs text-gray-500">Current State:</p>
                            <p className="text-blue-700">{cap.current_state}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Target State:</p>
                            <p className="text-blue-700">{cap.target_state}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CollapsibleSection>
          )}
        </div>
      )}
    </div>
  );
}

function CollapsibleSection({
  title,
  isOpen,
  onToggle,
  children,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="card">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between text-left"
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {isOpen && <div className="mt-4">{children}</div>}
    </div>
  );
}
