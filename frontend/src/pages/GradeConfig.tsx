import { useState, useEffect } from 'react';
import { Plus, Trash2, Loader2, CheckCircle, Wand2, Edit3 } from 'lucide-react';
import { gradesApi, metricsApi } from '../services/api';
import type { GradeSalary } from '../types';

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
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [gradesData, hierarchyData] = await Promise.all([
        gradesApi.list(),
        gradesApi.getStandardHierarchy()
      ]);
      setGrades(gradesData);
      setStandardHierarchy(hierarchyData);

      // Determine current mode based on existing grades
      if (gradesData.length === 0) {
        setMode(null); // No selection yet
      } else {
        // Check if it matches standard hierarchy
        const standardGrades = hierarchyData.hierarchy.map(h => h.grade);
        const currentGrades = gradesData.map(g => g.grade);
        const isStandard = standardGrades.every(g => currentGrades.includes(g)) &&
                          currentGrades.every(g => standardGrades.includes(g));
        setMode(isStandard ? 'auto' : 'manual');
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleImportStandard = async () => {
    setSaving(true);
    setSuccessMessage(null);
    try {
      await gradesApi.importStandard();
      await metricsApi.recalculate();
      await fetchData();
      setMode('auto');
      setSuccessMessage('Standard grade hierarchy imported successfully! Metrics recalculated.');
    } catch (error) {
      console.error('Failed to import standard grades:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleSwitchToManual = () => {
    setMode('manual');
  };

  const handleAddGrade = async () => {
    if (!newGrade.grade.trim() || !newGrade.median_salary) return;

    setSaving(true);
    try {
      const created = await gradesApi.create({
        grade: newGrade.grade,
        median_salary: parseFloat(newGrade.median_salary),
        currency: 'SGD',
        display_order: grades.length + 1,
      });
      setGrades([...grades, created]);
      setNewGrade({ grade: '', median_salary: '' });
      await metricsApi.recalculate();
    } catch (error) {
      console.error('Failed to add grade:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGrade = async (id: string) => {
    try {
      await gradesApi.delete(id);
      setGrades(grades.filter(g => g.id !== id));
      await metricsApi.recalculate();
    } catch (error) {
      console.error('Failed to delete grade:', error);
    }
  };

  const handleUpdateSalary = async (id: string, salary: number) => {
    try {
      const grade = grades.find(g => g.id === id);
      if (!grade) return;

      await gradesApi.update(id, { ...grade, median_salary: salary });
      setGrades(grades.map(g =>
        g.id === id ? { ...g, median_salary: salary } : g
      ));
    } catch (error) {
      console.error('Failed to update grade:', error);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Are you sure you want to clear all grades?')) return;

    setSaving(true);
    try {
      await gradesApi.clearAll();
      setGrades([]);
      setMode(null);
    } catch (error) {
      console.error('Failed to clear grades:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Grade & Salary Configuration</h1>
        <div className="flex gap-3">
          {grades.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={saving}
              className="btn btn-danger text-sm"
            >
              Clear All Grades
            </button>
          )}
        </div>
      </div>

      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
          <CheckCircle className="w-5 h-5" />
          {successMessage}
        </div>
      )}

      {/* Mode Selection - Always show to allow switching */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Auto-Populate Option */}
        <div
          onClick={handleImportStandard}
          className={`card cursor-pointer border-2 transition-all hover:border-primary-500 hover:shadow-lg ${
            mode === 'auto' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
          } ${saving ? 'opacity-50 pointer-events-none' : ''}`}
        >
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-2 rounded-lg ${mode === 'auto' ? 'bg-primary-200' : 'bg-primary-100'}`}>
              <Wand2 className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Auto-Populate Standard Hierarchy</h2>
              <p className="text-sm text-gray-500">Use pre-defined grade structure with salaries</p>
            </div>
            {mode === 'auto' && (
              <CheckCircle className="w-5 h-5 text-primary-600 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Automatically populate with the standard corporate grade hierarchy including SVP ($698k), VP ($432k), AVP ($296k), Senior Manager ($213k), Manager ($173k), and AO ($107k) levels.
          </p>
          {saving && <Loader2 className="w-5 h-5 animate-spin text-primary-600" />}
        </div>

        {/* Manual Option */}
        <div
          onClick={handleSwitchToManual}
          className={`card cursor-pointer border-2 transition-all hover:border-primary-500 hover:shadow-lg ${
            mode === 'manual' ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
          }`}
        >
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-2 rounded-lg ${mode === 'manual' ? 'bg-primary-200' : 'bg-gray-100'}`}>
              <Edit3 className="w-6 h-6 text-gray-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Manual Configuration</h2>
              <p className="text-sm text-gray-500">Define your own grade structure</p>
            </div>
            {mode === 'manual' && (
              <CheckCircle className="w-5 h-5 text-primary-600 ml-auto" />
            )}
          </div>
          <p className="text-sm text-gray-600">
            Manually add and configure grades with custom names and salaries. Useful for organizations with non-standard grade structures.
          </p>
        </div>
      </div>

      {/* Standard Hierarchy Preview - Show when no mode selected yet */}
      {mode === null && standardHierarchy && (
        <div className="card mb-8">
          <h3 className="font-semibold mb-4">Standard Grade Hierarchy Preview</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left py-2 px-4">Seniority</th>
                  <th className="text-left py-2 px-4">Available Job Grades</th>
                  <th className="text-right py-2 px-4">Salary ($)</th>
                </tr>
              </thead>
              <tbody>
                {standardHierarchy.seniority_levels.map((level) => (
                  <tr key={level.name} className="border-b">
                    <td className="py-2 px-4 font-medium">{level.name}</td>
                    <td className="py-2 px-4">
                      <div className="flex gap-2 flex-wrap">
                        {level.grades.map(g => (
                          <span key={g} className="px-2 py-0.5 bg-primary-100 text-primary-700 rounded text-xs">
                            {g}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2 px-4 text-right font-mono">
                      ${level.salary.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Current Grades Display */}
      {grades.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">
              {mode === 'auto' ? 'Standard Grade Hierarchy' : 'Custom Grade Configuration'}
            </h3>
            {mode === 'auto' && (
              <button
                onClick={handleSwitchToManual}
                className="text-sm text-primary-600 hover:underline"
              >
                Switch to Manual Mode
              </button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-4">Order</th>
                  <th className="text-left py-2 px-4">Grade</th>
                  <th className="text-left py-2 px-4">Median Salary</th>
                  <th className="text-left py-2 px-4">Currency</th>
                  {mode === 'manual' && <th className="text-right py-2 px-4">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {grades.map((grade) => (
                  <tr key={grade.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 px-4 text-gray-500">{grade.display_order}</td>
                    <td className="py-2 px-4 font-medium">{grade.grade}</td>
                    <td className="py-2 px-4">
                      {mode === 'manual' ? (
                        <input
                          type="number"
                          value={grade.median_salary}
                          onChange={(e) => handleUpdateSalary(grade.id, parseFloat(e.target.value))}
                          className="w-32 px-2 py-1 border rounded"
                        />
                      ) : (
                        <span className="font-mono">${grade.median_salary.toLocaleString()}</span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-gray-500">{grade.currency}</td>
                    {mode === 'manual' && (
                      <td className="py-2 px-4 text-right">
                        <button
                          onClick={() => handleDeleteGrade(grade.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}

                {/* Add new grade row - only in manual mode */}
                {mode === 'manual' && (
                  <tr className="bg-gray-50">
                    <td className="py-2 px-4 text-gray-400">{grades.length + 1}</td>
                    <td className="py-2 px-4">
                      <input
                        type="text"
                        value={newGrade.grade}
                        onChange={(e) => setNewGrade({ ...newGrade, grade: e.target.value })}
                        placeholder="Grade name"
                        className="w-full px-2 py-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-4">
                      <input
                        type="number"
                        value={newGrade.median_salary}
                        onChange={(e) => setNewGrade({ ...newGrade, median_salary: e.target.value })}
                        placeholder="Salary"
                        className="w-32 px-2 py-1 border rounded"
                      />
                    </td>
                    <td className="py-2 px-4 text-gray-500">SGD</td>
                    <td className="py-2 px-4 text-right">
                      <button
                        onClick={handleAddGrade}
                        disabled={!newGrade.grade.trim() || !newGrade.median_salary || saving}
                        className="btn btn-primary text-sm flex items-center gap-1 disabled:opacity-50"
                      >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        Add
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {mode === 'auto' && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              Using standard grade hierarchy. Grade gap calculations will be based on this order.
              To customize salaries or add custom grades, switch to Manual Mode.
            </div>
          )}
        </div>
      )}

      {/* Manual mode with no grades */}
      {mode === 'manual' && grades.length === 0 && (
        <div className="card">
          <h3 className="font-semibold mb-4">Manual Grade Configuration</h3>
          <p className="text-sm text-gray-500 mb-4">
            Add grades in order from highest (e.g., SVP) to lowest (e.g., AO).
            The order determines the grade gap calculations.
          </p>

          <div className="flex gap-4 items-end">
            <div>
              <label className="label">Grade Name</label>
              <input
                type="text"
                value={newGrade.grade}
                onChange={(e) => setNewGrade({ ...newGrade, grade: e.target.value })}
                placeholder="e.g., SVP, H8, TL"
                className="input"
              />
            </div>
            <div>
              <label className="label">Median Salary</label>
              <input
                type="number"
                value={newGrade.median_salary}
                onChange={(e) => setNewGrade({ ...newGrade, median_salary: e.target.value })}
                placeholder="e.g., 350000"
                className="input"
              />
            </div>
            <button
              onClick={handleAddGrade}
              disabled={!newGrade.grade.trim() || !newGrade.median_salary || saving}
              className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Add Grade
            </button>
          </div>

          <div className="mt-4">
            <button
              onClick={() => setMode(null)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              ← Back to selection
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
