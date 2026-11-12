/**
 * Shared workflow language with the other apps: import a Capability Compass
 * hand-off, show what the Compass found (read-only), grade findings as
 * Confirmed / Indicated / Hypothesis, keep hypotheses H1…, and send findings back.
 * All of it is optional — the app works with no hand-off file.
 */
import { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { compassApi } from '../services/api';
import type { CompassPreview, CompassState, Grade, Hypothesis, HypothesisStatus } from '../types';
import { Callout, Chip, Section } from './ui';

export const COMPASS_CHANGED = 'compass-changed';
const announce = () => window.dispatchEvent(new Event(COMPASS_CHANGED));

/** Same rule as the backend, so a finding's key is the same on both sides. */
export const slug = (text: string) =>
  (text || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48) || 'item';

const GRADE_COLOR: Record<Grade, string> = {
  confirmed: 'var(--color-score-green)',
  indicated: 'var(--color-score-amber)',
  hypothesis: 'var(--color-secondary)',
};
const GRADE_GLYPH: Record<Grade, string> = { confirmed: '●', indicated: '◐', hypothesis: '○' };

const detailOf = (e: unknown, fallback: string) =>
  (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? fallback;

/** Loads the shared state; `null` until loaded or when there is no org data yet. */
export function useCompass(): [CompassState | null, (s: CompassState) => void] {
  const [state, setState] = useState<CompassState | null>(null);
  useEffect(() => {
    const load = () => compassApi.get().then(setState).catch(() => setState(null));
    load();
    window.addEventListener(COMPASS_CHANGED, load);
    return () => window.removeEventListener(COMPASS_CHANGED, load);
  }, []);
  return [state, setState];
}

export function GradeBadge({ grade }: { grade: Grade }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-semibold" style={{ color: GRADE_COLOR[grade] }}>
      <span aria-hidden>{GRADE_GLYPH[grade]}</span>{grade.charAt(0).toUpperCase() + grade.slice(1)}
    </span>
  );
}

/** The shared grade for one finding: starts at the suggested grade, yours once you change it. */
export function GradeSelect({ findingRef, suggested, state, onChange }: {
  findingRef: string; suggested: Grade; state: CompassState; onChange: (s: CompassState) => void;
}) {
  const mine = state.grade_overrides[findingRef];
  const value = mine ?? suggested;
  return (
    <label className="inline-flex items-center gap-1.5 text-xs text-faint">
      <span aria-hidden style={{ color: GRADE_COLOR[value] }}>{GRADE_GLYPH[value]}</span>
      <span className="sr-only">Grade for {findingRef}</span>
      <select
        aria-label={`Grade for ${findingRef}`}
        className="rounded border border-hairline bg-white px-1.5 py-0.5 text-xs font-semibold text-ink"
        value={value}
        onChange={async (e) => {
          const next = e.target.value as Grade;
          onChange(await compassApi.setGrade(findingRef, next === suggested ? null : next));
          announce();
        }}
      >
        {state.grades.map((g) => <option key={g} value={g}>{state.grade_labels[g]}{g === suggested ? ' (suggested)' : ''}</option>)}
      </select>
      {mine && <span>set by you</span>}
    </label>
  );
}

// ------------------------------------------------------------------ import

export function CompassImport({ onImported }: { onImported?: (s: CompassState) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [packet, setPacket] = useState<unknown>(null);
  const [preview, setPreview] = useState<CompassPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replaceCriteria, setReplaceCriteria] = useState(false);
  const [replaceStrategy, setReplaceStrategy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string[] | null>(null);

  const reset = () => { setPacket(null); setPreview(null); setReplaceCriteria(false); setReplaceStrategy(false); };

  const choose = async (file?: File) => {
    if (!file) return;
    setError(null); setDone(null); reset();
    let parsed: unknown;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setError('This file could not be read as a Capability Compass hand-off (it is not valid JSON).');
      return;
    }
    try {
      setPacket(parsed);
      setPreview(await compassApi.preview(parsed));
    } catch (e) {
      setError(detailOf(e, 'The file could not be checked.'));
    }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      const state = await compassApi.importPacket(packet, replaceCriteria, replaceStrategy);
      setDone(state.applied ?? []);
      reset();
      onImported?.(state);
      announce();
    } catch (e) {
      setError(detailOf(e, 'The import failed.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <input ref={input} type="file" accept=".json,application/json" className="hidden" data-testid="compass-file"
        onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ''; }} />
      <button className="btn btn-secondary" onClick={() => input.current?.click()}>Import from Capability Compass</button>

      {error && <div className="mt-4"><Callout label="Not imported" tone="attention">{error}</Callout></div>}
      {done && (
        <div className="mt-4"><Callout label="Imported" tone="healthy">
          <ul className="list-disc pl-5">{done.map((d) => <li key={d}>{d}</li>)}</ul>
        </Callout></div>
      )}

      {preview && !preview.ok && (
        <div className="mt-4"><Callout label="Not imported" tone="attention">
          {preview.errors.join(' ')} Nothing was changed.
        </Callout></div>
      )}

      {preview?.ok && preview.engagement && (
        <div className="card mt-4 fade-up" role="region" aria-label="Import preview">
          <p className="eyebrow mb-1">Preview — nothing is changed until you confirm</p>
          <p className="font-display text-[22px] font-bold text-ink">{preview.engagement.name} <span className="text-primary-600">{preview.engagement.key}</span></p>
          <p className="text-sm text-faint">{[preview.engagement.industry, preview.engagement.scope].filter(Boolean).join(' · ')}</p>

          {preview.warnings.length > 0 && (
            <div className="mt-4"><Callout label="Check" tone="developing">
              <ul className="list-disc pl-5">{preview.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </Callout></div>
          )}

          <dl className="mt-5 space-y-5 text-sm">
            <div>
              <dt className="font-semibold text-ink">Comparison criteria</dt>
              <dd className="mt-1 text-secondary">{preview.criteria?.note}</dd>
              {preview.criteria && preview.criteria.problems.length > 0 && <dd className="mt-1 text-primary-700">{preview.criteria.problems.join('; ')}</dd>}
              {preview.criteria && ['set', 'ask'].includes(preview.criteria.action) && (
                <dd className="mt-2 flex flex-wrap gap-1.5">
                  {preview.criteria.incoming.map((c) => <Chip key={c.id}>{c.ref} {c.name} · {c.weight}</Chip>)}
                </dd>
              )}
              {preview.criteria?.action === 'ask' && (
                <dd className="mt-2">
                  <label className="flex items-center gap-2 text-secondary">
                    <input type="checkbox" checked={replaceCriteria} onChange={(e) => setReplaceCriteria(e.target.checked)} className="accent-[#C41E3A]" />
                    Replace my {preview.criteria.current_count} criteria with these
                  </label>
                </dd>
              )}
            </div>
            <div>
              <dt className="font-semibold text-ink">Strategy text</dt>
              <dd className="mt-1 text-secondary">{preview.strategy?.note}</dd>
              {preview.strategy?.action === 'ask' && (
                <dd className="mt-2">
                  <label className="flex items-center gap-2 text-secondary">
                    <input type="checkbox" checked={replaceStrategy} onChange={(e) => setReplaceStrategy(e.target.checked)} className="accent-[#C41E3A]" />
                    Replace my strategy text with the file's
                  </label>
                </dd>
              )}
            </div>
            <div>
              <dt className="font-semibold text-ink">What the Compass found</dt>
              <dd className="mt-1 text-secondary">
                {preview.context?.structure_findings} structure findings and {preview.context?.clusters} capability clusters are shown as read-only context.
                They never set a score. {preview.context?.ids} Compass IDs become available to attach to your findings.
              </dd>
            </div>
          </dl>

          <div className="mt-6 flex gap-3">
            <button className="btn btn-primary" onClick={confirm} disabled={busy}>{busy ? 'Importing…' : 'Confirm import'}</button>
            <button className="btn btn-quiet" onClick={reset} disabled={busy}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ read-only context

export function CompassContext({ state }: { state: CompassState | null }) {
  const [open, setOpen] = useState(false);
  if (!state?.engagement) return null;
  const { structure_lens, clusters } = state.context;
  return (
    <section className="card mb-10 p-0" aria-label="What the Compass found">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center justify-between gap-4 px-6 py-4 text-left">
        <span>
          <span className="eyebrow mb-1 block">Read-only context · {state.engagement.key}</span>
          <span className="font-display text-[20px] font-bold text-ink">What the Compass found</span>
          <span className="mt-0.5 block text-sm text-secondary">Evidence to test against the structure. It never sets or changes a score here.</span>
        </span>
        <span className="font-display text-2xl text-primary-600" aria-hidden>{open ? '–' : '+'}</span>
      </button>
      {open && (
        <div className="hairline-t grid gap-8 px-6 py-5 lg:grid-cols-2">
          <div>
            <p className="label">Structure lens</p>
            <ul className="divide-y divide-hairline text-sm">
              {structure_lens.map((l) => (
                <li key={l.ref} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-2">
                  <span className="tabular w-36 shrink-0 text-xs font-semibold text-primary-700">{l.ref}</span>
                  <span className="flex-1 text-ink">{l.cluster}<span className="block text-xs text-faint">{l.level} · {l.status}</span></span>
                  <GradeBadge grade={l.grade} />
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="label">Priority moves</p>
            <ul className="divide-y divide-hairline text-sm">
              {clusters.map((c) => (
                <li key={c.ref} className="py-2">
                  <span className="tabular mr-2 text-xs font-semibold text-primary-700">{c.ref}</span>
                  <span className="text-ink">{c.name}</span>
                  {c.economic_weight_pct != null && <span className="text-xs text-faint"> · {c.economic_weight_pct}% of economic weight</span>}
                  <span className="block text-secondary">{c.priority_move}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ hypotheses

const EMPTY = { statement: '', refuted_by: '', status: 'open' as HypothesisStatus, note: '' };
const STATUS_WORD: Record<HypothesisStatus, string> = { open: 'Open', supported: 'Supported', refuted: 'Refuted' };

export function HypothesisRegister({ state, onChange }: { state: CompassState; onChange: (s: CompassState) => void }) {
  const [draft, setDraft] = useState(EMPTY);
  const [editing, setEditing] = useState<Hypothesis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async (fn: () => Promise<CompassState>) => {
    setError(null);
    try { onChange(await fn()); announce(); } catch (e) { setError(detailOf(e, 'Could not save the hypothesis.')); }
  };
  const key = state.engagement?.key;

  return (
    <Section
      eyebrow="Operating-model hypotheses"
      title="What you think is true, and what would prove it wrong"
      lede="Write each hypothesis after reading the archetype analysis, with the evidence that would refute it. Numbers are never reused."
    >
      {error && <div className="mb-4"><Callout label="Not saved" tone="attention">{error}</Callout></div>}
      {state.hypotheses.length > 0 && (
        <ul className="card mb-5 divide-y divide-hairline p-0">
          {state.hypotheses.map((h) => editing?.ref === h.ref ? (
            <li key={h.ref} className="space-y-3 px-6 py-4">
              <p className="tabular text-sm font-semibold text-primary-700">{h.ref}</p>
              <input className="input" aria-label="Statement" value={editing.statement} onChange={(e) => setEditing({ ...editing, statement: e.target.value })} />
              <input className="input" aria-label="Refuting evidence" placeholder="What would refute it" value={editing.refuted_by} onChange={(e) => setEditing({ ...editing, refuted_by: e.target.value })} />
              <div className="flex flex-wrap gap-3">
                <select className="input w-auto" aria-label="Status" value={editing.status} onChange={(e) => setEditing({ ...editing, status: e.target.value as HypothesisStatus })}>
                  {state.hypothesis_statuses.map((s) => <option key={s} value={s}>{STATUS_WORD[s]}</option>)}
                </select>
                <input className="input flex-1" aria-label="Note" placeholder="Note" value={editing.note} onChange={(e) => setEditing({ ...editing, note: e.target.value })} />
              </div>
              <div className="flex gap-3">
                <button className="btn btn-primary" onClick={() => run(async () => { const s = await compassApi.updateHypothesis(h.ref, editing); setEditing(null); return s; })}>Save</button>
                <button className="btn btn-quiet" onClick={() => setEditing(null)}>Cancel</button>
              </div>
            </li>
          ) : (
            <li key={h.ref} className="grid gap-3 px-6 py-4 md:grid-cols-[72px_1fr_auto]">
              <p className="tabular text-sm font-semibold text-primary-700" title={key ? `${key}:${h.ref}` : undefined}>{h.ref}</p>
              <div className="text-sm">
                <p className="font-medium text-ink">{h.statement}</p>
                {h.refuted_by && <p className="mt-1 text-secondary"><span className="font-semibold text-ink">Refuted by:</span> {h.refuted_by}</p>}
                {h.note && <p className="mt-1 text-faint">{h.note}</p>}
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <Chip>{STATUS_WORD[h.status]}</Chip>
                  <GradeSelect findingRef={h.ref} suggested="hypothesis" state={state} onChange={onChange} />
                </div>
              </div>
              <div className="flex items-start gap-3 text-xs font-semibold">
                <button className="text-primary-600" onClick={() => setEditing(h)}>Edit</button>
                <button className="text-faint hover:text-ink" onClick={() => { if (confirm(`Delete ${h.ref}? Its number will not be used again.`)) run(() => compassApi.deleteHypothesis(h.ref)); }}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <form className="card space-y-3" onSubmit={(e) => { e.preventDefault(); run(async () => { const s = await compassApi.addHypothesis(draft); setDraft(EMPTY); return s; }); }}>
        <p className="eyebrow">Add a hypothesis</p>
        <input className="input" aria-label="New hypothesis statement" placeholder="e.g. Turnaround decisions are made at the station by the duty controller" value={draft.statement} onChange={(e) => setDraft({ ...draft, statement: e.target.value })} />
        <input className="input" aria-label="New hypothesis refuting evidence" placeholder="Evidence that would refute it, e.g. event records show another role deciding in more than 1 case in 5" value={draft.refuted_by} onChange={(e) => setDraft({ ...draft, refuted_by: e.target.value })} />
        <button type="submit" className="btn btn-secondary" disabled={!draft.statement.trim()}>Add hypothesis</button>
      </form>
    </Section>
  );
}

// ------------------------------------------------------------------ findings to send back

const KIND_LABEL: Record<string, string> = {
  structural_baseline: 'Structural baseline', work_activity: 'Work activity', hypothesis: 'Hypothesis', option_score: 'Option score',
};

export function FindingsRegister({ state, onChange }: { state: CompassState; onChange: (s: CompassState) => void }) {
  const [error, setError] = useState<string | null>(null);
  const setRelates = async (ref: string, refs: string[]) => {
    setError(null);
    try { onChange(await compassApi.setRelates(ref, refs)); } catch (e) { setError(detailOf(e, 'Could not save the link.')); }
  };
  return (
    <Section
      eyebrow={`Findings to send back${state.engagement ? ` · ${state.engagement.key}` : ''}`}
      title="What this app found, in the shared language"
      lede="Each finding carries a grade you can change and the Compass IDs it bears on. People appear as counts or job titles, never names."
      aside={
        <div className="flex flex-wrap gap-3">
          <a className="btn btn-secondary" href={compassApi.returnJsonUrl} download>Download return file (JSON)</a>
          <a className="btn btn-quiet" href={compassApi.returnTextUrl} target="_blank" rel="noreferrer">Readable text ↗</a>
        </div>
      }
    >
      {error && <div className="mb-4"><Callout label="Not saved" tone="attention">{error}</Callout></div>}
      <ul className="card divide-y divide-hairline p-0">
        {state.findings.map((f) => (
          <li key={f.ref} className="grid gap-x-6 gap-y-2 px-6 py-4 lg:grid-cols-[1fr_300px]" data-finding={f.ref}>
            <div className="min-w-0 text-sm">
              <p className="text-xs text-faint"><span className="tabular font-semibold text-primary-700">{f.ref}</span> · {KIND_LABEL[f.kind]}</p>
              <p className="font-medium text-ink">{f.title}{f.figure && <span className="font-normal text-secondary"> — {f.figure}</span>}</p>
              {f.detail && <p className="mt-0.5 text-secondary">{f.detail}</p>}
              <p className="mt-0.5 text-xs text-faint">Rests on: {f.source_note}</p>
            </div>
            <div className="space-y-2">
              <GradeSelect findingRef={f.ref} suggested={f.suggested_grade} state={state} onChange={onChange} />
              <div className="flex flex-wrap items-center gap-1.5">
                {f.relates_to.map((r) => (
                  <button key={r} title="Remove" onClick={() => setRelates(f.ref, f.relates_to.filter((x) => x !== r))}
                    className={clsx('rounded-full border border-hairline px-2 py-0.5 text-xs font-medium text-ink hover:border-primary-600')}>
                    {r} <span aria-hidden className="text-faint">×</span>
                  </button>
                ))}
                {state.refs.length > 0 ? (
                  <select aria-label={`Relate ${f.ref} to a Compass ID`} className="max-w-[170px] rounded border border-hairline bg-white px-1.5 py-0.5 text-xs text-secondary" value=""
                    onChange={(e) => e.target.value && setRelates(f.ref, [...f.relates_to, e.target.value])}>
                    <option value="">+ Relates to…</option>
                    {state.refs.filter((r) => !f.relates_to.includes(r.ref)).map((r) => <option key={r.ref} value={r.ref}>{r.ref} — {r.label.slice(0, 50)}</option>)}
                  </select>
                ) : <span className="text-xs text-faint">Import a Compass file to attach its IDs</span>}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}
