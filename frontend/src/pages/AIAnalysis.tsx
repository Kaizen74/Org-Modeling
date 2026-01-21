import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Brain, Loader2, AlertTriangle, ArrowRight, ChevronDown, ChevronUp, FileText, Upload, X } from 'lucide-react';
import { aiAnalysisApi, settingsApi } from '../services/api';
import type { AIAnalysisResult, ArchetypeScoreSummary } from '../types';

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
                  <ul className="space-y-2">
                    {analysis.category_3_strategy_alignment.key_gaps.map((gap, i) => (
                      <li key={i} className="text-sm text-yellow-700">
                        {typeof gap === 'string' ? (
                          <>&#8226; {gap}</>
                        ) : (
                          <div className="p-2 bg-yellow-100 rounded">
                            <p className="font-medium">&#8226; {gap.gap}</p>
                            {gap.strategy_reference && (
                              <p className="text-xs mt-1">Strategy Reference: {gap.strategy_reference}</p>
                            )}
                            {gap.structural_impact && (
                              <p className="text-xs mt-1">Structural Impact: {gap.structural_impact}</p>
                            )}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Recommended Archetypes */}
          {analysis.category_4_recommended_archetypes && (
            <CollapsibleSection
              title="Recommended Organizational Archetypes (7-Archetype Framework)"
              isOpen={expandedSections.archetypes}
              onToggle={() => toggleSection('archetypes')}
            >
              {/* Show design criteria and scope if available */}
              {!Array.isArray(analysis.category_4_recommended_archetypes) && (
                <div className="mb-4 space-y-2">
                  {analysis.category_4_recommended_archetypes.analysis_scope && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">Analysis Scope:</span>{' '}
                        {analysis.category_4_recommended_archetypes.analysis_scope === 'department'
                          ? `Department-Level (${analysis.category_4_recommended_archetypes.department_analyzed || 'Not specified'})`
                          : 'Organization-Wide'}
                      </p>
                    </div>
                  )}
                  {analysis.category_4_recommended_archetypes.design_criteria_analyzed && (
                    <div className="p-3 bg-blue-50 rounded-lg">
                      <p className="text-sm text-blue-700">
                        <span className="font-medium">Design Criteria Analyzed:</span>{' '}
                        {analysis.category_4_recommended_archetypes.design_criteria_analyzed}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* All Archetype Scores Comparison */}
              {!Array.isArray(analysis.category_4_recommended_archetypes) &&
                analysis.category_4_recommended_archetypes.all_archetype_scores &&
                analysis.category_4_recommended_archetypes.all_archetype_scores.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-md font-semibold mb-3">All 7 Archetypes - Fit Score Comparison</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-100">
                          <th className="text-left p-2">Archetype</th>
                          <th className="text-center p-2">Overall Score</th>
                          <th className="text-center p-2 hidden md:table-cell">Industry</th>
                          <th className="text-center p-2 hidden md:table-cell">Size</th>
                          <th className="text-center p-2 hidden lg:table-cell">Revenue</th>
                          <th className="text-center p-2 hidden lg:table-cell">Indicators</th>
                          <th className="text-left p-2">Fit Summary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...analysis.category_4_recommended_archetypes.all_archetype_scores]
                          .sort((a: ArchetypeScoreSummary, b: ArchetypeScoreSummary) => b.overall_score - a.overall_score)
                          .map((archScore: ArchetypeScoreSummary, i: number) => (
                          <tr key={i} className={`border-b ${i < 2 ? 'bg-green-50' : ''}`}>
                            <td className="p-2">
                              <span className="font-medium">{archScore.archetype_name}</span>
                              {!archScore.digital_first_applicable && (
                                <span className="ml-1 text-xs text-gray-400">(Digital-first)</span>
                              )}
                            </td>
                            <td className="text-center p-2">
                              <span className={`font-bold ${
                                archScore.overall_score >= 70 ? 'text-green-600' :
                                archScore.overall_score >= 50 ? 'text-yellow-600' :
                                'text-red-600'
                              }`}>
                                {archScore.overall_score}
                              </span>
                            </td>
                            <td className="text-center p-2 hidden md:table-cell">{archScore.score_breakdown?.industry_match || '-'}</td>
                            <td className="text-center p-2 hidden md:table-cell">{archScore.score_breakdown?.size_match || '-'}</td>
                            <td className="text-center p-2 hidden lg:table-cell">{archScore.score_breakdown?.revenue_model_match || '-'}</td>
                            <td className="text-center p-2 hidden lg:table-cell">{archScore.score_breakdown?.key_indicators_match || '-'}</td>
                            <td className="p-2 text-xs text-gray-600">{archScore.fit_summary}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    * Top 2 archetypes highlighted. Score weights: Industry (30%), Key Indicators (25%), Revenue Model (20%), Size (15%), Metrics (10%)
                  </p>
                </div>
              )}

              {/* Detailed Recommendations for Top 2 */}
              <h3 className="text-md font-semibold mb-3">Top Recommendations (Detailed Analysis)</h3>
              <div className="space-y-6">
                {(Array.isArray(analysis.category_4_recommended_archetypes)
                  ? analysis.category_4_recommended_archetypes
                  : analysis.category_4_recommended_archetypes.recommendations || []
                ).map((arch, i) => (
                  <div key={i} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        {arch.rank && (
                          <span className="inline-block px-2 py-0.5 bg-primary-100 text-primary-700 text-xs font-medium rounded mr-2">
                            #{arch.rank}
                          </span>
                        )}
                        <h4 className="text-lg font-semibold inline">{arch.archetype}</h4>
                        {arch.archetype_id && (
                          <span className="text-xs text-gray-400 ml-2">({arch.archetype_id})</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold text-primary-600">
                          {arch.overall_fit_score || arch.business_model_match_score}
                        </span>
                        <span className="text-sm text-gray-500">/ 100</span>
                      </div>
                    </div>

                    {/* Score Breakdown */}
                    {arch.score_breakdown && (
                      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                        <p className="font-medium text-gray-700 mb-2 text-sm">Score Breakdown:</p>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                          {Object.entries(arch.score_breakdown).map(([key, val]) => {
                            const score = typeof val === 'object' ? val.score : val;
                            const rationale = typeof val === 'object' ? val.rationale : null;
                            return (
                              <div key={key} className="text-center p-2 bg-white rounded" title={rationale || ''}>
                                <p className="font-bold text-primary-600">{score}</p>
                                <p className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    <p className="text-sm text-gray-600 mb-4">{arch.why_it_fits}</p>

                    {/* Design Criteria Addressed */}
                    {arch.design_criteria_addressed && arch.design_criteria_addressed.length > 0 && (
                      <div className="mb-4 p-3 bg-primary-50 rounded-lg">
                        <p className="font-medium text-primary-700 mb-1 text-sm">How This Addresses Your Design Criteria:</p>
                        <ul className="space-y-1 text-sm text-primary-600">
                          {arch.design_criteria_addressed.map((item, j) => (
                            <li key={j}>&#10003; {item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

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

                    {/* Warning Signs to Monitor */}
                    {arch.warning_signs_to_monitor && arch.warning_signs_to_monitor.length > 0 && (
                      <div className="mt-4 p-3 bg-amber-50 rounded-lg">
                        <p className="font-medium text-amber-700 mb-1 text-sm">Warning Signs to Monitor:</p>
                        <ul className="space-y-1 text-sm text-amber-600">
                          {arch.warning_signs_to_monitor.map((sign, j) => (
                            <li key={j}>&#9888; {sign}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Practical Examples */}
                    {arch.practical_examples && arch.practical_examples.length > 0 && (
                      <div className="mt-4 p-4 bg-indigo-50 rounded-lg">
                        <p className="font-medium text-indigo-800 mb-3">Real-World Examples</p>
                        <div className="space-y-3">
                          {arch.practical_examples.map((example, j) => (
                            <div key={j} className="p-3 bg-white rounded border border-indigo-100">
                              <p className="font-medium text-indigo-700">{example.company_or_scenario}</p>
                              <p className="text-sm text-gray-600 mt-1">{example.description}</p>
                              {example.key_success_factors && (
                                <p className="text-xs text-indigo-600 mt-2">
                                  <span className="font-medium">Key Success Factors:</span> {example.key_success_factors}
                                </p>
                              )}
                              {example.relevance_to_your_org && (
                                <p className="text-xs text-gray-500 mt-1 italic">
                                  <span className="font-medium">Relevance:</span> {example.relevance_to_your_org}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

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
                      {arch.confidence_rationale && (
                        <span className="text-xs text-gray-500 italic">
                          ({arch.confidence_rationale})
                        </span>
                      )}
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
