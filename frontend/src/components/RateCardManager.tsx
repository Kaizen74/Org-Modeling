import { useState, useEffect } from 'react'
import {
  DollarSign,
  Plus,
  Trash2,
  Save,
  Upload,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import { getRateCards, bulkCreateRateCards, deleteRateCard } from '../api/client'

interface RateCard {
  id?: string
  grade: string
  location: string
  base_salary_min?: number
  base_salary_mid: number
  base_salary_max?: number
  variable_comp_target: number
  benefits_value: number
  overhead_multiplier: number
  currency: string
  source?: string
}

interface RateCardManagerProps {
  projectId: string
  onUpdate?: () => void
}

const DEFAULT_LOCATION = 'Global'
const DEFAULT_CURRENCY = 'USD'

export default function RateCardManager({ projectId, onUpdate }: RateCardManagerProps) {
  const [rateCards, setRateCards] = useState<RateCard[]>([])
  const [_isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // New rate card form state
  const [newCards, setNewCards] = useState<RateCard[]>([
    {
      grade: '',
      location: DEFAULT_LOCATION,
      base_salary_mid: 0,
      variable_comp_target: 0,
      benefits_value: 0,
      overhead_multiplier: 1.4,
      currency: DEFAULT_CURRENCY,
    },
  ])

  useEffect(() => {
    loadRateCards()
  }, [projectId])

  const loadRateCards = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getRateCards(projectId)
      setRateCards(data)
    } catch (err: any) {
      setError('Failed to load rate cards')
    } finally {
      setIsLoading(false)
    }
  }

  const addNewRow = () => {
    setNewCards([
      ...newCards,
      {
        grade: '',
        location: DEFAULT_LOCATION,
        base_salary_mid: 0,
        variable_comp_target: 0,
        benefits_value: 0,
        overhead_multiplier: 1.4,
        currency: DEFAULT_CURRENCY,
      },
    ])
    setHasUnsavedChanges(true)
  }

  const updateNewCard = (index: number, field: keyof RateCard, value: string | number) => {
    const updated = [...newCards]
    updated[index] = { ...updated[index], [field]: value }
    setNewCards(updated)
    setHasUnsavedChanges(true)
  }

  const removeNewCard = (index: number) => {
    setNewCards(newCards.filter((_, i) => i !== index))
    setHasUnsavedChanges(true)
  }

  const handleSave = async () => {
    // Validate - filter out empty rows
    const validCards = newCards.filter(
      (card) => card.grade.trim() && card.base_salary_mid > 0
    )

    if (validCards.length === 0) {
      setError('Please enter at least one grade with a median salary')
      return
    }

    setIsSaving(true)
    setError(null)
    setSuccess(null)

    try {
      await bulkCreateRateCards(projectId, validCards)
      setSuccess(`Successfully saved ${validCards.length} rate card(s)`)
      setHasUnsavedChanges(false)

      // Reset new cards form
      setNewCards([
        {
          grade: '',
          location: DEFAULT_LOCATION,
          base_salary_mid: 0,
          variable_comp_target: 0,
          benefits_value: 0,
          overhead_multiplier: 1.4,
          currency: DEFAULT_CURRENCY,
        },
      ])

      // Reload
      await loadRateCards()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save rate cards')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this rate card?')) return

    try {
      await deleteRateCard(id)
      await loadRateCards()
      onUpdate?.()
    } catch (err: any) {
      setError('Failed to delete rate card')
    }
  }

  const handleImportCSV = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.csv'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (event) => {
        const text = event.target?.result as string
        const lines = text.split('\n').filter((line) => line.trim())

        if (lines.length < 2) {
          setError('CSV must have a header row and at least one data row')
          return
        }

        // Parse header
        const header = lines[0].toLowerCase().split(',').map((h) => h.trim())
        const gradeIdx = header.findIndex((h) => h.includes('grade'))
        const salaryIdx = header.findIndex(
          (h) => h.includes('salary') || h.includes('mid') || h.includes('median')
        )
        const locationIdx = header.findIndex((h) => h.includes('location'))

        if (gradeIdx === -1 || salaryIdx === -1) {
          setError('CSV must have "grade" and "salary" columns')
          return
        }

        // Parse data rows
        const imported: RateCard[] = []
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',').map((v) => v.trim())
          const grade = values[gradeIdx]
          const salary = parseFloat(values[salaryIdx]?.replace(/[$,]/g, '') || '0')
          const location = locationIdx >= 0 ? values[locationIdx] : DEFAULT_LOCATION

          if (grade && salary > 0) {
            imported.push({
              grade,
              location: location || DEFAULT_LOCATION,
              base_salary_mid: salary,
              variable_comp_target: 0,
              benefits_value: 0,
              overhead_multiplier: 1.4,
              currency: DEFAULT_CURRENCY,
            })
          }
        }

        if (imported.length > 0) {
          setNewCards(imported)
          setHasUnsavedChanges(true)
          setSuccess(`Imported ${imported.length} rows. Click Save to confirm.`)
        } else {
          setError('No valid data found in CSV')
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }

  const handleExportCSV = () => {
    const headers = ['Grade', 'Location', 'Median Salary', 'Variable Comp %', 'Benefits', 'Currency']
    const rows = rateCards.map((rc) => [
      rc.grade,
      rc.location,
      rc.base_salary_mid,
      rc.variable_comp_target,
      rc.benefits_value,
      rc.currency,
    ])

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rate_cards.csv'
    a.click()
  }

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Job Grades & Salaries
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Define median salaries for each job grade to enable cost analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleImportCSV}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
          >
            <Upload className="h-4 w-4" />
            Import CSV
          </button>
          {rateCards.length > 0 && (
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          )}
        </div>
      </div>

      {/* Status messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
          <CheckCircle className="h-5 w-5" />
          {success}
        </div>
      )}

      {/* Existing rate cards */}
      {rateCards.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-700 mb-3">
            Current Rate Cards ({rateCards.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 font-medium text-slate-600">Grade</th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">Location</th>
                  <th className="text-right py-2 px-3 font-medium text-slate-600">Median Salary</th>
                  <th className="text-right py-2 px-3 font-medium text-slate-600">Variable %</th>
                  <th className="text-right py-2 px-3 font-medium text-slate-600">Benefits</th>
                  <th className="text-right py-2 px-3 font-medium text-slate-600">Total Cost</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {rateCards.map((rc) => {
                  const totalCost =
                    (rc.base_salary_mid +
                      rc.base_salary_mid * rc.variable_comp_target +
                      rc.benefits_value) *
                    rc.overhead_multiplier
                  return (
                    <tr key={rc.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 px-3 font-medium">{rc.grade}</td>
                      <td className="py-2 px-3 text-slate-600">{rc.location}</td>
                      <td className="py-2 px-3 text-right">
                        {formatCurrency(rc.base_salary_mid, rc.currency)}
                      </td>
                      <td className="py-2 px-3 text-right">{(rc.variable_comp_target * 100).toFixed(0)}%</td>
                      <td className="py-2 px-3 text-right">
                        {formatCurrency(rc.benefits_value, rc.currency)}
                      </td>
                      <td className="py-2 px-3 text-right font-medium">
                        {formatCurrency(totalCost, rc.currency)}
                      </td>
                      <td className="py-2 px-3">
                        <button
                          onClick={() => rc.id && handleDelete(rc.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* New rate card input */}
      <div className="border-t border-slate-200 pt-4">
        <h3 className="text-sm font-medium text-slate-700 mb-3">Add New Rate Cards</h3>
        <div className="space-y-3">
          {newCards.map((card, index) => (
            <div
              key={index}
              className="grid grid-cols-12 gap-2 items-center p-3 bg-slate-50 rounded-lg"
            >
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Grade *</label>
                <input
                  type="text"
                  value={card.grade}
                  onChange={(e) => updateNewCard(index, 'grade', e.target.value)}
                  placeholder="E.g., E1, M2, L3"
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Location</label>
                <input
                  type="text"
                  value={card.location}
                  onChange={(e) => updateNewCard(index, 'location', e.target.value)}
                  placeholder="Global"
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Median Salary *</label>
                <input
                  type="number"
                  value={card.base_salary_mid || ''}
                  onChange={(e) => updateNewCard(index, 'base_salary_mid', parseFloat(e.target.value) || 0)}
                  placeholder="100000"
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Variable %</label>
                <input
                  type="number"
                  value={(card.variable_comp_target * 100) || ''}
                  onChange={(e) =>
                    updateNewCard(index, 'variable_comp_target', (parseFloat(e.target.value) || 0) / 100)
                  }
                  placeholder="15"
                  step="1"
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Benefits</label>
                <input
                  type="number"
                  value={card.benefits_value || ''}
                  onChange={(e) => updateNewCard(index, 'benefits_value', parseFloat(e.target.value) || 0)}
                  placeholder="10000"
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="col-span-1">
                <label className="block text-xs text-slate-500 mb-1">Currency</label>
                <select
                  value={card.currency}
                  onChange={(e) => updateNewCard(index, 'currency', e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="SGD">SGD</option>
                  <option value="HKD">HKD</option>
                  <option value="JPY">JPY</option>
                </select>
              </div>
              <div className="col-span-1 flex justify-end">
                {newCards.length > 1 && (
                  <button
                    onClick={() => removeNewCard(index)}
                    className="text-red-500 hover:text-red-700 p-1"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between mt-4">
          <button
            onClick={addNewRow}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700"
          >
            <Plus className="h-4 w-4" />
            Add another grade
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving || !hasUnsavedChanges}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? (
              <RefreshCw className="h-5 w-5 animate-spin" />
            ) : (
              <Save className="h-5 w-5" />
            )}
            Save Rate Cards
          </button>
        </div>
      </div>

      {/* Help text */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h4 className="font-medium text-blue-900 mb-2">Tip: Quick Import</h4>
        <p className="text-sm text-blue-700">
          Import grades from a CSV file with columns: <code className="bg-blue-100 px-1 rounded">Grade</code>,{' '}
          <code className="bg-blue-100 px-1 rounded">Salary</code> (or <code className="bg-blue-100 px-1 rounded">Median</code>),{' '}
          and optionally <code className="bg-blue-100 px-1 rounded">Location</code>.
        </p>
      </div>
    </div>
  )
}
