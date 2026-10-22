import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { gradesApi, metricsApi } from '../services/api';
import type { GradeSalary } from '../types';
import { PageHeader, Section, Callout, Chip, Loading, formatMoney } from '../components/ui';

interface StandardHierarchy {
  hierarchy: Array<{ seniority: string; grade: string; salary: number; order: number }>;
  seniority_levels: Array<{ name: string; grades: string[]; salary: number }>;
}

export default function GradeConfig() {
  const [grades, setGrades] = useState<GradeSalary[]>([]);
  const [standardHierarchy, setStandardHierarchy] = useState<StandardHierarchy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState<'auto' | 'manual' | null>(null);
  const [newGrade, setNewGrade] = useState({ grade: '', median_salary: '' });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [gradesData, hierarchyData] = await Promise.all([gradesApi.list(), gradesApi.getStandardHierarchy()]);
      setGrades(gradesData);
      setStandardHierarchy(hierarchyData);
      if (gradesData.length === 0) {
        setMode(null);
      } else {
        const standard = hierarchyData.hierarchy.map((h) => h.grade);
        const current = gradesData.map((g) => g.grade);
        setMode(standard.every((g) => current.includes(g)) && current.every((g) => standard.includes(g)) ? 'auto' : 'manual');
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImportStandard = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await gradesApi.importStandard();
      await metricsApi.recalculate().catch(() => undefined);
      await fetchData();
      setMode('auto');
      setMessage('Standard grade hierarchy loaded; costs recalculated.');
    } finally {
      setSaving(false);
    }
  };

  const handleAddGrade = async () => {
    if (!newGrade.grade.trim() || !newGrade.median_salary) return;
    setSaving(true);
    try {
      const created = await gradesApi.create({
        grade: newGrade.grade.trim(),
        median_salary: parseFloat(newGrade.median_salary),
        currency: 'SGD',
        display_order: grades.length + 1,
      });
      setGrades([...grades, created]);
      setNewGrade({ grade: '', median_salary: '' });
      await metricsApi.recalculate().catch(() => undefined);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGrade = async (id: string) => {
    await gradesApi.delete(id);
    setGrades(grades.filter((g) => g.id !== id));
    await metricsApi.recalculate().catch(() => undefined);
  };

  // Saved when the field is left, not on every keystroke
  const handleUpdateSalary = async (id: string, value: string) => {
    const salary = parseFloat(value);
    const grade = grades.find((g) => g.id === id);
    if (!grade || Number.isNaN(salary) || salary === grade.median_salary) return;
    await gradesApi.update(id, { ...grade, median_salary: salary });
    setGrades(grades.map((g) => (g.id === id ? { ...g, median_salary: salary } : g)));
    await metricsApi.recalculate().catch(() => undefined);
    setMessage(`${grade.grade} salary saved; costs recalculated.`);
  };

  const handleClearAll = async () => {
    if (!confirm('Clear every grade? Costs will fall back to the salaries in the CSV.')) return;
    setSaving(true);
    try {
      await gradesApi.clearAll();
      setGrades([]);
      setMode(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Loading label="Loading grades" />;

  return (
    <>
      <PageHeader
        eyebrow="Setup — grades and salaries"
        title="Grades and median salaries"
        lede="Grade order drives the grade-gap check between managers and their reports; median salaries fill in costs for anyone without a salary in the CSV. Grades in your upload are added automatically."
        actions={grades.length > 0 ? <button onClick={handleClearAll} disabled={saving} className="btn btn-quiet">Clear all grades</button> : undefined}
      />
      {message && <div className="mb-8"><Callout label="Saved" tone="healthy">{message}</Callout></div>}

      <Section eyebrow="01 · Choose a starting point">
        <div className="grid gap-px overflow-hidden border border-hairline bg-hairline md:grid-cols-2">
          {[
            {
              key: 'auto' as const,
              title: 'Standard hierarchy',
              body: 'Load the standard corporate grade structure with its median salaries (SVP to AO).',
              onClick: handleImportStandard,
            },
            {
              key: 'manual' as const,
              title: 'Your own grades',
              body: 'Add and edit grades and salaries yourself — for non-standard structures.',
              onClick: () => setMode('manual'),
            },
          ].map((opt) => (
            <button
              key={opt.key}
              onClick={opt.onClick}
              disabled={saving}
              className={clsx('bg-white p-6 text-left transition-colors hover:bg-wash', mode === opt.key && 'bg-primary-50 hover:bg-primary-50')}
            >
              <p className={clsx('eyebrow mb-2', mode !== opt.key && 'eyebrow-faint')}>{mode === opt.key ? 'In use' : 'Option'}</p>
              <h3 className="text-[20px]">{opt.title}</h3>
              <p className="mt-1 text-sm text-secondary">{opt.body}</p>
            </button>
          ))}
        </div>
      </Section>

      {mode === null && standardHierarchy && (
        <Section eyebrow="Preview" title="The standard hierarchy">
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                  <th className="px-5 py-3">Seniority</th>
                  <th className="px-4 py-3">Grades</th>
                  <th className="px-5 py-3 text-right">Median salary</th>
                </tr>
              </thead>
              <tbody>
                {standardHierarchy.seniority_levels.map((level) => (
                  <tr key={level.name} className="hairline-b last:border-0">
                    <td className="px-5 py-2.5 font-medium text-ink">{level.name}</td>
                    <td className="px-4 py-2.5"><div className="flex flex-wrap gap-1.5">{level.grades.map((g) => <Chip key={g}>{g}</Chip>)}</div></td>
                    <td className="tabular px-5 py-2.5 text-right text-ink">{formatMoney(level.salary)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {(grades.length > 0 || mode === 'manual') && (
        <Section eyebrow="02 · Grades in use" title={mode === 'auto' ? 'Standard hierarchy' : 'Your grade structure'} lede="Highest grade first; the order sets the grade-gap check.">
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="hairline-b text-left text-[11px] font-semibold uppercase tracking-[.14em] text-secondary">
                  <th className="px-5 py-3">Order</th>
                  <th className="px-4 py-3">Grade</th>
                  <th className="px-4 py-3">Median salary</th>
                  <th className="px-4 py-3">Currency</th>
                  {mode === 'manual' && <th className="px-5 py-3" />}
                </tr>
              </thead>
              <tbody>
                {grades.map((g) => (
                  <tr key={g.id} className="hairline-b">
                    <td className="tabular px-5 py-2.5 text-faint">{g.display_order}</td>
                    <td className="px-4 py-2.5 font-medium text-ink">{g.grade}</td>
                    <td className="px-4 py-2.5">
                      {mode === 'manual' ? (
                        <input type="number" defaultValue={g.median_salary} onBlur={(e) => handleUpdateSalary(g.id, e.target.value)} className="input w-36 py-1.5" aria-label={`Median salary for ${g.grade}`} />
                      ) : (
                        <span className="tabular text-ink">{g.median_salary.toLocaleString()}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-faint">{g.currency}</td>
                    {mode === 'manual' && (
                      <td className="px-5 py-2.5 text-right">
                        <button onClick={() => handleDeleteGrade(g.id)} className="text-xs font-semibold text-primary-600 hover:text-primary-700">Remove</button>
                      </td>
                    )}
                  </tr>
                ))}
                {mode === 'manual' && (
                  <tr className="bg-wash">
                    <td className="tabular px-5 py-2.5 text-faint">{grades.length + 1}</td>
                    <td className="px-4 py-2.5">
                      <input value={newGrade.grade} onChange={(e) => setNewGrade({ ...newGrade, grade: e.target.value })} placeholder="e.g. H8" className="input py-1.5" aria-label="New grade name" />
                    </td>
                    <td className="px-4 py-2.5">
                      <input type="number" value={newGrade.median_salary} onChange={(e) => setNewGrade({ ...newGrade, median_salary: e.target.value })} placeholder="e.g. 250000" className="input w-36 py-1.5" aria-label="New grade median salary" />
                    </td>
                    <td className="px-4 py-2.5 text-faint">SGD</td>
                    <td className="px-5 py-2.5 text-right">
                      <button onClick={handleAddGrade} disabled={!newGrade.grade.trim() || !newGrade.median_salary || saving} className="btn btn-primary py-1.5">Add</button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {mode === 'auto' && (
            <p className="mt-3 text-sm text-secondary">
              To change salaries or add grades, <button onClick={() => setMode('manual')} className="font-semibold text-primary-600">switch to your own grades</button>.
            </p>
          )}
        </Section>
      )}
    </>
  );
}
