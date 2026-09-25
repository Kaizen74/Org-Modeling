import { useState, useEffect } from 'react';
import { Key, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { settingsApi } from '../services/api';

export default function Settings() {
  const [apiKey, setApiKey] = useState('');
  const [maskedKey, setMaskedKey] = useState<string | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    model?: string;
  } | null>(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const status = await settingsApi.getStatus();
      setIsConfigured(status.configured);
      setMaskedKey(status.masked_key);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) return;

    setSaving(true);
    setTestResult(null);
    try {
      const result = await settingsApi.setApiKey(apiKey);
      setMaskedKey(result.masked_key);
      setIsConfigured(true);
      setApiKey('');
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to save API key',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testConnection();
      setTestResult({
        success: result.success,
        message: result.message,
        model: result.model,
      });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setTestResult({
        success: false,
        message: err.response?.data?.detail || 'Connection test failed',
      });
    } finally {
      setTesting(false);
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
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="card max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Key className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Claude API Configuration</h2>
            <p className="text-sm text-gray-500">
              Configure your Anthropic API key for AI-powered analysis
            </p>
          </div>
        </div>

        {/* Current Status */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            {isConfigured ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="font-medium text-green-700">API Key Configured</span>
              </>
            ) : (
              <>
                <XCircle className="w-5 h-5 text-red-500" />
                <span className="font-medium text-red-700">API Key Not Configured</span>
              </>
            )}
          </div>
          {maskedKey && (
            <p className="text-sm text-gray-500 mt-1">
              Current key: <code className="bg-gray-200 px-1 rounded">{maskedKey}</code>
            </p>
          )}
        </div>

        {/* API Key Input */}
        <div className="mb-4">
          <label htmlFor="apiKey" className="label">
            {isConfigured ? 'Update API Key' : 'Enter API Key'}
          </label>
          <input
            type="password"
            id="apiKey"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="input"
            placeholder="sk-ant-..."
          />
          <p className="text-xs text-gray-500 mt-1">
            Get your API key from{' '}
            <a
              href="https://console.anthropic.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline"
            >
              console.anthropic.com
            </a>
          </p>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={!apiKey.trim() || saving}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Key
          </button>

          {isConfigured && (
            <button
              onClick={handleTest}
              disabled={testing}
              className="btn btn-secondary flex items-center gap-2 disabled:opacity-50"
            >
              {testing && <Loader2 className="w-4 h-4 animate-spin" />}
              Test Connection
            </button>
          )}
        </div>

        {/* Test Result */}
        {testResult && (
          <div className={`mt-4 p-4 rounded-lg ${
            testResult.success ? 'bg-green-50' : 'bg-red-50'
          }`}>
            <div className="flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
              <span className={testResult.success ? 'text-green-700' : 'text-red-700'}>
                {testResult.message}
              </span>
            </div>
            {testResult.model && (
              <p className="text-sm text-green-600 mt-1">
                Model: {testResult.model}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
