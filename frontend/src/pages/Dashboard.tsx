import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { metricsApi, settingsApi } from '../services/api';
import type { MetricsSummary, HealthComponent } from '../types';
import {
  PageHeader,
  Section,
  StatTile,
  StatusPill,
  ScoreBar,
  ScoreLegend,
  Callout,
  EmptyState,
  Loading,
  scoreStatus,
  formatMoney,
} from '../components/ui';

/** The component costing the most points (shortfall × weight) is the headline. */
function biggestDrag(components: HealthComponent[]): HealthComponent | undefined {
  return [...components].sort((a, b) => (100 - b.score) * b.weight - (100 - a.score) * a.weight)[0];
}

export default function Dashboard() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [apiConfigured, setApiConfigured] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const status = await settingsApi.getStatus();
        setApiConfigured(status.configured);
        setSummary(await metricsApi.getSummary());
      } catch (err) {
        setError('Upload an org structure CSV to see its health.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <Loading label="Reading the organization" />;

  if (error || !summary) {
    return (
      <>
        <PageHeader eyebrow="01 · Diagnose" title="Start with the current state" />
        <EmptyState
          title="No organization loaded yet"
          body={error}
          action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>}
        />
      </>
    );
  }

  const components = summary.health_components ?? [];
  const drag = biggestDrag(components);
  const status = scoreStatus(summary.health_score);

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — overview"
        title={`Structural health is ${summary.health_score} out of 100`}
        lede={
          drag && drag.score < 70
            ? <>The biggest drag is <strong className="text-ink">{drag.label.toLowerCase()}</strong>: {drag.value}.</>
            : 'No single structural factor is dragging the score down.'
        }
        actions={<Link to="/metrics" className="btn btn-secondary">See the full structure →</Link>}
      />

      {!apiConfigured && (
        <div className="mb-8">
          <Callout label="AI analysis is off" tone="accent">
            Add your Claude API key in <Link to="/settings" className="text-primary-600 underline">Settings</Link> to
            unlock work-activity and archetype analysis. Structure metrics work without it.
          </Callout>
        </div>
      )}

      {/* Status band: the score and what drives it */}
      <div className="mb-14 grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <div className="card flex flex-col justify-between">
          <div>
            <p className="eyebrow eyebrow-faint mb-4">Structural health</p>
            <p className="display-number text-[88px] text-ink">
              {summary.health_score}
              <span className="text-[32px] text-faint">/100</span>
            </p>
            <div className="mt-4"><StatusPill status={status} /></div>
          </div>
          {components.length > 0 && (
            <dl className="mt-8 divide-y divide-hairline border-y border-hairline text-sm">
              {[
                { term: 'Strongest check', c: [...components].sort((a, b) => b.score - a.score)[0] },
                { term: 'Weakest check', c: [...components].sort((a, b) => a.score - b.score)[0] },
              ].map(({ term, c }) => (
                <div key={term} className="flex items-baseline justify-between gap-4 py-3">
                  <dt className="text-faint">{term}</dt>
                  <dd className="text-right font-medium text-ink">
                    {c.label} <span className="tabular text-secondary">· {c.score}</span>
                  </dd>
                </div>
              ))}
            </dl>
          )}
          <p className="mt-6 text-sm text-faint">
            A weighted blend of four structural checks against published benchmarks. Hover a bar to see its rule and source.
          </p>
        </div>

        <div className="card">
          <p className="eyebrow eyebrow-faint mb-5">What drives the score</p>
          <div className="space-y-5">
            {components.map((c) => (
              <div key={c.key} title={`${c.rule}. Source: ${c.source}`}>
                <ScoreBar score={c.score} label={`${c.label} · weight ${c.weight}%`} detail={c.value} />
              </div>
            ))}
          </div>
          <div className="mt-6 hairline-t pt-4"><ScoreLegend /></div>
        </div>
      </div>

      {/* Context band: the headline numbers */}
      <Section eyebrow="The organization in numbers">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatTile
            label="People"
            value={summary.total_employees.toLocaleString()}
            sub={summary.departments ? `${summary.departments} department${summary.departments === 1 ? '' : 's'}` : undefined}
          />
          <StatTile label="Managers" value={summary.total_managers.toLocaleString()} sub={`${summary.manager_ratio.toFixed(1)}% of people`} />
          <StatTile label="Average span" value={summary.average_span.toFixed(1)} sub="direct reports per manager" />
          <StatTile label="Layers" value={summary.layers} sub="in the reporting chain" />
          <StatTile label="People cost" value={formatMoney(summary.total_cost)} sub="annual salary base" />
        </div>
      </Section>

      {/* Detail band: what to do about it */}
      {summary.warnings.length > 0 && (
        <Section eyebrow="Where to look first" title="Structural signals worth investigating">
          <ol className="card divide-y divide-hairline p-0">
            {summary.warnings.map((warning, i) => (
              <li key={i} className="grid grid-cols-[64px_1fr] gap-4 px-6 py-5">
                <span className="display-number text-[34px] text-placeholder">{String(i + 1).padStart(2, '0')}</span>
                <div>
                  <p className="font-medium text-ink">{warning}</p>
                  {summary.recommendations?.[i] && <p className="mt-1 text-sm text-secondary">{summary.recommendations[i]}</p>}
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {summary.data_issues && summary.data_issues.length > 0 && (
        <Section eyebrow="Data quality">
          <Callout label="Check the source data" tone="developing">
            <ul className="space-y-1">
              {summary.data_issues.map((issue, i) => <li key={i}>· {issue}</li>)}
            </ul>
          </Callout>
        </Section>
      )}

      <Section eyebrow="Next steps">
        <div className="grid gap-px overflow-hidden border border-hairline bg-hairline md:grid-cols-3">
          {[
            { n: '01', to: '/metrics', title: 'Inspect the structure', body: 'Spans by manager, layers, cost by layer and department.' },
            { n: '02', to: '/work-activities', title: 'Read the work', body: 'Duplication, missing activities and weak hand-offs.' },
            { n: '03', to: '/analysis', title: 'Explore structural options', body: 'Score the seven archetypes against your strategy.' },
          ].map((step) => (
            <Link key={step.to} to={step.to} className="group bg-white p-6 transition-colors hover:bg-wash">
              <span className="display-number text-[34px] text-placeholder">{step.n}</span>
              <h3 className="mt-2 text-[20px]">{step.title}</h3>
              <p className="mt-1 text-sm text-secondary">{step.body}</p>
              <span className="mt-4 inline-block text-sm font-semibold text-primary-600">Open →</span>
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}
