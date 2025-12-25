import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, AlertTriangle, ArrowRight } from 'lucide-react';
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
import { metricsApi } from '../services/api';
import type { OrgMetrics } from '../types';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Metrics() {
  const [metrics, setMetrics] = useState<OrgMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

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
        <Link to="/analysis" className="btn btn-primary flex items-center gap-2">
          Run AI Analysis <ArrowRight className="w-4 h-4" />
        </Link>
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
