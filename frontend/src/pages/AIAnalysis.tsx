import { useState, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { aiAnalysisApi, settingsApi, metricsApi, scenariosApi } from '../services/api';
import type { AIAnalysisResult, ArchetypeRecommendation, ArchetypeScoreSummary } from '../types';
import ArchetypeDiagram from '../components/ArchetypeDiagram';
import { PageHeader, Section, Callout, Chip, Disclosure, StatusPill, ScoreBar, severityStatus, scoreStatus } from '../components/ui';
import type { Status } from '../components/ui';

const EVIDENCE_LABEL: Record<string, string> = {
  OBSERVABLE: 'Observable data',
  PERCEPTUAL: 'Self-reported',
  'MODEL-INFERRED': 'Inferred from research',
};

const CONFIDENCE_STATUS: Record<string, Status> = { High: 'healthy', Medium: 'developing', Low: 'attention' };

const CRITERIA: Array<[keyof ArchetypeScoreSummary['score_breakdown'], string, number]> = [
  ['industry_match', 'Industry', 30],
  ['key_indicators_match', 'Indicators', 25],
  ['revenue_model_match', 'Revenue model', 20],
  ['size_match', 'Size', 15],
  ['metrics_match', 'Metrics', 10],
];

/** Sequential ink shading for 0-100 cells: darker = stronger fit. */
function fitCell(score?: number) {
  if (score === undefined || score === null) return { background: 'transparent', color: 'var(--color-faint)' };
  const a = 0.06 + 0.6 * (score / 100);
  return { background: `rgba(28,31,36,${a})`, color: a > 0.42 ? '#fff' : 'var(--color-ink)' };
}

function GlyphList({ items, glyph, color }: { items?: string[]; glyph: string; color: string }) {
  if (!items?.length) return null;
  return (
    <ul className="space-y-1.5 text-sm text-secondary">
      {items.map((t, i) => <li key={i}><span className="mr-2 font-semibold" style={{ color }}>{glyph}</span>{t}</li>)}
    </ul>
  );
}

function Label({ children, color = 'var(--color-secondary)' }: { children: ReactNode; color?: string }) {
  return <p className="mb-2 text-[11px] font-semibold uppercase tracking-[.14em]" style={{ color }}>{children}</p>;
}

function Recommendation({ arch, onBuild }: { arch: ArchetypeRecommendation; onBuild: () => void }) {
  const score = arch.overall_fit_score ?? arch.business_model_match_score;
  return (
    <article className="card mb-6 p-0">
      <header className="flex flex-wrap items-start justify-between gap-4 px-6 py-5 hairline-b">
        <div>
          <p className="eyebrow mb-1">{arch.rank ? `Recommendation ${arch.rank}` : 'Recommendation'}</p>
          <h3 className="text-[26px] leading-tight">{arch.archetype}</h3>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-faint">
            {arch.transformation_timeline && <Chip>Timeline {arch.transformation_timeline}</Chip>}
            {arch.confidence_level && <StatusPill status={CONFIDENCE_STATUS[arch.confidence_level] ?? 'neutral'} label={`${arch.confidence_level} confidence`} />}
            {arch.confidence_rationale && <span className="max-w-md">{arch.confidence_rationale}</span>}
          </div>
        </div>
        {score !== undefined && (
          <div className="text-right">
            <p className="display-number text-[48px] text-ink">{score}<span className="text-[20px] text-faint">/100</span></p>
            {!!arch.score_discrepancy && <p className="text-xs text-faint">AI said {arch.ai_overall_score}</p>}
          </div>
        )}
      </header>

      <div className="px-6 py-6">
        {arch.score_breakdown && (
          <div className="mb-6 grid gap-x-8 gap-y-3 md:grid-cols-2">
            {Object.entries(arch.score_breakdown).map(([key, val]) => {
              const s = typeof val === 'object' ? val.score : val;
              const rationale = typeof val === 'object' ? val.rationale : undefined;
              return <ScoreBar key={key} score={Number(s) || 0} label={key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())} detail={rationale} />;
            })}
          </div>
        )}

        <Label color="var(--color-score-amber)">Interpretation · why it fits</Label>
        <p className="mb-6 max-w-[760px] text-ink">{arch.why_it_fits}</p>

        {arch.design_criteria_addressed && arch.design_criteria_addressed.length > 0 && (
          <div className="mb-6">
            <Label>How it meets your design criteria</Label>
            <GlyphList items={arch.design_criteria_addressed} glyph="✓" color="var(--color-score-green)" />
          </div>
        )}

        <div className="mb-6 grid gap-8 md:grid-cols-2">
          <div><Label color="var(--color-score-green)">Expected benefits</Label><GlyphList items={arch.expected_benefits} glyph="✓" color="var(--color-score-green)" /></div>
          <div><Label color="var(--color-score-red)">Implementation challenges</Label><GlyphList items={arch.implementation_challenges} glyph="×" color="var(--color-score-red)" /></div>
          {arch.critical_success_factors?.length > 0 && (
            <div><Label>Critical success factors</Label><GlyphList items={arch.critical_success_factors} glyph="·" color="var(--color-primary)" /></div>
          )}
          {arch.warning_signs_to_monitor && arch.warning_signs_to_monitor.length > 0 && (
            <div><Label color="var(--color-score-amber)">Warning signs to monitor</Label><GlyphList items={arch.warning_signs_to_monitor} glyph="!" color="var(--color-score-amber)" /></div>
          )}
        </div>

        {arch.differentiating_activities && arch.differentiating_activities.length > 0 && (
          <div className="mb-6">
            <Label color="var(--color-primary)">★ Differentiating activities — protect these</Label>
            <ul className="divide-y divide-hairline border-y border-hairline">
              {arch.differentiating_activities.map((a, j) => (
                <li key={j} className="py-3 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="font-medium text-ink">{a.activity}</p>
                    <span className="text-xs text-faint">{a.strategic_importance} importance{a.related_roles?.length ? ` · ${a.related_roles.join(', ')}` : ''}</span>
                  </div>
                  {a.description && <p className="mt-1 text-secondary">{a.description}</p>}
                  <p className="mt-1 text-secondary"><span className="font-semibold text-ink">Why it differentiates:</span> {a.why_differentiating}</p>
                  <p className="mt-1 text-secondary"><span className="font-semibold text-ink">How this structure supports it:</span> {a.how_archetype_supports}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {arch.practical_examples && arch.practical_examples.length > 0 && (
          <div className="mb-6">
            <Label>Who works this way (examples are model-inferred)</Label>
            <div className="grid gap-4 md:grid-cols-2">
              {arch.practical_examples.map((ex, j) => (
                <div key={j} className="hairline-t pt-3 text-sm">
                  <p className="font-medium text-ink">{ex.company_or_scenario}</p>
                  <p className="mt-1 text-secondary">{ex.description}</p>
                  {ex.key_success_factors && <p className="mt-1 text-faint">What makes it work: {ex.key_success_factors}</p>}
                  {ex.relevance_to_your_org && <p className="mt-1 text-faint italic">Relevance: {ex.relevance_to_your_org}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {arch.structure_diagram?.nodes?.length ? (
          <div className="mb-6">
            <Label>The organization redrawn in this archetype</Label>
            <ArchetypeDiagram diagram={arch.structure_diagram} />
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-3 hairline-t pt-5">
          <button className="btn btn-primary" onClick={onBuild}>Build this as a scenario →</button>
          <span className="text-xs text-faint">Creates a scenario tagged with this archetype, where you add design moves and measure them.</span>
        </div>
      </div>
    </article>
  );
}

export default function AIAnalysis() {
  const [analysis, setAnalysis] = useState<AIAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [designCriteria, setDesignCriteria] = useState('');
  const [strategyText, setStrategyText] = useState('');
  const [strategyMode, setStrategyMode] = useState<'text' | 'document'>('text');
  const [strategyFiles, setStrategyFiles] = useState<File[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [scopeDepartment, setScopeDepartment] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    settingsApi.getStatus().then((s) => setApiConfigured(s.configured)).catch(() => undefined);
    aiAnalysisApi.getLatest().then((r) => setAnalysis(r.ai_analysis)).catch(() => undefined);
    metricsApi.getLatest()
      .then((r) => setDepartments((r.metrics.department_analysis ?? []).map((d) => d.department)))
      .catch(() => undefined);
  }, []);

  const startScenarioFor = async (archetypeId: string | undefined, archetypeName: string) => {
    await scenariosApi.create(`${archetypeName.split(' (')[0]} design`, {
      source: archetypeId ? `archetype:${archetypeId}` : 'manual',
      description: `Implements the ${archetypeName} archetype`,
    });
    navigate('/scenarios');
  };

  const addFiles = (files: File[]) => {
    const valid = files.filter((f) => /\.(pdf|pptx|docx|txt)$/i.test(f.name));
    setStrategyFiles((prev) => [...prev, ...valid]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const scope = { department: scopeDepartment || undefined };
      const result = strategyMode === 'document' && strategyFiles.length > 0
        ? await aiAnalysisApi.analyzeWithDocuments(strategyFiles, designCriteria || undefined, undefined, scope)
        : await aiAnalysisApi.analyze(undefined, designCriteria || undefined, strategyText || undefined, scope);
      setAnalysis(result.ai_analysis);
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'The analysis could not be completed.');
    } finally {
      setLoading(false);
    }
  };

  const cat4 = analysis?.category_4_recommended_archetypes;
  const recs = !cat4 ? [] : Array.isArray(cat4) ? cat4 : cat4.recommendations ?? [];
  const allScores = cat4 && !Array.isArray(cat4) ? [...(cat4.all_archetype_scores ?? [])].sort((a, b) => b.overall_score - a.overall_score) : [];
  const alignment = analysis?.category_3_strategy_alignment;
  const diagnosis = analysis?.category_2_health_diagnosis;
  // The stored record also holds the work-activities analysis; only archetype results count here
  const ok = analysis && !analysis.error && Boolean(analysis.executive_summary || analysis.category_4_recommended_archetypes);
  const lead = recs[0];

  return (
    <>
      <PageHeader
        eyebrow="02 · Design — archetype options"
        title={ok && lead ? `${lead.archetype.split(' (')[0]} fits best${recs[1] ? `, then ${recs[1].archetype.split(' (')[0]}` : ''}` : 'Which structures fit the strategy'}
        lede="All seven archetypes are scored against your organization, strategy and design criteria; the overall score is computed from five weighted criteria. The AI sees departments, roles and figures — never names."
      />

      {!apiConfigured && (
        <div className="mb-8">
          <Callout label="AI analysis is off" tone="accent">
            Add your Claude API key in <Link to="/settings" className="text-primary-600 underline">Settings</Link> to run a new analysis. Saved results below remain available.
          </Callout>
        </div>
      )}

      <Disclosure eyebrow={ok ? 'Re-run the analysis' : 'Run the analysis'} title="Strategy and design brief" defaultOpen={!ok}>
        <div className="space-y-5">
          {departments.length > 1 && (
            <div>
              <label className="label" htmlFor="scope">What to design</label>
              <select id="scope" value={scopeDepartment} onChange={(e) => setScopeDepartment(e.target.value)} className="input">
                <option value="">The whole organization</option>
                {departments.map((d) => <option key={d} value={d}>One department: {d}</option>)}
              </select>
              <p className="mt-1.5 text-xs text-faint">Department scope recommends structures for that unit, using its roles and department-specific archetype guidance.</p>
            </div>
          )}
          <div>
            <label className="label" htmlFor="criteria">Design criteria (optional)</label>
            <textarea id="criteria" value={designCriteria} onChange={(e) => setDesignCriteria(e.target.value)} className="input h-24"
              placeholder="e.g. Faster decisions for frontline operations; one owner for each customer journey; fewer layers" />
          </div>
          <div>
            <span className="label">Strategy context (optional)</span>
            <div className="mb-3 flex gap-2">
              {(['text', 'document'] as const).map((m) => (
                <Chip key={m} active={strategyMode === m} onClick={() => setStrategyMode(m)}>{m === 'text' ? 'Paste text' : 'Upload documents'}</Chip>
              ))}
            </div>
            {strategyMode === 'text' ? (
              <textarea value={strategyText} onChange={(e) => setStrategyText(e.target.value)} className="input h-24" placeholder="Paste the strategic priorities, targets and context" aria-label="Strategy context" />
            ) : (
              <>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); addFiles(Array.from(e.dataTransfer.files)); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter') fileInputRef.current?.click(); }}
                  className="cursor-pointer border border-dashed border-hairline bg-white py-8 text-center transition-colors hover:border-primary-600"
                >
                  <input ref={fileInputRef} type="file" accept=".pdf,.pptx,.docx,.txt" multiple onChange={(e) => addFiles(Array.from(e.target.files || []))} className="hidden" />
                  <p className="font-medium text-ink">Drop strategy documents or click to browse</p>
                  <p className="mt-1 text-xs text-faint">PDF, PowerPoint, Word or text</p>
                </div>
                {strategyFiles.length > 0 && (
                  <ul className="mt-3 divide-y divide-hairline border-y border-hairline text-sm">
                    {strategyFiles.map((f, i) => (
                      <li key={i} className="flex items-center justify-between py-2">
                        <span className="text-ink">{f.name} <span className="text-faint">· {(f.size / 1024).toFixed(1)} KB</span></span>
                        <button onClick={() => setStrategyFiles((prev) => prev.filter((_, j) => j !== i))} className="text-xs font-semibold text-primary-600">Remove</button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
          <button onClick={handleRunAnalysis} disabled={loading || !apiConfigured} className="btn btn-primary"
            title={apiConfigured ? undefined : 'Add your Claude API key in Settings to run an analysis'}>
            {loading ? 'Analyzing — a minute or two…' : ok ? 'Re-run the analysis' : 'Run the analysis'}
          </button>
        </div>
      </Disclosure>

      {error && <div className="mb-8"><Callout label="Analysis failed" tone="attention">{error}</Callout></div>}
      {analysis?.error && !error && <div className="mb-8"><Callout label="Last analysis failed" tone="attention">{analysis.error}</Callout></div>}
      {ok && analysis.parse_warning && <div className="mb-8"><Callout label="Incomplete response" tone="developing">{analysis.parse_warning}</Callout></div>}

      {ok && (
        <>
          {analysis.executive_summary && (
            <Section eyebrow="Interpretation · AI">
              <p className="max-w-[760px] whitespace-pre-line font-display text-[20px] leading-relaxed text-ink">{analysis.executive_summary}</p>
            </Section>
          )}

          {allScores.length > 0 && cat4 && !Array.isArray(cat4) && (
            <Section
              eyebrow="01 · All seven archetypes"
              title="Fit against the five weighted criteria"
              lede={cat4.analysis_scope === 'department' ? `Department scope: ${cat4.department_analyzed}.` : undefined}
            >
              {cat4.ranking_note && <div className="mb-4"><Callout label="Check" tone="developing">{cat4.ranking_note}</Callout></div>}
              <div className="card overflow-x-auto p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="hairline-b align-bottom text-left">
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Archetype</th>
                      {CRITERIA.map(([k, label, w]) => (
                        <th key={k} className="px-2 py-3 text-center">
                          <span className="block text-[12px] font-semibold text-ink">{label}</span>
                          <span className="block text-[11px] text-faint">{w}%</span>
                        </th>
                      ))}
                      <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Overall</th>
                      <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allScores.map((a, i) => (
                      <tr key={a.archetype_id ?? i} className={clsx('hairline-b last:border-0', i < 2 && 'bg-primary-50/40')}>
                        <td className="px-5 py-3">
                          <p className="font-medium text-ink">{i < 2 && <span className="tabular mr-2 text-primary-600">{i + 1}</span>}{a.archetype_name}</p>
                          {a.digital_first_applicable === false && <p className="text-xs text-faint">Digital-first model</p>}
                        </td>
                        {CRITERIA.map(([k]) => (
                          <td key={k} className="px-2 py-2 text-center">
                            <span className="tabular inline-flex h-8 w-12 items-center justify-center rounded font-semibold" style={fitCell(a.score_breakdown?.[k])}>
                              {a.score_breakdown?.[k] ?? '–'}
                            </span>
                          </td>
                        ))}
                        <td className="px-4 py-3 text-right">
                          <span className="display-number text-[22px] text-ink">{a.overall_score}</span>
                          {!!a.score_discrepancy && <span className="block text-[11px] text-faint" title="The AI's own overall figure; the score shown is computed from the five criteria">AI said {a.ai_overall_score}</span>}
                        </td>
                        <td className="max-w-xs px-5 py-3 text-xs text-secondary">{a.fit_summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-faint">
                Criterion scores are AI judgements (model-inferred); the overall score is their weighted average, computed by the app. Darker cells fit better.
                {cat4.design_criteria_analyzed && <> Design criteria considered: {cat4.design_criteria_analyzed}</>}
              </p>
            </Section>
          )}

          {recs.length > 0 && (
            <Section eyebrow="02 · Recommended options" title="The two strongest fits in detail">
              {recs.map((arch, i) => <Recommendation key={i} arch={arch} onBuild={() => startScenarioFor(arch.archetype_id, arch.archetype)} />)}
            </Section>
          )}

          {diagnosis && (
            <Disclosure eyebrow="03 · Diagnosis" title="Structural strengths, weaknesses and pathologies">
              <div className="mb-6 grid gap-8 md:grid-cols-2">
                <div><Label color="var(--color-score-green)">Strengths</Label><GlyphList items={diagnosis.strengths} glyph="✓" color="var(--color-score-green)" /></div>
                <div><Label color="var(--color-score-red)">Weaknesses</Label><GlyphList items={diagnosis.weaknesses} glyph="×" color="var(--color-score-red)" /></div>
              </div>
              {diagnosis.pathologies?.length > 0 && (
                <ul className="divide-y divide-hairline border-y border-hairline">
                  {diagnosis.pathologies.map((p, i) => (
                    <li key={i} className="py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-ink">{p.name}</p>
                        <StatusPill status={severityStatus(p.severity)} label={p.severity} />
                        {p.evidence_class && <Chip>{EVIDENCE_LABEL[p.evidence_class] ?? p.evidence_class}</Chip>}
                        {p.dimension && <Chip>{p.dimension}</Chip>}
                        {p.confidence && <span className="text-xs text-faint" title={p.confidence_rationale || ''}>Confidence <b className="text-secondary">{p.confidence}</b>{p.confidence_rationale && ` — ${p.confidence_rationale}`}</span>}
                      </div>
                      <p className="mt-1 text-sm text-secondary">{p.description}</p>
                      <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Impact:</span> {p.impact}</p>
                      {p.supporting_evidence && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Evidence:</span> {p.supporting_evidence}</p>}
                      {p.disconfirming_evidence && p.disconfirming_evidence !== 'None identified' && (
                        <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-ink">Does not fully fit:</span> {p.disconfirming_evidence}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {diagnosis.critical_risks?.length > 0 && (
                <div className="mt-6"><Label color="var(--color-score-red)">Critical risks</Label><GlyphList items={diagnosis.critical_risks} glyph="!" color="var(--color-score-red)" /></div>
              )}
            </Disclosure>
          )}

          {alignment && (
            <Disclosure
              eyebrow="04 · Strategy alignment"
              title={`Current structure scores ${alignment.overall_alignment_score}/100 against the strategy`}
              meta={<StatusPill status={scoreStatus(alignment.overall_alignment_score)} label={`Grade ${alignment.alignment_grade}`} />}
              defaultOpen={false}
            >
              {alignment.strategy_documents_analyzed && <p className="mb-5 text-sm text-secondary"><span className="font-semibold text-ink">Strategy read as:</span> {alignment.strategy_documents_analyzed}</p>}
              <div className="mb-6 grid gap-x-8 gap-y-4 md:grid-cols-2">
                {Object.entries(alignment.scores || {}).map(([key, d]) => (
                  <ScoreBar key={key} score={d.score} label={key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())} detail={d.rationale} />
                ))}
              </div>
              {alignment.key_gaps?.length > 0 && (
                <>
                  <Label color="var(--color-score-amber)">Gaps between structure and strategy</Label>
                  <ul className="divide-y divide-hairline border-y border-hairline text-sm">
                    {alignment.key_gaps.map((g, i) => (
                      <li key={i} className="py-3">
                        {typeof g === 'string' ? <span className="text-ink">{g}</span> : (
                          <>
                            <p className="font-medium text-ink">{g.gap}</p>
                            {g.strategy_reference && <p className="mt-1 text-secondary">Strategy: {g.strategy_reference}</p>}
                            {g.structural_impact && <p className="mt-1 text-secondary">Structural cause: {g.structural_impact}</p>}
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {alignment.alignment_strengths && alignment.alignment_strengths.length > 0 && (
                <div className="mt-5"><Label color="var(--color-score-green)">Where the structure supports the strategy</Label><GlyphList items={alignment.alignment_strengths} glyph="✓" color="var(--color-score-green)" /></div>
              )}
            </Disclosure>
          )}

          {analysis.category_1_industry_trends?.insights?.length ? (
            <Disclosure eyebrow="05 · Benchmarks and trends" title="What the research says" defaultOpen={false}>
              <ul className="divide-y divide-hairline border-y border-hairline">
                {analysis.category_1_industry_trends.insights.map((ins, i) => (
                  <li key={i} className="py-4 text-sm">
                    <p className="font-medium text-ink">{ins.topic}</p>
                    <p className="mt-1 text-secondary">{ins.finding}</p>
                    <p className="mt-1 text-faint">Source: {ins.source}{ins.relevance_to_org && <> · For this organization: {ins.relevance_to_org}</>}</p>
                  </li>
                ))}
              </ul>
            </Disclosure>
          ) : null}

          {analysis.action_plan && (
            <Disclosure eyebrow="06 · Recommendation" title="Action plan">
              <div className="grid gap-px overflow-hidden border border-hairline bg-hairline md:grid-cols-3">
                {[
                  ['01', 'Quick wins', analysis.action_plan.phase_1_quick_wins],
                  ['02', 'Structural changes', analysis.action_plan.phase_2_structural],
                  ['03', 'Optimization', analysis.action_plan.phase_3_optimization],
                ].map(([n, title, items]) => (
                  <div key={n as string} className="bg-white p-5">
                    <span className="display-number text-[30px] text-placeholder">{n as string}</span>
                    <h3 className="mb-2 mt-1 text-[18px]">{title as string}</h3>
                    <GlyphList items={items as string[]} glyph="·" color="var(--color-primary)" />
                  </div>
                ))}
              </div>
              <p className="mt-3 text-sm text-secondary">
                Turn these into measured options in the <Link to="/scenarios" className="text-primary-600 underline">Scenario Studio</Link>, then see their <Link to="/implementation" className="text-primary-600 underline">implications</Link>.
              </p>
            </Disclosure>
          )}

          {analysis.data_gaps && analysis.data_gaps.length > 0 && (
            <Section eyebrow="Limits of this analysis" title="What the data can't tell us">
              <ul className="card divide-y divide-hairline p-0">
                {analysis.data_gaps.map((g, i) => (
                  <li key={i} className="px-6 py-4">
                    <p className="font-medium text-ink">{g.gap}</p>
                    {g.why_it_matters && <p className="mt-1 text-sm text-secondary">{g.why_it_matters}</p>}
                    {g.observable_indicator_to_close && <p className="mt-1 text-sm text-secondary"><span className="font-semibold text-primary-600">Measure next:</span> {g.observable_indicator_to_close}</p>}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <p className="text-xs text-faint">
            Archetype fit, benchmarks and examples are AI interpretations; figures come from your data.
            {analysis._llm && ` Produced by ${analysis._llm.model_served}.`}
          </p>
        </>
      )}
    </>
  );
}
