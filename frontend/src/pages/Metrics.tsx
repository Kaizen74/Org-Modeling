import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, AlertTriangle, ArrowRight, RefreshCw, Briefcase, Brain } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { metricsApi, aiAnalysisApi, settingsApi } from '../services/api';
import type { OrgMetrics, QuickWorkActivitiesAnalysis, WorkActivitiesAnalysis } from '../types';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Metrics() {
  const [metrics, setMetrics] = useState<OrgMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Work Activities State
  const [workActivitiesQuick, setWorkActivitiesQuick] = useState<QuickWorkActivitiesAnalysis | null>(null);
  const [workActivitiesAnalysis, setWorkActivitiesAnalysis] = useState<WorkActivitiesAnalysis | null>(null);
  const [analyzingWorkActivities, setAnalyzingWorkActivities] = useState(false);
  const [workActivitiesError, setWorkActivitiesError] = useState<string | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [industry, setIndustry] = useState('');

  useEffect(() => {
    fetchMetrics();
    fetchWorkActivitiesQuick();
    fetchWorkActivitiesLatest();
    checkApiStatus();
  }, []);

  const checkApiStatus = async () => {
    try {
      const status = await settingsApi.getStatus();
      setApiConfigured(status.configured);
    } catch (err) {
      console.error('Failed to check API status:', err);
    }
  };

  const fetchMetrics = async () => {
    try {
      const result = await metricsApi.getLatest();
      setMetrics(result.metrics);
    } catch (err) {
      setError('No metrics available. Please upload org data first.');
    } finally {
      setLoading(false);
    }
  };

  const fetchWorkActivitiesQuick = async () => {
    try {
      const result = await aiAnalysisApi.getQuickWorkActivities();
      setWorkActivitiesQuick(result);
    } catch (err) {
      // No work activities data available
    }
  };

  const fetchWorkActivitiesLatest = async () => {
    try {
      const result = await aiAnalysisApi.getLatestWorkActivities();
      setWorkActivitiesAnalysis(result.work_activities_analysis);
    } catch (err) {
      // No existing analysis
    }
  };

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      const result = await metricsApi.recalculate();
      setMetrics(result.metrics);
    } catch (err) {
      console.error('Failed to recalculate:', err);
    } finally {
      setRecalculating(false);
    }
  };

  const handleAnalyzeWorkActivities = async () => {
    setAnalyzingWorkActivities(true);
    setWorkActivitiesError(null);
    try {
      const result = await aiAnalysisApi.analyzeWorkActivities(industry || undefined);
      setWorkActivitiesAnalysis(result.work_activities_analysis);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setWorkActivitiesError(error.response?.data?.detail || 'Failed to analyze work activities');
    } finally {
      setAnalyzingWorkActivities(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Organizational Metrics</h1>
        <div className="card text-center py-8">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-600 mb-2">No Metrics Available</h2>
          <p className="text-gray-500 mb-4">{error}</p>
          <Link to="/upload" className="btn btn-primary inline-flex items-center gap-2">
            Upload CSV <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const spanDistData = Object.entries(metrics.span_of_control.distribution).map(([name, value]) => ({
    name,
    value,
  }));

  const managerICData = [
    { name: 'Managers', value: metrics.manager_stats.total_managers },
    { name: 'ICs', value: metrics.manager_stats.total_ics },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Organizational Metrics</h1>
        <div className="flex gap-3">
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
          >
            {recalculating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Recalculate
          </button>
          <Link to="/analysis" className="btn btn-primary flex items-center gap-2">
            Archetype Analysis <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SummaryCard
          title="Total Employees"
          value={metrics.total_employees}
        />
        <SummaryCard
          title="Manager Ratio"
          value={`${metrics.manager_stats.manager_ratio_pct}%`}
          subtitle={`${metrics.manager_stats.total_managers} managers`}
        />
        <SummaryCard
          title="Avg Span of Control"
          value={metrics.span_of_control.average_span.toFixed(2)}
          subtitle={`Median: ${metrics.span_of_control.median_span}`}
        />
        <SummaryCard
          title="Org Layers"
          value={metrics.layer_analysis.total_layers}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Span Distribution */}
        <div className="card">
          <h3 className="font-semibold mb-4">Span of Control Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={spanDistData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-2 text-sm text-gray-500">
            {Object.entries(metrics.span_of_control.distribution_pct).map(([k, v]) => (
              <span key={k} className="mr-4">{k}: {v}%</span>
            ))}
          </div>
        </div>

        {/* Manager vs IC */}
        <div className="card">
          <h3 className="font-semibold mb-4">Manager vs Individual Contributors</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={managerICData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {managerICData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cost Analysis */}
      <div className="card mb-8">
        <h3 className="font-semibold mb-4">Cost Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-500">Total Cost</p>
            <p className="text-2xl font-bold">
              ${(metrics.cost_analysis.total_cost / 1000000).toFixed(2)}M
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Avg Cost per Employee</p>
            <p className="text-2xl font-bold">
              ${metrics.cost_analysis.average_cost_per_employee.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Avg Grade Gap</p>
            <p className="text-2xl font-bold">
              {metrics.grade_gap_analysis.average_grade_gap.toFixed(2)}
            </p>
            <p className="text-xs text-gray-400">
              ({metrics.grade_gap_analysis.total_comparisons} comparisons)
            </p>
          </div>
        </div>
      </div>

      {/* Work Activities Analysis - Current State */}
      <div className="card mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <Briefcase className="w-5 h-5" />
            Work Activities Analysis
          </h3>
          {workActivitiesQuick && (
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              workActivitiesQuick.coverage_percentage >= 80
                ? 'bg-green-100 text-green-700'
                : workActivitiesQuick.coverage_percentage >= 50
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {workActivitiesQuick.coverage_percentage}% Coverage
            </span>
          )}
        </div>

        {!workActivitiesQuick || workActivitiesQuick.employees_with_work_activities === 0 ? (
          <div className="text-center py-6 bg-gray-50 rounded-lg">
            <Briefcase className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-600 mb-2">No work activities data found</p>
            <p className="text-sm text-gray-500">
              Upload a CSV with a "Work Activities" column to analyze job coherence and synergy
            </p>
          </div>
        ) : (
          <>
            {/* Coverage Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-3 bg-blue-50 rounded-lg text-center">
                <p className="text-xl font-bold text-blue-600">{workActivitiesQuick.employees_with_work_activities}</p>
                <p className="text-xs text-blue-700">Positions with Activities</p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg text-center">
                <p className="text-xl font-bold text-green-600">{workActivitiesQuick.departments_with_activities}</p>
                <p className="text-xs text-green-700">Departments</p>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg text-center">
                <p className="text-xl font-bold text-purple-600">{workActivitiesQuick.coverage_percentage}%</p>
                <p className="text-xs text-purple-700">Data Coverage</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-xl font-bold text-gray-600">{workActivitiesQuick.status}</p>
                <p className="text-xs text-gray-700">Status</p>
              </div>
            </div>

            {/* Department Breakdown */}
            {workActivitiesQuick.department_breakdown && workActivitiesQuick.department_breakdown.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Activities by Department</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {workActivitiesQuick.department_breakdown.slice(0, 6).map((dept, i) => (
                    <div key={i} className="p-3 border rounded-lg">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-sm">{dept.department}</span>
                        <span className="text-xs text-gray-500">{dept.positions_with_activities} positions</span>
                      </div>
                      {dept.sample_activities.length > 0 && (
                        <p className="text-xs text-gray-500 truncate" title={dept.sample_activities[0]}>
                          e.g., {dept.sample_activities[0].substring(0, 60)}...
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Analysis Section */}
            {apiConfigured ? (
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-3">AI-Powered Coherence & Synergy Analysis</h4>

                {!workActivitiesAnalysis ? (
                  <div className="flex flex-col md:flex-row items-start md:items-end gap-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-500">Industry Context (Optional)</label>
                      <input
                        type="text"
                        value={industry}
                        onChange={(e) => setIndustry(e.target.value)}
                        className="input mt-1"
                        placeholder="E.g., Airlines, Technology, Healthcare..."
                      />
                    </div>
                    <button
                      onClick={handleAnalyzeWorkActivities}
                      disabled={analyzingWorkActivities}
                      className="btn btn-primary flex items-center gap-2 whitespace-nowrap"
                    >
                      {analyzingWorkActivities ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Analyzing...
                        </>
                      ) : (
                        <>
                          <Brain className="w-4 h-4" />
                          Analyze Coherence & Synergy
                        </>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Overall Coherence Score */}
                    {workActivitiesAnalysis.overall_coherence && (
                      <div className="flex items-center justify-between p-4 bg-primary-50 rounded-lg">
                        <div>
                          <p className="font-medium text-primary-800">Organization Coherence Score</p>
                          <p className="text-sm text-primary-600">{workActivitiesAnalysis.overall_coherence.integration_assessment}</p>
                        </div>
                        <div className="text-3xl font-bold text-primary-600">
                          {workActivitiesAnalysis.overall_coherence.organization_coherence_score}/100
                        </div>
                      </div>
                    )}

                    {/* Department Coherence Summary */}
                    {workActivitiesAnalysis.departmental_coherence && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2">Department Coherence Scores</h5>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {workActivitiesAnalysis.departmental_coherence.slice(0, 8).map((dept, i) => (
                            <div key={i} className="p-2 border rounded text-center">
                              <p className={`text-lg font-bold ${
                                dept.coherence_score >= 70 ? 'text-green-600' :
                                dept.coherence_score >= 50 ? 'text-yellow-600' : 'text-red-600'
                              }`}>
                                {dept.coherence_score}
                              </p>
                              <p className="text-xs text-gray-600 truncate" title={dept.department}>{dept.department}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Work Themes Summary */}
                    {workActivitiesAnalysis.work_themes && workActivitiesAnalysis.work_themes.primary_themes && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-700 mb-2">Primary Work Themes</h5>
                        <div className="flex flex-wrap gap-2">
                          {workActivitiesAnalysis.work_themes.primary_themes.slice(0, 5).map((theme, i) => (
                            <span key={i} className={`px-3 py-1 rounded-full text-sm ${
                              theme.strategic_importance === 'High' ? 'bg-green-100 text-green-700' :
                              theme.strategic_importance === 'Medium' ? 'bg-blue-100 text-blue-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {theme.theme} ({theme.percentage_of_org}%)
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Industry Comparison */}
                    {workActivitiesAnalysis.industry_comparison && (
                      <div className="p-3 bg-indigo-50 rounded-lg">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium text-indigo-800">Industry Alignment</p>
                            <p className="text-sm text-indigo-600">{workActivitiesAnalysis.industry_comparison.industry_identified}</p>
                          </div>
                          <p className="text-2xl font-bold text-indigo-600">
                            {workActivitiesAnalysis.industry_comparison.activity_mix_assessment?.alignment_score || 0}/100
                          </p>
                        </div>
                      </div>
                    )}

                    {/* View Full Analysis Link */}
                    <div className="flex justify-between items-center pt-2">
                      <button
                        onClick={handleAnalyzeWorkActivities}
                        disabled={analyzingWorkActivities}
                        className="text-sm text-primary-600 hover:text-primary-800 flex items-center gap-1"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Re-analyze
                      </button>
                      <Link
                        to="/work-activities"
                        className="text-sm text-primary-600 hover:text-primary-800 flex items-center gap-1"
                      >
                        View Full Analysis <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                )}

                {workActivitiesError && (
                  <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                    <AlertTriangle className="w-4 h-4 inline mr-1" />
                    {workActivitiesError}
                  </div>
                )}
              </div>
            ) : (
              <div className="border-t pt-4">
                <p className="text-sm text-gray-500">
                  <Link to="/settings" className="text-primary-600 hover:underline">Configure Claude API</Link>
                  {' '}to enable AI-powered coherence and synergy analysis
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Health Indicators */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Health Indicators</h3>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            metrics.health_indicators.health_score >= 70
              ? 'bg-green-100 text-green-700'
              : metrics.health_indicators.health_score >= 50
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
          }`}>
            Score: {metrics.health_indicators.health_score}/100
            (Grade: {metrics.health_indicators.health_grade})
          </div>
        </div>

        {metrics.health_indicators.warnings.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Warnings</h4>
            <ul className="space-y-1">
              {metrics.health_indicators.warnings.map((warning, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-yellow-700 bg-yellow-50 p-2 rounded">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        )}

        {metrics.health_indicators.recommendations.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Recommendations</h4>
            <ul className="space-y-1">
              {metrics.health_indicators.recommendations.map((rec, i) => (
                <li key={i} className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                  &#8226; {rec}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
}) {
  return (
    <div className="card">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
