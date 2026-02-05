"""
Work Activities Analysis Service.

Provides AI-powered analysis of work activities across the organization:
1. Coherence & Synergy Analysis - How well activities align within teams
2. Work Theme Synthesis - Common patterns and themes of work
3. Industry Benchmark Comparison - How activities compare to competitors
"""

from anthropic import Anthropic
from typing import List, Dict, Optional
import json


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

        Returns structured analysis:
        - Department coherence scores
        - Work theme synthesis
        - Industry comparison
        - Recommendations
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
                max_tokens=8000,
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

**YOUR ANALYSIS MUST COVER 4 AREAS:**

## 1. DEPARTMENTAL COHERENCE & SYNERGY ANALYSIS
For each department/sub-department, analyze:
- **Activity Coherence Score (0-100):** How well do the work activities within this team align with each other? Do they form a coherent set of responsibilities?
- **Synergy Assessment:** Are there natural synergies between roles? Are there gaps or overlaps?
- **Value Chain Position:** Where does this department sit in the organization's value chain?
- **Internal Dependencies:** How dependent are roles on each other within the department?

## 2. WORK THEME SYNTHESIS
Identify and synthesize the major themes of work performed across the organization:
- **Primary Themes:** What are the 3-5 main categories of work?
- **Theme Distribution:** How are resources allocated across themes?
- **Strategic Alignment:** Do the work themes align with typical organizational priorities?
- **Missing Capabilities:** Are there gaps in work themes that might indicate missing capabilities?

## 3. INDUSTRY BENCHMARK COMPARISON
Compare the organization's work activities against typical competitors and industry standards:
- **Activity Mix Analysis:** How does the work activity mix compare to industry norms?
- **Role Specialization:** Are roles appropriately specialized or generalized for the industry?
- **Emerging Activities:** Are there industry-standard activities that are missing?
- **Competitive Positioning:** Based on work activities, where might this org have competitive advantages or disadvantages?

## 4. RECOMMENDATIONS
Based on your analysis, provide actionable recommendations:
- **Structural Recommendations:** How could work be better organized?
- **Role Optimization:** Which roles might benefit from redesign?
- **Capability Gaps:** What capabilities should be developed?
- **Quick Wins:** What changes could be made immediately?

**OUTPUT FORMAT (JSON):**
```json
{{
  "work_activities_summary": {{
    "total_positions_analyzed": 0,
    "departments_analyzed": 0,
    "positions_with_activities": 0,
    "industry_context": "string"
  }},

  "departmental_coherence": [
    {{
      "department": "Department Name",
      "position_count": 0,
      "coherence_score": 0,
      "coherence_rationale": "Why this score",
      "synergy_assessment": {{
        "strengths": ["strength 1", "strength 2"],
        "gaps": ["gap 1"],
        "overlaps": ["overlap 1"]
      }},
      "value_chain_position": "Front-line/Support/Core Operations/Strategy",
      "internal_dependencies": "High/Medium/Low",
      "key_activities": ["main activity 1", "main activity 2"]
    }}
  ],

  "overall_coherence": {{
    "organization_coherence_score": 0,
    "cross_department_synergies": ["synergy 1", "synergy 2"],
    "cross_department_gaps": ["gap 1", "gap 2"],
    "integration_assessment": "How well departments work together"
  }},

  "work_themes": {{
    "primary_themes": [
      {{
        "theme": "Theme Name",
        "description": "What this theme encompasses",
        "departments_involved": ["dept1", "dept2"],
        "position_count": 0,
        "percentage_of_org": 0,
        "strategic_importance": "High/Medium/Low"
      }}
    ],
    "theme_distribution_assessment": "Analysis of how work is distributed",
    "strategic_alignment_score": 0,
    "missing_capabilities": ["capability 1", "capability 2"]
  }},

  "industry_comparison": {{
    "industry_identified": "Industry name inferred or provided",
    "activity_mix_assessment": {{
      "alignment_score": 0,
      "over_represented": ["activity type 1"],
      "under_represented": ["activity type 2"],
      "unique_strengths": ["strength 1"]
    }},
    "role_specialization": {{
      "assessment": "Too specialized/Well balanced/Too generalized",
      "rationale": "Why this assessment"
    }},
    "emerging_industry_activities": [
      {{
        "activity": "Activity name",
        "industry_prevalence": "High/Medium/Low",
        "present_in_org": true,
        "recommendation": "What to do"
      }}
    ],
    "competitive_positioning": {{
      "potential_advantages": ["advantage 1"],
      "potential_disadvantages": ["disadvantage 1"],
      "overall_assessment": "Summary statement"
    }}
  }},

  "recommendations": {{
    "structural": [
      {{
        "recommendation": "What to do",
        "rationale": "Why",
        "impact": "High/Medium/Low",
        "effort": "High/Medium/Low",
        "affected_departments": ["dept1"]
      }}
    ],
    "role_optimization": [
      {{
        "current_role": "Role name",
        "recommendation": "What to change",
        "rationale": "Why"
      }}
    ],
    "capability_development": [
      {{
        "capability": "Capability name",
        "current_state": "Description",
        "target_state": "Description",
        "priority": "High/Medium/Low"
      }}
    ],
    "quick_wins": ["quick win 1", "quick win 2"]
  }},

  "executive_summary": "2-3 paragraph summary of key findings and recommendations"
}}
```

Be specific and actionable. Ground all analysis in the actual work activities provided. Identify specific roles and departments in your recommendations.
"""

    def _parse_response(self, response_text: str) -> Dict:
        """Parse AI response and extract JSON."""
        try:
            # Try to find JSON in the response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1

            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                return {
                    "error": "Could not parse response",
                    "raw_response": response_text
                }
        except json.JSONDecodeError as e:
            return {
                "error": f"JSON parse error: {str(e)}",
                "raw_response": response_text
            }

    def get_quick_analysis(self, employees: List[Dict]) -> Dict:
        """
        Get quick analysis without API call.

        Provides basic statistics about work activities.
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

        return {
            "total_employees": total,
            "employees_with_work_activities": with_activities,
            "coverage_percentage": round(coverage_pct, 1),
            "departments_with_activities": len(by_department),
            "department_breakdown": dept_breakdown,
            "status": "complete" if coverage_pct > 80 else "partial" if coverage_pct > 20 else "minimal"
        }
