/**
 * Compass anchor roles by country: which roles exist where, and why.
 * The Compass status is the Compass assessor's judgement and is never changed here;
 * where the org file disagrees, a flag says so in words. Matches, reasons and grades are the designer's.
 */
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { compassApi } from '../services/api';
import type { CompassRole, CompassRolesView, Grade, ReasonClass, RoleCell } from '../types';
import { Callout, Chip, EmptyState, Loading, PageHeader, Section } from '../components/ui';
import { GradeBadge } from '../components/Compass';

const people = (n: number) => `${n} ${n === 1 ? 'person' : 'people'}`;
const STATUS_WORD: Record<string, string> = { exists: 'Exists', thin: 'Thin', absent: 'Absent' };
const label = (c: string) => c || 'Whole organization';
/** Editors open below a long table: bring them into view next to where the designer is working. */
function useScrollIntoView() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }); }, []);
  return ref;
}

const detailOf = (e: unknown, fallback: string) =>
  (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? fallback;

function MatchEditor({ role, titles, onSave, onCancel }: {
  role: CompassRole; titles: string[]; onSave: (t: string[] | null) => void; onCancel: () => void;
}) {
  const [picked, setPicked] = useState<string[]>(role.match_confirmed ? role.titles : role.suggestions.map((s) => s.title));
  const toggle = (t: string) => setPicked((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]));
  const ref = useScrollIntoView();
  return (
    <div ref={ref} className="card fade-up" role="region" aria-label={`Match ${role.ref} to job titles`}>
      <p className="eyebrow mb-1">Job titles for {role.ref}</p>
      <p className="mb-4 font-medium text-ink">{role.title}</p>
      <div className="mb-4 grid max-h-72 gap-1 overflow-y-auto sm:grid-cols-2">
        {titles.map((t) => (
          <label key={t} className="flex items-center gap-2 text-sm text-secondary">
            <input type="checkbox" checked={picked.includes(t)} onChange={() => toggle(t)} className="accent-[#C41E3A]" />
            {t}
            {role.suggestions.find((s) => s.title === t) && <span className="text-xs text-faint">({role.suggestions.find((s) => s.title === t)!.kind} match)</span>}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <button className="btn btn-primary" onClick={() => onSave(picked)} disabled={!picked.length}>Confirm these titles</button>
        <button className="btn btn-secondary" onClick={() => onSave([])}>No job title in this file</button>
        {role.match_confirmed && <button className="btn btn-quiet" onClick={() => onSave(null)}>Back to “not matched yet”</button>}
        <button className="btn btn-quiet" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function ReasonEditor({ view, role, cell, onSave, onCancel }: {
  view: CompassRolesView; role: CompassRole; cell: RoleCell;
  onSave: (r: { reason_class: ReasonClass; text: string; compared_with: string; grade: Grade | null }) => void; onCancel: () => void;
}) {
  const [reasonClass, setReasonClass] = useState<ReasonClass>(cell.reason?.reason_class ?? 'unknown');
  const [text, setText] = useState(cell.reason?.text ?? '');
  const [compared, setCompared] = useState(cell.reason?.compared_with ?? '');
  const [grade, setGrade] = useState<Grade | ''>(cell.reason?.grade ?? '');
  const others = view.file_countries.filter((c) => c !== cell.country);
  const ref = useScrollIntoView();
  return (
    <div ref={ref} className="card fade-up" role="region" aria-label={`Reason for ${role.ref} in ${label(cell.country)}`}>
      <p className="eyebrow mb-1">Why {role.title} {cell.holders === 0 ? 'is missing' : 'is as it is'} in {label(cell.country)}</p>
      <p className="mb-4 text-sm text-faint">{role.ref} · {cell.holders === null ? 'not matched yet' : people(cell.holders)} · Compass status {STATUS_WORD[cell.compass_status ?? ''] ?? '—'}{cell.status_confirmed === false ? ' (to confirm)' : ''}</p>
      <div className="mb-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Reason">
        {view.reason_classes.map((k) => (
          <button key={k} type="button" role="radio" aria-checked={reasonClass === k} title={view.reason_help[k]}
            onClick={() => setReasonClass(k)}
            className={clsx('rounded border px-3 py-1.5 text-sm', reasonClass === k ? 'border-primary-600 bg-primary-50 text-ink' : 'border-hairline text-secondary hover:border-ink')}>
            {view.reason_labels[k]}
          </button>
        ))}
      </div>
      <p className="mb-3 text-xs text-faint">{view.reason_help[reasonClass]}</p>
      <label className="label" htmlFor="reason-text">In one line</label>
      <input id="reason-text" className="input mb-4" value={text} onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Created when the country won its two largest renewal contracts" />
      <div className="mb-5 flex flex-wrap gap-4">
        <div>
          <label className="label" htmlFor="compared-with">Compared with (optional)</label>
          <select id="compared-with" className="input w-auto" value={compared} onChange={(e) => setCompared(e.target.value)}>
            <option value="">No other country</option>
            {others.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="reason-grade">Grade (your judgement)</label>
          <select id="reason-grade" className="input w-auto" value={grade} onChange={(e) => setGrade(e.target.value as Grade | '')}>
            <option value="">Suggested ({text ? 'Indicated' : 'Hypothesis'})</option>
            {view.grades.map((g) => <option key={g} value={g}>{g[0].toUpperCase() + g.slice(1)}</option>)}
          </select>
        </div>
      </div>
      <div className="flex gap-3">
        <button className="btn btn-primary" onClick={() => onSave({ reason_class: reasonClass, text, compared_with: compared, grade: grade || null })}>Save reason</button>
        <button className="btn btn-quiet" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function Cell({ cell, onEdit }: { cell: RoleCell; onEdit: () => void }) {
  if (!cell.in_packet) return <span className="text-xs text-faint">Not in this country's Compass file</span>;
  const r = cell.reason;
  return (
    <div className="space-y-1 text-xs">
      <p className="flex flex-wrap items-baseline gap-x-2">
        <span className="tabular text-[15px] font-semibold text-ink">{cell.holders === null ? '–' : cell.holders}</span>
        <span className="text-faint">{cell.holders === null ? 'not matched yet' : cell.holders === 1 ? 'holder' : 'holders'}</span>
        <span className="text-secondary">· {cell.status_confirmed === false
          ? <b className="text-[color:var(--color-score-amber)]">To confirm</b>
          : `Compass: ${STATUS_WORD[cell.compass_status ?? ''] ?? cell.compass_status}`}</span>
      </p>
      {cell.flag && <p className="text-[color:var(--color-score-amber)]"><span aria-hidden>⚑ </span>{cell.flag}</p>}
      {r && (r.text || r.reason_class !== 'unknown') ? (
        <p className="text-secondary">
          <b className="text-ink">{{ required: 'Required', chosen: 'Chosen', inherited: 'Inherited', unknown: 'Not known yet' }[r.reason_class]}</b>
          {r.compared_with && ` vs ${r.compared_with}`}{r.text && ` — ${r.text}`}
          {r.grade && <span className="ml-1"><GradeBadge grade={r.grade} /></span>}
        </p>
      ) : cell.missing_note ? <p className="font-semibold text-primary-700">{cell.missing_note}</p> : null}
      <button className="font-semibold text-primary-600 hover:text-primary-700" onClick={onEdit}>{r ? 'Edit reason' : 'Record reason'}</button>
    </div>
  );
}

export default function CompassRoles() {
  const [view, setView] = useState<CompassRolesView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [matching, setMatching] = useState<string | null>(null);
  const [reasonFor, setReasonFor] = useState<{ ref: string; country: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    compassApi.roles().then(setView).catch(() => setError('Upload an org file first.')).finally(() => setLoading(false));
  }, []);
  const run = async (fn: () => Promise<CompassRolesView>) => {
    setNotice(null);
    try { setView(await fn()); } catch (e) { setNotice(detailOf(e, 'Could not save.')); }
  };

  if (loading) return <Loading label="Matching Compass roles to the org file" />;
  if (error || !view) {
    return (<><PageHeader eyebrow="01 · Diagnose — Compass roles" title="Which roles exist where, and why" />
      <EmptyState title="No organization loaded yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} /></>);
  }
  if (!view.links.length) {
    return (<><PageHeader eyebrow="01 · Diagnose — Compass roles" title="Which roles exist where, and why" />
      <EmptyState title="No Compass file linked yet" body="Import a Capability Compass hand-off file for each country on the Upload page; its anchor roles appear here."
        action={<Link to="/upload" className="btn btn-primary">Import a Compass file →</Link>} /></>);
  }

  const exactWaiting = view.roles.filter((r) => !r.match_confirmed && r.suggestions.some((s) => s.kind === 'exact')).length;
  const unmatchedRoles = view.roles.filter((r) => !r.match_confirmed).length;
  const role = matching ? view.roles.find((r) => r.ref === matching) : undefined;
  const reasonRole = reasonFor ? view.roles.find((r) => r.ref === reasonFor.ref) : undefined;
  const reasonCell = reasonRole?.cells.find((c) => c.country === reasonFor?.country);

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — Compass roles"
        title="Which roles exist where, and why"
        lede="Each Compass anchor role, matched to job titles in the org file and counted per country. The Compass status is the Compass assessor's judgement and is never changed here; where the org file disagrees, a flag says so."
        actions={exactWaiting > 0 ? <button className="btn btn-primary" onClick={() => run(compassApi.acceptExactMatches)}>Accept {exactWaiting} exact title match{exactWaiting === 1 ? '' : 'es'}</button> : undefined}
      />
      {notice && <div className="mb-6"><Callout label="Not saved" tone="attention">{notice}</Callout></div>}
      {unmatchedRoles > 0 && (
        <div className="mb-6"><Callout label="Still to match" tone="developing">
          {unmatchedRoles} role{unmatchedRoles === 1 ? ' is' : 's are'} not matched to a job title yet. They count as neither existing nor absent, and are left out of the findings files until you confirm a match or “No job title in this file”.
        </Callout></div>
      )}

      <div className="mb-8 grid gap-4" style={{ gridTemplateColumns: `repeat(${view.links.length}, minmax(0, 1fr))` }}>
        {view.links.map((l) => {
          const s = view.summary[l.country];
          return (
            <div key={l.country} className="card py-4">
              <p className="eyebrow mb-1">{label(l.country)} · {l.key}</p>
              <p className="text-sm text-secondary">
                <b className="text-ink">{s.exists}</b> exist · <b className="text-ink">{s.absent}</b> absent · <b className="text-ink">{s.to_confirm}</b> to confirm{s.not_matched ? <> · <b className="text-ink">{s.not_matched}</b> not matched</> : null}
              </p>
            </div>
          );
        })}
      </div>

      <Section eyebrow="Anchor roles" title={`${view.roles.length} roles across ${view.links.length} ${view.links.length === 1 ? 'link' : 'countries'}`}>
        <div className="card overflow-x-auto p-0">
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                <th className="w-[280px] px-5 py-3">Role and job titles</th>
                {view.links.map((l) => <th key={l.country} className="px-4 py-3">{label(l.country)}</th>)}
              </tr>
            </thead>
            <tbody>
              {view.roles.map((r) => (
                <tr key={r.ref} className="hairline-b align-top last:border-0" data-role={r.ref}>
                  <td className="px-5 py-3">
                    <p className="text-xs"><span className="tabular font-semibold text-primary-700">{r.ref}</span> <span className="text-faint">· {r.cluster_ref} · {r.route}</span></p>
                    <p className="font-medium text-ink">{r.title}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
                      {r.match_confirmed
                        ? (r.titles.length ? r.titles.map((t) => <Chip key={t}>{t}</Chip>) : <span className="text-secondary">No job title in this file</span>)
                        : r.suggestions.length
                          ? <span className="text-faint">Suggested: {r.suggestions.map((s) => `${s.title} (${s.kind})`).join('; ')}</span>
                          : <span className="text-faint">No title suggested</span>}
                      <button className="font-semibold text-primary-600 hover:text-primary-700" onClick={() => { setReasonFor(null); setMatching(r.ref); }}>
                        {r.match_confirmed ? 'Change' : 'Match…'}
                      </button>
                    </div>
                  </td>
                  {r.cells.map((c) => (
                    <td key={c.country} className="px-4 py-3">
                      <Cell cell={c} onEdit={() => { setMatching(null); setReasonFor({ ref: r.ref, country: c.country }); }} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-faint">
          {view.unmatched_titles} job title{view.unmatched_titles === 1 ? '' : 's'} in the org file match no Compass role.
          Holders count people whose job title is matched to the role, in the country where they work.
        </p>

        {role && (
          <div className="mt-4">
            <MatchEditor key={role.ref} role={role} titles={view.file_titles} onCancel={() => setMatching(null)}
              onSave={(t) => run(async () => { const v = await compassApi.setRoleMatch(role.ref, t); setMatching(null); return v; })} />
          </div>
        )}
        {reasonRole && reasonCell && (
          <div className="mt-4">
            <ReasonEditor key={`${reasonRole.ref}-${reasonCell.country}`} view={view} role={reasonRole} cell={reasonCell} onCancel={() => setReasonFor(null)}
              onSave={(r) => run(async () => { const v = await compassApi.setRoleReason({ ref: reasonRole.ref, country: reasonCell.country, ...r }); setReasonFor(null); return v; })} />
          </div>
        )}
      </Section>

      {view.match_log.length > 0 && (
        <Section eyebrow="Audit" title="Recent changes to title matches">
          <ul className="card divide-y divide-hairline p-0 text-sm">
            {[...view.match_log].reverse().slice(0, 8).map((e, i) => (
              <li key={i} className="px-6 py-2.5 text-secondary">
                <span className="tabular mr-2 font-semibold text-primary-700">{e.ref}</span>
                {e.before === null ? 'not matched' : e.before.length ? e.before.join(', ') : 'no job title'} → <b className="text-ink">{e.after === null ? 'not matched' : e.after.length ? e.after.join(', ') : 'no job title'}</b>
                <span className="ml-2 text-xs text-faint">{e.at.replace('T', ' ').replace('Z', ' UTC')}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </>
  );
}
