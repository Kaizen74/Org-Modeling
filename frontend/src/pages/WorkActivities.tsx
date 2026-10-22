import { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { aiAnalysisApi, settingsApi } from '../services/api';
import AIRoleOverlay from '../components/AIRoleOverlay';
import { FIVE_DIMENSIONS } from '../types';
import type {
  WorkActivitiesAnalysis,
  QuickWorkActivitiesAnalysis,
  DimensionTag,
  StructuralRecommendation,
} from '../types';
import {
  PageHeader,
  Section,
  StatTile,
  StatusPill,
  ScoreBar,
  Callout,
  Chip,
  Disclosure,
  EmptyState,
  severityStatus,
} from '../components/ui';

function plural(n: number, singular: string, pluralForm = `${singular}s`) {
  return `${n} ${n === 1 ? singular : pluralForm}`;
}

/** Tag row shown on every finding: dimension, indicator type, confidence. */
function FindingTags({ item, confidence, rationale }: { item: DimensionTag; confidence?: string; rationale?: string }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {item.dimension && <Chip>{item.dimension}</Chip>}
      {item.indicator_type && <Chip>{item.indicator_type} indicator</Chip>}
      {confidence && (
        <span className="text-xs text-faint" title={rationale || ''}>
          Confidence: <span className="font-semibold text-secondary">{confidence}</span>
          {rationale && <span className="ml-1">— {rationale}</span>}
        </span>
      )}
    </div>
  );
}

function FindingRow({
  n,
  title,
  meta,
  severity,
  children,
}: {
  n: number;
  title: string;
  meta?: ReactNode;
  severity?: string;
  children?: ReactNode;
}) {
  return (
    <li className="grid grid-cols-[48px_1fr] gap-4 px-6 py-5">
      <span className="display-number text-[26px] text-placeholder">{String(n).padStart(2, '0')}</span>
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <p className="font-medium text-ink">{title}</p>
          {severity && <StatusPill status={severityStatus(severity)} label={severity} />}
        </div>
        {meta && <p className="mt-1 text-sm text-faint">{meta}</p>}
        {children}
      </div>
    </li>
  );
}

function RecommendationList({ title, items }: { title: string; items?: StructuralRecommendation[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-8">
      <p className="label">{title}</p>
      <ul className="divide-y divide-hairline border-y border-hairline">
        {items.map((rec, i) => (
          <li key={i} className="py-3">
            <p className="font-medium text-ink">{rec.recommendation}</p>
            {(rec.rationale || rec.addresses) && (
              <p className="mt-1 text-sm text-secondary">{rec.rationale || `Addresses: ${rec.addresses}`}</p>
            )}
            <p className="mt-1 text-xs text-faint">
              {[rec.priority && `Priority ${rec.priority}`, rec.impact && `Impact ${rec.impact}`, rec.effort && `Effort ${rec.effort}`]
                .filter(Boolean)
                .join(' · ')}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function WorkActivities() {
  const [analysis, setAnalysis] = useState<WorkActivitiesAnalysis | null>(null);
  const [quick, setQuick] = useState<QuickWorkActivitiesAnalysis | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [industry, setIndustry] = useState('');

  useEffect(() => {
    settingsApi.getStatus().then((s) => setApiConfigured(s.configured)).catch(() => undefined);
    aiAnalysisApi.getQuickWorkActivities().then(setQuick).catch(() => undefined);
    aiAnalysisApi.getLatestWorkActivities().then((r) => setAnalysis(r.work_activities_analysis)).catch(() => undefined);
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await aiAnalysisApi.analyzeWorkActivities(industry || undefined);
      setAnalysis(result.work_activities_analysis);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'The work activities analysis could not be completed.');
    } finally {
      setRunning(false);
    }
  };

  const noActivities = quick !== null && quick.employees_with_work_activities === 0;
  const result = analysis && !analysis.error ? analysis : null;
  const duplications = result?.activity_duplication?.duplications ?? [];
  const missing = result?.missing_activities?.gaps ?? [];
  const handoffs = result?.coordination_gaps?.gaps ?? [];

  // Findings by dimension: rows = five dimensions, columns = the three core analyses
  const byDimension = FIVE_DIMENSIONS.map((dim) => ({
    dim,
    duplication: duplications.filter((d) => d.dimension === dim).length,
    missing: missing.filter((g) => g.dimension === dim).length,
    handoffs: handoffs.filter((g) => g.dimension === dim).length,
  }));
  const untagged = [...duplications, ...missing, ...handoffs].filter(
    (f) => !f.dimension || !(FIVE_DIMENSIONS as readonly string[]).includes(f.dimension)
  ).length;
  const maxCell = Math.max(1, ...byDimension.flatMap((r) => [r.duplication, r.missing, r.handoffs]));

  const title = result
    ? `${plural(duplications.length, 'duplication')}, ${plural(missing.length, 'missing activity', 'missing activities')}, ${plural(handoffs.length, 'weak hand-off')}`
    : 'What the work is, role by role';

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — work activities"
        title={title}
        lede={
          result
            ? 'Where work overlaps between roles, what is missing against industry practice, and where hand-offs between departments need strengthening.'
            : 'Analyze the work activities in your CSV for duplication across roles, gaps against industry practice, and weak hand-offs between departments.'
        }
      />

      {/* Coverage */}
      {quick && (
        <Section eyebrow="Data coverage">
          <div className="grid gap-4 md:grid-cols-3">
            <StatTile
              label="Positions described"
              value={`${quick.employees_with_work_activities} / ${quick.total_employees}`}
              sub="have work activities in the CSV"
            />
            <StatTile
              label="Coverage"
              value={`${quick.coverage_percentage}%`}
              status={quick.coverage_percentage >= 80 ? 'healthy' : quick.coverage_percentage >= 20 ? 'developing' : 'attention'}
            />
            <StatTile label="Departments covered" value={quick.departments_with_activities} />
          </div>
          {quick.status !== 'complete' && !noActivities && (
            <div className="mt-4">
              <Callout label="Partial coverage" tone="developing">
                {quick.status === 'minimal'
                  ? 'Few positions describe their work, so findings will be indicative only.'
                  : 'Some positions have no work activities; findings cover only the described roles.'}
              </Callout>
            </div>
          )}
          {quick.potential_duplications && quick.potential_duplications.length > 0 && (
            <div className="card mt-4">
              <p className="label">Early signals — shared words across roles (no AI)</p>
              <div className="flex flex-wrap gap-2">
                {quick.potential_duplications.map((d) => (
                  <span key={d.keyword} title={d.roles.join(', ')}>
                    <Chip>{d.keyword} · {d.roles_count} roles</Chip>
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {noActivities ? (
        <EmptyState
          title="No work activities in this upload"
          body='Add a "Work Activities" column to your CSV describing what each role does, then upload it again.'
          action={<Link to="/upload" className="btn btn-primary">Upload data →</Link>}
        />
      ) : (
        <Section eyebrow={result ? 'Re-run the analysis' : 'Run the analysis'}>
          {apiConfigured ? (
            <div className="card flex flex-col gap-4 md:flex-row md:items-end">
              <div className="flex-1">
                <label className="label" htmlFor="industry">Industry context (optional)</label>
                <input
                  id="industry"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="input"
                  placeholder="e.g. Aviation ground services, Airlines, Healthcare"
                />
                <p className="mt-1.5 text-xs text-faint">Sharpens the industry comparison. Only job titles and activities are sent — never names.</p>
              </div>
              <button onClick={handleRun} disabled={running} className="btn btn-primary whitespace-nowrap">
                {running ? 'Analyzing — about a minute…' : result ? 'Re-run analysis' : 'Run current-state analysis'}
              </button>
            </div>
          ) : (
            <Callout label="AI analysis is off" tone="accent">
              Add your Claude API key in <Link to="/settings" className="text-primary-600 underline">Settings</Link> to run this analysis.
            </Callout>
          )}
          {error && <div className="mt-4"><Callout label="Analysis failed" tone="attention">{error}</Callout></div>}
          {analysis?.error && !error && (
            <div className="mt-4"><Callout label="Last analysis failed" tone="attention">{analysis.error}</Callout></div>
          )}
          {result?.parse_warning && (
            <div className="mt-4"><Callout label="Incomplete response" tone="developing">{result.parse_warning}</Callout></div>
          )}
        </Section>
      )}

      {!noActivities && <AIRoleOverlay />}

      {result && (
        <>
          {result.executive_summary && (
            <Section eyebrow="Interpretation · AI">
              <p className="max-w-[760px] whitespace-pre-line font-display text-[20px] leading-relaxed text-ink">
                {result.executive_summary}
              </p>
            </Section>
          )}

          {/* The three core findings at a glance */}
          <Section eyebrow="02 · Core findings">
            <div className="grid gap-px overflow-hidden border border-hairline bg-hairline md:grid-cols-3">
              {[
                { label: 'Duplicated work', count: duplications.length, severity: result.activity_duplication?.severity_assessment, summary: result.activity_duplication?.summary, anchor: '#duplication' },
                { label: 'Missing activities', count: missing.length, severity: result.missing_activities?.severity_assessment, summary: result.missing_activities?.summary, anchor: '#missing' },
                { label: 'Weak hand-offs', count: handoffs.length, severity: result.coordination_gaps?.severity_assessment, summary: result.coordination_gaps?.summary, anchor: '#handoffs' },
              ].map((c) => (
                <a key={c.label} href={c.anchor} className="bg-white p-6 transition-colors hover:bg-wash">
                  <p className="eyebrow eyebrow-faint">{c.label}</p>
                  <p className="display-number mt-3 text-[48px] text-ink">{c.count}</p>
                  {c.severity && <div className="mt-2"><StatusPill status={severityStatus(c.severity)} label={`${c.severity} overall`} /></div>}
                  {c.summary && <p className="mt-3 line-clamp-3 text-sm text-secondary">{c.summary}</p>}
                </a>
              ))}
            </div>
          </Section>

          {/* Findings by dimension */}
          <Section
            eyebrow="03 · By dimension"
            title="Where the findings sit across the five dimensions"
            lede="Each finding is tagged with one dimension. Darker cells hold more findings."
          >
            <div className="card overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="hairline-b text-left">
                    <th className="px-6 py-3 text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Dimension</th>
                    <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Duplication</th>
                    <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Missing</th>
                    <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Hand-offs</th>
                  </tr>
                </thead>
                <tbody>
                  {byDimension.map((row) => (
                    <tr key={row.dim} className="hairline-b last:border-0">
                      <td className="px-6 py-3 font-medium text-ink">{row.dim}</td>
                      {[row.duplication, row.missing, row.handoffs].map((n, i) => (
                        <td key={i} className="px-4 py-2 text-center">
                          <span
                            className="tabular inline-flex h-9 w-12 items-center justify-center rounded font-semibold"
                            style={{
                              background: n ? `rgba(28,31,36,${0.08 + 0.5 * (n / maxCell)})` : 'transparent',
                              color: n / maxCell > 0.6 ? '#fff' : n ? 'var(--color-ink)' : 'var(--color-placeholder)',
                            }}
                          >
                            {n || '–'}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {untagged > 0 && (
              <p className="mt-2 text-xs text-faint">
                {plural(untagged, 'finding')} not tagged with a dimension (analyses run before dimension tagging) — re-run to tag them.
              </p>
            )}
          </Section>

          {/* Detail: duplication */}
          {duplications.length > 0 && (
            <div id="duplication" className="scroll-mt-8">
              <Disclosure eyebrow="Duplication" title="Work done in more than one place" meta={<span className="text-sm text-faint">{plural(duplications.length, 'finding')}</span>}>
                <ol className="-mx-6 -my-6 divide-y divide-hairline">
                  {duplications.map((d, i) => (
                    <FindingRow
                      key={i}
                      n={i + 1}
                      title={d.activity}
                      severity={d.severity}
                      meta={[d.duplication_type, d.affected_roles?.join(', ')].filter(Boolean).join(' · ')}
                    >
                      {d.evidence && <p className="mt-2 text-sm text-secondary"><span className="font-semibold text-ink">Evidence:</span> {d.evidence}</p>}
                      {d.business_impact && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Impact:</span> {d.business_impact}</p>}
                      {d.recommended_action && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-primary-600">Action:</span> {d.recommended_action}</p>}
                      <FindingTags item={d} confidence={d.confidence} rationale={d.confidence_rationale} />
                    </FindingRow>
                  ))}
                </ol>
              </Disclosure>
            </div>
          )}

          {/* Detail: missing activities */}
          {missing.length > 0 && (
            <div id="missing" className="scroll-mt-8">
              <Disclosure eyebrow="Gaps vs industry practice" title="Activities the organization may be missing" meta={<span className="text-sm text-faint">{plural(missing.length, 'finding')}</span>}>
                <ol className="-mx-6 -my-6 divide-y divide-hairline">
                  {missing.map((g, i) => (
                    <FindingRow
                      key={i}
                      n={i + 1}
                      title={g.activity}
                      severity={g.severity}
                      meta={[g.affected_departments?.join(', '), g.affected_roles?.join(', ')].filter(Boolean).join(' · ')}
                    >
                      {g.industry_benchmark && <p className="mt-2 text-sm text-secondary"><span className="font-semibold text-ink">Industry practice (inferred):</span> {g.industry_benchmark}</p>}
                      {g.business_risk && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Risk:</span> {g.business_risk}</p>}
                      {g.recommendation && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-primary-600">Action:</span> {g.recommendation}</p>}
                      <FindingTags item={g} confidence={g.confidence} rationale={g.confidence_rationale} />
                    </FindingRow>
                  ))}
                </ol>
              </Disclosure>
            </div>
          )}

          {/* Detail: coordination */}
          {handoffs.length > 0 && (
            <div id="handoffs" className="scroll-mt-8">
              <Disclosure eyebrow="Coordination" title="Hand-offs that need strengthening" meta={<span className="text-sm text-faint">{plural(handoffs.length, 'finding')}</span>}>
                <ol className="-mx-6 -my-6 divide-y divide-hairline">
                  {handoffs.map((g, i) => (
                    <FindingRow
                      key={i}
                      n={i + 1}
                      title={g.handoff_point}
                      severity={g.severity}
                      meta={`${g.from_department} → ${g.to_department}${g.gap_type ? ` · ${g.gap_type}` : ''}`}
                    >
                      {g.current_state && <p className="mt-2 text-sm text-secondary"><span className="font-semibold text-ink">Today:</span> {g.current_state}</p>}
                      {g.industry_practice && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Leading practice (inferred):</span> {g.industry_practice}</p>}
                      {g.recommended_interface && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-primary-600">Add:</span> {g.recommended_interface}</p>}
                      <FindingTags item={g} confidence={g.confidence} rationale={g.confidence_rationale} />
                    </FindingRow>
                  ))}
                </ol>
              </Disclosure>
            </div>
          )}

          {/* Coherence */}
          {result.departmental_coherence && result.departmental_coherence.length > 0 && (
            <Disclosure eyebrow="Coherence" title="How well the work fits together within each department" defaultOpen={false}>
              {result.overall_coherence && (
                <div className="mb-8">
                  <ScoreBar score={result.overall_coherence.organization_coherence_score} label="Organization coherence" detail={result.overall_coherence.integration_assessment} />
                  <div className="mt-5 grid gap-6 md:grid-cols-2 text-sm">
                    {result.overall_coherence.cross_department_synergies?.length > 0 && (
                      <div>
                        <p className="label" style={{ color: 'var(--color-score-green)' }}>Synergies across departments</p>
                        <ul className="space-y-1 text-secondary">{result.overall_coherence.cross_department_synergies.map((s, i) => <li key={i}><span className="text-score-green">✓</span> {s}</li>)}</ul>
                      </div>
                    )}
                    {result.overall_coherence.cross_department_gaps?.length > 0 && (
                      <div>
                        <p className="label" style={{ color: 'var(--color-score-red)' }}>Gaps across departments</p>
                        <ul className="space-y-1 text-secondary">{result.overall_coherence.cross_department_gaps.map((g, i) => <li key={i}><span className="text-score-red">×</span> {g}</li>)}</ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div className="grid gap-x-10 gap-y-8 md:grid-cols-2">
                {result.departmental_coherence.map((d, i) => (
                  <div key={i}>
                    <ScoreBar score={d.coherence_score} label={`${d.department} · ${d.position_count} positions`} />
                    <p className="mt-2 text-sm text-secondary">{d.coherence_rationale}</p>
                    <p className="mt-1 text-xs text-faint">{[d.value_chain_position, d.internal_dependencies && `Dependencies: ${d.internal_dependencies}`].filter(Boolean).join(' · ')}</p>
                    {d.synergy_assessment?.strengths?.slice(0, 2).map((s, j) => <p key={`s${j}`} className="mt-1 text-sm text-secondary"><span className="text-score-green">✓</span> {s}</p>)}
                    {d.synergy_assessment?.gaps?.slice(0, 2).map((g, j) => <p key={`g${j}`} className="mt-1 text-sm text-secondary"><span className="text-score-red">×</span> {g}</p>)}
                    {d.synergy_assessment?.overlaps?.slice(0, 2).map((o, j) => <p key={`o${j}`} className="mt-1 text-sm text-secondary"><span className="text-score-amber">≈</span> {o}</p>)}
                  </div>
                ))}
              </div>
            </Disclosure>
          )}

          {/* Themes */}
          {result.work_themes && (
            <Disclosure eyebrow="Themes" title="The main kinds of work in the organization" defaultOpen={false}>
              <ScoreBar score={result.work_themes.strategic_alignment_score} label="Alignment of work themes with priorities" detail={result.work_themes.theme_distribution_assessment} />
              <ul className="mt-6 divide-y divide-hairline border-y border-hairline">
                {result.work_themes.primary_themes?.map((t, i) => (
                  <li key={i} className="grid gap-2 py-4 md:grid-cols-[1fr_auto]">
                    <div>
                      <p className="font-medium text-ink">{t.theme}</p>
                      <p className="text-sm text-secondary">{t.description}</p>
                      <p className="mt-1 text-xs text-faint">{t.departments_involved?.join(', ')}</p>
                    </div>
                    <div className="text-right text-sm">
                      <p className="tabular font-semibold text-ink">{t.percentage_of_org}% of org</p>
                      <p className="text-xs text-faint">{t.strategic_importance} importance</p>
                    </div>
                  </li>
                ))}
              </ul>
              {result.work_themes.missing_capabilities?.length > 0 && (
                <div className="mt-6">
                  <p className="label">Capabilities not found in the work</p>
                  <div className="flex flex-wrap gap-2">{result.work_themes.missing_capabilities.map((c, i) => <Chip key={i}>{c}</Chip>)}</div>
                </div>
              )}
            </Disclosure>
          )}

          {/* Industry comparison */}
          {result.industry_comparison && (
            <Disclosure eyebrow="Industry comparison (inferred)" title={`Against ${result.industry_comparison.industry_identified || 'industry'} practice`} defaultOpen={false}>
              {result.industry_comparison.activity_mix_assessment && (
                <div className="grid gap-8 md:grid-cols-2">
                  <div>
                    <ScoreBar score={result.industry_comparison.activity_mix_assessment.alignment_score} label="Activity mix alignment" />
                    {result.industry_comparison.activity_mix_assessment.unique_strengths?.length > 0 && (
                      <div className="mt-4">
                        <p className="label">Distinctive strengths</p>
                        <ul className="space-y-1 text-sm text-secondary">{result.industry_comparison.activity_mix_assessment.unique_strengths.map((s, i) => <li key={i}><span className="text-score-green">✓</span> {s}</li>)}</ul>
                      </div>
                    )}
                  </div>
                  <div className="text-sm">
                    {result.industry_comparison.activity_mix_assessment.over_represented?.length > 0 && (
                      <p className="mb-2 text-secondary"><span className="font-semibold text-ink">Over-represented:</span> {result.industry_comparison.activity_mix_assessment.over_represented.join(', ')}</p>
                    )}
                    {result.industry_comparison.activity_mix_assessment.under_represented?.length > 0 && (
                      <p className="mb-2 text-secondary"><span className="font-semibold text-ink">Under-represented:</span> {result.industry_comparison.activity_mix_assessment.under_represented.join(', ')}</p>
                    )}
                    {result.industry_comparison.role_specialization && (
                      <p className="text-secondary"><span className="font-semibold text-ink">Role specialization:</span> {result.industry_comparison.role_specialization.assessment} — {result.industry_comparison.role_specialization.rationale}</p>
                    )}
                  </div>
                </div>
              )}
              {result.industry_comparison.competitive_positioning && (
                <div className="mt-8 hairline-t pt-6">
                  <p className="font-display text-[18px] italic text-ink">{result.industry_comparison.competitive_positioning.overall_assessment}</p>
                  <div className="mt-4 grid gap-6 text-sm md:grid-cols-2">
                    <ul className="space-y-1 text-secondary">{result.industry_comparison.competitive_positioning.potential_advantages?.map((a, i) => <li key={i}><span className="text-score-green">✓</span> {a}</li>)}</ul>
                    <ul className="space-y-1 text-secondary">{result.industry_comparison.competitive_positioning.potential_disadvantages?.map((d, i) => <li key={i}><span className="text-score-red">×</span> {d}</li>)}</ul>
                  </div>
                </div>
              )}
            </Disclosure>
          )}

          {/* Recommendations */}
          {result.recommendations && (
            <Disclosure eyebrow="04 · What to do" title="Recommendations">
              {result.recommendations.quick_wins && result.recommendations.quick_wins.length > 0 && (
                <div className="mb-8">
                  <p className="label">Quick wins</p>
                  <ul className="space-y-1.5 text-secondary">{result.recommendations.quick_wins.map((w, i) => <li key={i}><span className="mr-2 text-primary-600">·</span>{w}</li>)}</ul>
                </div>
              )}
              <RecommendationList title="Resolve duplication" items={result.recommendations.duplication_resolution} />
              <RecommendationList title="Add missing activities" items={result.recommendations.missing_activity_additions} />
              <RecommendationList title="Strengthen coordination" items={result.recommendations.coordination_improvements} />
              <RecommendationList title="Structural" items={result.recommendations.structural} />
              {result.recommendations.role_optimization && result.recommendations.role_optimization.length > 0 && (
                <div className="mb-8">
                  <p className="label">Role changes</p>
                  <ul className="divide-y divide-hairline border-y border-hairline">
                    {result.recommendations.role_optimization.map((r, i) => (
                      <li key={i} className="py-3">
                        <p className="font-medium text-ink">{r.current_role}: {r.recommendation}</p>
                        <p className="mt-1 text-sm text-secondary">{r.rationale}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {result.recommendations.capability_development && result.recommendations.capability_development.length > 0 && (
                <div>
                  <p className="label">Capability development</p>
                  <ul className="divide-y divide-hairline border-y border-hairline">
                    {result.recommendations.capability_development.map((c, i) => (
                      <li key={i} className="grid gap-2 py-3 md:grid-cols-[1fr_1fr_1fr_auto] text-sm">
                        <p className="font-medium text-ink">{c.capability}</p>
                        <p className="text-secondary"><span className="text-faint">Now:</span> {c.current_state}</p>
                        <p className="text-secondary"><span className="text-faint">Target:</span> {c.target_state}</p>
                        <StatusPill status={severityStatus(c.priority)} label={`${c.priority} priority`} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Disclosure>
          )}

          {/* Data gaps */}
          {result.data_gaps && result.data_gaps.length > 0 && (
            <Section eyebrow="Limits of this analysis" title="What the data can't tell us">
              <ul className="card divide-y divide-hairline p-0">
                {result.data_gaps.map((g, i) => (
                  <li key={i} className="px-6 py-4">
                    <p className="font-medium text-ink">{g.gap}</p>
                    {g.why_it_matters && <p className="mt-1 text-sm text-secondary">{g.why_it_matters}</p>}
                    {g.observable_indicator_to_close && (
                      <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-primary-600">Measure next:</span> {g.observable_indicator_to_close}</p>
                    )}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <p className="text-xs text-faint">
            Findings are AI interpretations of job titles and activity text; industry comparisons are inferred, not measured.
            {result._llm && ` Produced by ${result._llm.model_served}.`}
            {' '}<Link to="/analysis" className="text-primary-600">Use these findings in archetype options →</Link>
          </p>
        </>
      )}
    </>
  );
}
