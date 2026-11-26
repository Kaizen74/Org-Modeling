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

const DRAG_TYPE = 'application/x-job-titles';

/** Titles carried by a drag: the whole selection when the dragged title is part of it. */
function dragTitles(e: React.DragEvent, title: string, selected: Set<string>) {
  const titles = selected.has(title) ? [...selected] : [title];
  e.dataTransfer.setData(DRAG_TYPE, JSON.stringify(titles));
  e.dataTransfer.setData('text/plain', titles.join('\n'));
  e.dataTransfer.effectAllowed = 'move';
}

function droppedTitles(e: React.DragEvent): string[] {
  try { return JSON.parse(e.dataTransfer.getData(DRAG_TYPE) || '[]'); } catch { return []; }
}

/** A drop target that highlights while titles are dragged over it. */
function useDrop(onDrop: (titles: string[]) => void) {
  const [over, setOver] = useState(false);
  return {
    over,
    props: {
      onDragOver: (e: React.DragEvent) => { if (e.dataTransfer.types.includes(DRAG_TYPE)) { e.preventDefault(); setOver(true); } },
      onDragLeave: () => setOver(false),
      onDrop: (e: React.DragEvent) => { e.preventDefault(); setOver(false); const t = droppedTitles(e); if (t.length) onDrop(t); },
    },
  };
}

function FamilyCard({ family, view, run, selected, onMove }: {
  family: RoleFamily; view: RoleFamiliesView; run: (fn: () => Promise<RoleFamiliesView>) => void;
  selected: Set<string>; onMove: (titles: string[], to: string | null) => void;
}) {
  const [name, setName] = useState(family.name);
  const others = view.families.filter((f) => f.ref !== family.ref);
  const drop = useDrop((titles) => onMove(titles, family.ref));
  return (
    <li {...drop.props} className={clsx('px-5 py-3 transition-colors', drop.over && 'bg-primary-50 outline outline-2 outline-primary-600')} data-family={family.ref}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="tabular w-14 text-sm font-semibold text-primary-700">{family.ref}</span>
        <input className="input w-44 py-1 text-sm" aria-label={`Name of ${family.ref}`} value={name} onChange={(e) => setName(e.target.value)}
          onBlur={() => name.trim() && name !== family.name && run(() => familiesApi.update(family.ref, { name }))} />
        <span className="text-xs text-faint">{family.headcount} {family.headcount === 1 ? 'person' : 'people'} · {family.titles.length} title{family.titles.length === 1 ? '' : 's'}</span>
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
          <span key={t} draggable onDragStart={(e) => dragTitles(e, t, selected)} data-chip={t}
            className={clsx('inline-flex cursor-grab items-center gap-1 rounded-full border px-2 py-0.5 text-ink active:cursor-grabbing',
              selected.has(t) ? 'border-primary-600 bg-primary-50' : 'border-hairline')}>
            <span aria-hidden className="text-faint">⠿</span>{t}
            <button title="Take this title out of the family" aria-label={`Take ${t} out of ${family.ref}`} className="text-faint hover:text-primary-700"
              onClick={() => onMove([t], null)}>×</button>
          </span>
        ))}
        {family.empty && <span className="font-semibold text-[color:var(--color-score-amber)]">No titles: drag some in, or retire it. Left out of the Compass files until it has titles.</span>}
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

/** Drop titles here (or choose "New family…" in Move to) to start a family; it asks for a name first. */
function NewFamilyZone({ pending, setPending, onCreate }: {
  pending: string[]; setPending: (t: string[]) => void; onCreate: (name: string, titles: string[]) => void;
}) {
  const [name, setName] = useState('');
  const drop = useDrop((titles) => setPending([...new Set([...pending, ...titles])]));
  return (
    <div {...drop.props} data-testid="new-family-zone"
      className={clsx('card mb-4 border-dashed py-4 transition-colors', drop.over && 'bg-primary-50 outline outline-2 outline-primary-600')}>
      {pending.length === 0 ? (
        <p className="text-sm text-faint"><b className="text-ink">New family:</b> drop job titles here to start one.</p>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-secondary">New family with {pending.length} title{pending.length === 1 ? '' : 's'}: {pending.join('; ')}</p>
          <div className="flex flex-wrap gap-2">
            <input className="input w-64 py-1 text-sm" aria-label="New family name" placeholder="Name the family, e.g. Airline relations"
              value={name} onChange={(e) => setName(e.target.value)} autoFocus />
            <button className="btn btn-primary py-1 text-sm" disabled={!name.trim()} onClick={() => { onCreate(name, pending); setName(''); }}>Create family</button>
            <button className="btn btn-quiet py-1 text-sm" onClick={() => setPending([])}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Every job title: search, filter, select several, drag, or move with the bar below. Dropping here takes titles out of their family. */
function TitlesPane({ view, selected, setSelected, onMove, onNew }: {
  view: RoleFamiliesView; selected: Set<string>; setSelected: (s: Set<string>) => void;
  onMove: (titles: string[], to: string | null) => void; onNew: (titles: string[]) => void;
}) {
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState<'unassigned' | 'all'>('unassigned');
  const [to, setTo] = useState('');
  const drop = useDrop((titles) => onMove(titles, null));
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const shown = view.titles.filter((t) => (scope === 'all' || !t.family) && words.every((w) => t.title.toLowerCase().includes(w)));
  const allShown = shown.length > 0 && shown.every((t) => selected.has(t.title));
  const toggle = (title: string) => { const n = new Set(selected); if (n.has(title)) n.delete(title); else n.add(title); setSelected(n); };
  const move = () => {
    const titles = [...selected];
    if (to === '__new') onNew(titles);
    else onMove(titles, to === '__out' ? null : to);
    setTo('');
  };
  return (
    <div {...drop.props} className={clsx('card p-0 transition-colors lg:sticky lg:top-4', drop.over && 'outline outline-2 outline-primary-600')} aria-label="Job titles" role="region">
      <div className="hairline-b space-y-2 px-4 py-3">
        <input className="input py-1.5 text-sm" placeholder="Find job titles, e.g. airline" aria-label="Find job titles" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button className={clsx('rounded-full border px-2.5 py-0.5', scope === 'unassigned' ? 'border-primary-600 bg-primary-50 text-ink' : 'border-hairline text-secondary')}
            onClick={() => setScope('unassigned')}>Not in a family ({view.unassigned})</button>
          <button className={clsx('rounded-full border px-2.5 py-0.5', scope === 'all' ? 'border-primary-600 bg-primary-50 text-ink' : 'border-hairline text-secondary')}
            onClick={() => setScope('all')}>All titles ({view.titles.length})</button>
          <label className="ml-auto flex items-center gap-1.5 text-secondary">
            <input type="checkbox" className="accent-[#C41E3A]" checked={allShown} disabled={!shown.length}
              onChange={() => { const n = new Set(selected); shown.forEach((t) => (allShown ? n.delete(t.title) : n.add(t.title))); setSelected(n); }} />
            Select all shown ({shown.length})
          </label>
        </div>
      </div>
      <ul className="max-h-[52vh] divide-y divide-hairline overflow-y-auto text-sm">
        {shown.map((t) => (
          <li key={t.title} draggable onDragStart={(e) => dragTitles(e, t.title, selected)} data-title={t.title}
            className={clsx('flex cursor-grab items-center gap-2 px-4 py-1.5 active:cursor-grabbing', selected.has(t.title) && 'bg-primary-50')}>
            <input type="checkbox" className="accent-[#C41E3A]" checked={selected.has(t.title)} onChange={() => toggle(t.title)} aria-label={`Select ${t.title}`} />
            <span aria-hidden className="text-faint">⠿</span>
            <span className="min-w-0 flex-1 truncate text-ink" title={t.title}>{t.title}</span>
            <span className="tabular text-xs text-faint">{t.headcount}</span>
            {t.family && <span className="tabular text-xs font-semibold text-primary-700">{t.family}</span>}
          </li>
        ))}
        {!shown.length && <li className="px-4 py-3 text-xs text-faint">No titles match.</li>}
      </ul>
      <div className="hairline-t flex flex-wrap items-center gap-2 px-4 py-3 text-sm" role="group" aria-label="Move selected titles">
        <span className="text-secondary">{selected.size} selected</span>
        <select className="input w-auto py-1 text-sm" aria-label="Move selected titles to" value={to} onChange={(e) => setTo(e.target.value)} disabled={!selected.size}>
          <option value="">Move to…</option>
          <option value="__new">A new family…</option>
          {view.families.map((f) => <option key={f.ref} value={f.ref}>{f.ref} {f.name}</option>)}
          <option value="__out">Out of every family</option>
        </select>
        <button className="btn btn-secondary py-1 text-sm" disabled={!selected.size || !to} onClick={move}>Move</button>
        {selected.size > 0 && <button className="text-xs text-faint hover:text-ink" onClick={() => setSelected(new Set())}>Clear</button>}
      </div>
    </div>
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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<string[]>([]);
  useEffect(() => { familiesApi.get().then(setView).catch(() => setError('Upload an org file first.')).finally(() => setLoading(false)); }, []);
  const run = async (fn: () => Promise<RoleFamiliesView>) => {
    setNotice(null);
    try { setView(await fn()); } catch (e) { setNotice(detailOf(e, 'Could not save.')); }
  };

  const moveTitles = (titles: string[], to: string | null) =>
    run(async () => { const v = await familiesApi.move(titles, to); setSelected(new Set()); return v; });

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

      <Section eyebrow="01 · Group job titles" title={view.families.length ? `${view.families.length} famil${view.families.length === 1 ? 'y' : 'ies'} confirmed` : 'No families confirmed yet'}
        lede={`${view.unassigned} job title${view.unassigned === 1 ? '' : 's'} not in a family yet. Drag titles onto a family, or tick several and use Move to; a selected title drags with the rest of the selection. Renaming keeps a family's ID; merging keeps the older ID.`}>
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <TitlesPane view={view} selected={selected} setSelected={setSelected} onMove={moveTitles} onNew={(t) => setPending([...new Set([...pending, ...t])])} />
          <div>
            <NewFamilyZone pending={pending} setPending={setPending}
              onCreate={(name, titles) => run(async () => { const v = await familiesApi.move(titles, 'new', name); setPending([]); setSelected(new Set()); return v; })} />
            {view.families.length > 0 ? (
              <ul className="card divide-y divide-hairline p-0" aria-label="Families">
                {view.families.map((f) => <FamilyCard key={`${f.ref}-${f.name}`} family={f} view={view} run={run} selected={selected} onMove={moveTitles} />)}
              </ul>
            ) : <p className="text-sm text-faint">Confirm a suggestion below, or drop titles on New family.</p>}
          </div>
        </div>
        {view.suggestions.length > 0 && (
          <details className="mt-8" open={!view.families.length}>
            <summary className="eyebrow mb-2 cursor-pointer">Suggested from shared key words ({view.suggestions.length})</summary>
            <ul className="card divide-y divide-hairline p-0" aria-label="Suggested families">
              {view.suggestions.map((s) => (
                <Suggestion key={s.name + s.titles.join('|')} name={s.name} titles={s.titles} onConfirm={(name, titles) => run(() => familiesApi.confirm(name, titles))} />
              ))}
            </ul>
          </details>
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
