"""
Archetype reference data for AI analysis engine.
Contains the 7 organizational archetypes with comparison criteria.
"""

ARCHETYPES = {
    "1_functional": {
        "name": "Functional Structure (The Efficiency Machine)",
        "best_for_industries": [
            "Utilities", "Mining", "Heavy Manufacturing",
            "Single-Product businesses", "Asset-heavy operations"
        ],
        "best_for_departments": [
            "Manufacturing/Operations (always)",
            "Finance (expertise depth)",
            "Legal (practice area specialization)",
            "R&D Research (deep expertise)",
            "Corporate Functions (default)"
        ],
        "org_size_sweet_spot": "1,000-100,000+",
        "primary_organizing_principle": "Functional expertise",
        "value_creation": "Internal manufacturing/operations",
        "revenue_model": "Product sales, Asset utilization",
        "key_indicators": [
            "Asset-heavy operations (high capital investment)",
            "Safety-critical operations (utilities, mining)",
            "Single core product or service",
            "Need for deep functional expertise",
            "Economies of scale paramount in each function"
        ],
        "success_metrics": [
            "Unit cost per product",
            "Defect rate / Quality metrics",
            "Asset utilization %",
            "Safety incidents (target: 0)",
            "Uptime %"
        ],
        "typical_layers": "6-8 layers",
        "typical_span": "5-8 (functional expertise required)",
        "core_tension": "Efficiency vs. Responsiveness",
        "failure_mode": "Functional silos - departments optimize locally, customer suffers",
        "warning_signs": [
            "Handoff delays between departments",
            "Not my problem culture",
            "Long approval chains",
            "Slow response to market changes"
        ],
        "example_companies": ["General Electric (traditional)", "ExxonMobil", "Duke Energy", "Rio Tinto"]
    },

    "2_divisional": {
        "name": "Divisional Structure (The Conglomerate)",
        "best_for_industries": [
            "Diversified holding companies",
            "Multi-brand retailers",
            "Global banks (retail + investment + wealth)",
            "Portfolio companies"
        ],
        "best_for_departments": [
            "Rarely used at department level",
            "Exception: Regional IT divisions serving distinct businesses"
        ],
        "org_size_sweet_spot": "10,000-500,000+",
        "primary_organizing_principle": "Business portfolios",
        "value_creation": "Portfolio of independent businesses",
        "revenue_model": "Division P&Ls, Investment returns",
        "key_indicators": [
            "Multiple unrelated business lines",
            "Different customer bases per division",
            "Minimal operational synergies",
            "Need for autonomous P&L accountability",
            "Portfolio management approach"
        ],
        "success_metrics": [
            "ROIC per division",
            "Portfolio PE ratio",
            "Conglomerate discount (should be <10%)",
            "Division autonomy score"
        ],
        "typical_layers": "3-5 layers (corporate to division to function)",
        "typical_span": "3-12 divisions per corporate leader",
        "core_tension": "Synergy vs. Autonomy",
        "failure_mode": "Conglomerate discount - stock trades below sum-of-parts",
        "warning_signs": [
            "No synergies being captured",
            "Activist investors circling",
            "Divisions compete for capital",
            "No compelling reason to be together"
        ],
        "example_companies": ["Berkshire Hathaway", "Johnson & Johnson", "3M", "Honeywell"]
    },

    "3_front_back_hybrid": {
        "name": "Front-Back Hybrid (The Global Maker-Seller)",
        "best_for_industries": [
            "FMCG / Consumer Goods",
            "Pharmaceuticals",
            "Automotive",
            "Global manufacturing with regional sales",
            "Aviation services"
        ],
        "best_for_departments": [
            "Commercial/Sales (MOST COMMON): Global Marketing + Regional Sales",
            "Supply Chain: Global Procurement + Regional Logistics",
            "IT/Digital: Global Platforms + Regional Support",
            "HR: Global COEs (Comp, L&D) + Regional HRBPs",
            "Product: Global Product Management + Regional Product Marketing",
            "Customer Service: Global Standards + Regional Delivery"
        ],
        "org_size_sweet_spot": "5,000-200,000",
        "primary_organizing_principle": "Value chain stages (Make global, Sell local)",
        "value_creation": "Global production + Regional sales",
        "revenue_model": "Product sales (global efficiency + local market fit)",
        "key_indicators": [
            "Global production/operations + Regional sales",
            "Need to balance standardization vs. localization",
            "Economies of scale in making + customization in selling",
            "Geographic expansion with local market differences",
            "Tension between efficiency and responsiveness"
        ],
        "success_metrics": [
            "Global gross margin",
            "Regional market share by geography",
            "R&D as % revenue",
            "Manufacturing cost per unit (global)",
            "Local market penetration (regional)"
        ],
        "typical_layers": "5-7 layers",
        "typical_span": "6-10 (varies by layer)",
        "core_tension": "Standardization vs. Localization",
        "failure_mode": "Global-local warfare - HQ and regions constantly fight",
        "warning_signs": [
            "Regional teams go around global standards",
            "Global mandates ignored locally",
            "HQ doesn't understand our market complaints",
            "Unclear decision rights on global vs. local"
        ],
        "example_companies": ["Procter & Gamble", "Coca-Cola", "Unilever", "Nestle", "Toyota"]
    },

    "4_process_based": {
        "name": "Process-Based Structure (The Lean Flow)",
        "best_for_industries": [
            "Logistics (FedEx, UPS)",
            "Chemical Processing",
            "Insurance (claims processing)",
            "High-Volume Manufacturing",
            "Banking (transaction processing)",
            "Airport/Aviation services"
        ],
        "best_for_departments": [
            "Service Delivery: Order-to-Cash, Customer Onboarding, Claims Processing",
            "Manufacturing: Material Flow (Receiving to Production to Shipping)",
            "Commercial: Quote-to-Cash, Lead-to-Order",
            "Finance: Procure-to-Pay, Record-to-Report",
            "HR: Hire-to-Retire process",
            "Supply Chain: Source-to-Deliver",
            "Passenger Services: Check-in to Boarding to Baggage"
        ],
        "org_size_sweet_spot": "500-50,000",
        "primary_organizing_principle": "End-to-end workflows",
        "value_creation": "Process efficiency",
        "revenue_model": "Transaction fees, Service revenue",
        "key_indicators": [
            "High-volume transactional operations",
            "Clear end-to-end processes",
            "Handoff delays between functions causing problems",
            "Customer experience degraded by silos",
            "Process efficiency more critical than functional depth"
        ],
        "success_metrics": [
            "Process cycle time (days)",
            "First-pass yield %",
            "Cost per transaction",
            "Customer satisfaction / NPS",
            "Throughput (units per period)"
        ],
        "typical_layers": "4-6 layers",
        "typical_span": "8-15 (process flow)",
        "core_tension": "Functional expertise vs. Customer journey",
        "failure_mode": "Process rigidity - workflow becomes strait-jacket",
        "warning_signs": [
            "Workarounds proliferate",
            "Customer complaints about inflexibility",
            "Process metrics good, customer satisfaction poor",
            "Can't handle exceptions"
        ],
        "example_companies": ["FedEx", "UPS", "Amazon Fulfillment", "Progressive Insurance", "Toyota Production System"]
    },

    "5_matrix_project": {
        "name": "Matrix Project Organization (The Builder)",
        "best_for_industries": [
            "Construction (Bechtel, Fluor)",
            "Oil & Gas EPC (Engineering, Procurement, Construction)",
            "Aerospace (Boeing, Airbus)",
            "Defense Contractors (Lockheed Martin)",
            "Professional Services"
        ],
        "best_for_departments": [
            "Engineering/R&D: Drug development programs, Product development projects",
            "IT: ERP implementations, Digital transformations, Major system rollouts",
            "Commercial: Strategic account teams, Large deal pursuit",
            "Corporate Projects: M&A integration, Change management programs"
        ],
        "org_size_sweet_spot": "500-50,000",
        "primary_organizing_principle": "Temporary projects",
        "value_creation": "Project delivery",
        "revenue_model": "Project fees (fixed-price or T&M contracts)",
        "key_indicators": [
            "Project-based revenue (not recurring products)",
            "Temporary teams assembled per project",
            "Need for cross-functional integration per project",
            "Project timeline and budget are primary metrics",
            "Functional expertise needed but project execution is king"
        ],
        "success_metrics": [
            "Schedule variance (on-time delivery)",
            "Budget variance (on-budget)",
            "Scope completion %",
            "Client satisfaction score",
            "Resource utilization %"
        ],
        "typical_layers": "4-6 layers",
        "typical_span": "PM: 5-10 project leads, FM: 10-20 specialists",
        "core_tension": "Project needs vs. Functional standards",
        "failure_mode": "Resource contention - every PM fighting for same engineers",
        "warning_signs": [
            "Your project isn't a priority",
            "Engineers burn out from conflicting demands",
            "Projects delayed waiting for resources",
            "Unclear prioritization mechanism"
        ],
        "example_companies": ["Bechtel", "Boeing", "Lockheed Martin", "McKinsey", "Accenture"]
    },

    "6_platform_ecosystem": {
        "name": "Platform Ecosystem Model (The Network Orchestrator)",
        "best_for_industries": [
            "Digital platforms (AWS, Azure, GCP)",
            "SaaS platforms (Salesforce, Shopify, Stripe)",
            "Marketplaces (Airbnb, Uber, Etsy)",
            "API-first businesses"
        ],
        "best_for_departments": [
            "IT/Digital: Internal Developer Platform, Data Platform, ML Platform",
            "Commercial: Marketplace operations (managing sellers + buyers)",
            "R&D: Open innovation platforms (external researchers use tools)",
            "RARE for traditional departments (Manufacturing, Finance, HR, Legal)"
        ],
        "org_size_sweet_spot": "50-100,000",
        "primary_organizing_principle": "Value enablement for external partners",
        "value_creation": "External ecosystem partners create value",
        "revenue_model": "Transaction fees, Revenue share, Usage-based pricing",
        "key_indicators": [
            "External developers build on your APIs/infrastructure",
            "API or marketplace revenue >30% of total",
            "Two-sided or multi-sided market",
            "Network effects are primary competitive moat",
            "Developer Relations or Partner Success teams exist"
        ],
        "success_metrics": [
            "API calls per month",
            "Ecosystem GMV (Gross Merchandise Value)",
            "Developer NPS",
            "Time-to-first-API-call",
            "Partner apps created per month",
            "Revenue share to partners"
        ],
        "typical_layers": "3-5 layers (platform core) + Flat ecosystem",
        "typical_span": "Platform: Internal teams, Ecosystem: 100s-1000s of partners",
        "core_tension": "Internal products vs. Ecosystem competition",
        "failure_mode": "Ecosystem death spiral - developers leave platform",
        "warning_signs": [
            "Declining API call volume",
            "Developer NPS dropping",
            "Competitors ecosystems growing faster",
            "Top partners defecting",
            "Platform competing too aggressively with partners"
        ],
        "example_companies": ["AWS", "Salesforce", "Shopify", "Stripe", "Airbnb", "Uber"],
        "use_sparingly": True,
        "digital_first_only": True
    },

    "7_team_topologies": {
        "name": "Team Topologies Model (The Fast Flow Organization)",
        "best_for_industries": [
            "Software companies (SaaS, Enterprise software)",
            "Digital banks (ING, Monzo, N26)",
            "E-commerce platforms (Zalando, ASOS)",
            "Media/Streaming (Netflix, Spotify)",
            "Tech-enabled services"
        ],
        "best_for_departments": [
            "IT/Digital: Stream-aligned teams (Mobile, Web, APIs) + Platform teams (DevOps, Data, Security)",
            "Product/Engineering: Product squads owning features end-to-end",
            "Digital Commercial: E-commerce squad, Digital marketing squad, CRM squad",
            "NOT suitable for: Traditional Manufacturing, Finance, Legal, HR"
        ],
        "org_size_sweet_spot": "50-10,000",
        "primary_organizing_principle": "Team cognitive load optimization & flow",
        "value_creation": "Continuous product delivery",
        "revenue_model": "Product subscriptions, Usage-based revenue",
        "key_indicators": [
            "Software/digital product revenue >50%",
            "Continuous deployment (weekly or daily releases)",
            "Cross-functional product teams exist or desired",
            "Internal platform teams being discussed",
            "Deployment bottlenecks slowing teams down"
        ],
        "success_metrics": [
            "Lead time (idea to production)",
            "Deployment frequency (deploys per week)",
            "MTTR (Mean Time To Recovery)",
            "Change fail rate %",
            "Team cognitive load score",
            "Platform service adoption rate"
        ],
        "typical_layers": "3-4 layers (minimize hierarchy)",
        "typical_span": "5-9 (two-pizza teams)",
        "core_tension": "Team autonomy vs. Dependencies",
        "failure_mode": "Cognitive overload - teams try to own too much",
        "warning_signs": [
            "Deployment frequency slowing",
            "Quality degrading",
            "Team burnout / We need more people constantly",
            "Poor platform services forcing workarounds"
        ],
        "example_companies": ["Spotify", "Netflix", "ING Bank", "Zalando", "Monzo"],
        "use_sparingly": True,
        "digital_first_only": True
    }
}

# Archetype applicability scoring weights
SCORING_WEIGHTS = {
    "industry_match": 30,
    "size_match": 15,
    "revenue_model_match": 20,
    "key_indicators_match": 25,
    "metrics_match": 10
}

# Department-level archetype preferences
DEPARTMENT_ARCHETYPES = {
    "commercial_sales": {
        "primary": "3_front_back_hybrid",
        "alternatives": ["4_process_based", "7_team_topologies"],
        "avoid": ["1_functional"]
    },
    "manufacturing_operations": {
        "primary": "1_functional",
        "alternatives": ["4_process_based"],
        "avoid": ["7_team_topologies", "6_platform_ecosystem"]
    },
    "finance": {
        "primary": "1_functional",
        "alternatives": ["3_front_back_hybrid", "4_process_based"],
        "avoid": ["7_team_topologies", "6_platform_ecosystem"]
    },
    "hr": {
        "primary": "3_front_back_hybrid",
        "alternatives": ["1_functional"],
        "avoid": ["5_matrix_project", "7_team_topologies"]
    },
    "it_digital": {
        "primary": "7_team_topologies",
        "alternatives": ["6_platform_ecosystem", "3_front_back_hybrid"],
        "avoid": ["1_functional"]
    },
    "rd_engineering": {
        "primary": "5_matrix_project",
        "alternatives": ["1_functional"],
        "avoid": ["4_process_based"]
    },
    "service_delivery": {
        "primary": "4_process_based",
        "alternatives": ["3_front_back_hybrid"],
        "avoid": ["5_matrix_project"]
    },
    "passenger_services": {
        "primary": "4_process_based",
        "alternatives": ["3_front_back_hybrid"],
        "avoid": ["6_platform_ecosystem", "7_team_topologies"]
    }
}


def get_archetype_by_id(archetype_id: str) -> dict:
    """Get archetype data by ID."""
    return ARCHETYPES.get(archetype_id, {})


def get_all_archetypes_summary() -> list:
    """Get summary of all archetypes for display."""
    return [
        {
            "id": arch_id,
            "name": arch_data["name"],
            "best_for_industries": arch_data["best_for_industries"],
            "organizing_principle": arch_data["primary_organizing_principle"],
            "typical_size": arch_data["org_size_sweet_spot"],
            "core_tension": arch_data["core_tension"],
            "example_companies": arch_data.get("example_companies", []),
            "digital_first_only": arch_data.get("digital_first_only", False)
        }
        for arch_id, arch_data in ARCHETYPES.items()
    ]


def get_department_recommendation(department: str) -> dict:
    """Get archetype recommendation for a specific department."""
    return DEPARTMENT_ARCHETYPES.get(department, {})
