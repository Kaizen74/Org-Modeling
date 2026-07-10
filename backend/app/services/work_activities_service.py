"""
Work Activities Analysis Service.

Provides AI-powered analysis of work activities across the organization:
1. Activity Duplication Analysis - Identify duplicate work across job titles
2. Missing Activities Analysis - Compare against industry benchmarks
3. Coordination Gaps Analysis - Identify handoff/collaboration needs
4. Coherence & Synergy Analysis - How well activities align within teams
5. Work Theme Synthesis - Common patterns and themes of work
"""

from anthropic import Anthropic
from typing import List, Dict, Optional
import json
import re


class WorkActivitiesAnalysisService:
    """Analyze work activities using Claude AI."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key."""
        self.client = None
        if api_key:
            self.client = Anthropic(api_key=api_key)

    async def analyze_work_activities(
        self,
        employees: List[Dict],
        industry: Optional[str] = None
    ) -> Dict:
        """
        Perform comprehensive work activities analysis.

        Args:
            employees: List of employee dicts with work_activities field
            industry: Optional industry context for benchmarking

        Returns structured analysis including:
        - Activity duplication across roles
        - Missing activities vs industry benchmarks
        - Coordination gaps between departments
        - Department coherence scores
        - Work theme synthesis
        """
        if not self.client:
            return {
                "error": "Claude API not configured",
                "message": "Please configure your API key in Settings"
            }

        # Filter employees with work activities
        employees_with_activities = [
            emp for emp in employees
            if emp.get("work_activities", "").strip()
        ]

        if not employees_with_activities:
            return {
                "error": "No work activities data",
                "message": "No employees have work activities defined. Please ensure the CSV includes a 'Work Activities' column."
            }

        prompt = self._build_prompt(employees_with_activities, industry)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=12000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Extract JSON from response
            return self._parse_response(response_text)

        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}",
                "raw_response": str(e)
            }

    def _build_prompt(
        self,
        employees: List[Dict],
        industry: Optional[str]
    ) -> str:
        """Build the work activities analysis prompt."""

        # Group employees by department
        by_department = {}
        for emp in employees:
            dept = emp.get("department", "Unknown")
            if dept not in by_department:
                by_department[dept] = []
            by_department[dept].append(emp)

        # Build department summaries
        dept_summaries = []
        for dept, emps in by_department.items():
            emp_list = "\n".join([
                f"  - {emp['name']} ({emp['job_title']}, {emp['grade']}): {emp.get('work_activities', 'Not specified')}"
                for emp in emps
            ])
            dept_summaries.append(f"**{dept}** ({len(emps)} positions):\n{emp_list}")

        department_data = "\n\n".join(dept_summaries)

        industry_context = f"\n**INDUSTRY CONTEXT:** {industry}" if industry else "\n**INDUSTRY CONTEXT:** Not specified (infer from organization structure and job titles)"

        return f"""You are an expert organizational design consultant specializing in work activity analysis and job design. Analyze the following organization's work activities and provide structured insights.

**ORGANIZATION DATA:**
- Total Positions with Work Activities: {len(employees)}
- Departments: {len(by_department)}
{industry_context}

**POSITIONS BY DEPARTMENT:**
{department_data}

**EVIDENCE DISCIPLINE (MANDATORY):**
1. Facts, interpretation, and recommendation are separate registers. Quote actual work-activity text as evidence; label your reading of it as interpretation.
2. Classify evidence: OBSERVABLE (verbatim from the uploaded work activities/job titles) vs MODEL-INFERRED (your industry knowledge). Industry benchmarks are MODEL-INFERRED — never present them as facts about this organization.
3. Every duplication, gap, and coordination finding carries a confidence level (High/Medium/Low) with one-line justification. Findings resting only on MODEL-INFERRED evidence are capped at Medium.
4. Do not inflate one phrase match into a duplication pattern; quote the overlapping activity text from each affected role.
5. Populate data_gaps honestly: what this text-based analysis cannot verify, and the observable indicator that would verify it (e.g., time allocation data, RACI records, handoff logs).

**YOUR ANALYSIS MUST COVER 6 KEY AREAS:**

## 1. ACTIVITY DUPLICATION ANALYSIS (CRITICAL)
Identify and analyze duplication of work activities across different job titles:
- **Duplicate Activities:** List specific work activities that appear in multiple job titles
- **Duplication Severity:** Rate the extent of duplication (High/Medium/Low)
- **Impact Assessment:** Explain the business impact of each duplication (e.g., inefficiency, confusion, conflict)
- **Affected Roles:** Which specific roles have overlapping activities
- **Resolution Priority:** Which duplications should be addressed first

## 2. MISSING ACTIVITIES ANALYSIS (CRITICAL)
Based on industry research and best practices for similar job titles:
- **Missing Critical Activities:** Work activities that are typically performed by similar roles in the industry but are absent here
- **Gap Severity:** Rate how critical each missing activity is (Critical/Important/Nice-to-have)
- **Industry Benchmark:** Reference what similar organizations typically include
- **Affected Roles:** Which roles are missing these activities
- **Business Risk:** What risks arise from these missing activities

## 3. COORDINATION & HANDOFF GAPS (CRITICAL)
Identify where coordination between departments needs strengthening:
- **Handoff Points:** Where work passes between departments/roles
- **Coordination Gaps:** Where collaboration is weak or undefined
- **Gap Severity:** Rate each gap (Critical/Important/Minor)
- **Recommended Interfaces:** What coordination mechanisms should be added
- **Industry Practice:** How similar organizations handle these handoffs

## 4. DEPARTMENTAL COHERENCE & SYNERGY
For each department, analyze:
- **Coherence Score (0-100):** How well activities align within the team
- **Synergy Assessment:** Natural synergies and gaps between roles
- **Value Chain Position:** Where department sits in value chain

## 5. WORK THEME SYNTHESIS
- **Primary Themes:** 3-5 main categories of work
- **Theme Distribution:** How resources are allocated
- **Strategic Alignment Score (0-100):** Do themes align with priorities

## 6. RECOMMENDATIONS
Prioritized, actionable recommendations addressing:
- Duplication resolution
- Missing activity additions
- Coordination improvements
- Quick wins

**OUTPUT FORMAT (JSON):**
```json
{{
  "work_activities_summary": {{
    "total_positions_analyzed": 0,
    "departments_analyzed": 0,
    "positions_with_activities": 0,
    "industry_context": "string"
  }},

  "activity_duplication": {{
    "overall_duplication_score": 0,
    "severity_assessment": "High/Medium/Low",
    "duplications": [
      {{
        "activity": "Description of duplicated activity",
        "affected_roles": ["Role 1", "Role 2"],
        "affected_departments": ["Dept 1", "Dept 2"],
        "duplication_type": "Full Overlap/Partial Overlap/Ambiguous Boundary",
        "severity": "High/Medium/Low",
        "business_impact": "Description of negative impact",
        "resolution_priority": 1,
        "recommended_action": "How to resolve this duplication",
        "evidence": "Quoted overlapping activity text from each affected role",
        "confidence": "High/Medium/Low",
        "confidence_rationale": "One-line justification"
      }}
    ],
    "summary": "Overall assessment of duplication issues"
  }},

  "missing_activities": {{
    "overall_gap_score": 0,
    "severity_assessment": "Critical/Moderate/Minor",
    "gaps": [
      {{
        "activity": "Description of missing activity",
        "industry_benchmark": "What similar orgs typically do (MODEL-INFERRED — say so)",
        "affected_roles": ["Role that should have this"],
        "affected_departments": ["Dept"],
        "severity": "Critical/Important/Nice-to-have",
        "business_risk": "Risk of not having this activity",
        "recommendation": "How to address this gap",
        "confidence": "High/Medium/Low",
        "confidence_rationale": "One-line justification (capped at Medium if purely model-inferred)"
      }}
    ],
    "summary": "Overall assessment of activity gaps vs industry"
  }},

  "coordination_gaps": {{
    "overall_coordination_score": 0,
    "severity_assessment": "Critical/Moderate/Minor",
    "gaps": [
      {{
        "handoff_point": "Where work transfers between teams",
        "from_department": "Source department",
        "to_department": "Receiving department",
        "from_roles": ["Role names"],
        "to_roles": ["Role names"],
        "current_state": "How it works now (or doesn't)",
        "gap_type": "Missing Handoff/Unclear Ownership/No Feedback Loop/Timing Issues",
        "severity": "Critical/Important/Minor",
        "industry_practice": "How leading orgs handle this",
        "recommended_interface": "What coordination mechanism to add",
        "confidence": "High/Medium/Low",
        "confidence_rationale": "One-line justification"
      }}
    ],
    "summary": "Overall assessment of coordination effectiveness"
  }},

  "departmental_coherence": [
    {{
      "department": "Department Name",
      "position_count": 0,
      "coherence_score": 0,
      "coherence_rationale": "Why this score",
      "synergy_assessment": {{
        "strengths": ["strength 1"],
        "gaps": ["gap 1"],
        "overlaps": ["overlap 1"]
      }},
      "value_chain_position": "Front-line/Support/Core Operations/Strategy",
      "key_activities": ["main activity 1", "main activity 2"]
    }}
  ],

  "overall_coherence": {{
    "organization_coherence_score": 0,
    "cross_department_synergies": ["synergy 1"],
    "cross_department_gaps": ["gap 1"],
    "integration_assessment": "How well departments work together"
  }},

  "work_themes": {{
    "primary_themes": [
      {{
        "theme": "Theme Name",
        "description": "What this theme encompasses",
        "departments_involved": ["dept1"],
        "position_count": 0,
        "percentage_of_org": 0,
        "strategic_importance": "High/Medium/Low"
      }}
    ],
    "theme_distribution_assessment": "Analysis of how work is distributed",
    "strategic_alignment_score": 0,
    "missing_capabilities": ["capability 1"]
  }},

  "industry_comparison": {{
    "industry_identified": "Industry name",
    "activity_mix_assessment": {{
      "alignment_score": 0,
      "over_represented": ["activity type 1"],
      "under_represented": ["activity type 2"],
      "unique_strengths": ["strength 1"]
    }},
    "competitive_positioning": {{
      "potential_advantages": ["advantage 1"],
      "potential_disadvantages": ["disadvantage 1"],
      "overall_assessment": "Summary statement"
    }}
  }},

  "recommendations": {{
    "duplication_resolution": [
      {{
        "recommendation": "What to do",
        "addresses": "Which duplication this resolves",
        "priority": "High/Medium/Low",
        "effort": "High/Medium/Low"
      }}
    ],
    "missing_activity_additions": [
      {{
        "recommendation": "What to add",
        "addresses": "Which gap this fills",
        "priority": "High/Medium/Low",
        "effort": "High/Medium/Low"
      }}
    ],
    "coordination_improvements": [
      {{
        "recommendation": "What to improve",
        "addresses": "Which coordination gap",
        "priority": "High/Medium/Low",
        "effort": "High/Medium/Low"
      }}
    ],
    "quick_wins": ["quick win 1", "quick win 2"]
  }},

  "executive_summary": "2-3 paragraph summary focusing on duplication, gaps, and coordination issues",

  "data_gaps": [
    {{
      "gap": "What this text-based analysis cannot verify",
      "why_it_matters": "Which finding this limits",
      "observable_indicator_to_close": "Measurable data that would verify it (e.g., time allocation, RACI records, handoff logs)"
    }}
  ]
}}
```

Be specific and actionable. Reference actual job titles and departments from the data. Ground all analysis in research-based industry benchmarks where possible.
"""

    def _parse_response(self, response_text: str) -> Dict:
        """Parse AI response and extract JSON."""
        try:
            # Try to find JSON code block first
            json_start = response_text.find("```json")
            if json_start != -1:
                json_end = response_text.find("```", json_start + 7)
                if json_end != -1:
                    json_str = response_text[json_start + 7:json_end].strip()
                else:
                    json_str = response_text[json_start + 7:].strip()
            else:
                # Try to find raw JSON
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                else:
                    return {
                        "error": "Could not parse response",
                        "raw_response": response_text
                    }

            # Try to parse
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to repair truncated JSON
                repaired = self._repair_truncated_json(json_str)
                if repaired:
                    try:
                        result = json.loads(repaired)
                        result["_json_repaired"] = True
                        return result
                    except json.JSONDecodeError:
                        pass

                # Extract what we can
                return self._extract_partial_data(response_text)

        except Exception as e:
            return {
                "error": f"JSON parse error: {str(e)}",
                "raw_response": response_text
            }

    def _repair_truncated_json(self, json_str: str) -> Optional[str]:
        """Attempt to repair truncated JSON."""
        open_braces = json_str.count('{') - json_str.count('}')
        open_brackets = json_str.count('[') - json_str.count(']')

        if open_braces <= 0 and open_brackets <= 0:
            return None

        repaired = json_str.rstrip()

        # Remove incomplete string
        if repaired.count('"') % 2 == 1:
            last_quote = repaired.rfind('"')
            prev_quote = repaired.rfind('"', 0, last_quote)
            if prev_quote != -1:
                repaired = repaired[:prev_quote]

        # Clean trailing
        repaired = repaired.rstrip()
        while repaired and repaired[-1] in ',:"':
            repaired = repaired[:-1].rstrip()

        # Recount and close
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')

        repaired += ']' * open_brackets
        repaired += '}' * open_braces

        return repaired if open_braces > 0 or open_brackets > 0 else None

    def _extract_partial_data(self, response_text: str) -> Dict:
        """Extract partial data when full JSON parsing fails."""
        result = {
            "parse_warning": "Partial data extracted due to response format issues",
            "raw_response": response_text
        }

        # Try to extract executive summary
        exec_match = re.search(r'"executive_summary"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text)
        if exec_match:
            result["executive_summary"] = exec_match.group(1).replace('\\"', '"').replace('\\n', '\n')

        return result

    def get_quick_analysis(self, employees: List[Dict]) -> Dict:
        """
        Get quick analysis without API call.

        Provides basic statistics and preliminary duplication detection.
        """
        employees_with_activities = [
            emp for emp in employees
            if emp.get("work_activities", "").strip()
        ]

        # Group by department
        by_department = {}
        for emp in employees_with_activities:
            dept = emp.get("department", "Unknown")
            if dept not in by_department:
                by_department[dept] = []
            by_department[dept].append(emp)

        # Calculate coverage
        total = len(employees)
        with_activities = len(employees_with_activities)
        coverage_pct = (with_activities / total * 100) if total > 0 else 0

        # Department breakdown
        dept_breakdown = []
        for dept, emps in sorted(by_department.items(), key=lambda x: -len(x[1])):
            dept_breakdown.append({
                "department": dept,
                "positions_with_activities": len(emps),
                "sample_activities": [e.get("work_activities", "")[:100] for e in emps[:3]]
            })

        # Quick duplication check (simple keyword matching)
        activity_keywords = {}
        for emp in employees_with_activities:
            activities = emp.get("work_activities", "").lower()
            words = set(activities.replace(",", " ").replace(".", " ").split())
            for word in words:
                if len(word) > 4:  # Skip short words
                    if word not in activity_keywords:
                        activity_keywords[word] = []
                    activity_keywords[word].append(emp.get("job_title", "Unknown"))

        # Find potential duplications (keywords appearing in 3+ different job titles)
        potential_duplications = []
        for keyword, titles in activity_keywords.items():
            unique_titles = set(titles)
            if len(unique_titles) >= 3:
                potential_duplications.append({
                    "keyword": keyword,
                    "roles_count": len(unique_titles),
                    "roles": list(unique_titles)[:5]
                })

        return {
            "total_employees": total,
            "employees_with_work_activities": with_activities,
            "coverage_percentage": round(coverage_pct, 1),
            "departments_with_activities": len(by_department),
            "department_breakdown": dept_breakdown,
            "potential_duplications_detected": len(potential_duplications),
            "potential_duplications": potential_duplications[:5],
            "status": "complete" if coverage_pct > 80 else "partial" if coverage_pct > 20 else "minimal"
        }
