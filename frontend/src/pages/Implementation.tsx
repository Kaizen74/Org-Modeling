import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { scenariosApi, comparisonApi, packUrl } from '../services/api';
import type { ImplementationPlan, ScenarioListItem } from '../types';
import { PageHeader, Section, StatTile, StatusPill, EmptyState, Loading, Callout, severityStatus, formatMoney } from '../components/ui';

function signedMoney(n: number) {
  if (!n) return '—';
  return `${n > 0 ? '+' : '−'}${formatMoney(Math.abs(n))}`;
}

export default function Implementation() {
  const [scenarios, setScenarios] = useState<ScenarioListItem[]>([]);
  const [selected, setSelected] = useState('');
  const [plan, setPlan] = useState<ImplementationPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeNames, setIncludeNames] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const list = (await scenariosApi.list()).scenarios;
        setScenarios(list);
        // Default to the option that leads the comparison, else the latest scenario
        const ranking = (await comparisonApi.get().catch(() => null))?.result.ranking ?? [];
        const lead = ranking.find((id) => id !== 'current' && list.some((s) => s.id === id));
        const first = lead ?? list[list.length - 1]?.id ?? '';
        setSelected(first);
      } catch {
        setError('Upload an org structure CSV first.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (selected) scenariosApi.implementation(selected).then(setPlan).catch(() => setPlan(null));
  }, [selected]);

  if (loading) return <Loading label="Working out the implications" />;
  if (error) {
    return (
      <>
        <PageHeader eyebrow="03 · Implement" title="Implementation implications" />
        <EmptyState title="Nothing to implement yet" body={error} action={<Link to="/upload" className="btn btn-primary">Upload org data →</Link>} />
      </>
    );
  }
  if (!scenarios.length) {
    return (
      <>
        <PageHeader eyebrow="03 · Implement" title="Implementation implications" />
        <EmptyState
          title="Build an option first"
          body="Implementation implications are worked out for a scenario. Create one in the Scenario Studio."
          action={<Link to="/scenarios" className="btn btn-primary">Open the Scenario Studio →</Link>}
        />
      </>
    );
  }

  const high = plan?.risks.filter((r) => r.severity === 'High').length ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="03 · Implement"
        title={plan ? `${plan.name}: ${plan.summary.people_affected} people affected, ${high} high risk${high === 1 ? '' : 's'}` : 'Implementation implications'}
        lede="Cost, change load, risks and a transition sequence, worked out from the scenario's design moves. Appoint before you remove: new roles are filled first, people move next, roles are removed once their reports have a new home."
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-secondary">
              <input type="checkbox" checked={includeNames} onChange={(e) => setIncludeNames(e.target.checked)} className="accent-[#C41E3A]" />
              Include names in the pack
            </label>
            <a className="btn btn-primary" href={packUrl(selected || undefined, includeNames)} target="_blank" rel="noreferrer">
              Open board pack ↗
            </a>
          </>
        }
      />

      <div className="mb-10 flex flex-wrap items-center gap-3">
        <label className="label mb-0" htmlFor="scenario">Option</label>
        <select id="scenario" className="input w-auto" value={selected} onChange={(e) => setSelected(e.target.value)}>
          {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <span className="text-xs text-faint">The pack opens in a new tab — use the browser's Print → Save as PDF for a document. Names are replaced by job titles unless you tick the box.</span>
      </div>

      {plan && (
        <>
          <Section eyebrow="01 · At a glance">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile label="People affected" value={plan.summary.people_affected} sub={`${plan.summary.people_affected_pct}% of the organization`} />
              <StatTile label="New manager" value={plan.summary.new_manager} sub={`${plan.summary.managers_gaining} manager${plan.summary.managers_gaining === 1 ? '' : 's'} gain people · ${plan.summary.managers_losing} lose people`} />
              <StatTile label="Roles" value={`−${plan.summary.roles_removed} / +${plan.summary.roles_added}`} sub="removed / added" />
              <StatTile label="Annual cost change" value={signedMoney(plan.cost.net_change)} sub={`${formatMoney(plan.cost.removed_roles)} removed · ${formatMoney(plan.cost.added_roles)} added`} />
            </div>
            <p className="mt-2 text-xs text-faint">{plan.cost.note}</p>
          </Section>

          <Section eyebrow="02 · Risks" title={plan.risks.length ? 'What could go wrong, and what to do about it' : 'No rule-based risks flagged'}>
            {plan.risks.length > 0 && (
              <ul className="card divide-y divide-hairline p-0">
                {plan.risks.map((r, i) => (
                  <li key={i} className="grid gap-3 px-6 py-4 md:grid-cols-[140px_1fr_1fr]">
                    <div>
                      <StatusPill status={severityStatus(r.severity)} label={r.severity} />
                      <p className="mt-1 text-xs text-faint">{r.area}</p>
                    </div>
                    <p className="text-sm text-ink">{r.risk}</p>
                    <p className="text-sm text-secondary"><span className="font-semibold text-primary-600">Mitigate:</span> {r.mitigation}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow="03 · Transition sequence" title="In what order">
            <ol className="space-y-4">
              {plan.waves.map((w, i) => (
                <li key={w.key} className="card grid grid-cols-[56px_1fr] gap-4">
                  <span className="display-number text-[34px] text-placeholder">{String(i + 1).padStart(2, '0')}</span>
                  <div>
                    <h3 className="text-[20px]">{w.title}</h3>
                    <p className="mt-1 text-sm text-secondary">{w.guidance}</p>
                    {w.moves.length > 0 && (
                      <ul className="mt-3 space-y-1.5 text-sm">
                        {w.moves.map((m) => (
                          <li key={m.index}>
                            <span className="mr-2 text-primary-600">·</span>{m.message}
                            {m.note && <span className="text-faint"> — {m.note}</span>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </Section>

          <Section eyebrow="04 · Change load" title="Who needs a conversation">
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="card">
                <p className="label">Managers whose team changes</p>
                <ul className="divide-y divide-hairline text-sm">
                  {[...plan.change_load.managers_gaining, ...plan.change_load.managers_losing].map((m) => (
                    <li key={m.employee_id} className="flex justify-between gap-4 py-2">
                      <span className="text-ink">{m.name}</span>
                      <span className="tabular text-secondary">{m.span_before} → <span className="font-semibold text-ink">{m.span_after}</span> reports</span>
                    </li>
                  ))}
                  {!plan.change_load.managers_gaining.length && !plan.change_load.managers_losing.length && <li className="py-2 text-faint">None</li>}
                </ul>
              </div>
              <div className="card">
                <p className="label">People with a new manager</p>
                <ul className="max-h-80 divide-y divide-hairline overflow-auto text-sm">
                  {plan.change_load.new_manager.map((p) => (
                    <li key={p.employee_id} className="py-2">
                      <span className="text-ink">{p.name}</span> <span className="text-faint">· {p.job_title}</span>
                      <span className="block text-xs text-secondary">{p.from} → {p.to}</span>
                    </li>
                  ))}
                  {!plan.change_load.new_manager.length && <li className="py-2 text-faint">None</li>}
                </ul>
              </div>
              {plan.change_load.roles_removed.length > 0 && (
                <div className="card">
                  <p className="label">Roles removed</p>
                  <ul className="divide-y divide-hairline text-sm">
                    {plan.change_load.roles_removed.map((r) => (
                      <li key={r.employee_id} className="flex justify-between gap-4 py-2">
                        <span><span className="text-ink">{r.name}</span> <span className="text-faint">· {r.job_title}</span></span>
                        <span className="tabular text-secondary">{formatMoney(r.salary)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {plan.change_load.new_department.length > 0 && (
                <div className="card">
                  <p className="label">People changing department</p>
                  <ul className="divide-y divide-hairline text-sm">
                    {plan.change_load.new_department.map((p) => (
                      <li key={p.employee_id} className="py-2"><span className="text-ink">{p.name}</span> <span className="text-secondary">· {p.from} → {p.to}</span></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Section>

          <Callout label="Before you announce anything" tone="developing">
            These implications are worked out by rule from the design moves. Check them with the affected leaders, HR and employee-relations
            colleagues, and follow local consultation requirements.
          </Callout>
        </>
      )}
    </>
  );
}
