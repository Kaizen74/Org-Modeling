import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { testApiKey, saveApiKey, getApiKey, checkHealth } from '../api/client'
import type { HealthStatus } from '../api/types'
import {
  Key,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
  Server,
  Database,
  Brain,
} from 'lucide-react'

export default function SettingsPage() {
  const { setApiKey, setApiKeyConfig, apiKeyConfig, setError } = useAppStore()

  const [inputKey, setInputKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [testResult, setTestResult] = useState<{ valid: boolean; message: string } | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)

  useEffect(() => {
    loadApiKeyConfig()
    loadHealth()
  }, [])

  const loadApiKeyConfig = async () => {
    try {
      const config = await getApiKey()
      if (config) {
        setApiKeyConfig(config)
      }
    } catch (err) {
      // API key not configured yet
    }
  }

  const loadHealth = async () => {
    try {
      const data = await checkHealth()
      setHealth(data)
    } catch (err: any) {
      setError('Failed to check system health')
    }
  }

  const handleTest = async () => {
    if (!inputKey) return

    setIsTesting(true)
    setTestResult(null)

    try {
      const result = await testApiKey(inputKey)
      setTestResult({
        valid: result.is_valid,
        message: result.message,
      })
    } catch (err: any) {
      setTestResult({
        valid: false,
        message: err.message || 'Failed to test API key',
      })
    } finally {
      setIsTesting(false)
    }
  }

  const handleSave = async () => {
    if (!inputKey) return

    setIsSaving(true)
    try {
      const config = await saveApiKey(inputKey)
      setApiKey(inputKey)
      setApiKeyConfig(config)
      setInputKey('')
      setTestResult(null)
    } catch (err: any) {
      setError(err.message || 'Failed to save API key')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500">Configure your application settings</p>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="h-5 w-5" />
          System Status
        </h2>

        {health ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Server className="h-5 w-5 text-slate-500" />
              <div>
                <p className="text-sm text-slate-500">API Status</p>
                <div className="flex items-center gap-2">
                  {health.status === 'healthy' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="font-medium">{health.status}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Database className="h-5 w-5 text-slate-500" />
              <div>
                <p className="text-sm text-slate-500">Database</p>
                <div className="flex items-center gap-2">
                  {health.database === 'connected' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="font-medium">{health.database}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <Brain className="h-5 w-5 text-slate-500" />
              <div>
                <p className="text-sm text-slate-500">Claude API</p>
                <div className="flex items-center gap-2">
                  {health.claude_api === 'available' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                  )}
                  <span className="font-medium">{health.claude_api}</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-slate-500">
            <RefreshCw className="h-5 w-5 animate-spin" />
            Checking system status...
          </div>
        )}
      </div>

      {/* API Key Configuration */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Key className="h-5 w-5" />
          Claude API Key
        </h2>

        <p className="text-slate-600 mb-4">
          Enter your Anthropic API key to enable AI-powered organizational analysis.
          Get your API key from{' '}
          <a
            href="https://console.anthropic.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700"
          >
            console.anthropic.com
          </a>
        </p>

        {/* Current Key Status */}
        {apiKeyConfig && (
          <div className="p-4 bg-slate-50 rounded-lg mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {apiKeyConfig.is_valid ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <div>
                  <p className="font-medium">
                    Current Key: ****{apiKeyConfig.api_key_hint}
                  </p>
                  <p className="text-sm text-slate-500">
                    {apiKeyConfig.is_valid ? 'Valid and active' : 'Invalid or expired'}
                  </p>
                </div>
              </div>
              <div className="text-right text-sm text-slate-500">
                <p>{apiKeyConfig.total_requests} requests</p>
                <p>{apiKeyConfig.total_tokens_used.toLocaleString()} tokens used</p>
              </div>
            </div>
          </div>
        )}

        {/* New Key Input */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {apiKeyConfig ? 'Update API Key' : 'Enter API Key'}
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full px-3 py-2 pr-20 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showKey ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={`p-3 rounded-lg ${
                testResult.valid
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.valid ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <XCircle className="h-5 w-5" />
                )}
                {testResult.message}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleTest}
              disabled={!inputKey || isTesting}
              className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
            >
              {isTesting ? (
                <RefreshCw className="h-5 w-5 animate-spin" />
              ) : (
                <CheckCircle className="h-5 w-5" />
              )}
              Test Key
            </button>
            <button
              onClick={handleSave}
              disabled={!inputKey || isSaving || (testResult !== null && !testResult.valid)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSaving ? (
                <RefreshCw className="h-5 w-5 animate-spin" />
              ) : (
                <Key className="h-5 w-5" />
              )}
              Save Key
            </button>
          </div>
        </div>

        {/* Security Note */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-1">Security Note</h4>
          <p className="text-sm text-blue-700">
            Your API key is stored locally and is only sent to the Anthropic API for AI analysis.
            It is never shared with third parties. For production deployments, consider using
            environment variables on the server.
          </p>
        </div>
      </div>

      {/* Version Info */}
      <div className="mt-6 text-center text-sm text-slate-500">
        <p>OrgDesign Pro v1.0.0</p>
        <p>Powered by Claude AI and React</p>
      </div>
    </div>
  )
}
