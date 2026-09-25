import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  UserCheck,
  DollarSign,
  Layers,
  Activity,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';
import { metricsApi, settingsApi } from '../services/api';

interface MetricsSummary {
  total_employees: number;
  total_managers: number;
  manager_ratio: number;
  average_span: number;
  total_cost: number;
  layers: number;
  health_score: number;
  health_grade: string;
  warnings: string[];
}

export default function Dashboard() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const status = await settingsApi.getStatus();
        setApiConfigured(status.configured);

        const data = await metricsApi.getSummary();
        setSummary(data);
      } catch (err) {
        setError('No org data available. Upload a CSV to get started.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {!apiConfigured && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 text-yellow-800">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Claude API not configured</span>
          </div>
          <p className="text-sm text-yellow-700 mt-1">
            Configure your API key in{' '}
            <Link to="/settings" className="underline">Settings</Link>
            {' '}to enable AI analysis.
          </p>
        </div>
      )}

      {error ? (
        <div className="card">
          <div className="text-center py-8">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-gray-600 mb-2">No Organization Data</h2>
            <p className="text-gray-500 mb-4">{error}</p>
            <Link to="/upload" className="btn btn-primary inline-flex items-center gap-2">
              Upload CSV <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      ) : summary && (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <MetricCard
              title="Total Employees"
              value={summary.total_employees.toLocaleString()}
              icon={Users}
              color="blue"
            />
            <MetricCard
              title="Managers"
              value={summary.total_managers.toLocaleString()}
              subtitle={`${summary.manager_ratio.toFixed(1)}% of org`}
              icon={UserCheck}
              color="green"
            />
            <MetricCard
              title="Avg Span of Control"
              value={summary.average_span.toFixed(2)}
              subtitle="direct reports per manager"
              icon={Activity}
              color="purple"
            />
            <MetricCard
              title="Total Cost"
              value={`$${(summary.total_cost / 1000000).toFixed(2)}M`}
              icon={DollarSign}
              color="yellow"
            />
            <MetricCard
              title="Org Layers"
              value={summary.layers.toString()}
              subtitle="hierarchical levels"
              icon={Layers}
              color="indigo"
            />
            <MetricCard
              title="Health Score"
              value={`${summary.health_score}/100`}
              subtitle={`Grade: ${summary.health_grade}`}
              icon={Activity}
              color={summary.health_score >= 70 ? 'green' : summary.health_score >= 50 ? 'yellow' : 'red'}
            />
          </div>

          {/* Warnings */}
          {summary.warnings.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-500" />
                Health Warnings
              </h2>
              <ul className="space-y-2">
                {summary.warnings.map((warning, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="text-yellow-500 mt-0.5">&#9679;</span>
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Actions */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link to="/metrics" className="card hover:shadow-lg transition-shadow">
              <h3 className="font-medium">View Full Metrics</h3>
              <p className="text-sm text-gray-500 mt-1">Detailed org analysis</p>
            </Link>
            <Link to="/analysis" className="card hover:shadow-lg transition-shadow">
              <h3 className="font-medium">AI Analysis</h3>
              <p className="text-sm text-gray-500 mt-1">Get AI-powered insights</p>
            </Link>
            <Link to="/org-chart" className="card hover:shadow-lg transition-shadow">
              <h3 className="font-medium">Org Chart</h3>
              <p className="text-sm text-gray-500 mt-1">Visualize structure</p>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'purple' | 'yellow' | 'indigo' | 'red';
}

function MetricCard({ title, value, subtitle, icon: Icon, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    indigo: 'bg-indigo-50 text-indigo-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
