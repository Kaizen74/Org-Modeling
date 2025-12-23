import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts'
import type { MetricsSummary, Metric } from '../api/types'
import {
  Users,
  DollarSign,
  Layers,
  GitBranch,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from 'lucide-react'

interface MetricsDashboardProps {
  metrics: MetricsSummary | null
  onRefresh: () => void
}

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  status,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  status?: 'healthy' | 'warning' | 'critical'
}) {
  const statusColors = {
    healthy: 'text-green-500',
    warning: 'text-yellow-500',
    critical: 'text-red-500',
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-2 rounded-lg ${status ? 'bg-slate-100' : 'bg-blue-100'}`}>
          <Icon className={`h-5 w-5 ${status ? statusColors[status] : 'text-blue-600'}`} />
        </div>
      </div>
    </div>
  )
}

export default function MetricsDashboard({ metrics, onRefresh }: MetricsDashboardProps) {
  const spanDistribution = useMemo(() => {
    if (!metrics?.metrics) return []
    const spanMetric = metrics.metrics.find((m) => m.metric_type === 'span_distribution')
    if (!spanMetric?.breakdown?.distribution) return []

    return Object.entries(spanMetric.breakdown.distribution).map(([span, count]) => ({
      span: `${span} reports`,
      count: count as number,
    }))
  }, [metrics])

  const functionData = useMemo(() => {
    if (!metrics?.metrics) return []
    const funcMetric = metrics.metrics.find((m) => m.metric_type === 'function_distribution')
    if (!funcMetric?.breakdown) return []

    return Object.entries(funcMetric.breakdown).slice(0, 8).map(([name, count], i) => ({
      name,
      value: count as number,
      fill: COLORS[i % COLORS.length],
    }))
  }, [metrics])

  const levelData = useMemo(() => {
    if (!metrics?.metrics) return []
    const levelMetric = metrics.metrics.find((m) => m.metric_type === 'level_distribution')
    if (!levelMetric?.breakdown) return []

    return Object.entries(levelMetric.breakdown)
      .filter(([level]) => level !== 'Unknown' && level !== '0')
      .map(([level, count]) => ({
        level: `Level ${level}`,
        count: count as number,
      }))
      .sort((a, b) => parseInt(a.level.split(' ')[1]) - parseInt(b.level.split(' ')[1]))
  }, [metrics])

  if (!metrics) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500">
        <Layers className="h-12 w-12 mb-4 text-slate-300" />
        <p className="mb-4">No metrics calculated yet</p>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="h-5 w-5" />
          Calculate Metrics
        </button>
      </div>
    )
  }

  const getMetricStatus = (type: string): 'healthy' | 'warning' | 'critical' | undefined => {
    const metric = metrics.metrics.find((m) => m.metric_type === type)
    return metric?.status as 'healthy' | 'warning' | 'critical' | undefined
  }

  return (
    <div className="p-6 overflow-auto h-full">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          title="Total Headcount"
          value={metrics.total_headcount.toLocaleString()}
          icon={Users}
        />
        <MetricCard
          title="Total FTE"
          value={metrics.total_fte.toLocaleString()}
          icon={Users}
        />
        <MetricCard
          title="Total Cost"
          value={`$${(metrics.total_cost / 1000000).toFixed(1)}M`}
          subtitle="Loaded cost"
          icon={DollarSign}
        />
        <MetricCard
          title="Hierarchy Layers"
          value={metrics.max_layers}
          icon={Layers}
          status={getMetricStatus('hierarchy_depth')}
        />
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          title="Avg Span of Control"
          value={`${metrics.avg_span_of_control.toFixed(1)}:1`}
          icon={GitBranch}
          status={getMetricStatus('span_of_control_avg')}
        />
        <MetricCard
          title="Functions"
          value={metrics.functions.length}
          icon={TrendingUp}
        />
        <MetricCard
          title="Locations"
          value={metrics.locations.length}
          icon={TrendingUp}
        />
        <MetricCard
          title="Warnings"
          value={metrics.metrics.filter((m) => m.status === 'warning').length}
          icon={AlertTriangle}
          status={metrics.metrics.some((m) => m.status === 'warning') ? 'warning' : 'healthy'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Span Distribution */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold mb-4">Span of Control Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={spanDistribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="span" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Function Distribution */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold mb-4">Headcount by Function</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={functionData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {functionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Level Distribution */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold mb-4">Headcount by Level</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={levelData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis dataKey="level" type="category" tick={{ fontSize: 12 }} width={60} />
              <Tooltip />
              <Bar dataKey="count" fill="#22c55e" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* All Metrics List */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold mb-4">All Metrics</h3>
          <div className="space-y-2 max-h-[250px] overflow-auto">
            {metrics.metrics.map((metric) => (
              <div
                key={metric.id || metric.metric_type}
                className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
              >
                <div className="flex items-center gap-2">
                  {metric.status === 'healthy' && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {metric.status === 'warning' && (
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  )}
                  {metric.status === 'critical' && (
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  )}
                  {!metric.status && <div className="w-4" />}
                  <span className="text-sm text-slate-600">
                    {metric.metric_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="font-medium">{metric.value_formatted || metric.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
