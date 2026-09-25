"""
Research-calibrated organizational design benchmarks.

Every benchmark carries a named source so AI analysis cites credible research
instead of inventing numbers. Figures reflect published research as of 2025-2026;
update this file (not the prompts) when newer research supersedes them.
"""

SPAN_OF_CONTROL_BENCHMARKS = {
    "general_target": {
        "range": "5-10 direct reports",
        "source": "Cross-industry organization design practice (Gartner span-of-control benchmarking)",
        "note": "Ideal span depends on work complexity, employee experience, and manager capacity"
    },
    "knowledge_work": {
        "range": "6-8 direct reports",
        "source": "Industry benchmarking of professional/knowledge-worker teams",
        "note": "Complex, judgment-heavy work requires more manager attention per report"
    },
    "operational_transactional": {
        "range": "15-25 direct reports",
        "source": "Industry benchmarking of standardized operational roles",
        "note": "Routine, standardized work supports much wider spans"
    },
    "current_average_trend": {
        "figure": "12.1 average direct reports per manager (2025), up ~50% since 2013",
        "source": "Gallup research, 2025",
        "note": "Reflects widespread middle-management consolidation; widening spans without redesigning the manager role drives overload"
    },
    "manager_overload_signal": {
        "figure": "75% of CHROs report their managers are overwhelmed",
        "source": "Gartner CHRO survey",
        "note": "Span decisions must account for manager capacity, not just cost"
    },
    "mckinsey_managerial_archetypes": {
        "player_coach": {"span": "3-5", "definition": "Manager also carries significant individual-contributor work"},
        "coach": {"span": "6-7", "definition": "Substantial people-development responsibility, some individual work"},
        "supervisor": {"span": "8-10", "definition": "Moderate individual work, standardized processes"},
        "facilitator": {"span": "11-15", "definition": "Primarily coordination and oversight of self-sufficient teams"},
        "source": "McKinsey & Company, 'How to identify the right spans of control for your organization'",
        "note": "Span targets should be set per managerial archetype, not one org-wide number"
    }
}

LAYERS_BENCHMARKS = {
    "complexity_signal": {
        "figure": "Two-thirds of 2,500+ surveyed leaders say their organizations are overly complex and inefficient",
        "source": "McKinsey & Company leadership survey",
        "note": "Excess layers compound approvals, slow decisions, and fragment communication"
    },
    "typical_guidance": {
        "range": "Most organizations under 5,000 FTE operate effectively with 5-7 layers; each layer beyond need adds cost and decision latency",
        "source": "Spans-and-layers consulting practice (McKinsey, Bain, Deloitte org-design literature)",
        "note": "Layer count should follow decision-speed requirements, not headcount alone"
    }
}

MANAGER_RATIO_BENCHMARKS = {
    "typical_range": {
        "range": "15-25% of workforce in people-manager roles",
        "source": "Cross-industry HR benchmarking",
        "note": "Above 30% usually signals over-layering or fragmented teams"
    }
}

ORG_DESIGN_TRENDS_2026 = [
    {
        "trend": "Skills-based organization",
        "finding": "Work is increasingly organized around skills and capabilities rather than fixed jobs, with skills matched to problems in real time across teams, technology, and external partners",
        "source": "Deloitte Global Human Capital Trends 2026 (with Oxford Economics; 9,000+ leaders, 89 countries)"
    },
    {
        "trend": "Human-AI work redesign",
        "finding": "In AI-affected professions, required skill sets change ~66% faster than in other areas; org design must build capacity to partner with intelligent systems, not just tool training",
        "source": "Deloitte Global Human Capital Trends 2026"
    },
    {
        "trend": "Manager role redefinition",
        "finding": "As agentic AI absorbs routine coordination and administration, the manager role shifts toward coaching, talent brokering, and team assembly",
        "source": "Deloitte Global Human Capital Trends 2026"
    },
    {
        "trend": "Adaptability gap",
        "finding": "85% of leaders view workforce adaptability as critical, yet only 7% believe they excel at enabling continuous growth and adaptation",
        "source": "Deloitte Global Human Capital Trends 2026"
    },
    {
        "trend": "Middle-management consolidation",
        "finding": "Average manager span grew to 12.1 direct reports (2025), up nearly 50% since 2013, driven by delayering and cost pressure",
        "source": "Gallup research, 2025"
    }
]


def get_benchmarks_prompt_section() -> str:
    """Format benchmarks as a prompt section with sources, for AI analysis grounding."""
    mma = SPAN_OF_CONTROL_BENCHMARKS["mckinsey_managerial_archetypes"]
    trends = "\n".join(
        f"- {t['trend']}: {t['finding']} [Source: {t['source']}]"
        for t in ORG_DESIGN_TRENDS_2026
    )
    return f"""**RESEARCH-CALIBRATED BENCHMARKS (cite these sources; do not invent benchmark figures):**

Span of control:
- General target: {SPAN_OF_CONTROL_BENCHMARKS['general_target']['range']} [Source: {SPAN_OF_CONTROL_BENCHMARKS['general_target']['source']}]
- Knowledge work: {SPAN_OF_CONTROL_BENCHMARKS['knowledge_work']['range']}; Operational/transactional: {SPAN_OF_CONTROL_BENCHMARKS['operational_transactional']['range']}
- Current trend: {SPAN_OF_CONTROL_BENCHMARKS['current_average_trend']['figure']} [Source: {SPAN_OF_CONTROL_BENCHMARKS['current_average_trend']['source']}]
- Manager overload: {SPAN_OF_CONTROL_BENCHMARKS['manager_overload_signal']['figure']} [Source: {SPAN_OF_CONTROL_BENCHMARKS['manager_overload_signal']['source']}]
- McKinsey managerial archetypes (set spans per archetype, not org-wide): Player-Coach {mma['player_coach']['span']}, Coach {mma['coach']['span']}, Supervisor {mma['supervisor']['span']}, Facilitator {mma['facilitator']['span']} [Source: {mma['source']}]

Layers:
- {LAYERS_BENCHMARKS['complexity_signal']['figure']} [Source: {LAYERS_BENCHMARKS['complexity_signal']['source']}]
- {LAYERS_BENCHMARKS['typical_guidance']['range']} [Source: {LAYERS_BENCHMARKS['typical_guidance']['source']}]

Manager ratio:
- {MANAGER_RATIO_BENCHMARKS['typical_range']['range']} [Source: {MANAGER_RATIO_BENCHMARKS['typical_range']['source']}]; {MANAGER_RATIO_BENCHMARKS['typical_range']['note']}

2026 organization design trends:
{trends}
"""
