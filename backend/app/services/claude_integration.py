"""
Claude AI Integration Service.

Provides AI-powered organizational analysis using the Anthropic Claude API:
- Structural diagnosis
- Pathology detection (Frozen Middle, Collaborative Overload, etc.)
- Transformation recommendations
- Narrative generation for scenario comparisons
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic, APIError, AuthenticationError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. AI features will be unavailable.")


@dataclass
class AnalysisResult:
    """Result of AI analysis."""
    analysis_type: str
    success: bool
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    narrative: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_type": self.analysis_type,
            "success": self.success,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "narrative": self.narrative,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "generated_at": self.generated_at.isoformat(),
        }


# Analysis prompts
SYSTEM_PROMPT = """You are an expert organizational design consultant with deep knowledge of:
- Kates-Kesler Organization Design Framework
- McKinsey 7S Model
- Galbraith's Star Model
- Span of Control optimization
- Organizational pathology detection

You analyze organizational structures and provide actionable recommendations.
Always be specific, reference framework principles, and provide evidence-based insights.
Format responses as structured JSON when requested."""


STRUCTURAL_ANALYSIS_PROMPT = """Analyze this organizational structure and identify key characteristics:

Organization Data:
{org_data}

Metrics:
{metrics}

Provide a comprehensive structural analysis in JSON format:
{{
    "findings": [
        {{
            "category": "structure|efficiency|complexity|governance",
            "title": "Brief finding title",
            "description": "Detailed description with evidence",
            "severity": "low|medium|high",
            "evidence": ["specific data points supporting this finding"]
        }}
    ],
    "strengths": ["List of organizational strengths"],
    "areas_for_improvement": ["List of improvement opportunities"],
    "overall_assessment": "1-2 paragraph summary"
}}"""


PATHOLOGY_DETECTION_PROMPT = """Analyze this organization for common organizational pathologies:

Organization Data:
{org_data}

Metrics:
{metrics}

Detect and report on these common pathologies:
1. Frozen Middle - Bloated middle management slowing decisions
2. Collaborative Overload - Too many people in decision-making
3. Matrix Muddle - Unclear reporting in matrix structures
4. Span Drought - Spans too narrow, excessive layers
5. Span Deluge - Spans too wide, insufficient management
6. Orphan Problem - Disconnected or poorly integrated units
7. Empire Building - Unnecessary team expansion
8. Siloed Structure - Lack of cross-functional integration

Return JSON format:
{{
    "pathologies_detected": [
        {{
            "name": "Pathology name",
            "severity": "mild|moderate|severe",
            "description": "How it manifests in this org",
            "evidence": ["specific data points"],
            "affected_areas": ["functions or units affected"],
            "impact": "Business impact of this pathology",
            "remediation": "Recommended fix"
        }}
    ],
    "healthy_patterns": ["Positive patterns observed"],
    "risk_assessment": "Overall risk level and summary"
}}"""


RECOMMENDATIONS_PROMPT = """Based on this organizational analysis, provide transformation recommendations:

Organization Data:
{org_data}

Metrics:
{metrics}

Findings:
{findings}

Generate specific, actionable recommendations in JSON format:
{{
    "recommendations": [
        {{
            "priority": "critical|high|medium|low",
            "title": "Recommendation title",
            "description": "Detailed description",
            "rationale": "Why this is recommended",
            "framework_reference": "Which design framework supports this",
            "implementation_steps": ["Step 1", "Step 2"],
            "expected_impact": {{
                "cost_reduction": "percentage or N/A",
                "efficiency_gain": "description",
                "risk_mitigation": "description"
            }},
            "effort": "low|medium|high",
            "timeline": "immediate|short-term|medium-term|long-term"
        }}
    ],
    "quick_wins": ["Recommendations that can be implemented immediately"],
    "strategic_initiatives": ["Longer-term structural changes"],
    "change_management_notes": "Key considerations for implementation"
}}"""


COMPARISON_NARRATIVE_PROMPT = """Generate a professional narrative comparing these two organizational scenarios:

Baseline Scenario (Current State):
{baseline}

Target Scenario (Future State):
{target}

Changes Summary:
{changes}

Write a 2-3 paragraph executive summary explaining:
1. The key differences between the two scenarios
2. The business rationale for the changes
3. Expected benefits and risks

Use professional consulting language suitable for a C-suite presentation.
Be specific about numbers and impacts."""


class ClaudeAnalysisService:
    """
    AI-powered organizational analysis using Claude API.

    Features:
    - Structural analysis
    - Pathology detection
    - Transformation recommendations
    - Scenario comparison narratives
    - API key validation
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        """
        Initialize the Claude analysis service.

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            model: Claude model to use
            max_tokens: Maximum tokens in response
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required for AI features")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self._client: Optional[Anthropic] = None

    @property
    def client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Anthropic API key not configured")
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def validate_api_key(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Test if the API key is valid.

        Args:
            api_key: API key to test (uses configured key if not provided)

        Returns:
            Dict with validation result
        """
        test_key = api_key or self.api_key
        if not test_key:
            return {
                "is_valid": False,
                "message": "No API key provided",
                "model_available": None,
            }

        try:
            client = Anthropic(api_key=test_key)
            # Make a minimal request to test the key
            response = client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
            )
            return {
                "is_valid": True,
                "message": "API key is valid",
                "model_available": self.model,
            }
        except AuthenticationError:
            return {
                "is_valid": False,
                "message": "Invalid API key",
                "model_available": None,
            }
        except APIError as e:
            return {
                "is_valid": False,
                "message": f"API error: {str(e)}",
                "model_available": None,
            }
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"Connection error: {str(e)}",
                "model_available": None,
            }

    def analyze_structure(
        self,
        org_data: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> AnalysisResult:
        """
        Perform structural analysis of the organization.

        Args:
            org_data: Organization structure data
            metrics: Calculated metrics

        Returns:
            AnalysisResult with findings and recommendations
        """
        prompt = STRUCTURAL_ANALYSIS_PROMPT.format(
            org_data=json.dumps(self._prepare_org_summary(org_data), indent=2),
            metrics=json.dumps(metrics, indent=2),
        )

        return self._run_analysis("structural", prompt)

    def detect_pathologies(
        self,
        org_data: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> AnalysisResult:
        """
        Detect organizational pathologies.

        Args:
            org_data: Organization structure data
            metrics: Calculated metrics

        Returns:
            AnalysisResult with detected pathologies
        """
        prompt = PATHOLOGY_DETECTION_PROMPT.format(
            org_data=json.dumps(self._prepare_org_summary(org_data), indent=2),
            metrics=json.dumps(metrics, indent=2),
        )

        return self._run_analysis("pathology", prompt)

    def generate_recommendations(
        self,
        org_data: Dict[str, Any],
        metrics: Dict[str, Any],
        findings: List[Dict[str, Any]],
    ) -> AnalysisResult:
        """
        Generate transformation recommendations.

        Args:
            org_data: Organization structure data
            metrics: Calculated metrics
            findings: Previous analysis findings

        Returns:
            AnalysisResult with recommendations
        """
        prompt = RECOMMENDATIONS_PROMPT.format(
            org_data=json.dumps(self._prepare_org_summary(org_data), indent=2),
            metrics=json.dumps(metrics, indent=2),
            findings=json.dumps(findings, indent=2),
        )

        return self._run_analysis("recommendations", prompt)

    def generate_comparison_narrative(
        self,
        baseline: Dict[str, Any],
        target: Dict[str, Any],
        changes: Dict[str, Any],
    ) -> AnalysisResult:
        """
        Generate narrative comparing two scenarios.

        Args:
            baseline: Baseline scenario data
            target: Target scenario data
            changes: Summary of changes

        Returns:
            AnalysisResult with narrative
        """
        prompt = COMPARISON_NARRATIVE_PROMPT.format(
            baseline=json.dumps(self._prepare_scenario_summary(baseline), indent=2),
            target=json.dumps(self._prepare_scenario_summary(target), indent=2),
            changes=json.dumps(changes, indent=2),
        )

        return self._run_analysis("comparison", prompt, expect_json=False)

    def run_comprehensive_analysis(
        self,
        org_data: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, AnalysisResult]:
        """
        Run all analysis types.

        Args:
            org_data: Organization structure data
            metrics: Calculated metrics

        Returns:
            Dict of analysis results by type
        """
        results = {}

        # Structural analysis
        results["structural"] = self.analyze_structure(org_data, metrics)

        # Pathology detection
        results["pathology"] = self.detect_pathologies(org_data, metrics)

        # Recommendations (using findings from above)
        all_findings = []
        if results["structural"].success:
            all_findings.extend(results["structural"].findings)
        if results["pathology"].success:
            all_findings.extend(results["pathology"].findings)

        results["recommendations"] = self.generate_recommendations(
            org_data, metrics, all_findings
        )

        return results

    def _run_analysis(
        self,
        analysis_type: str,
        prompt: str,
        expect_json: bool = True,
    ) -> AnalysisResult:
        """Execute an analysis prompt and parse results."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            if expect_json:
                # Extract JSON from response
                parsed = self._parse_json_response(content)

                # Get findings - normalize pathology format to standard finding format
                findings = parsed.get("findings", [])
                pathologies = parsed.get("pathologies_detected", [])

                # Convert pathologies to findings format (they use "name" instead of "title")
                for pathology in pathologies:
                    findings.append({
                        "title": pathology.get("name", "Unknown Issue"),
                        "description": pathology.get("description", ""),
                        "severity": self._map_pathology_severity(pathology.get("severity", "moderate")),
                        "evidence": pathology.get("evidence", []),
                        "category": "pathology",
                        "impact": pathology.get("impact"),
                        "remediation": pathology.get("remediation"),
                    })

                recommendations = parsed.get("recommendations", [])
                narrative = parsed.get("overall_assessment", parsed.get("risk_assessment"))
            else:
                findings = []
                recommendations = []
                narrative = content

            return AnalysisResult(
                analysis_type=analysis_type,
                success=True,
                findings=findings,
                recommendations=recommendations,
                narrative=narrative,
                tokens_used=tokens_used,
            )

        except AuthenticationError:
            return AnalysisResult(
                analysis_type=analysis_type,
                success=False,
                findings=[],
                recommendations=[],
                error="Invalid API key",
            )
        except APIError as e:
            return AnalysisResult(
                analysis_type=analysis_type,
                success=False,
                findings=[],
                recommendations=[],
                error=f"API error: {str(e)}",
            )
        except Exception as e:
            logger.exception(f"Analysis error: {e}")
            return AnalysisResult(
                analysis_type=analysis_type,
                success=False,
                findings=[],
                recommendations=[],
                error=f"Analysis failed: {str(e)}",
            )

    def _map_pathology_severity(self, severity: str) -> str:
        """Map pathology severity (mild/moderate/severe) to finding severity (low/medium/high)."""
        mapping = {
            "mild": "low",
            "moderate": "medium",
            "severe": "high",
        }
        return mapping.get(severity.lower(), "medium")

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from Claude's response."""
        # Try to find JSON block
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass

            # Return empty structure if parsing fails
            logger.warning("Could not parse JSON from Claude response")
            return {"findings": [], "recommendations": []}

    def _prepare_org_summary(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a summary of org data for the prompt (avoid token limits)."""
        employees = org_data.get("employees", [])

        # Summarize by function and level
        function_counts = {}
        level_counts = {}
        sample_employees = []

        for emp in employees[:100]:  # Sample for large orgs
            func = emp.get("function", "Unknown")
            function_counts[func] = function_counts.get(func, 0) + 1

            level = emp.get("level", 0)
            level_counts[str(level)] = level_counts.get(str(level), 0) + 1

            if len(sample_employees) < 10:
                sample_employees.append({
                    "name": emp.get("full_name", ""),
                    "title": emp.get("job_title", ""),
                    "level": level,
                    "function": func,
                })

        return {
            "total_employees": len(employees),
            "function_distribution": function_counts,
            "level_distribution": level_counts,
            "sample_employees": sample_employees,
            "relationships_count": len(org_data.get("relationships", [])),
            "forest_count": len(org_data.get("forests", [])),
        }

    def _prepare_scenario_summary(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare scenario summary for comparison prompts."""
        return {
            "name": scenario.get("name", ""),
            "employee_count": len(scenario.get("employees", [])),
            "total_cost": scenario.get("total_cost", 0),
            "metrics": scenario.get("metrics", {}),
        }


def create_analysis_service(api_key: Optional[str] = None) -> ClaudeAnalysisService:
    """
    Create a Claude analysis service instance.

    Args:
        api_key: Optional API key (uses env var if not provided)

    Returns:
        ClaudeAnalysisService instance
    """
    return ClaudeAnalysisService(api_key=api_key)
