"""
AI Analysis Service with Structured Categories.

Provides AI-powered org analysis with structured output categories:
1. Industry Trends
2. Org Structure Health Diagnosis
3. Strategy Alignment Score
4. Recommended Archetypes
"""

from anthropic import Anthropic
from typing import List, Dict, Optional
import json
import os


class AIAnalysisService:
    """
    AI-powered org analysis with structured output categories.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    async def analyze_organization(
        self,
        metrics: Dict,
        employees: List[Dict],
        strategy_documents: Optional[List[str]] = None,
        design_criteria: Optional[str] = None
    ) -> Dict:
        """
        Perform comprehensive AI analysis with structured categorization.

        Returns structured insights across 4 categories:
        - Industry trends & benchmarks
        - Health diagnosis
        - Strategy alignment scoring
        - Recommended archetypes
        """
        if not self.client:
            return {
                "error": "Claude API not configured",
                "message": "Please configure your API key in Settings"
            }

        prompt = self._build_prompt(metrics, employees, strategy_documents, design_criteria)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse structured response
            result = self._parse_structured_response(response)
            return result

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get AI analysis"
            }

    def _build_prompt(
        self,
        metrics: Dict,
        employees: List[Dict],
        strategy_docs: Optional[List[str]],
        design_criteria: Optional[str]
    ) -> str:
        """Build the comprehensive analysis prompt."""

        # Format metrics nicely
        manager_stats = metrics.get("manager_stats", {})
        span_stats = metrics.get("span_of_control", {})
        cost_stats = metrics.get("cost_analysis", {})
        layer_stats = metrics.get("layer_analysis", {})
        gap_stats = metrics.get("grade_gap_analysis", {})

        return f"""You are an expert organizational design consultant. Analyze this organization and provide structured insights.

**ORGANIZATIONAL DATA:**
- Total Employees: {metrics.get('total_employees', 0)}
- Managers: {manager_stats.get('total_managers', 0)} ({manager_stats.get('manager_ratio_pct', 0)}%)
- Individual Contributors: {manager_stats.get('total_ics', 0)} ({manager_stats.get('ic_ratio_pct', 0)}%)
- Average Span of Control: {span_stats.get('average_span', 0)}
- Median Span: {span_stats.get('median_span', 0)}
- Total Cost: ${cost_stats.get('total_cost', 0):,.0f}
- Average Cost per Employee: ${cost_stats.get('average_cost_per_employee', 0):,.0f}
- Organizational Layers: {layer_stats.get('total_layers', 0)}
- Average Grade Gap: {gap_stats.get('average_grade_gap', 0)}

**Span Distribution:**
{json.dumps(span_stats.get('distribution', {}), indent=2)}

**Distribution Percentages:**
{json.dumps(span_stats.get('distribution_pct', {}), indent=2)}

{"**STRATEGIC CONTEXT (FROM UPLOADED DOCUMENTS):**" if strategy_docs else ""}
{"IMPORTANT: Use the specific content below to assess how well the organization structure aligns with the stated strategy." if strategy_docs else ""}
{chr(10).join(strategy_docs) if strategy_docs else "No strategic documents provided."}

{"**ORGANIZATION DESIGN CRITERIA (USER-SPECIFIED):**" if design_criteria else ""}
{"IMPORTANT: The organization should be evaluated against these specific design criteria provided by the user:" if design_criteria else ""}
{design_criteria if design_criteria else "No specific design criteria provided."}

**YOUR ANALYSIS MUST BE STRUCTURED IN 4 CATEGORIES:**

## 1. INDUSTRY TRENDS & BENCHMARKS
Based on current research and best practices:
- Optimal span of control for this org size/type
- Manager ratio benchmarks
- Cost per employee norms for similar organizations
- Emerging org design trends relevant to this structure

Provide 3-5 insights with context.

## 2. ORG STRUCTURE HEALTH DIAGNOSIS
Evaluate against established frameworks:
- Kates-Kesler Five Activators
- McKinsey Managerial Archetypes
- Spans & Layers best practices

Identify:
- Strengths (what's working well)
- Weaknesses (structural issues)
- Pathologies (Frozen Middle, Collaborative Overload, etc.)
- Critical risks

## 3. STRATEGY ALIGNMENT SCORE
**CRITICAL: This section MUST directly reference and analyze the specific content from:**
1. The uploaded strategy documents (if provided) - quote specific strategic objectives, priorities, or initiatives
2. The user's design criteria (if provided) - evaluate against each stated requirement

Score alignment on these dimensions:
- Strategic clarity (0-100): How well does the current structure support the SPECIFIC strategic objectives mentioned in the documents?
- Execution readiness (0-100): Does the structure have the capability to deliver on the SPECIFIC initiatives and priorities stated?
- Efficiency score (0-100): Is the cost structure aligned with efficiency goals mentioned in the strategy/criteria?
- Agility score (0-100): Can the structure adapt to changes implied by the strategic direction?
- OVERALL ALIGNMENT SCORE (0-100): Weighted average

**For each score, you MUST:**
1. Reference specific text/objectives from the strategy documents or design criteria
2. Explain how the current org metrics (span, layers, costs) support or hinder those specific objectives
3. Identify specific structural gaps between current state and strategic requirements

## 4. RECOMMENDED ORGANIZATIONAL ARCHETYPES

Evaluate the organization against these 5 proven industry archetypes and recommend 2-3 best fits:

**ARCHETYPE 1: The Functional Structure (The Efficiency Machine)**
- Best For: Utilities, Mining, Heavy Manufacturing, Single-Product businesses
- Logic: Centralize engineering/operations for reliability and safety

**ARCHETYPE 2: The Divisional Structure (The Conglomerate)**
- Best For: Diversified Holding Companies, Banks with distinct units
- Logic: Business units as investment portfolios with autonomy

**ARCHETYPE 3: The Front-Back Hybrid (The Global Maker-Seller)**
- Best For: FMCG, Pharma, Consumer Goods, Automotive
- Logic: Centralized production + local sales/marketing

**ARCHETYPE 4: The Process-Based Structure (The Lean Flow)**
- Best For: Logistics, Insurance, High-Volume Manufacturing
- Logic: Organize around workflow, not departments

**ARCHETYPE 5: The Matrix Project Organization (The Builder)**
- Best For: Construction, Oil & Gas, Aerospace, Defense
- Logic: Project managers control budget/schedule, functions provide expertise

**FOR EACH RECOMMENDED ARCHETYPE, PROVIDE:**
1. Business Model Match Score (0-100)
2. Why It Fits: Specific evidence
3. Expected Benefits: Quantified where possible
4. Implementation Challenges
5. Transformation Timeline (Quick: 3-6 months, Medium: 6-12 months, Long: 12-18 months)
6. Confidence Level: High/Medium/Low
7. Critical Success Factors: Top 3 things for success

**OUTPUT FORMAT (JSON):**

```json
{{
  "executive_summary": "2-3 paragraph overview of key findings",

  "category_1_industry_trends": {{
    "insights": [
      {{
        "topic": "Topic name",
        "finding": "Key finding",
        "source": "Source/framework",
        "relevance_to_org": "How this applies"
      }}
    ]
  }},

  "category_2_health_diagnosis": {{
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "pathologies": [
      {{
        "name": "Pathology name",
        "description": "What it means",
        "impact": "Business impact",
        "severity": "High/Medium/Low"
      }}
    ],
    "critical_risks": ["risk 1", "risk 2"]
  }},

  "category_3_strategy_alignment": {{
    "strategy_context_analyzed": "Brief summary of key strategic objectives/themes from uploaded documents",
    "design_criteria_analyzed": "Brief summary of user's design criteria requirements",
    "scores": {{
      "strategic_clarity": {{"score": 0, "rationale": "explanation referencing specific strategy content", "supporting_evidence": "quote or reference from strategy docs"}},
      "execution_readiness": {{"score": 0, "rationale": "explanation referencing specific initiatives", "supporting_evidence": "quote or reference from strategy docs"}},
      "efficiency": {{"score": 0, "rationale": "explanation referencing cost/efficiency goals", "supporting_evidence": "quote or reference from strategy docs"}},
      "agility": {{"score": 0, "rationale": "explanation referencing adaptability needs", "supporting_evidence": "quote or reference from strategy docs"}}
    }},
    "overall_alignment_score": 0,
    "alignment_grade": "A-F",
    "key_gaps": [
      {{"gap": "gap description", "strategy_reference": "what strategy/criteria this relates to", "structural_impact": "how org structure causes this gap"}}
    ],
    "alignment_strengths": ["areas where structure supports strategy well"]
  }},

  "category_4_recommended_archetypes": [
    {{
      "archetype": "Archetype Name",
      "business_model_match_score": 0,
      "why_it_fits": "Detailed explanation",
      "expected_benefits": ["benefit 1", "benefit 2"],
      "implementation_challenges": ["challenge 1", "challenge 2"],
      "transformation_timeline": "X-Y months",
      "confidence_level": "High/Medium/Low",
      "critical_success_factors": ["factor 1", "factor 2", "factor 3"]
    }}
  ],

  "action_plan": {{
    "phase_1_quick_wins": ["action 1", "action 2"],
    "phase_2_structural": ["action 1", "action 2"],
    "phase_3_optimization": ["action 1", "action 2"]
  }}
}}
```

Be specific and actionable. Ground all recommendations in the data provided.
"""

    def _parse_structured_response(self, response) -> Dict:
        """Extract and parse JSON from Claude's response."""
        full_text = ""
        for block in response.content:
            if block.type == "text":
                full_text += block.text

        # Try to extract JSON
        try:
            # Look for JSON code block
            json_start = full_text.find("```json")
            if json_start != -1:
                json_end = full_text.find("```", json_start + 7)
                if json_end != -1:
                    json_str = full_text[json_start + 7:json_end].strip()
                    result = json.loads(json_str)
                    result["raw_response"] = full_text
                    return result

            # Try to find raw JSON
            json_start = full_text.find("{")
            json_end = full_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = full_text[json_start:json_end]
                result = json.loads(json_str)
                result["raw_response"] = full_text
                return result

            # Fallback - return as executive summary
            return {
                "executive_summary": full_text,
                "parse_error": "Could not extract structured JSON",
                "raw_response": full_text
            }

        except json.JSONDecodeError as e:
            return {
                "executive_summary": full_text,
                "parse_error": f"JSON parse error: {str(e)}",
                "raw_response": full_text
            }
        except Exception as e:
            return {
                "executive_summary": full_text,
                "parse_error": str(e),
                "raw_response": full_text
            }

    def get_quick_analysis(self, metrics: Dict) -> Dict:
        """Get a quick, non-AI analysis based on metrics alone."""
        manager_stats = metrics.get("manager_stats", {})
        span_stats = metrics.get("span_of_control", {})
        health = metrics.get("health_indicators", {})

        insights = []

        # Span analysis
        avg_span = span_stats.get("average_span", 0)
        if avg_span < 4:
            insights.append({
                "type": "warning",
                "category": "span",
                "message": f"Low average span ({avg_span}) suggests over-management",
                "recommendation": "Consider consolidating teams to increase spans to 5-8"
            })
        elif avg_span > 10:
            insights.append({
                "type": "warning",
                "category": "span",
                "message": f"High average span ({avg_span}) may strain managers",
                "recommendation": "Consider adding team leads or splitting large teams"
            })
        else:
            insights.append({
                "type": "success",
                "category": "span",
                "message": f"Healthy average span of control ({avg_span})",
                "recommendation": "Maintain current structure"
            })

        # Manager ratio
        mgr_ratio = manager_stats.get("manager_ratio_pct", 0)
        if mgr_ratio > 30:
            insights.append({
                "type": "warning",
                "category": "ratio",
                "message": f"High manager ratio ({mgr_ratio}%) indicates overhead",
                "recommendation": "Benchmark: Industry average is 15-25% managers"
            })

        return {
            "quick_insights": insights,
            "health_score": health.get("health_score", 0),
            "health_grade": health.get("health_grade", "?"),
            "warnings": health.get("warnings", []),
            "recommendations": health.get("recommendations", [])
        }
