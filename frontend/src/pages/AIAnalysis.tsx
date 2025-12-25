import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Brain, Loader2, AlertTriangle, ArrowRight, ChevronDown, ChevronUp, FileText, Upload, X } from 'lucide-react';
import { aiAnalysisApi, settingsApi } from '../services/api';
import type { AIAnalysisResult } from '../types';

export default function AIAnalysis() {
  const [analysis, setAnalysis] = useState<AIAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [designCriteria, setDesignCriteria] = useState('');
  const [strategyText, setStrategyText] = useState('');
  const [strategyMode, setStrategyMode] = useState<'text' | 'document'>('text');
  const [strategyFiles, setStrategyFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    trends: true,
    health: true,
    alignment: true,
    archetypes: true,
    actions: true,
  });

  useEffect(() => {
    checkApiStatus();
    loadExistingAnalysis();
  }, []);

  const checkApiStatus = async () => {
    try {
      const status = await settingsApi.getStatus();
      setApiConfigured(status.configured);
    } catch (err) {
      console.error('Failed to check API status:', err);
    }
  };

  const loadExistingAnalysis = async () => {
    try {
      const result = await aiAnalysisApi.getLatest();
      setAnalysis(result.ai_analysis);
    } catch (err) {
      // No existing analysis
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(f =>
      f.name.endsWith('.pdf') ||
      f.name.endsWith('.pptx') ||
      f.name.endsWith('.docx') ||
      f.name.endsWith('.txt')
    );
    setStrategyFiles(prev => [...prev, ...validFiles]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setStrategyFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      let result;
      if (strategyMode === 'document' && strategyFiles.length > 0) {
        result = await aiAnalysisApi.analyzeWithDocuments(
          strategyFiles,
          designCriteria || undefined
        );
      } else {
        result = await aiAnalysisApi.analyze(
          undefined,
          designCriteria || undefined,
          strategyText || undefined
        );
      }
      setAnalysis(result.ai_analysis);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (!apiConfigured) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">AI Analysis</h1>
        <div className="card text-center py-8">
          <Brain className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-600 mb-2">Claude API Not Configured</h2>
          <p className="text-gray-500 mb-4">
            Configure your Anthropic API key to enable AI-powered analysis.
          </p>
          <Link to="/settings" className="btn btn-primary inline-flex items-center gap-2">
            Configure API Key <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">AI-Powered Analysis</h1>

      {/* Input Section */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4">Analysis Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="label">Design Criteria (Optional)</label>
            <textarea
              value={designCriteria}
              onChange={(e) => setDesignCriteria(e.target.value)}
              className="input h-24"
              placeholder="E.g., We are focusing on agility and customer-centricity. We want to reduce layers..."
            />
          </div>

          <div>
            <label className="label">Strategy Context (Optional)</label>

            {/* Mode Toggle */}
            <div className="flex gap-2 mb-3">
              <button
                type="button"
                onClick={() => setStrategyMode('text')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  strategyMode === 'text'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Text Input
              </button>
              <button
                type="button"
                onClick={() => setStrategyMode('document')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  strategyMode === 'document'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Upload Documents
              </button>
            </div>

            {strategyMode === 'text' ? (
              <textarea
                value={strategyText}
                onChange={(e) => setStrategyText(e.target.value)}
                className="input h-24"
                placeholder="Paste key strategy points or business context..."
              />
            ) : (
              <div className="space-y-3">
                {/* File Upload Area */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-primary-500 transition-colors"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.pptx,.docx,.txt"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">
                    Click to upload or drag and drop
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    PDF, PowerPoint (.pptx), Word (.docx), or Text files
                  </p>
                </div>

                {/* Uploaded Files List */}
                {strategyFiles.length > 0 && (
                  <div className="space-y-2">
                    {strategyFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-700">{file.name}</span>
                          <span className="text-xs text-gray-400">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="p-1 hover:bg-gray-200 rounded"
                        >
                          <X className="w-4 h-4 text-gray-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={loading}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing (this may take 30-60 seconds)...
              </>
            ) : (
              <>
                <Brain className="w-5 h-5" />
                Run AI Analysis
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-50 border-red-200 mb-6">
          <div className="flex items-center gap-2 text-red-700">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">{error}</span>
          </div>
        </div>
      )}

      {/* Results */}
      {analysis && !analysis.error && (
        <div className="space-y-6">
          {/* Executive Summary */}
          {analysis.executive_summary && (
            <div className="card">
              <h2 className="text-lg font-semibold mb-3">Executive Summary</h2>
              <div className="prose prose-sm max-w-none text-gray-600">
                {analysis.executive_summary}
              </div>
            </div>
          )}

          {/* Industry Trends */}
          {analysis.category_1_industry_trends && (
            <CollapsibleSection
              title="Industry Trends & Benchmarks"
              isOpen={expandedSections.trends}
              onToggle={() => toggleSection('trends')}
            >
              <div className="space-y-4">
                {analysis.category_1_industry_trends.insights?.map((insight, i) => (
                  <div key={i} className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900">{insight.topic}</h4>
                    <p className="text-sm text-blue-700 mt-1">{insight.finding}</p>
                    <p className="text-xs text-blue-500 mt-2">
                      Source: {insight.source} | Relevance: {insight.relevance_to_org}
                    </p>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Health Diagnosis */}
          {analysis.category_2_health_diagnosis && (
            <CollapsibleSection
              title="Org Structure Health Diagnosis"
              isOpen={expandedSections.health}
              onToggle={() => toggleSection('health')}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-2">Strengths</h4>
                  <ul className="space-y-1">
                    {analysis.category_2_health_diagnosis.strengths?.map((s, i) => (
                      <li key={i} className="text-sm text-green-700">&#10003; {s}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-4 bg-red-50 rounded-lg">
                  <h4 className="font-medium text-red-800 mb-2">Weaknesses</h4>
                  <ul className="space-y-1">
                    {analysis.category_2_health_diagnosis.weaknesses?.map((w, i) => (
                      <li key={i} className="text-sm text-red-700">&#10007; {w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {analysis.category_2_health_diagnosis.pathologies?.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Pathologies</h4>
                  <div className="space-y-2">
                    {analysis.category_2_health_diagnosis.pathologies.map((p, i) => (
                      <div key={i} className={`p-3 rounded-lg ${
                        p.severity === 'High' ? 'bg-red-50' :
                        p.severity === 'Medium' ? 'bg-yellow-50' : 'bg-gray-50'
                      }`}>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{p.name}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            p.severity === 'High' ? 'bg-red-200 text-red-800' :
                            p.severity === 'Medium' ? 'bg-yellow-200 text-yellow-800' :
                            'bg-gray-200 text-gray-800'
                          }`}>{p.severity}</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{p.description}</p>
                        <p className="text-xs text-gray-500 mt-1">Impact: {p.impact}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Strategy Alignment */}
          {analysis.category_3_strategy_alignment && (
            <CollapsibleSection
              title="Strategy Alignment Score"
              isOpen={expandedSections.alignment}
              onToggle={() => toggleSection('alignment')}
            >
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-primary-100">
                  <span className="text-3xl font-bold text-primary-600">
                    {analysis.category_3_strategy_alignment.overall_alignment_score}
                  </span>
                </div>
                <p className="text-lg font-medium mt-2">
                  Grade: {analysis.category_3_strategy_alignment.alignment_grade}
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(analysis.category_3_strategy_alignment.scores || {}).map(([key, data]) => (
                  <div key={key} className="p-4 bg-gray-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-primary-600">{data.score}</p>
                    <p className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</p>
                  </div>
                ))}
              </div>

              {analysis.category_3_strategy_alignment.key_gaps?.length > 0 && (
                <div className="mt-4 p-4 bg-yellow-50 rounded-lg">
                  <h4 className="font-medium text-yellow-800 mb-2">Key Gaps</h4>
                  <ul className="space-y-1">
                    {analysis.category_3_strategy_alignment.key_gaps.map((gap, i) => (
                      <li key={i} className="text-sm text-yellow-700">&#8226; {gap}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Recommended Archetypes */}
          {(analysis.category_4_recommended_archetypes?.length ?? 0) > 0 && (
            <CollapsibleSection
              title="Recommended Organizational Archetypes"
              isOpen={expandedSections.archetypes}
              onToggle={() => toggleSection('archetypes')}
            >
              <div className="space-y-6">
                {analysis.category_4_recommended_archetypes!.map((arch, i) => (
                  <div key={i} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-lg font-semibold">{arch.archetype}</h4>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold text-primary-600">
                          {arch.business_model_match_score}
                        </span>
                        <span className="text-sm text-gray-500">/ 100</span>
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 mb-4">{arch.why_it_fits}</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="font-medium text-green-700 mb-1">Expected Benefits</p>
                        <ul className="space-y-1 text-gray-600">
                          {arch.expected_benefits?.map((b, j) => (
                            <li key={j}>&#10003; {b}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="font-medium text-red-700 mb-1">Implementation Challenges</p>
                        <ul className="space-y-1 text-gray-600">
                          {arch.implementation_challenges?.map((c, j) => (
                            <li key={j}>&#10007; {c}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                        Timeline: {arch.transformation_timeline}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        arch.confidence_level === 'High' ? 'bg-green-100 text-green-700' :
                        arch.confidence_level === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        Confidence: {arch.confidence_level}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Action Plan */}
          {analysis.action_plan && (
            <CollapsibleSection
              title="Action Plan"
              isOpen={expandedSections.actions}
              onToggle={() => toggleSection('actions')}
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-800 mb-2">Phase 1: Quick Wins</h4>
                  <ul className="space-y-1">
                    {analysis.action_plan.phase_1_quick_wins?.map((a, i) => (
                      <li key={i} className="text-sm text-green-700">&#8226; {a}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-800 mb-2">Phase 2: Structural</h4>
                  <ul className="space-y-1">
                    {analysis.action_plan.phase_2_structural?.map((a, i) => (
                      <li key={i} className="text-sm text-blue-700">&#8226; {a}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h4 className="font-medium text-purple-800 mb-2">Phase 3: Optimization</h4>
                  <ul className="space-y-1">
                    {analysis.action_plan.phase_3_optimization?.map((a, i) => (
                      <li key={i} className="text-sm text-purple-700">&#8226; {a}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </CollapsibleSection>
          )}
        </div>
      )}
    </div>
  );
}

function CollapsibleSection({
  title,
  isOpen,
  onToggle,
  children,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="card">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between text-left"
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>
      {isOpen && <div className="mt-4">{children}</div>}
    </div>
  );
}
