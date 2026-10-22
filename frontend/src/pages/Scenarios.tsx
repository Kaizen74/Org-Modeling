import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { scenariosApi, orgDataApi, metricsApi, aiAnalysisApi } from '../services/api';
import type {
  DesignMove,
  MoveType,
  ScenarioDetail,
  ScenarioHeadline,
  ScenarioListItem,
  ScenarioPerson,
} from '../types';
import { PageHeader, Section, Callout, EmptyState, Loading, StatusPill, scoreStatus, formatMoney } from '../components/ui';

// Which way is "better" for each headline figure; neutral ones are just shown
const ROWS: Array<{ key: keyof ScenarioHeadline; label: string; better?: 'up' | 'down'; money?: boolean }> = [
  { key: 'health_score', label: 'Structural health', better: 'up' },
  { key: 'spans_within_benchmark', label: 'Managers within span benchmark', better: 'up' },
  { key: 'single_report_managers', label: 'Single-report managers', better: 'down' },
  { key: 'layers', label: 'Layers', better: 'down' },
  { key: 'headcount', label: 'People' },
  { key: 'managers', label: 'Managers' },
  { key: 'manager_ratio_pct', label: 'Manager ratio %' },
  { key: 'median_span', label: 'Median span' },
  { key: 'total_cost', label: 'People cost', money: true },
  { key: 'ai_capacity_fte', label: 'Capacity AI could free (FTE)', better: 'up' },
];

const MOVE_LABELS: Record<MoveType, { label: string; hint: string }> = {
  reassign: { label: 'Move a person or team', hint: 'Their whole team moves with them' },
  remove_role: { label: 'Remove a role', hint: 'Their direct reports move up a level' },
  add_role: { label: 'Add a role', hint: 'New positions under a manager' },
  merge_teams: { label: 'Merge two teams', hint: "One manager's reports move to another" },
  change_role: { label: 'Redesign a role', hint: 'New title, grade, salary or department' },
  move_department: { label: 'Rename or fold a department', hint: 'Everyone in it moves' },
};

function signed(n: number, money = false) {
  if (!n) return '—';
  const v = money ? formatMoney(Math.abs(n)) : Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return `${n > 0 ? '+' : '−'}${v}`;
}

function changeColor(n: number, better?: 'up' | 'down') {
  if (!n || !better) return 'var(--color-ink)';
  return (n > 0) === (better === 'up') ? 'var(--color-score-green)' : 'var(--color-score-red)';
}

/** Text input + datalist: pick a person by typing a name, title or department. */
function PersonPicker({ id, label, people, value, onChange, optional }: {
  id: string; label: string; people: ScenarioPerson[]; value: string; onChange: (id: string) => void; optional?: boolean;
}) {
  const optionText = (p: ScenarioPerson) => `${p.name} — ${p.job_title}${p.department ? ` · ${p.department}` : ''} [${p.employee_id}]`;
  const selected = people.find((p) => p.employee_id === value);
  const [text, setText] = useState(selected ? optionText(selected) : '');
  useEffect(() => { setText(selected ? optionText(selected) : ''); }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div>
      <label className="label" htmlFor={id}>{label}{optional && <span className="ml-1 normal-case tracking-normal text-faint">(optional)</span>}</label>
      <input
        id={id}
        list={`${id}-list`}
        className="input"
        value={text}
        placeholder="Type a name, title or department"
        onChange={(e) => {
          setText(e.target.value);
          const match = e.target.value.match(/\[([^\]]+)\]$/);
          onChange(match ? match[1] : '');
        }}
      />
      <datalist id={`${id}-list`}>
        {people.map((p) => <option key={p.employee_id} value={optionText(p)} />)}
      </datalist>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div><span className="label">{label}</span>{children}</div>;
}

function MoveForm({ people, departments, onAdd, busy }: {
  people: ScenarioPerson[]; departments: string[]; onAdd: (m: DesignMove) => void; busy: boolean;
}) {
  const [type, setType] = useState<MoveType>('remove_role');
  const [m, setM] = useState<DesignMove>({ type: 'remove_role' });
  const managers = useMemo(() => {
    const ids = new Set(people.map((p) => p.manager_id).filter(Boolean));
    return people.filter((p) => ids.has(p.employee_id));
  }, [people]);
  const set = (patch: Partial<DesignMove>) => setM((prev) => ({ ...prev, ...patch }));
  const reset = (t: MoveType) => { setType(t); setM({ type: t }); };

  const valid =
    (type === 'reassign' && m.person_id && m.new_manager_id) ||
    (type === 'remove_role' && m.person_id) ||
    (type === 'add_role' && m.manager_id && m.title) ||
    (type === 'merge_teams' && m.from_manager_id && m.into_manager_id) ||
    (type === 'change_role' && m.person_id && (m.title || m.grade || m.salary || m.department)) ||
    (type === 'move_department' && m.department && m.new_department);

  return (
    <form
      className="card space-y-4"
      onSubmit={(e) => { e.preventDefault(); if (valid) { onAdd({ ...m, type }); reset(type); } }}
    >
      <p className="eyebrow">Add a design move</p>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(MOVE_LABELS) as MoveType[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => reset(t)}
            className={clsx('rounded-full border px-3 py-1 text-xs font-medium transition-colors',
              type === t ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-hairline text-secondary hover:border-ink hover:text-ink')}
          >
            {MOVE_LABELS[t].label}
          </button>
        ))}
      </div>
      <p className="text-sm text-faint">{MOVE_LABELS[type].hint}</p>

      <div className="grid gap-4 md:grid-cols-2">
        {type === 'reassign' && (<>
          <PersonPicker id="mv-person" label="Who moves" people={people} value={m.person_id ?? ''} onChange={(v) => set({ person_id: v })} />
          <PersonPicker id="mv-to" label="New manager" people={people} value={m.new_manager_id ?? ''} onChange={(v) => set({ new_manager_id: v })} />
          <Field label="New department (optional)">
            <input className="input" list="mv-depts" value={m.department ?? ''} onChange={(e) => set({ department: e.target.value })} />
          </Field>
        </>)}
        {type === 'remove_role' && (<>
          <PersonPicker id="mv-person" label="Role to remove" people={people} value={m.person_id ?? ''} onChange={(v) => set({ person_id: v })} />
          <PersonPicker id="mv-to" label="Their reports move to" optional people={managers} value={m.reports_to ?? ''} onChange={(v) => set({ reports_to: v || undefined })} />
        </>)}
        {type === 'add_role' && (<>
          <Field label="Job title"><input className="input" value={m.title ?? ''} onChange={(e) => set({ title: e.target.value })} placeholder="e.g. Turnaround Coordinator" /></Field>
          <PersonPicker id="mv-mgr" label="Reports to" people={people} value={m.manager_id ?? ''} onChange={(v) => set({ manager_id: v })} />
          <Field label="Grade (sets salary from the grade table)"><input className="input" value={m.grade ?? ''} onChange={(e) => set({ grade: e.target.value })} /></Field>
          <Field label="How many"><input type="number" min={1} max={500} className="input" value={m.count ?? 1} onChange={(e) => set({ count: Number(e.target.value) })} /></Field>
          <Field label="Department (defaults to the manager's)">
            <input className="input" list="mv-depts" value={m.department ?? ''} onChange={(e) => set({ department: e.target.value })} />
          </Field>
          <Field label="Salary (optional override)"><input type="number" className="input" value={m.salary ?? ''} onChange={(e) => set({ salary: e.target.value ? Number(e.target.value) : undefined })} /></Field>
        </>)}
        {type === 'merge_teams' && (<>
          <PersonPicker id="mv-from" label="Team to merge (its manager)" people={managers} value={m.from_manager_id ?? ''} onChange={(v) => set({ from_manager_id: v })} />
          <PersonPicker id="mv-into" label="Into the team of" people={managers} value={m.into_manager_id ?? ''} onChange={(v) => set({ into_manager_id: v })} />
          <label className="flex items-center gap-2 text-sm text-secondary md:col-span-2">
            <input type="checkbox" checked={!!m.remove_from_manager} onChange={(e) => set({ remove_from_manager: e.target.checked })} className="accent-[#C41E3A]" />
            Also remove the merged team's manager role
          </label>
        </>)}
        {type === 'change_role' && (<>
          <PersonPicker id="mv-person" label="Role to redesign" people={people} value={m.person_id ?? ''} onChange={(v) => set({ person_id: v })} />
          <Field label="New title"><input className="input" value={m.title ?? ''} onChange={(e) => set({ title: e.target.value })} /></Field>
          <Field label="New grade"><input className="input" value={m.grade ?? ''} onChange={(e) => set({ grade: e.target.value })} /></Field>
          <Field label="New department"><input className="input" list="mv-depts" value={m.department ?? ''} onChange={(e) => set({ department: e.target.value })} /></Field>
        </>)}
        {type === 'move_department' && (<>
          <Field label="Department"><input className="input" list="mv-depts" value={m.department ?? ''} onChange={(e) => set({ department: e.target.value })} /></Field>
          <Field label="New name, or the department it folds into"><input className="input" list="mv-depts" value={m.new_department ?? ''} onChange={(e) => set({ new_department: e.target.value })} /></Field>
        </>)}
      </div>
      <datalist id="mv-depts">{departments.map((d) => <option key={d} value={d} />)}</datalist>

      <Field label="Why this move (kept with the scenario)">
        <input className="input" value={m.note ?? ''} onChange={(e) => set({ note: e.target.value })} placeholder="e.g. Single-report layer; frees capacity for frontline supervision" />
      </Field>
      <button type="submit" disabled={!valid || busy} className="btn btn-primary">{busy ? 'Applying…' : 'Add move'}</button>
    </form>
  );
}

/** Two markers on one 0–100 track: where health is now and where the scenario takes it. */
function HealthDumbbell({ before, after }: { before: number; after: number }) {
  const lo = Math.min(before, after), hi = Math.max(before, after);
  const color = after >= before ? 'var(--color-score-green)' : 'var(--color-score-red)';
  return (
    <div className="card">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="eyebrow eyebrow-faint mb-2">Structural health</p>
          <p className="display-number text-[44px] text-ink">
            {before}<span className="mx-3 text-faint">→</span>{after}
          </p>
        </div>
        <StatusPill status={scoreStatus(after)} />
      </div>
      <div className="relative h-6" role="img" aria-label={`Health ${before} now, ${after} in this scenario`}>
        <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-track" />
        <div className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full" style={{ left: `${lo}%`, width: `${hi - lo}%`, background: color, opacity: 0.35 }} />
        <span className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-faint" style={{ left: `${before}%` }} title={`Now: ${before}`} />
        <span className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white" style={{ left: `${after}%`, background: color }} title={`Scenario: ${after}`} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-faint"><span>0</span><span>● now · ● scenario</span><span>100</span></div>
    </div>
  );
}

export default function Scenarios() {
  const [list, setList] = useState<ScenarioListItem[]>([]);
  const [baseline, setBaseline] = useState<ScenarioHeadline | null>(null);
  const [active, setActive] = useState<ScenarioDetail | null>(null);
  const [people, setPeople] = useState<ScenarioPerson[]>([]);
  const [singleReportIds, setSingleReportIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newArchetype, setNewArchetype] = useState('');
  const [archetypes, setArchetypes] = useState<Array<{ id: string; name: string }>>([]);

  const refreshList = async () => {
    const r = await scenariosApi.list();
    setList(r.scenarios);
    setBaseline(r.baseline);
    return r.scenarios;
  };

  useEffect(() => {
    (async () => {
      try {
        const [scenarios, org, metrics] = await Promise.all([refreshList(), orgDataApi.getLatest(), metricsApi.getLatest()]);
        setPeople(org.employees.map((e) => ({
          employee_id: e.employee_id, name: e.name, job_title: e.job_title, department: e.department,
          manager_id: e.manager_id ?? null, grade: e.grade, is_new: false,
        })));
        // Single-report managers below the top are the quick-start delayering candidates
        setSingleReportIds(
          (metrics.metrics.span_of_control.manager_assessments ?? [])
            .filter((a) => a.span === 1)
            .map((a) => a.manager_id)
            .filter((id) => org.employees.find((e) => e.employee_id === id)?.manager_id)
        );
        if (scenarios.length) setActive(await scenariosApi.get(scenarios[scenarios.length - 1].id));
        // Recommended archetypes (if an archetype analysis has been run) can be tagged on a scenario
        aiAnalysisApi.getLatest().then((r) => {
          const cat = r.ai_analysis?.category_4_recommended_archetypes;
          const recs = cat && !Array.isArray(cat) ? cat.recommendations ?? [] : [];
          setArchetypes(recs.filter((x) => x.archetype_id).map((x) => ({ id: x.archetype_id as string, name: x.archetype })));
        }).catch(() => undefined);
      } catch {
        setError('Upload an org structure CSV first — scenarios start from the current state.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const run = async (fn: () => Promise<ScenarioDetail | void>) => {
    setBusy(true);
    try {
      const result = await fn();
      if (result) setActive(result);
      await refreshList();
    } finally {
      setBusy(false);
    }
  };

  const create = (name: string, moves: DesignMove[] = [], cloneFrom?: string, source?: string) =>
    run(() => scenariosApi.create(name, { moves, cloneFrom, source }));

  const departments = useMemo(() => [...new Set(people.map((p) => p.department).filter(Boolean))].sort(), [people]);
  const pickerPeople = active?.people ?? people;

  if (loading) return <Loading label="Loading scenarios" />;
  if (error) {
    return (
      <>
        <PageHeader eyebrow="02 · Design — scenario studio" title="Scenario Studio" />
        <EmptyState title="No organization to design from" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="02 · Design — scenario studio"
        title="Build structural options and see what each one changes"
        lede="Each scenario starts from the current organization. Add design moves — remove a layer, merge teams, add a role — and every change is measured the same way as the current state."
      />

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        {/* Scenario list */}
        <aside className="space-y-3 self-start">
          <div className="card py-4">
            <p className="eyebrow eyebrow-faint mb-1">Current state</p>
            {baseline && (
              <p className="text-sm text-secondary">
                Health <span className="tabular font-semibold text-ink">{baseline.health_score}</span> ·{' '}
                {baseline.layers} layers · {formatMoney(baseline.total_cost)}
              </p>
            )}
          </div>
          {list.map((s) => (
            <button
              key={s.id}
              onClick={() => run(() => scenariosApi.get(s.id))}
              className={clsx('card block w-full py-4 text-left transition-colors hover:bg-wash', active?.id === s.id && 'border-primary-600')}
            >
              <p className="font-medium text-ink">{s.name}</p>
              <p className="text-xs text-faint">
                {s.source?.startsWith('archetype:') && <span className="text-primary-600">Archetype · </span>}
                {s.move_count} move{s.move_count === 1 ? '' : 's'}{s.skipped_moves ? ` · ${s.skipped_moves} skipped` : ''}
              </p>
              <p className="tabular mt-2 flex flex-wrap gap-x-3 text-xs">
                <span style={{ color: changeColor(s.delta.health_score, 'up') }}>Health {signed(s.delta.health_score)}</span>
                <span style={{ color: changeColor(s.delta.layers, 'down') }}>Layers {signed(s.delta.layers)}</span>
                <span className="text-ink">Cost {signed(s.delta.total_cost, true)}</span>
              </p>
            </button>
          ))}
          <form
            className="card space-y-2 py-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) {
                create(newName.trim(), [], undefined, newArchetype ? `archetype:${newArchetype}` : 'manual');
                setNewName('');
                setNewArchetype('');
              }
            }}
          >
            <label className="label" htmlFor="new-scenario">New scenario</label>
            <input id="new-scenario" className="input" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Delayer Customer Experience" />
            {archetypes.length > 0 && (
              <select className="input text-sm" value={newArchetype} onChange={(e) => setNewArchetype(e.target.value)} aria-label="Implements archetype">
                <option value="">Not tied to an archetype</option>
                {archetypes.map((a) => <option key={a.id} value={a.id}>Implements: {a.name}</option>)}
              </select>
            )}
            <button type="submit" className="btn btn-secondary w-full justify-center" disabled={!newName.trim() || busy}>Create</button>
          </form>
          {singleReportIds.length > 0 && (
            <button
              className="card block w-full py-4 text-left transition-colors hover:bg-wash"
              disabled={busy}
              onClick={() => create(
                'Remove single-report managers',
                singleReportIds.map((id) => ({ type: 'remove_role', person_id: id, note: 'Manages one person: layer-removal candidate' }))
              )}
            >
              <p className="eyebrow mb-1">Quick start</p>
              <p className="text-sm font-medium text-ink">Remove the {singleReportIds.length} single-report managers</p>
              <p className="text-xs text-faint">Their one report moves up a level. Edit the moves afterwards.</p>
            </button>
          )}
        </aside>

        {/* Active scenario */}
        <div>
          {!active ? (
            <EmptyState
              title="No scenario yet"
              body="Create a scenario on the left, or use the quick start, then add design moves to see how the structure changes."
            />
          ) : (
            <>
              <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow mb-2">Scenario</p>
                  <h2 className="text-[32px] leading-tight">{active.name}</h2>
                  {active.description && <p className="mt-2 text-secondary">{active.description}</p>}
                  <p className="mt-2 text-sm text-faint">
                    {active.impact.people_affected} people affected ({active.impact.people_affected_pct}%) ·{' '}
                    {active.impact.roles_removed.length} roles removed · {active.impact.roles_added.length} added ·{' '}
                    {active.impact.new_manager.length} get a new manager
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="btn btn-quiet" disabled={busy} onClick={() => create(`${active.name} (copy)`, [], active.id)}>Duplicate</button>
                  <button
                    className="btn btn-quiet"
                    disabled={busy}
                    onClick={() => { if (confirm(`Delete “${active.name}”?`)) run(async () => { await scenariosApi.remove(active.id); setActive(null); }); }}
                  >
                    Delete
                  </button>
                </div>
              </div>

              <Section eyebrow="01 · Effect on the organization">
                <div className="grid items-start gap-6 xl:grid-cols-[0.8fr_1.2fr]">
                  <HealthDumbbell before={active.baseline.health_score} after={active.scenario.health_score} />
                  <div className="card overflow-x-auto p-0">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                          <th className="px-5 py-3">Measure</th>
                          <th className="px-4 py-3 text-right">Now</th>
                          <th className="px-4 py-3 text-right">Scenario</th>
                          <th className="px-5 py-3 text-right">Change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ROWS.filter((r) => r.key !== 'ai_capacity_fte' || active.baseline.ai_capacity_fte || active.scenario.ai_capacity_fte).map((r) => {
                          const d = (active.delta[r.key] as number) ?? 0;
                          const fmt = (v: number) => (r.money ? formatMoney(v) : v.toLocaleString(undefined, { maximumFractionDigits: 2 }));
                          return (
                            <tr key={r.key} className="hairline-b last:border-0">
                              <td className="whitespace-nowrap px-5 py-2.5 text-ink">{r.label}</td>
                              <td className="tabular px-4 py-2.5 text-right text-secondary">{fmt((active.baseline[r.key] as number) ?? 0)}</td>
                              <td className="tabular px-4 py-2.5 text-right font-semibold text-ink">{fmt((active.scenario[r.key] as number) ?? 0)}</td>
                              <td className="tabular px-5 py-2.5 text-right font-semibold" style={{ color: changeColor(d, r.better) }}>{signed(d, r.money)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
                <p className="mt-2 text-xs text-faint">Green and red mark changes with a clear direction; cost and headcount are shown without judgement.</p>
              </Section>

              <Section eyebrow="02 · Design moves" title={`${active.moves.length} move${active.moves.length === 1 ? '' : 's'}, applied in order`}>
                {active.moves.length > 0 && (
                  <ol className="card mb-6 divide-y divide-hairline p-0">
                    {active.moves.map((mv, i) => {
                      const log = active.move_log[i];
                      return (
                        <li key={i} className="grid grid-cols-[40px_1fr_auto] gap-3 px-5 py-4">
                          <span className="display-number text-[22px] text-placeholder">{String(i + 1).padStart(2, '0')}</span>
                          <div>
                            <p className={clsx('text-sm', log?.status === 'skipped' ? 'text-faint line-through' : 'text-ink')}>
                              {log?.message ?? MOVE_LABELS[mv.type]?.label}
                            </p>
                            {log?.status === 'skipped' && <p className="mt-1 text-xs" style={{ color: 'var(--color-score-red)' }}>Skipped: {log.message}</p>}
                            {mv.note && <p className="mt-1 text-xs text-faint">Why: {mv.note}</p>}
                          </div>
                          <button className="text-xs font-semibold text-primary-600 hover:text-primary-700" disabled={busy} onClick={() => run(() => scenariosApi.removeMove(active.id, i))}>
                            Remove
                          </button>
                        </li>
                      );
                    })}
                  </ol>
                )}
                <MoveForm people={pickerPeople} departments={departments} busy={busy} onAdd={(m) => run(() => scenariosApi.addMove(active.id, m))} />
              </Section>

              <Section eyebrow="03 · Departments" title="Before and after, by department">
                <div className="card overflow-x-auto p-0">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                        <th className="px-5 py-3">Department</th>
                        <th className="px-4 py-3 text-right">People</th>
                        <th className="px-4 py-3 text-right">Managers</th>
                        <th className="px-4 py-3 text-right">Avg span</th>
                        <th className="px-5 py-3 text-right">Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {active.departments.map((d) => (
                        <tr key={d.department} className={clsx('hairline-b last:border-0', d.status === 'unchanged' && 'text-faint')}>
                          <td className="px-5 py-2.5">
                            <span className={d.status === 'unchanged' ? '' : 'font-medium text-ink'}>{d.department}</span>
                            {d.status === 'new' && <span className="ml-2 text-xs text-primary-600">new</span>}
                            {d.status === 'removed' && <span className="ml-2 text-xs text-faint">removed</span>}
                          </td>
                          <td className="tabular px-4 py-2.5 text-right">{d.headcount_before} → <span className="font-semibold">{d.headcount_after}</span></td>
                          <td className="tabular px-4 py-2.5 text-right">{d.managers_before} → <span className="font-semibold">{d.managers_after}</span></td>
                          <td className="tabular px-4 py-2.5 text-right">{d.average_span_before} → <span className="font-semibold">{d.average_span_after}</span></td>
                          <td className="tabular px-5 py-2.5 text-right">{formatMoney(d.cost_before)} → <span className="font-semibold">{formatMoney(d.cost_after)}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>

              {active.move_log.some((m) => m.status === 'skipped') && (
                <Callout label="Some moves were skipped" tone="developing">
                  Skipped moves are kept so you can fix or remove them; they have no effect on the figures above.
                </Callout>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
