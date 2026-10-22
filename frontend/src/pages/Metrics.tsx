import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { metricsApi } from '../services/api';
import type { OrgMetrics, ManagerSpanAssessment } from '../types';
import {
  PageHeader,
  Section,
  StatTile,
  BenchmarkPill,
  ScoreBar,
  ScoreLegend,
  Callout,
  Chip,
  EmptyState,
  Loading,
  formatMoney,
} from '../components/ui';

type SpanFilter = 'all' | 'below' | 'within' | 'above';

const BENCH_COLORS = {
  below: 'var(--color-score-amber)',
  within: 'var(--color-score-green)',
  above: 'var(--color-score-red)',
};

/** Horizontal bar used inside tables and lists (bars start at zero). */
function InlineBar({ value, max, color = 'var(--color-ink)' }: { value: number; max: number; color?: string }) {
  return (
    <span className="block h-1.5 w-full rounded-full bg-track">
      <span className="block h-full rounded-full" style={{ width: `${max ? (value / max) * 100 : 0}%`, background: color }} />
    </span>
  );
}

export default function Metrics() {
  const [metrics, setMetrics] = useState<OrgMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [spanFilter, setSpanFilter] = useState<SpanFilter>('all');
  const [deptFilter, setDeptFilter] = useState('');
  const [showAllManagers, setShowAllManagers] = useState(false);

  useEffect(() => {
    metricsApi
      .getLatest()
      .then((r) => setMetrics(r.metrics))
      .catch(() => setError('Upload an org structure CSV to see its structure.'))
      .finally(() => setLoading(false));
  }, []);

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      setMetrics((await metricsApi.recalculate()).metrics);
    } finally {
      setRecalculating(false);
    }
  };

  const assessments = useMemo<ManagerSpanAssessment[]>(
    () => metrics?.span_of_control.manager_assessments ?? [],
    [metrics]
  );
  const filteredManagers = assessments.filter(
    (a) => (spanFilter === 'all' || a.status === spanFilter) && (!deptFilter || a.department === deptFilter)
  );

  if (loading) return <Loading label="Calculating the structure" />;
  if (error || !metrics) {
    return (
      <>
        <PageHeader eyebrow="01 · Diagnose — structure" title="Structure" />
        <EmptyState title="No organization loaded yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} />
      </>
    );
  }

  const span = metrics.span_of_control;
  const vs = span.distribution_vs_benchmark ?? { 'Below benchmark': 0, 'Within benchmark': 0, 'Above benchmark': 0 };
  const managers = metrics.manager_stats.total_managers;
  const below = vs['Below benchmark'];
  const within = vs['Within benchmark'];
  const above = vs['Above benchmark'];
  const depts = metrics.department_analysis ?? [];
  const layers = metrics.layer_analysis;
  const layerRows = Object.entries(layers.by_level)
    .map(([layer, v]) => ({ layer: Number(layer), count: v.count }))
    .sort((a, b) => a.layer - b.layer);
  const maxLayerCount = Math.max(1, ...layerRows.map((r) => r.count));
  const costByLayer = Object.entries(metrics.cost_analysis.by_level ?? {})
    .map(([layer, v]) => ({ layer: Number(layer), ...v }))
    .sort((a, b) => a.layer - b.layer);
  const maxLayerCost = Math.max(1, ...costByLayer.map((r) => r.total_cost));
  const costByGrade = Object.entries(metrics.cost_analysis.by_grade ?? {})
    .map(([grade, v]) => ({ grade, ...v }))
    .sort((a, b) => b.total_cost - a.total_cost);
  const maxDeptHeadcount = Math.max(1, ...depts.map((d) => d.headcount));
  const layersComponent = metrics.health_indicators.components?.find((c) => c.key === 'layers');

  const headline =
    managers === 0
      ? 'No reporting lines found'
      : within * 2 >= managers
        ? `${within} of ${managers} managers have spans that fit their work`
        : below >= above
          ? `${below} of ${managers} managers run teams narrower than their benchmark`
          : `${above} of ${managers} managers run teams wider than their benchmark`;

  const shownManagers = showAllManagers ? filteredManagers : filteredManagers.slice(0, 20);

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — structure"
        title={headline}
        lede={`Spans are judged against the benchmark for each team's kind of work: knowledge work 5–10 direct reports, operational work 15–25. Average span ${span.average_span.toFixed(1)}, median ${span.median_span}.`}
        actions={
          <>
            <button onClick={handleRecalculate} disabled={recalculating} className="btn btn-quiet">
              {recalculating ? 'Recalculating…' : 'Recalculate'}
            </button>
            <Link to="/org-chart" className="btn btn-secondary">See the org chart →</Link>
          </>
        }
      />

      <div className="mb-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile label="People" value={metrics.total_employees.toLocaleString()} sub={depts.length ? `${depts.length} departments` : undefined} />
        <StatTile label="Managers" value={managers} sub={`${metrics.manager_stats.manager_ratio_pct}% of people`} />
        <StatTile label="Median span" value={span.median_span} sub={`range ${span.min_span}–${span.max_span}`} />
        <StatTile
          label="Layers"
          value={layers.total_layers}
          sub={layers.declared_layers && layers.declared_layers !== layers.total_layers ? `Level column says ${layers.declared_layers}` : 'in the reporting chain'}
        />
        <StatTile label="Cost per person" value={formatMoney(metrics.cost_analysis.average_cost_per_employee)} sub={`${formatMoney(metrics.cost_analysis.total_cost)} in total`} />
      </div>

      {/* Spans */}
      <Section eyebrow="01 · Spans" title="Every manager against the benchmark for their work">
        {managers > 0 && (
          <div className="card mb-4">
            <div className="flex h-3 w-full overflow-hidden rounded-full" role="img" aria-label={`${below} below, ${within} within, ${above} above benchmark`}>
              {([['below', below], ['within', within], ['above', above]] as const).map(([k, n]) =>
                n ? <span key={k} style={{ width: `${(n / managers) * 100}%`, background: BENCH_COLORS[k] }} /> : null
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-6 text-sm">
              {([['below', below, 'below benchmark'], ['within', within, 'within'], ['above', above, 'above']] as const).map(([k, n, label]) => (
                <span key={k} className="flex items-center gap-2">
                  <BenchmarkPill status={k} />
                  <span className="tabular font-semibold text-ink">{n}</span>
                  <span className="text-secondary">{label}</span>
                </span>
              ))}
              {!!span.single_report_managers && (
                <span className="text-secondary">· <span className="tabular font-semibold text-ink">{span.single_report_managers}</span> managers with one direct report</span>
              )}
            </div>
          </div>
        )}

        <div className="mb-3 flex flex-wrap items-center gap-2">
          {(['all', 'below', 'within', 'above'] as SpanFilter[]).map((f) => (
            <Chip key={f} active={spanFilter === f} onClick={() => setSpanFilter(f)}>
              {f === 'all' ? `All managers (${assessments.length})` : `${f[0].toUpperCase()}${f.slice(1)} (${assessments.filter((a) => a.status === f).length})`}
            </Chip>
          ))}
          {depts.length > 1 && (
            <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="input ml-auto w-auto py-1.5 text-sm" aria-label="Filter by department">
              <option value="">All departments</option>
              {depts.map((d) => <option key={d.department} value={d.department}>{d.department}</option>)}
            </select>
          )}
        </div>

        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                <th className="px-6 py-3">Manager</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Team's work</th>
                <th className="px-4 py-3 text-right">Span</th>
                <th className="px-4 py-3 text-right">Benchmark</th>
                <th className="px-6 py-3">Position</th>
              </tr>
            </thead>
            <tbody>
              {shownManagers.map((a) => (
                <tr key={a.manager_id} className="hairline-b last:border-0">
                  <td className="px-6 py-3">
                    <p className="font-medium text-ink">{a.manager}</p>
                    <p className="text-xs text-faint">{a.job_title}</p>
                  </td>
                  <td className="px-4 py-3 text-secondary">{a.department}</td>
                  <td className="px-4 py-3 text-secondary" title={`Why: ${a.work_type_basis}`}>
                    {a.work_type === 'operational' ? 'Operational' : 'Knowledge'}
                    <span className="block text-xs text-faint">{a.work_type_basis}</span>
                  </td>
                  <td className="tabular px-4 py-3 text-right font-semibold text-ink">{a.span}</td>
                  <td className="tabular px-4 py-3 text-right text-secondary">{a.benchmark_range[0]}–{a.benchmark_range[1]}</td>
                  <td className="px-6 py-3"><BenchmarkPill status={a.status} /></td>
                </tr>
              ))}
              {filteredManagers.length === 0 && (
                <tr><td colSpan={6} className="px-6 py-6 text-center text-faint">No managers match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {filteredManagers.length > 20 && (
          <button onClick={() => setShowAllManagers(!showAllManagers)} className="mt-3 text-sm font-semibold text-primary-600">
            {showAllManagers ? 'Show fewer' : `Show all ${filteredManagers.length} managers`}
          </button>
        )}
        <p className="mt-3 text-xs text-faint">
          A team's work is read from an optional Work Type column, else from its members: mostly managers → knowledge range; operational job titles → operational range.
        </p>
      </Section>

      {/* Departments */}
      {depts.length > 0 && (
        <Section eyebrow="02 · Departments" title="The same lenses, department by department" lede="Sorted by size. Bars start at zero.">
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                  <th className="px-6 py-3">Department</th>
                  <th className="w-48 px-4 py-3">People</th>
                  <th className="px-4 py-3 text-right">Managers</th>
                  <th className="px-4 py-3 text-right">Avg span</th>
                  <th className="px-4 py-3">Spans vs benchmark</th>
                  <th className="px-4 py-3 text-right">Layers</th>
                  <th className="px-4 py-3 text-right">Cost share</th>
                  <th className="px-6 py-3 text-right">Reports from other depts</th>
                </tr>
              </thead>
              <tbody>
                {depts.map((d) => (
                  <tr key={d.department} className="hairline-b align-top last:border-0">
                    <td className="px-6 py-3">
                      <p className="font-medium text-ink">{d.department}</p>
                      <p className="text-xs text-faint">{d.top_titles.slice(0, 3).map((t) => `${t.title} (${t.count})`).join(' · ')}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="tabular font-semibold text-ink">{d.headcount}</span>
                      <span className="ml-1 text-xs text-faint">{d.headcount_pct}%</span>
                      <span className="mt-1.5 block"><InlineBar value={d.headcount} max={maxDeptHeadcount} /></span>
                    </td>
                    <td className="tabular px-4 py-3 text-right text-secondary">{d.managers} <span className="text-xs text-faint">({d.manager_ratio_pct}%)</span></td>
                    <td className="tabular px-4 py-3 text-right font-semibold text-ink">{d.average_span || '–'}</td>
                    <td className="px-4 py-3">
                      <span className="tabular flex gap-3 text-xs">
                        <span style={{ color: BENCH_COLORS.below }}>↓ {d.spans_vs_benchmark.below}</span>
                        <span style={{ color: BENCH_COLORS.within }}>✓ {d.spans_vs_benchmark.within}</span>
                        <span style={{ color: BENCH_COLORS.above }}>↑ {d.spans_vs_benchmark.above}</span>
                      </span>
                      {!!d.single_report_managers && <span className="mt-1 block text-xs text-faint">{d.single_report_managers} with one report</span>}
                    </td>
                    <td className="tabular px-4 py-3 text-right text-secondary">{d.layers_spanned.join('–')}</td>
                    <td className="tabular px-4 py-3 text-right text-secondary">{d.cost_pct}%</td>
                    <td className="tabular px-6 py-3 text-right text-secondary">{d.reports_from_other_departments}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Layers */}
      <Section eyebrow="03 · Layers" title={layersComponent ? layersComponent.value : `${layers.total_layers} layers`}>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="card">
            <p className="label">People in each layer</p>
            <ul className="mt-3 space-y-3">
              {layerRows.map((r) => (
                <li key={r.layer} className="grid grid-cols-[72px_1fr_48px] items-center gap-3 text-sm">
                  <span className="text-secondary">Layer {r.layer}</span>
                  <InlineBar value={r.count} max={maxLayerCount} />
                  <span className="tabular text-right font-semibold text-ink">{r.count}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <p className="label">Longest reporting chain</p>
            {layers.longest_chain && layers.longest_chain.length > 0 ? (
              <ol className="mt-3 space-y-2">
                {layers.longest_chain.map((name, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm" style={{ paddingLeft: `${i * 14}px` }}>
                    <span className="tabular w-6 text-xs text-faint">{i + 1}</span>
                    <span className="text-ink">{name}</span>
                  </li>
                ))}
              </ol>
            ) : <p className="text-sm text-faint">Not available — recalculate to refresh.</p>}
            <p className="mt-4 text-xs text-faint">Start delayering conversations here: each step is a hand-off and an approval.</p>
          </div>
        </div>
        {layers.level_mismatches && layers.level_mismatches.count > 0 && (
          <div className="mt-4">
            <Callout label={`${layers.level_mismatches.count} Level values disagree with the reporting chain`} tone="developing">
              Layers above are counted from who reports to whom. Examples:{' '}
              {layers.level_mismatches.examples.slice(0, 5).map((m) => `${m.name} (Level ${m.declared_level}, actually layer ${m.actual_layer})`).join('; ')}.
            </Callout>
          </div>
        )}
      </Section>

      {/* Cost */}
      <Section eyebrow="04 · Cost" title={`${formatMoney(metrics.cost_analysis.total_cost)} annual people cost`}>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="card">
            <p className="label">Cost by layer</p>
            <ul className="mt-3 space-y-3">
              {costByLayer.map((r) => (
                <li key={r.layer} className="grid grid-cols-[72px_1fr_72px] items-center gap-3 text-sm">
                  <span className="text-secondary">Layer {r.layer}</span>
                  <InlineBar value={r.total_cost} max={maxLayerCost} />
                  <span className="tabular text-right font-semibold text-ink">{formatMoney(r.total_cost)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card overflow-x-auto">
            <p className="label">Cost by grade</p>
            <table className="mt-2 w-full text-sm">
              <tbody>
                {costByGrade.map((g) => (
                  <tr key={g.grade} className="hairline-b last:border-0">
                    <td className="py-2 font-medium text-ink">{g.grade}</td>
                    <td className="tabular py-2 text-right text-secondary">{g.count} people</td>
                    <td className="tabular py-2 text-right font-semibold text-ink">{formatMoney(g.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 text-sm text-secondary">
              Average grade gap between a manager and their reports:{' '}
              <span className="tabular font-semibold text-ink">{metrics.grade_gap_analysis.average_grade_gap.toFixed(2)}</span>
              <span className="text-faint"> ({metrics.grade_gap_analysis.total_comparisons} pairs)</span>
            </p>
            {metrics.grade_gap_analysis.unusual_gaps && metrics.grade_gap_analysis.unusual_gaps.length > 0 && (
              <p className="mt-1 text-xs text-faint">
                {metrics.grade_gap_analysis.unusual_gaps.length} pairs with a gap under 1 or over 4 grades, e.g.{' '}
                {metrics.grade_gap_analysis.unusual_gaps.slice(0, 2).map((g) => `${g.manager} (${g.manager_grade}) → ${g.subordinate} (${g.subordinate_grade})`).join('; ')}
              </p>
            )}
          </div>
        </div>
      </Section>

      {/* Health checks */}
      {metrics.health_indicators.components && (
        <Section eyebrow="05 · Health checks" title={`Structural health ${metrics.health_indicators.health_score}/100`}>
          <div className="card">
            <div className="grid gap-x-10 gap-y-6 md:grid-cols-2">
              {metrics.health_indicators.components.map((c) => (
                <div key={c.key}>
                  <ScoreBar score={c.score} label={`${c.label} · weight ${c.weight}%`} detail={c.value} />
                  <p className="mt-1 text-xs text-faint">{c.rule}. Benchmark: {c.benchmark}. Source: {c.source}.</p>
                </div>
              ))}
            </div>
            <div className="mt-6 hairline-t pt-4"><ScoreLegend /></div>
          </div>
        </Section>
      )}

      <Callout label="Next: read the work" tone="accent">
        Structure shows who reports to whom. <Link to="/work-activities" className="text-primary-600 underline">Work activities</Link> shows
        what those people do — duplication, gaps and weak hand-offs.
      </Callout>
    </>
  );
}
