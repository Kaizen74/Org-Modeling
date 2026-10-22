import { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import { PageHeader, Section, StatusPill, Callout, Loading } from '../components/ui';

export default function Settings() {
  const [apiKey, setApiKey] = useState('');
  const [maskedKey, setMaskedKey] = useState<string | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; model?: string } | null>(null);

  useEffect(() => {
    settingsApi
      .getStatus()
      .then((status) => {
        setIsConfigured(status.configured);
        setMaskedKey(status.masked_key);
      })
      .catch((error) => console.error('Failed to fetch status:', error))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!apiKey.trim()) return;
    setSaving(true);
    setTestResult(null);
    try {
      const result = await settingsApi.setApiKey(apiKey);
      setMaskedKey(result.masked_key);
      setIsConfigured(true);
      setApiKey('');
    } catch {
      setTestResult({ success: false, message: 'The key could not be saved.' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testConnection();
      setTestResult({ success: result.success, message: result.message, model: result.model });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setTestResult({ success: false, message: err.response?.data?.detail || 'Connection test failed' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) return <Loading label="Loading settings" />;

  return (
    <>
      <PageHeader
        eyebrow="Setup — settings"
        title="Claude API key"
        lede="The AI analyses (work activities, archetype options, suggested scores and AI-role tags) use your Anthropic API key. Structure metrics, the org chart, scenarios and the board pack work without it."
      />

      <div className="max-w-2xl">
        <Section eyebrow="Status">
          <div className="card flex flex-wrap items-center gap-3">
            <StatusPill status={isConfigured ? 'healthy' : 'attention'} label={isConfigured ? 'Key configured' : 'No key yet'} />
            {maskedKey && <span className="text-sm text-secondary">Current key: <code className="rounded-sm bg-wash px-1.5 py-0.5 text-ink">{maskedKey}</code></span>}
          </div>
        </Section>

        <Section eyebrow={isConfigured ? 'Replace the key' : 'Add a key'}>
          <div className="card">
            <label htmlFor="apiKey" className="label">API key</label>
            <input
              type="password"
              id="apiKey"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="input"
              placeholder="sk-ant-…"
              autoComplete="off"
            />
            <p className="mt-1.5 text-xs text-faint">
              Create one at{' '}
              <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 underline">console.anthropic.com</a>.
              It is stored on this machine only.
            </p>
            <div className="mt-5 flex gap-3">
              <button onClick={handleSave} disabled={!apiKey.trim() || saving} className="btn btn-primary">
                {saving ? 'Saving…' : 'Save key'}
              </button>
              {isConfigured && (
                <button onClick={handleTest} disabled={testing} className="btn btn-secondary">
                  {testing ? 'Testing…' : 'Test the connection'}
                </button>
              )}
            </div>
          </div>
          {testResult && (
            <div className="mt-4">
              <Callout label={testResult.success ? 'Connected' : 'Not connected'} tone={testResult.success ? 'healthy' : 'attention'}>
                {testResult.message}{testResult.model && <> — model <code>{testResult.model}</code></>}
              </Callout>
            </div>
          )}
        </Section>

        <Section eyebrow="What is sent to the AI">
          <p className="text-sm text-secondary">
            Job titles, grades, departments, work-activity text, aggregate figures and your strategy and design-criteria text.
            Personal names are never sent.
          </p>
        </Section>
      </div>
    </>
  );
}
