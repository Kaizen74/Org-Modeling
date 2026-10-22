/**
 * Optional overlay: the role of AI in each role's work.
 * Collapsed by default and never required — every other screen works without it.
 */
import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { aiDispositionApi } from '../services/api';
import type { Disposition, DispositionPayload } from '../types';
import { Callout, formatMoney } from './ui';

const LABELS: Record<Disposition, { label: string; color: string }> = {
  automate: { label: 'Automate', color: 'var(--color-primary)' },
  augment: { label: 'Augment', color: 'var(--color-score-amber)' },
  keep_human: { label: 'Keep human', color: 'var(--color-ink)' },
};

export default function AIRoleOverlay() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<DispositionPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (open && !data) aiDispositionApi.get().then(setData).catch(() => setNotice('Upload org data first.'));
  }, [open, data]);

  const run = async (fn: () => Promise<DispositionPayload>, done?: (d: DispositionPayload) => string) => {
    setBusy(true);
    setNotice(null);
    try {
      const d = await fn();
      setData(d);
      if (done) setNotice(done(d));
    } catch (e: unknown) {
      setNotice((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'That did not work.');
    } finally {
      setBusy(false);
    }
  };

  const s = data?.summary;
  return (
    <section className="card mb-14 p-0">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left" aria-expanded={open}>
        <span>
          <span className="eyebrow mb-1 block">Optional overlay</span>
          <span className="font-display text-[22px] font-bold text-ink">The role of AI in this work</span>
          <span className="mt-1 block text-sm text-secondary">
            Tag roles as automate, augment or keep human to see the capacity AI could free in each scenario. Skip it any time — nothing else depends on it.
          </span>
        </span>
        <span className="font-display text-2xl text-primary-600" aria-hidden>{open ? '–' : '+'}</span>
      </button>

      {open && (
        <div className="hairline-t px-6 py-6">
          {!data ? <p className="text-sm text-faint">{notice ?? 'Loading roles…'}</p> : (
            <>
              <div className="mb-5 flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-secondary">
                  <input type="checkbox" checked={data.enabled} onChange={(e) => run(() => aiDispositionApi.setEnabled(e.target.checked))} className="accent-[#C41E3A]" />
                  Show AI capacity in scenarios and comparisons
                </label>
                {data.ai_available && (
                  <button className="btn btn-quiet ml-auto" disabled={busy} onClick={() => run(() => aiDispositionApi.suggest(), (d) => `${d.suggestions_added ?? 0} roles tagged by the AI. Your own tags were left as they are.`)}>
                    {busy ? 'Working…' : 'Suggest tags for untagged roles (AI)'}
                  </button>
                )}
              </div>

              {s && (
                <div className="mb-6 grid gap-4 md:grid-cols-4">
                  {(Object.keys(LABELS) as Disposition[]).map((k) => (
                    <div key={k} className="hairline-t pt-3" style={{ borderTopColor: LABELS[k].color, borderTopWidth: 2 }}>
                      <p className="text-[11px] font-semibold uppercase tracking-[.14em]" style={{ color: LABELS[k].color }}>{LABELS[k].label}</p>
                      <p className="tabular mt-1 text-sm text-ink">{s.by_disposition[k].roles} roles · {s.by_disposition[k].people} people</p>
                    </div>
                  ))}
                  <div className="hairline-t pt-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[.14em] text-faint">Capacity AI could free</p>
                    <p className="tabular mt-1 text-sm text-ink">{s.capacity_fte} FTE · {formatMoney(s.capacity_cost)}</p>
                  </div>
                </div>
              )}
              {notice && <div className="mb-4"><Callout label="Note" tone="accent">{notice}</Callout></div>}

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                      <th className="py-2 pr-4">Role</th>
                      <th className="px-2 py-2 text-right">People</th>
                      <th className="px-2 py-2">Role of AI</th>
                      <th className="px-2 py-2 text-right">Time freed</th>
                      <th className="py-2 pl-2">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.roles.map((r) => (
                      <tr key={r.job_title} className="hairline-b align-top last:border-0">
                        <td className="py-2.5 pr-4">
                          <p className="font-medium text-ink">{r.job_title}</p>
                          <p className="text-xs text-faint">{r.departments.join(', ')}</p>
                        </td>
                        <td className="tabular px-2 py-2.5 text-right text-secondary">{r.headcount}</td>
                        <td className="px-2 py-2.5">
                          <div className="flex flex-wrap gap-1">
                            {(Object.keys(LABELS) as Disposition[]).map((k) => (
                              <button
                                key={k}
                                disabled={busy}
                                onClick={() => run(() => aiDispositionApi.tag(r.job_title, r.tag?.disposition === k ? null : k, r.tag?.capacity_freed_pct ?? (k === 'automate' ? 60 : k === 'augment' ? 20 : 0)))}
                                className={clsx('rounded-full border px-2.5 py-0.5 text-xs font-medium',
                                  r.tag?.disposition === k ? 'text-white' : 'border-hairline text-secondary hover:border-ink')}
                                style={r.tag?.disposition === k ? { background: LABELS[k].color, borderColor: LABELS[k].color } : undefined}
                              >
                                {LABELS[k].label}
                              </button>
                            ))}
                          </div>
                          {r.tag && <p className="mt-1 text-[11px] text-faint">{r.tag.source === 'ai' ? `AI suggestion${r.tag.confidence ? ` · ${r.tag.confidence} confidence` : ''}` : 'Your tag'}</p>}
                        </td>
                        <td className="px-2 py-2.5 text-right">
                          {r.tag ? (
                            <input
                              type="number" min={0} max={100} defaultValue={r.tag.capacity_freed_pct}
                              className="input w-20 py-1 text-right"
                              aria-label={`Share of time freed for ${r.job_title}`}
                              onBlur={(e) => {
                                const v = Number(e.target.value);
                                if (r.tag && v !== r.tag.capacity_freed_pct) run(() => aiDispositionApi.tag(r.job_title, r.tag!.disposition, v, r.tag!.rationale));
                              }}
                            />
                          ) : <span className="text-faint">—</span>}
                        </td>
                        <td className="max-w-xs py-2.5 pl-2 text-xs text-secondary">{r.tag?.rationale || (r.activities[0] ? <span className="text-faint">{r.activities[0].slice(0, 90)}</span> : '')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-faint">
                Freed capacity is shown alongside each scenario; it never changes headcount by itself. Decide what to do with it — redeploy, absorb growth or remove roles — through design moves.
              </p>
            </>
          )}
        </div>
      )}
    </section>
  );
}
