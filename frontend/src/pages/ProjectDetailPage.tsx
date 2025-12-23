import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import {
  getProject,
  getScenarios,
  uploadDataset,
  getDatasetPreview,
  publishDataset,
} from '../api/client'
import type { Project, Scenario, DatasetPreview } from '../api/types'
import {
  ArrowLeft,
  Upload,
  FileSpreadsheet,
  GitBranch,
  Play,
  CheckCircle,
  AlertCircle,
  Clock,
  X,
} from 'lucide-react'

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { setCurrentProject, setScenarios, scenarios, setLoading, setError } = useAppStore()

  const [project, setProject] = useState<Project | null>(null)
  const [uploadedDataset, setUploadedDataset] = useState<DatasetPreview | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [scenarioName, setScenarioName] = useState('')
  const [isBaseline, setIsBaseline] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadProject()
      loadScenarios()
    }
  }, [projectId])

  const loadProject = async () => {
    if (!projectId) return
    try {
      const data = await getProject(projectId)
      setProject(data)
      setCurrentProject(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load project')
    }
  }

  const loadScenarios = async () => {
    if (!projectId) return
    try {
      const data = await getScenarios(projectId)
      setScenarios(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load scenarios')
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      await handleFileUpload(file)
    }
  }, [projectId])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await handleFileUpload(file)
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!projectId) return

    const validTypes = ['.pptx', '.csv', '.xlsx', '.xls']
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!validTypes.includes(ext)) {
      setError(`Invalid file type. Supported: ${validTypes.join(', ')}`)
      return
    }

    setLoading(true)
    try {
      const dataset = await uploadDataset(projectId, file)
      const preview = await getDatasetPreview(dataset.id)
      setUploadedDataset(preview)
    } catch (err: any) {
      setError(err.message || 'Failed to upload file')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!uploadedDataset || !scenarioName.trim()) return

    setLoading(true)
    try {
      const scenario = await publishDataset(
        uploadedDataset.id,
        scenarioName,
        undefined,
        isBaseline
      )
      setShowPublishModal(false)
      setUploadedDataset(null)
      setScenarioName('')
      await loadScenarios()
      navigate(`/scenarios/${scenario.id}`)
    } catch (err: any) {
      setError(err.message || 'Failed to publish dataset')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'validated':
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'pending':
      case 'draft':
        return <Clock className="h-5 w-5 text-yellow-500" />
      case 'rejected':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading project...</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/projects"
          className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Projects
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{project.name}</h1>
            <p className="text-slate-500">{project.client_name}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Section */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h2 className="text-lg font-semibold mb-4">Upload Org Chart</h2>

            {!uploadedDataset ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-slate-300 hover:border-slate-400'
                }`}
              >
                <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-600 mb-2">
                  Drag and drop your file here, or
                </p>
                <label className="cursor-pointer">
                  <span className="text-blue-600 hover:text-blue-700">browse files</span>
                  <input
                    type="file"
                    accept=".pptx,.csv,.xlsx,.xls"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
                <p className="text-sm text-slate-400 mt-2">
                  Supports: PowerPoint (.pptx), CSV, Excel (.xlsx)
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Preview */}
                <div className="flex items-start justify-between p-4 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="h-8 w-8 text-blue-500" />
                    <div>
                      <p className="font-medium">{uploadedDataset.source_filename}</p>
                      <p className="text-sm text-slate-500">
                        {uploadedDataset.total_employees} employees, {uploadedDataset.levels_detected} levels
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setUploadedDataset(null)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                {/* Validation Errors */}
                {uploadedDataset.validation_errors.length > 0 && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="font-medium text-yellow-800 mb-2">
                      Validation Issues ({uploadedDataset.validation_errors.length})
                    </h4>
                    <ul className="space-y-1 text-sm text-yellow-700">
                      {uploadedDataset.validation_errors.slice(0, 5).map((err, i) => (
                        <li key={i}>• {err.message}</li>
                      ))}
                      {uploadedDataset.validation_errors.length > 5 && (
                        <li>...and {uploadedDataset.validation_errors.length - 5} more</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">
                      {uploadedDataset.total_employees}
                    </p>
                    <p className="text-sm text-slate-500">Employees</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">
                      {uploadedDataset.total_relationships}
                    </p>
                    <p className="text-sm text-slate-500">Relationships</p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">
                      {uploadedDataset.levels_detected}
                    </p>
                    <p className="text-sm text-slate-500">Levels</p>
                  </div>
                </div>

                {uploadedDataset.outside_canvas_count > 0 && (
                  <p className="text-sm text-blue-600">
                    Note: {uploadedDataset.outside_canvas_count} shapes were detected outside the visible canvas and included
                  </p>
                )}

                {/* Publish Button */}
                <button
                  onClick={() => setShowPublishModal(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Play className="h-5 w-5" />
                  Publish as Scenario
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Scenarios List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h2 className="text-lg font-semibold mb-4">Scenarios</h2>

            {scenarios.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <GitBranch className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p>No scenarios yet</p>
                <p className="text-sm">Upload and publish an org chart</p>
              </div>
            ) : (
              <div className="space-y-3">
                {scenarios.map((scenario) => (
                  <Link
                    key={scenario.id}
                    to={`/scenarios/${scenario.id}`}
                    className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 hover:border-blue-500 transition-colors"
                  >
                    {getStatusIcon(scenario.status)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">
                        {scenario.name}
                      </p>
                      <p className="text-sm text-slate-500">
                        {scenario.employee_count || 0} employees
                        {scenario.is_baseline && (
                          <span className="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                            Baseline
                          </span>
                        )}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Publish as Scenario</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Scenario Name
                </label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., As-Is FY24"
                />
              </div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isBaseline}
                  onChange={(e) => setIsBaseline(e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span className="text-sm text-slate-600">Mark as baseline (current state)</span>
              </label>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowPublishModal(false)}
                className="px-4 py-2 text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                disabled={!scenarioName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Publish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
