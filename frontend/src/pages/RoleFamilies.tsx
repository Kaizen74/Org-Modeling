/**
 * Role families: every job title grouped once for the whole org file (RF-nn),
 * then compared across units: in every unit, in some, or only in one — and why.
 * Suggestions come from shared key words; nothing is applied until confirmed. No AI.
 */
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { familiesApi } from '../services/api';
import type { ReasonClass, RoleFamiliesView, RoleFamily } from '../types';
import { Callout, EmptyState, Loading, PageHeader, Section, unitWords } from '../components/ui';

const REASON_LABEL: Record<ReasonClass, string> = { required: 'Required', chosen: 'Chosen', inherited: 'Inherited', unknown: 'Not known yet' };
const REASON_HELP: Record<ReasonClass, string> = {
  required: 'Regulation, a customer contract or the physical site makes it necessary',
  chosen: 'A deliberate local decision someone can state',
  inherited: 'History, an acquisition or habit; nobody decided it',
  unknown: 'Not known yet',
};
const detailOf = (e: unknown, fallback: string) =>
  (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? fallback;

function Suggestion({ name: initial, titles, onConfirm }: { name: string; titles: string[]; onConfirm: (name: string, titles: string[]) => void }) {
  const [name, setName] = useState(initial);
  const [picked, setPicked] = useState<string[]>(titles);
  return (
    <li className="px-5 py-3" data-suggestion={initial}>
      <div className="flex flex-wrap items-center gap-2">
        <input className="input w-60 py-1 text-sm" aria-label={`Family name for ${initial}`} value={name} onChange={(e) => setName(e.target.value)} />
        {titles.map((t) => (
          <label key={t} className="flex items-center gap-1.5 text-xs text-secondary">
            <input type="checkbox" checked={picked.includes(t)} className="accent-[#C41E3A]"
              onChange={() => setPicked((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]))} />
            {t}
          </label>
        ))}
        <button className="btn btn-quiet ml-auto py-1 text-xs" disabled={!picked.length || !name.trim()} onClick={() => onConfirm(name, picked)}>Confirm family</button>
      </div>
    </li>
  );
}

function FamilyCard({ family, view, run }: { family: RoleFamily; view: RoleFamiliesView; run: (fn: () => Promise<RoleFamiliesView>) => void }) {
  const [name, setName] = useState(family.name);
  const others = view.families.filter((f) => f.ref !== family.ref);
  const addable = view.titles.filter((t) => t.family !== family.ref);
  return (
    <li className="px-5 py-3" data-family={family.ref}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="tabular w-14 text-sm font-semibold text-primary-700">{family.ref}</span>
        <input className="input w-60 py-1 text-sm" aria-label={`Name of ${family.ref}`} value={name} onChange={(e) => setName(e.target.value)}
          onBlur={() => name.trim() && name !== family.name && run(() => familiesApi.update(family.ref, { name }))} />
        <span className="text-xs text-faint">{family.headcount} {family.headcount === 1 ? 'person' : 'people'}</span>
        <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
          {others.length > 0 && (
            <select className="rounded border border-hairline bg-white px-1.5 py-0.5" aria-label={`Merge ${family.ref} with`} value=""
              onChange={(e) => e.target.value && confirm(`Merge ${family.ref} and ${e.target.value}? The older ID stays; the other is retired and never reused.`) && run(() => familiesApi.merge(family.ref, e.target.value))}>
              <option value="">Merge with…</option>
              {others.map((f) => <option key={f.ref} value={f.ref}>{f.ref} {f.name}</option>)}
            </select>
          )}
          <button className="font-semibold text-faint hover:text-ink"
            onClick={() => confirm(`Retire ${family.ref}? Its titles go back to unassigned and the number is never reused.`) && run(() => familiesApi.retire(family.ref))}>Retire</button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-16 text-xs">
        {family.titles.map((t) => (
          <button key={t} title="Take this title out of the family" className="rounded-full border border-hairline px-2 py-0.5 text-ink hover:border-primary-600"
            onClick={() => run(() => familiesApi.update(family.ref, { titles: family.titles.filter((x) => x !== t) }))}>
            {t} <span aria-hidden className="text-faint">×</span>
          </button>
        ))}
        <select className="max-w-[220px] rounded border border-hairline bg-white px-1.5 py-0.5 text-secondary" aria-label={`Add a job title to ${family.ref}`} value=""
          onChange={(e) => e.target.value && run(() => familiesApi.update(family.ref, { titles: [...family.titles, e.target.value] }))}>
          <option value="">+ Add a title…</option>
          {addable.map((t) => <option key={t.title} value={t.title}>{t.title}{t.family ? ` (now in ${t.family})` : ''}</option>)}
        </select>
        {view.cluster_refs.length > 0 && (
          <>
            {family.relates_to.map((r) => (
              <button key={r} title="Remove" className="rounded-full border border-hairline px-2 py-0.5 text-ink"
                onClick={() => run(() => familiesApi.update(family.ref, { relates_to: family.relates_to.filter((x) => x !== r) }))}>{r} <span aria-hidden className="text-faint">×</span></button>
            ))}
            <select className="max-w-[200px] rounded border border-hairline bg-white px-1.5 py-0.5 text-secondary" aria-label={`Compass cluster for ${family.ref}`} value=""
              onChange={(e) => e.target.value && run(() => familiesApi.update(family.ref, { relates_to: [...family.relates_to, e.target.value] }))}>
              <option value="">+ Serves cluster…</option>
              {view.cluster_refs.filter((c) => !family.relates_to.includes(c.ref)).map((c) => <option key={c.ref} value={c.ref}>{c.ref} {c.label}</option>)}
            </select>
          </>
        )}
      </div>
    </li>
  );
}

function ReasonEditor({ family, unit, units, onSave, onCancel }: {
  family: RoleFamily; unit: string; units: string[];
  onSave: (c: ReasonClass | null, text: string, compared: string) => void; onCancel: () => void;
}) {
  const current = family.reasons[unit];
  const [cls, setCls] = useState<ReasonClass>(current?.reason_class ?? 'unknown');
  const [text, setText] = useState(current?.text ?? '');
  const [compared, setCompared] = useState(current?.compared_with ?? '');
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollIntoView?.({ block: 'center', behavior: 'smooth' }); }, []);
  const n = family.by_unit[unit] ?? 0;
  return (
    <div ref={ref} className="card fade-up" role="region" aria-label={`Why ${family.ref} in ${unit}`}>
      <p className="eyebrow mb-1">Why {family.name} {n ? 'is here' : 'is absent'} in {unit}</p>
      <p className="mb-4 text-sm text-faint">{family.ref} · {n} {n === 1 ? 'person' : 'people'}</p>
      <div className="mb-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Reason">
        {(Object.keys(REASON_LABEL) as ReasonClass[]).map((k) => (
          <button key={k} type="button" role="radio" aria-checked={cls === k} title={REASON_HELP[k]} onClick={() => setCls(k)}
            className={clsx('rounded border px-3 py-1.5 text-sm', cls === k ? 'border-primary-600 bg-primary-50 text-ink' : 'border-hairline text-secondary hover:border-ink')}>
            {REASON_LABEL[k]}
          </button>
        ))}
      </div>
      <p className="mb-3 text-xs text-faint">{REASON_HELP[cls]}</p>
      <label className="label" htmlFor="family-reason">In one sentence</label>
      <input id="family-reason" className="input mb-4" value={text} onChange={(e) => setText(e.target.value)} />
      <label className="label" htmlFor="family-compared">Compared with (optional)</label>
      <select id="family-compared" className="input mb-5 w-auto" value={compared} onChange={(e) => setCompared(e.target.value)}>
        <option value="">No other unit</option>
        {units.filter((u) => u !== unit).map((u) => <option key={u} value={u}>{u}</option>)}
      </select>
      <div className="flex gap-3">
        <button className="btn btn-primary" onClick={() => onSave(cls, text, compared)}>Save reason</button>
        {current && <button className="btn btn-quiet" onClick={() => onSave(null, '', '')}>Clear</button>}
        <button className="btn btn-quiet" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function RoleFamilies() {
  const [view, setView] = useState<RoleFamiliesView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ ref: string; unit: string } | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { familiesApi.get().then(setView).catch(() => setError('Upload an org file first.')).finally(() => setLoading(false)); }, []);
  const run = async (fn: () => Promise<RoleFamiliesView>) => {
    setNotice(null);
    try { setView(await fn()); } catch (e) { setNotice(detailOf(e, 'Could not save.')); }
  };

  if (loading) return <Loading label="Grouping job titles" />;
  if (error || !view) {
    return (<><PageHeader eyebrow="01 · Diagnose — role families" title="Which roles are common, and which are unique" />
      <EmptyState title="No organization loaded yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} /></>);
  }
  const unit = unitWords(view.unit_label);
  const editFamily = editing ? view.families.find((f) => f.ref === editing.ref) : undefined;
  const presenceWord = (f: RoleFamily) =>
    f.presence === 'every' ? `In every ${unit.lower}` : f.presence === 'only' ? `Only in ${f.only_in}` : f.presence === 'some' ? 'In some' : f.presence === 'none' ? 'Nobody' : '';

  return (
    <>
      <PageHeader
        eyebrow="01 · Diagnose — role families"
        title="Which roles are common, and which are unique"
        lede={`Group every job title into a family once, for the whole org file. Each family keeps its ID (RF-01, RF-02…) in every ${unit.lower}'s Compass file, so the Compass can line ${unit.plural} up. Suggestions come from shared key words; nothing is applied until you confirm it.`}
      />
      {notice && <div className="mb-6"><Callout label="Not saved" tone="attention">{notice}</Callout></div>}

      <Section eyebrow="01 · Families" title={view.families.length ? `${view.families.length} famil${view.families.length === 1 ? 'y' : 'ies'} confirmed` : 'No families confirmed yet'}
        lede={`${view.unassigned} job title${view.unassigned === 1 ? '' : 's'} not in a family yet. Rename a family by editing its name; renaming keeps its ID. Merging keeps the older ID.`}>
        {view.families.length > 0 && (
          <ul className="card mb-6 divide-y divide-hairline p-0">
            {view.families.map((f) => <FamilyCard key={`${f.ref}-${f.name}`} family={f} view={view} run={run} />)}
          </ul>
        )}
        {view.suggestions.length > 0 && (
          <>
            <p className="eyebrow mb-2">Suggested from shared key words</p>
            <ul className="card divide-y divide-hairline p-0" aria-label="Suggested families">
              {view.suggestions.map((s) => (
                <Suggestion key={s.name + s.titles.join('|')} name={s.name} titles={s.titles} onConfirm={(name, titles) => run(() => familiesApi.confirm(name, titles))} />
              ))}
            </ul>
          </>
        )}
        {view.retired.length > 0 && <p className="mt-3 text-xs text-faint">Retired, never reused: {view.retired.map((r) => `${r.ref} ${r.name}${r.merged_into ? ` (merged into ${r.merged_into})` : ''}`).join('; ')}.</p>}
      </Section>

      {view.units.length > 0 && view.families.length > 0 && (
        <Section eyebrow={`02 · Roles across ${unit.plural}`} title={`Which families are in every ${unit.lower}, in some, or only one`}
          lede={`Head-count per ${unit.lower}, counted from the file. For a family that isn't in every ${unit.lower}, record why it is, or isn't, there; that reason goes into the ${unit.lower}'s Compass file.`}>
          <div className="card overflow-x-auto p-0">
            <table className="w-full table-fixed text-sm" aria-label={`Roles across ${unit.plural}`}>
              <thead>
                <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                  <th className="w-[260px] px-5 py-3">Family</th>
                  {view.units.map((u) => <th key={u} className="px-4 py-3">{u}</th>)}
                </tr>
              </thead>
              <tbody>
                {view.families.map((f) => (
                  <tr key={f.ref} className="hairline-b align-top last:border-0" data-across={f.ref}>
                    <td className="px-5 py-3">
                      <p className="text-xs"><span className="tabular font-semibold text-primary-700">{f.ref}</span></p>
                      <p className="font-medium text-ink">{f.name}</p>
                      <p className={clsx('mt-1 text-xs font-semibold', f.presence === 'every' ? 'text-[color:var(--color-score-green)]' : 'text-[color:var(--color-score-amber)]')}>
                        <span aria-hidden>{f.presence === 'every' ? '● ' : f.presence === 'only' ? '◆ ' : '◐ '}</span>{presenceWord(f)}
                      </p>
                    </td>
                    {view.units.map((u) => {
                      const n = f.by_unit[u] ?? 0;
                      const r = f.reasons[u];
                      return (
                        <td key={u} className="px-4 py-3 text-xs">
                          <p><span className="tabular text-[15px] font-semibold text-ink">{n || '–'}</span> <span className="text-faint">{n ? (n === 1 ? 'person' : 'people') : 'absent'}</span></p>
                          {r && <p className="mt-1 text-secondary"><b className="text-ink">{REASON_LABEL[r.reason_class]}</b>{r.compared_with && ` vs ${r.compared_with}`}{r.text && ` — ${r.text}`}</p>}
                          {(f.presence !== 'every' || r) && (
                            <button className="mt-1 font-semibold text-primary-600 hover:text-primary-700" onClick={() => setEditing({ ref: f.ref, unit: u })}>{r ? 'Edit why' : 'Why?'}</button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {editFamily && editing && (
            <div className="mt-4">
              <ReasonEditor key={`${editing.ref}-${editing.unit}`} family={editFamily} unit={editing.unit} units={view.units} onCancel={() => setEditing(null)}
                onSave={(c, text, compared) => run(async () => { const v = await familiesApi.setReason(editing.ref, editing.unit, c, text, compared); setEditing(null); return v; })} />
            </div>
          )}
          <p className="mt-2 text-xs text-faint">Compass anchor roles stay on their own screen; a family can include an anchor role's job titles.</p>
        </Section>
      )}
      {!view.units.length && view.families.length > 0 && (
        <Callout label="One unit" tone="neutral">Add a Country (or Station, Asset, Business unit, Unit) column to the org file to compare families across units.</Callout>
      )}
    </>
  );
}
