import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { comparisonApi } from '../services/api';
import type { ComparisonCriterion, ComparisonPayload } from '../types';
import { PageHeader, Section, Callout, EmptyState, Loading, Chip, formatMoney } from '../components/ui';

/** Sequential ink shading for 0-100 cells: darker = stronger. */
function cellStyle(score: number | null | undefined) {
  if (score === null || score === undefined) return { background: 'transparent', color: 'var(--color-faint)' };
  const a = 0.06 + 0.6 * (score / 100);
  return { background: `rgba(28,31,36,${a})`, color: a > 0.42 ? '#fff' : 'var(--color-ink)' };
}

function sourceTag(source: string) {
  if (source === 'current') return 'Baseline';
  if (source.startsWith('archetype:')) return `Archetype: ${source.slice(10).replace(/^\d+_/, '').replace(/_/g, ' ')}`;
  return 'Scenario';
}

function CriteriaEditor({ data, onSaved }: { data: ComparisonPayload; onSaved: (d: ComparisonPayload) => void }) {
  const [rows, setRows] = useState<ComparisonCriterion[]>(data.criteria);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(data.criteria), [data.criteria]);
  const total = rows.reduce((n, r) => n + (Number(r.weight) || 0), 0) || 1;
  const dirty = JSON.stringify(rows) !== JSON.stringify(data.criteria);
  const update = (i: number, patch: Partial<ComparisonCriterion>) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      onSaved(await comparisonApi.saveCriteria(rows));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Could not save the criteria');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card p-0">
      <table className="w-full text-sm">
        <thead>
          <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
            <th className="px-5 py-3">Criterion</th>
            <th className="px-3 py-3">How it's scored</th>
            <th className="w-24 px-3 py-3 text-right">Weight</th>
            <th className="w-40 px-3 py-3">Share</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="hairline-b">
              <td className="px-5 py-2.5">
                <input className="input min-w-[240px] py-1.5" value={r.name} onChange={(e) => update(i, { name: e.target.value })} aria-label="Criterion name" />
              </td>
              <td className="px-3 py-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <select className="input w-auto py-1.5" value={r.kind} onChange={(e) => update(i, { kind: e.target.value as 'measured' | 'judged', metric: e.target.value === 'measured' ? r.metric ?? 'total_cost' : undefined })} aria-label="Scoring">
                    <option value="judged">Judged (1–5)</option>
                    <option value="measured">Measured</option>
                  </select>
                  {r.kind === 'measured' && (
                    <>
                      <select className="input w-auto py-1.5" value={r.metric} onChange={(e) => update(i, { metric: e.target.value, better: data.measurable[e.target.value]?.better })} aria-label="Measure">
                        {Object.entries(data.measurable).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
                      </select>
                      <select className="input w-auto py-1.5" value={r.better ?? data.measurable[r.metric ?? '']?.better} onChange={(e) => update(i, { better: e.target.value as 'higher' | 'lower' })} aria-label="Better direction">
                        <option value="lower">lower is better</option>
                        <option value="higher">higher is better</option>
                      </select>
                    </>
                  )}
                </div>
              </td>
              <td className="px-3 py-2.5">
                <input type="number" min={0} className="input py-1.5 text-right" value={r.weight} onChange={(e) => update(i, { weight: Number(e.target.value) })} aria-label="Weight" />
              </td>
              <td className="px-3 py-2.5">
                <span className="tabular mr-2 text-xs text-secondary">{Math.round(((Number(r.weight) || 0) / total) * 100)}%</span>
                <span className="inline-block h-1.5 w-24 rounded-full bg-track align-middle">
                  <span className="block h-full rounded-full bg-ink" style={{ width: `${((Number(r.weight) || 0) / total) * 100}%` }} />
                </span>
              </td>
              <td className="px-5 py-2.5 text-right">
                <button className="text-xs font-semibold text-primary-600" onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex flex-wrap items-center gap-3 px-5 py-4">
        <button className="btn btn-quiet" onClick={() => setRows((rs) => [...rs, { id: `c${Date.now()}`, name: 'New criterion', kind: 'judged', weight: 10 }])}>Add criterion</button>
        <button className="btn btn-primary" disabled={!dirty || saving} onClick={save}>{saving ? 'Saving…' : 'Save criteria'}</button>
        <button className="ml-auto text-sm text-faint hover:text-ink" onClick={async () => onSaved(await comparisonApi.resetCriteria())}>Reset to defaults</button>
      </div>
      {error && <div className="px-5 pb-4"><Callout label="Not saved" tone="attention">{error}</Callout></div>}
    </div>
  );
}

export default function Compare() {
  const [data, setData] = useState<ComparisonPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ optionId: string; criterionId: string } | null>(null);
  const [draft, setDraft] = useState<{ score: number | null; rationale: string }>({ score: null, rationale: '' });
  const [suggesting, setSuggesting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    comparisonApi.get().then(setData).catch(() => setError('Upload an org structure CSV first.')).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Scoring the options" />;
  if (error || !data) {
    return (
      <>
        <PageHeader eyebrow="02 · Design — compare options" title="Compare options" />
        <EmptyState title="Nothing to compare yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} />
      </>
    );
  }

  const { options, criteria, result, judgments } = data;
  const byId = Object.fromEntries(options.map((o) => [o.id, o]));
  const leader = result.ranking[0] ? byId[result.ranking[0]] : undefined;
  const missingCount = Object.values(result.missing).reduce((n, m) => n + m.length, 0);
  const totalWeight = criteria.reduce((n, c) => n + (c.weight || 0), 0) || 1;

  const openEditor = (optionId: string, criterionId: string) => {
    const j = judgments[optionId]?.[criterionId];
    setEditing({ optionId, criterionId });
    setDraft({ score: j?.score ?? null, rationale: j?.rationale ?? '' });
  };
  const saveJudgment = async () => {
    if (!editing) return;
    setData(await comparisonApi.judge(editing.optionId, editing.criterionId, draft.score, draft.rationale));
    setEditing(null);
  };
  const suggest = async () => {
    setSuggesting(true);
    setNotice(null);
    try {
      const d = await comparisonApi.suggest();
      setData(d);
      setNotice(`${d.suggestions_added ?? 0} AI suggestions added. Your own scores were left untouched.`);
    } catch (e: unknown) {
      setNotice((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'The AI could not suggest scores.');
    } finally {
      setSuggesting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="02 · Design — compare options"
        title={
          options.length < 2
            ? 'Create a scenario to compare it with today'
            : leader
              ? `${leader.name} ${result.complete ? 'scores' : 'provisionally scores'} highest against your criteria`
              : 'Score the options against your criteria'
        }
        lede={
          options.length < 2
            ? <>Build options in the <Link to="/scenarios" className="text-primary-600 underline">Scenario Studio</Link>; each one appears here alongside the current state.</>
            : `Measured criteria are scored from each option's figures; judged criteria are your 1–5 assessments.${missingCount ? ` ${missingCount} judged score${missingCount === 1 ? ' is' : 's are'} still missing, so totals are provisional.` : ''}`
        }
        actions={data.ai_available && options.length > 1 ? (
          <button className="btn btn-quiet" onClick={suggest} disabled={suggesting}>{suggesting ? 'Asking the AI…' : 'Suggest judged scores (AI)'}</button>
        ) : undefined}
      />
      {notice && <div className="mb-8"><Callout label="Suggestions" tone="accent">{notice}</Callout></div>}

      <Section eyebrow="01 · Options against criteria" title="Weighted scores" lede="Darker cells score higher. Click a judged cell to score it; AI suggestions are marked and can be changed.">
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="hairline-b align-bottom text-left">
                <th className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Option</th>
                {criteria.map((c) => (
                  <th key={c.id} className="px-2 py-3 text-center">
                    <span className="block text-[12px] font-semibold text-ink">{c.name}</span>
                    <span className="block text-[11px] text-faint">{c.kind === 'measured' ? 'measured' : 'judged'} · {Math.round((c.weight / totalWeight) * 100)}%</span>
                  </th>
                ))}
                <th className="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">Weighted total</th>
              </tr>
            </thead>
            <tbody>
              {options.map((o) => {
                const rank = result.ranking.indexOf(o.id);
                const total = result.totals[o.id];
                return (
                  <tr key={o.id} className="hairline-b last:border-0">
                    <td className="px-5 py-3">
                      <p className="font-medium text-ink">{rank >= 0 && <span className="tabular mr-2 text-primary-600">{rank + 1}</span>}{o.name}</p>
                      <p className="text-xs text-faint">{sourceTag(o.source)}{o.move_count ? ` · ${o.move_count} moves` : ''}</p>
                    </td>
                    {criteria.map((c) => {
                      const score = result.cells[o.id]?.[c.id];
                      const j = judgments[o.id]?.[c.id];
                      const isEditing = editing?.optionId === o.id && editing?.criterionId === c.id;
                      const content = (
                        <span className="tabular inline-flex h-10 w-16 flex-col items-center justify-center rounded" style={cellStyle(score)}>
                          <span className="font-semibold leading-none">{score === null || score === undefined ? (c.kind === 'judged' ? 'Score' : '–') : Math.round(score)}</span>
                          {j && <span className="mt-0.5 text-[10px] leading-none opacity-80">{j.source === 'ai' ? 'AI' : 'you'} · {j.score}/5</span>}
                        </span>
                      );
                      return (
                        <td key={c.id} className="px-2 py-2 text-center">
                          {c.kind === 'judged' ? (
                            <button
                              onClick={() => openEditor(o.id, c.id)}
                              title={j?.rationale || 'Click to score'}
                              className={clsx('rounded', isEditing ? 'ring-2 ring-primary-600' : score === null || score === undefined ? 'border border-dashed border-placeholder' : '')}
                            >
                              {content}
                            </button>
                          ) : content}
                        </td>
                      );
                    })}
                    <td className="px-5 py-3 text-right">
                      <span className="display-number text-[24px] text-ink">{total === null ? '–' : Math.round(total)}</span>
                      <span className="mt-1 block h-1.5 w-full rounded-full bg-track">
                        <span className="block h-full rounded-full bg-primary-600" style={{ width: `${total ?? 0}%` }} />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {editing && (
          <div className="card mt-4 fade-up">
            <p className="eyebrow mb-1">Score</p>
            <p className="mb-4 text-ink">
              <span className="font-semibold">{byId[editing.optionId]?.name}</span> on{' '}
              <span className="font-semibold">{criteria.find((c) => c.id === editing.criterionId)?.name}</span>
            </p>
            <div className="mb-4 flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setDraft((d) => ({ ...d, score: n }))}
                  className={clsx('h-12 w-14 rounded border text-center', draft.score === n ? 'border-primary-600 bg-primary-50' : 'border-hairline hover:border-primary-600')}
                >
                  <span className="block font-display text-[20px] font-bold leading-none text-ink">{n}</span>
                  <span className="block text-[10px] text-faint">{['poor', 'weak', 'fair', 'good', 'strong'][n - 1]}</span>
                </button>
              ))}
            </div>
            {judgments[editing.optionId]?.[editing.criterionId]?.source === 'ai' && (
              <p className="mb-3 text-xs text-faint">
                AI suggestion · {judgments[editing.optionId][editing.criterionId].evidence_class ?? 'evidence not stated'} · confidence {judgments[editing.optionId][editing.criterionId].confidence ?? '—'}
              </p>
            )}
            <label className="label" htmlFor="rationale">Reason</label>
            <input id="rationale" className="input mb-4" value={draft.rationale} onChange={(e) => setDraft((d) => ({ ...d, rationale: e.target.value }))} placeholder="What makes this option stronger or weaker on this criterion?" />
            <div className="flex gap-2">
              <button className="btn btn-primary" onClick={saveJudgment} disabled={draft.score === null}>Save score</button>
              <button className="btn btn-quiet" onClick={() => setEditing(null)}>Cancel</button>
              {judgments[editing.optionId]?.[editing.criterionId] && (
                <button className="ml-auto text-sm text-faint hover:text-ink" onClick={async () => { setData(await comparisonApi.judge(editing.optionId, editing.criterionId, null)); setEditing(null); }}>Clear score</button>
              )}
            </div>
          </div>
        )}
        <p className="mt-3 text-xs text-faint">
          Measured criteria place each option between the worst (0) and best (100) of the options compared; judged 1–5 maps to 0–100. Totals are weighted averages of the scored criteria.
        </p>
      </Section>

      <Section eyebrow="02 · Your design criteria" title="What matters, and how much" lede="Name the criteria from your design brief and weight them. Measured criteria are scored automatically from each option.">
        <CriteriaEditor data={data} onSaved={setData} />
      </Section>

      <Section eyebrow="03 · The figures behind the measured scores">
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                <th className="px-5 py-3">Option</th>
                <th className="px-3 py-3 text-right">Health</th>
                <th className="px-3 py-3 text-right">Layers</th>
                <th className="px-3 py-3 text-right">Managers</th>
                <th className="px-3 py-3 text-right">Spans within</th>
                <th className="px-3 py-3 text-right">Single-report</th>
                <th className="px-3 py-3 text-right">People</th>
                <th className="px-3 py-3 text-right">Cost</th>
                <th className="px-5 py-3 text-right">People affected</th>
              </tr>
            </thead>
            <tbody>
              {options.map((o) => (
                <tr key={o.id} className="hairline-b tabular last:border-0">
                  <td className="px-5 py-2.5 font-medium text-ink">{o.name}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.health_score}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.layers}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.managers}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.spans_within_benchmark}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.single_report_managers}</td>
                  <td className="px-3 py-2.5 text-right">{o.figures.headcount}</td>
                  <td className="px-3 py-2.5 text-right">{formatMoney(o.figures.total_cost)}</td>
                  <td className="px-5 py-2.5 text-right">{o.figures.people_affected_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {options.filter((o) => o.id !== 'current').map((o) => (
            <Link key={o.id} to="/scenarios"><Chip>Edit “{o.name}” →</Chip></Link>
          ))}
        </div>
      </Section>
    </>
  );
}
