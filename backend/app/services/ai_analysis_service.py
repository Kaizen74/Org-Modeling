"""
AI Analysis Service with Structured Categories.

Provides AI-powered org analysis with structured output categories:
1. Industry Trends
2. Org Structure Health Diagnosis
3. Strategy Alignment Score
4. Recommended Archetypes (7-archetype framework)
"""

from anthropic import Anthropic
from typing import List, Dict, Optional
import json
import os

from ..resources.archetypes_reference import (
    ARCHETYPES,
    SCORING_WEIGHTS,
    DEPARTMENT_ARCHETYPES,
    get_all_archetypes_summary,
    get_department_recommendation
)


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
        design_criteria: Optional[str] = None,
        analysis_scope: str = "organization",
        department: Optional[str] = None
    ) -> Dict:
        """
        Perform comprehensive AI analysis with structured categorization.

        Args:
            metrics: Organization metrics dict
            employees: List of employee dicts
            strategy_documents: Optional list of strategy document contents
            design_criteria: Optional text describing design criteria
            analysis_scope: "organization" for full org, "department" for dept-level
            department: Department name when analysis_scope is "department"

        Returns structured insights across 4 categories:
        - Industry trends & benchmarks
        - Health diagnosis
        - Strategy alignment scoring
        - Recommended archetypes (all 7 evaluated and scored)
        """
        if not self.client:
            return {
                "error": "Claude API not configured",
                "message": "Please configure your API key in Settings"
            }

        prompt = self._build_prompt(
            metrics, employees, strategy_documents, design_criteria,
            analysis_scope, department
        )

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

    def _build_archetype_reference(self, analysis_scope: str, department: Optional[str]) -> str:
        """Build archetype reference section for the prompt."""
        archetypes_text = []

        for arch_id, arch_data in ARCHETYPES.items():
            digital_note = " [DIGITAL-FIRST ONLY]" if arch_data.get("digital_first_only") else ""

            archetypes_text.append(f"""
**{arch_data['name']}{digital_note}**
- ID: {arch_id}
- Best For Industries: {', '.join(arch_data['best_for_industries'][:4])}
- Best For Departments: {', '.join(arch_data['best_for_departments'][:3])}
- Org Size Sweet Spot: {arch_data['org_size_sweet_spot']}
- Primary Organizing Principle: {arch_data['primary_organizing_principle']}
- Value Creation: {arch_data['value_creation']}
- Revenue Model: {arch_data['revenue_model']}
- Key Indicators: {', '.join(arch_data['key_indicators'][:3])}
- Success Metrics: {', '.join(arch_data['success_metrics'][:3])}
- Typical Layers: {arch_data['typical_layers']}
- Typical Span: {arch_data['typical_span']}
- Core Tension: {arch_data['core_tension']}
- Failure Mode: {arch_data['failure_mode']}
- Warning Signs: {', '.join(arch_data['warning_signs'][:2])}
- Example Companies: {', '.join(arch_data.get('example_companies', [])[:3])}
""")

        dept_guidance = ""
        if analysis_scope == "department" and department:
            dept_key = department.lower().replace(" ", "_").replace("/", "_")
            dept_rec = get_department_recommendation(dept_key)
            if dept_rec:
                primary = ARCHETYPES.get(dept_rec.get("primary", ""), {}).get("name", "")
                alts = [ARCHETYPES.get(a, {}).get("name", "") for a in dept_rec.get("alternatives", [])]
                avoid = [ARCHETYPES.get(a, {}).get("name", "") for a in dept_rec.get("avoid", [])]
                dept_guidance = f"""
**DEPARTMENT-SPECIFIC GUIDANCE FOR {department.upper()}:**
- Primary Recommended: {primary}
- Alternative Options: {', '.join(alts)}
- Archetypes to Avoid: {', '.join(avoid)}
"""

        return "\n".join(archetypes_text) + dept_guidance

    def _build_prompt(
        self,
        metrics: Dict,
        employees: List[Dict],
        strategy_docs: Optional[List[str]],
        design_criteria: Optional[str],
        analysis_scope: str = "organization",
        department: Optional[str] = None
    ) -> str:
        """Build the comprehensive analysis prompt."""

        # Format metrics nicely
        manager_stats = metrics.get("manager_stats", {})
        span_stats = metrics.get("span_of_control", {})
        cost_stats = metrics.get("cost_analysis", {})
        layer_stats = metrics.get("layer_analysis", {})
        gap_stats = metrics.get("grade_gap_analysis", {})

        # Build archetype reference
        archetype_reference = self._build_archetype_reference(analysis_scope, department)

        # Scope context
        scope_context = ""
        if analysis_scope == "department" and department:
            scope_context = f"\n**ANALYSIS SCOPE: DEPARTMENT-LEVEL for {department}**\nFocus your archetype recommendations on what works best for this specific department, not the entire organization.\n"
        else:
            scope_context = "\n**ANALYSIS SCOPE: ORGANIZATION-WIDE**\nProvide archetype recommendations for the entire organization structure.\n"

        return f"""You are an expert organizational design consultant with deep expertise in the 7 canonical organizational archetypes. Analyze this organization and provide structured insights.
{scope_context}
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
{"USE FOR: Strategy Alignment Score (Category 3) - Assess how well the org structure supports the strategic objectives below." if strategy_docs else ""}
{chr(10).join(strategy_docs) if strategy_docs else "No strategic documents provided."}

{"**ORGANIZATION DESIGN CRITERIA (USER-SPECIFIED):**" if design_criteria else ""}
{"USE FOR: Archetype Recommendations (Category 4) - Recommend org structures that best achieve these design criteria." if design_criteria else ""}
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
**CRITICAL: This section assesses how well the CURRENT org structure aligns with the organization's STRATEGY.**
**Use ONLY the uploaded strategy documents for this analysis.**

If strategy documents are provided, you MUST:
- Quote specific strategic objectives, priorities, initiatives, or goals from the documents
- Assess whether the current org structure (spans, layers, costs, reporting lines) supports or hinders each objective

Score alignment on these dimensions:
- Strategic clarity (0-100): How well does the current structure support the SPECIFIC strategic objectives mentioned in the strategy documents?
- Execution readiness (0-100): Does the structure have the capability to deliver on the SPECIFIC initiatives and priorities stated in the strategy?
- Efficiency score (0-100): Is the cost structure aligned with efficiency/profitability goals mentioned in the strategy?
- Agility score (0-100): Can the structure adapt to market changes or transformation needs implied by the strategy?
- OVERALL ALIGNMENT SCORE (0-100): Weighted average

**For each score, you MUST:**
1. Reference specific text/objectives from the uploaded strategy documents
2. Explain how the current org metrics (span, layers, costs) support or hinder those specific strategic objectives
3. Identify specific structural gaps between current org state and strategic requirements

## 4. RECOMMENDED ORGANIZATIONAL ARCHETYPES (7-ARCHETYPE FRAMEWORK)
**CRITICAL: This section evaluates ALL 7 organizational archetypes and recommends the top 2 best fits.**
**Use the organization design criteria (user-specified) to guide your recommendations.**

**ARCHETYPE SCORING METHODOLOGY:**
Score each archetype (0-100) based on these weighted criteria:
- Industry Match (30%): How well does the archetype fit the apparent industry/sector?
- Size Match (15%): Is the org size within the archetype's sweet spot?
- Revenue Model Match (20%): Does the business model align with the archetype's value creation logic?
- Key Indicators Match (25%): Do the org's characteristics match the archetype's key indicators?
- Metrics Match (10%): Do span, layers, and structure metrics align with the archetype's typical patterns?

**THE 7 ORGANIZATIONAL ARCHETYPES:**
{archetype_reference}

**EVALUATION REQUIREMENTS:**
1. Score ALL 7 archetypes using the methodology above
2. Rank them from highest to lowest fit
3. Select the TOP 2 archetypes for detailed recommendations
4. For digital-first archetypes (Platform Ecosystem, Team Topologies), explicitly assess if the organization has sufficient digital DNA

**FOR EACH OF THE TOP 2 RECOMMENDED ARCHETYPES, PROVIDE:**
1. Archetype Name and ID
2. Overall Fit Score (0-100) with breakdown by criteria
3. Why It Fits: Specific evidence from the org data
4. Design Criteria Addressed: How this archetype achieves the user's stated design criteria
5. Expected Benefits: Quantified where possible
6. Implementation Challenges: Specific to this org's current state
7. Transformation Timeline: Quick (3-6 months), Medium (6-12 months), or Long (12-18 months)
8. Confidence Level: High/Medium/Low with rationale
9. Critical Success Factors: Top 3 things for success
10. Warning Signs to Monitor: From the archetype's failure mode
11. **Practical Examples**: 1-2 real-world examples:
    - Well-known companies that successfully use this structure
    - How they implemented it and what makes it work
    - Relevance to this organization's situation

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
    "strategy_documents_analyzed": "Brief summary of key strategic objectives/themes extracted from uploaded strategy documents",
    "scores": {{
      "strategic_clarity": {{"score": 0, "rationale": "explanation referencing specific strategy content", "supporting_evidence": "quote from strategy docs"}},
      "execution_readiness": {{"score": 0, "rationale": "explanation referencing specific initiatives", "supporting_evidence": "quote from strategy docs"}},
      "efficiency": {{"score": 0, "rationale": "explanation referencing cost/efficiency goals", "supporting_evidence": "quote from strategy docs"}},
      "agility": {{"score": 0, "rationale": "explanation referencing adaptability needs", "supporting_evidence": "quote from strategy docs"}}
    }},
    "overall_alignment_score": 0,
    "alignment_grade": "A-F",
    "key_gaps": [
      {{"gap": "gap description", "strategy_reference": "specific strategic objective this relates to", "structural_impact": "how current org structure causes this gap"}}
    ],
    "alignment_strengths": ["areas where current structure supports strategy well"]
  }},

  "category_4_recommended_archetypes": {{
    "design_criteria_analyzed": "Summary of user's org design criteria requirements",
    "analysis_scope": "organization or department",
    "department_analyzed": "Department name if department-level analysis",
    "all_archetype_scores": [
      {{
        "archetype_id": "1_functional",
        "archetype_name": "Functional Structure (The Efficiency Machine)",
        "overall_score": 0,
        "score_breakdown": {{
          "industry_match": 0,
          "size_match": 0,
          "revenue_model_match": 0,
          "key_indicators_match": 0,
          "metrics_match": 0
        }},
        "fit_summary": "One-line summary of why this score",
        "digital_first_applicable": true
      }}
    ],
    "recommendations": [
      {{
        "rank": 1,
        "archetype_id": "archetype_id",
        "archetype": "Archetype Name",
        "overall_fit_score": 0,
        "score_breakdown": {{
          "industry_match": {{"score": 0, "rationale": "explanation"}},
          "size_match": {{"score": 0, "rationale": "explanation"}},
          "revenue_model_match": {{"score": 0, "rationale": "explanation"}},
          "key_indicators_match": {{"score": 0, "rationale": "explanation"}},
          "metrics_match": {{"score": 0, "rationale": "explanation"}}
        }},
        "design_criteria_addressed": ["how this archetype addresses each design criteria requirement"],
        "why_it_fits": "Detailed explanation linking to design criteria and org data",
        "expected_benefits": ["benefit 1", "benefit 2"],
        "implementation_challenges": ["challenge 1", "challenge 2"],
        "transformation_timeline": "X-Y months",
        "confidence_level": "High/Medium/Low",
        "confidence_rationale": "Why this confidence level",
        "critical_success_factors": ["factor 1", "factor 2", "factor 3"],
        "warning_signs_to_monitor": ["warning sign from archetype failure mode"],
        "practical_examples": [
          {{
            "company_or_scenario": "Company name or 'Illustrative Scenario'",
            "description": "How they implement this archetype",
            "key_success_factors": "What makes it work for them",
            "relevance_to_your_org": "How this example applies to your situation"
          }}
        ]
      }}
    ]
  }},

  "action_plan": {{
    "phase_1_quick_wins": ["action 1", "action 2"],
    "phase_2_structural": ["action 1", "action 2"],
    "phase_3_optimization": ["action 1", "action 2"]
  }}
}}
```

Be specific and actionable. Ground all recommendations in the data provided. Score ALL 7 archetypes in all_archetype_scores, then provide detailed recommendations for the TOP 2.
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
