import { useState, useEffect } from 'react';
import { Plus, Trash2, Save, Loader2 } from 'lucide-react';
import { gradesApi } from '../services/api';
import type { GradeSalary } from '../types';

export default function GradeConfig() {
  const [grades, setGrades] = useState<GradeSalary[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newGrade, setNewGrade] = useState({ grade: '', median_salary: '' });

  useEffect(() => {
    fetchGrades();
  }, []);

  const fetchGrades = async () => {
    try {
      const data = await gradesApi.list();
      setGrades(data);
    } catch (error) {
      console.error('Failed to fetch grades:', error);
    } finally {
      setLoading(false);
    }
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

  const handleQuickImport = async () => {
    const defaultGrades = {
      'SVP': 350000,
      'H8': 250000,
      'H7': 200000,
      'H6': 180000,
      'H5': 130000,
      'TL': 90000,
      'AO': 60000,
    };

    setSaving(true);
    try {
      await gradesApi.bulkImport(defaultGrades);
      await fetchGrades();
    } catch (error) {
      console.error('Failed to import grades:', error);
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
        <button
          onClick={handleQuickImport}
          disabled={saving}
          className="btn btn-secondary text-sm"
        >
          Import Default Grades
        </button>
      </div>

      <div className="card">
        <p className="text-sm text-gray-500 mb-4">
          Configure grade levels and their median salaries. This is used for grade gap analysis.
        </p>

        {/* Grade Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4">Order</th>
                <th className="text-left py-2 px-4">Grade</th>
                <th className="text-left py-2 px-4">Median Salary</th>
                <th className="text-left py-2 px-4">Currency</th>
                <th className="text-right py-2 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {grades.map((grade) => (
                <tr key={grade.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-4 text-gray-500">{grade.display_order}</td>
                  <td className="py-2 px-4 font-medium">{grade.grade}</td>
                  <td className="py-2 px-4">
                    <input
                      type="number"
                      value={grade.median_salary}
                      onChange={(e) => handleUpdateSalary(grade.id, parseFloat(e.target.value))}
                      className="w-32 px-2 py-1 border rounded"
                    />
                  </td>
                  <td className="py-2 px-4 text-gray-500">{grade.currency}</td>
                  <td className="py-2 px-4 text-right">
                    <button
                      onClick={() => handleDeleteGrade(grade.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}

              {/* Add new grade row */}
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
                    className="btn btn-primary btn-sm flex items-center gap-1 disabled:opacity-50"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Add
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {grades.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No grades configured. Add grades above or import defaults.
          </div>
        )}
      </div>
    </div>
  );
}
