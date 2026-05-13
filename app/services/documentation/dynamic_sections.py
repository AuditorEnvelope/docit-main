"""
Dynamic Section Generator - Intent-Based Documentation Sections

FORBIDDEN: Generic titles like "Overview," "Architecture," or "Workflow."
MANDATORY: Intent-Based Titles derived directly from code logic.

Title Generation Formula: [Action Verb] + [Domain of Responsibility] + [System Impact]

Example Transformations:
  "Authentication" → "Enforcing Identity Perimeter & Token Lifecycle"
  "Database" → "Persistent State Management & Relational Integrity"
  "API" → "Orchestrating Request-Response Cycles & Data Contracts"
"""

from dataclasses import dataclass
from typing import List, Optional
from app.services.documentation.discovery_scanner import (
    DiscoveryReport,
    DiscoveredPrimitive,
    PrimitiveType,
    DataJourney,
)


@dataclass
class DynamicSection:
    """A documentation section generated from discovery."""
    id: str
    title: str  # Intent-based title
    description: str  # What to document
    primitives: List[str]  # Related discovered primitives
    subsections: List[str]
    priority: int  # Higher = more important
    persona: str  # "internal" or "dev"


# Action verbs for title generation
ACTION_VERBS = {
    PrimitiveType.INGRESS: [
        "Ingesting", "Receiving", "Capturing", "Accepting", "Handling",
        "Processing", "Routing", "Dispatching"
    ],
    PrimitiveType.EGRESS: [
        "Emitting", "Persisting", "Transmitting", "Dispatching", "Writing",
        "Publishing", "Syncing", "Exporting"
    ],
    PrimitiveType.STATE: [
        "Modeling", "Structuring", "Organizing", "Defining", "Representing",
        "Encapsulating", "Abstracting"
    ],
    PrimitiveType.ORCHESTRATOR: [
        "Orchestrating", "Coordinating", "Managing", "Directing", "Mediating",
        "Sequencing", "Governing", "Controlling"
    ],
}

# Domain phrases based on patterns
DOMAIN_PHRASES = {
    "api": "API Request Handling",
    "route": "Request Routing",
    "auth": "Identity Verification",
    "user": "User Context",
    "session": "Session State",
    "token": "Token Lifecycle",
    "database": "Data Persistence",
    "db": "Database Operations",
    "model": "Entity Models",
    "schema": "Data Schemas",
    "controller": "Request Controllers",
    "service": "Service Layer",
    "middleware": "Middleware Pipeline",
    "handler": "Event Handling",
    "client": "External Clients",
    "fetch": "HTTP Communication",
    "logger": "System Observability",
    "error": "Error Management",
    "config": "Configuration Management",
    "component": "Component Tree",
    "hook": "React Hooks",
    "context": "Application State",
    "store": "State Management",
    "util": "Utility Functions",
    "helper": "Helper Functions",
}

# Impact phrases
IMPACT_PHRASES = {
    PrimitiveType.INGRESS: [
        "& System Entry Points",
        "& Data Reception Layer",
        "& Input Boundary",
        "& Request Processing",
    ],
    PrimitiveType.EGRESS: [
        "& Side Effect Management",
        "& External Integration",
        "& Output Boundary",
        "& Data Export Layer",
    ],
    PrimitiveType.STATE: [
        "& Data Integrity",
        "& Entity Relationships",
        "& Persistence Layer",
        "& Schema Evolution",
    ],
    PrimitiveType.ORCHESTRATOR: [
        "& Cross-Cutting Concerns",
        "& System Coordination",
        "& Flow Control",
        "& Dependency Graph",
    ],
}


def generate_sections_from_discovery(
    report: DiscoveryReport,
    persona: str = "internal"
) -> List[DynamicSection]:
    """
    Generate documentation sections from discovery report.

    This is the main entry point. It:
    1. Analyzes discovered primitives
    2. Groups related primitives
    3. Generates intent-based titles
    4. Creates section specifications
    """
    sections = []

    # 1. INGRESS SECTIONS
    if report.ingress_points:
        sections.extend(_generate_ingress_sections(report, persona))

    # 2. EGRESS SECTIONS
    if report.egress_points:
        sections.extend(_generate_egress_sections(report, persona))

    # 3. STATE SECTIONS
    if report.state_models:
        sections.extend(_generate_state_sections(report, persona))

    # 4. ORCHESTRATOR SECTIONS
    if report.orchestrators:
        sections.extend(_generate_orchestrator_sections(report, persona))

    # 5. DATA JOURNEY SECTIONS (traces)
    if report.data_journeys:
        sections.extend(_generate_journey_sections(report, persona))

    # 6. CONSTRAINTS & BRITTLE POINTS (internal only)
    if persona == "internal":
        if report.constraints or report.brittle_points:
            sections.append(_generate_constraints_section(report))

    # Sort by priority
    sections.sort(key=lambda s: -s.priority)

    # Limit to reasonable number
    return sections[:8]


def _generate_ingress_sections(report: DiscoveryReport, persona: str) -> List[DynamicSection]:
    """Generate sections for ingress points."""
    sections = []

    # Group by file or pattern
    api_ingress = [p for p in report.ingress_points if 'endpoint' in p.description.lower(
    ) or 'api' in p.file_path.lower()]
    event_ingress = [p for p in report.ingress_points if 'event' in p.description.lower(
    ) or 'handler' in p.name.lower()]
    ui_ingress = [p for p in report.ingress_points if 'component' in p.description.lower(
    ) or 'page' in p.file_path.lower()]

    if api_ingress and persona == "internal":
        sections.append(DynamicSection(
            id="request-ingress-boundary",
            title=_generate_title(PrimitiveType.INGRESS, api_ingress, "api"),
            description=_build_ingress_description(api_ingress),
            primitives=[p.name for p in api_ingress[:5]],
            subsections=[
                "Entry Point Registry & Route Definitions",
                "Request Validation & Schema Enforcement",
                "Authentication & Authorization Checks",
                "Rate Limiting & Throttling",
            ],
            priority=90,
            persona=persona,
        ))

    if event_ingress and persona == "internal":
        sections.append(DynamicSection(
            id="event-ingress-processing",
            title=_generate_title(PrimitiveType.INGRESS,
                                  event_ingress, "handler"),
            description="Document the event reception layer, handlers, and processing queues.",
            primitives=[p.name for p in event_ingress[:5]],
            subsections=[
                "Event Handler Registry",
                "Queue Processing & Acknowledgment",
                "Error Handling & Retry Logic",
            ],
            priority=75,
            persona=persona,
        ))

    if ui_ingress:
        # For frontend, generate appropriate sections
        sections.append(DynamicSection(
            id="ui-entry-points",
            title="Rendering Component Hierarchy & Page Structure",
            description="Document the UI entry points, page components, and routing structure.",
            primitives=[p.name for p in ui_ingress[:5]],
            subsections=[
                "Page Components & Route Definitions",
                "Layout Components & Shared Structure",
                "Entry Point Data Loading",
            ],
            priority=85,
            persona=persona,
        ))

    return sections


def _generate_egress_sections(report: DiscoveryReport, persona: str) -> List[DynamicSection]:
    """Generate sections for egress points."""
    sections = []

    db_egress = [p for p in report.egress_points if any(
        k in p.description.lower() for k in ['database', 'mongo', 'sql', 'prisma'])]
    api_egress = [p for p in report.egress_points if any(
        k in p.description.lower() for k in ['http', 'api', 'fetch', 'request'])]
    external_egress = [p for p in report.egress_points if any(
        k in p.description.lower() for k in ['email', 'sms', 'payment', 'stripe', 'openai'])]

    if db_egress and persona == "internal":
        sections.append(DynamicSection(
            id="data-persistence-layer",
            title=_generate_title(PrimitiveType.EGRESS, db_egress, "database"),
            description=_build_egress_description(db_egress, "database"),
            primitives=[p.name for p in db_egress[:5]],
            subsections=[
                "Transaction Boundaries & Atomicity",
                "Connection Pooling & Management",
                "Query Patterns & Optimization",
                "Migration & Schema Evolution",
            ],
            priority=85,
            persona=persona,
        ))

    if api_egress and persona == "internal":
        sections.append(DynamicSection(
            id="external-api-integration",
            title="Orchestrating External API Calls & Circuit Breakers",
            description=_build_egress_description(api_egress, "api"),
            primitives=[p.name for p in api_egress[:5]],
            subsections=[
                "API Client Implementations",
                "Retry & Backoff Strategies",
                "Timeout Configuration",
                "Error Handling & Fallbacks",
            ],
            priority=70,
            persona=persona,
        ))

    if external_egress:
        title = "Integrating External Services & Third-Party SDKs"
        sections.append(DynamicSection(
            id="external-service-integration",
            title=title,
            description=_build_egress_description(external_egress, "external"),
            primitives=[p.name for p in external_egress[:5]],
            subsections=[
                "Service Client Configuration",
                "Authentication with External Services",
                "Rate Limiting & Quotas",
            ],
            priority=65,
            persona=persona,
        ))

    return sections


def _generate_state_sections(report: DiscoveryReport, persona: str) -> List[DynamicSection]:
    """Generate sections for state models."""
    sections = []

    if report.state_models and persona == "internal":
        # Generate entity relationship section
        sections.append(DynamicSection(
            id="entity-state-management",
            title=_generate_title(PrimitiveType.STATE,
                                  report.state_models, "model"),
            description="Document the data models, their relationships, and state transitions.",
            primitives=[p.name for p in report.state_models[:8]],
            subsections=[
                "Entity Relationship Diagram",
                "State Transitions & Lifecycle",
                "Validation Rules & Constraints",
                "Serialization & Deserialization",
            ],
            priority=80,
            persona=persona,
        ))

    return sections


def _generate_orchestrator_sections(report: DiscoveryReport, persona: str) -> List[DynamicSection]:
    """Generate sections for orchestrators."""
    sections = []

    if report.orchestrators and persona == "internal":
        top_orchestrators = report.orchestrators[:5]

        sections.append(DynamicSection(
            id="system-orchestration-core",
            title=_generate_title(PrimitiveType.ORCHESTRATOR,
                                  top_orchestrators, "core"),
            description="Document the high-centrality files that coordinate system flow.",
            primitives=[p.name for p in top_orchestrators],
            subsections=[
                "Dependency Flow & Import Graph",
                "Initialization Sequence",
                "Cross-Module Coordination",
                "Critical Path Analysis",
            ],
            priority=75,
            persona=persona,
        ))

    return sections


def _generate_journey_sections(report: DiscoveryReport, persona: str) -> List[DynamicSection]:
    """Generate sections for data journeys."""
    sections = []

    if report.data_journeys and persona == "internal":
        # Create a single section for the most important journey
        journey = report.data_journeys[0]

        sections.append(DynamicSection(
            id="data-flow-journey",
            title=f"Tracing {journey.data_type} Lifecycle & Transformation Pipeline",
            description=f"Follow {journey.data_type} from entry through transformation to persistence.",
            primitives=[journey.ingress_point] +
            journey.transformation_points[:3],
            subsections=[
                "Ingress & Input Validation",
                "Transformation & Processing Stages",
                "Persistence & Storage",
                "Egress & Output Generation",
            ],
            priority=70,
            persona=persona,
        ))

    return sections


def _generate_constraints_section(report: DiscoveryReport) -> DynamicSection:
    """Generate section for constraints and brittle points."""
    return DynamicSection(
        id="system-constraints-caveats",
        title="Documenting System Constraints & Known Limitations",
        description="Critical constraints, limitations, and brittle code that maintainers must know.",
        primitives=[],
        subsections=[
            "Known Limitations & Workarounds",
            "Brittle Code & Edge Cases",
            "Performance Constraints",
            "Deprecation Notices",
        ],
        priority=50,
        persona="internal",
    )


def _generate_title(
    primitive_type: PrimitiveType,
    primitives: List[DiscoveredPrimitive],
    domain_hint: str
) -> str:
    """
    Generate an intent-based title using the formula:
    [Action Verb] + [Domain of Responsibility] + [System Impact]
    """
    import random

    # Get action verb
    verbs = ACTION_VERBS.get(primitive_type, ["Managing"])
    verb = random.choice(verbs)

    # Get domain from primitives or hint
    domain = _infer_domain(primitives, domain_hint)

    # Get impact phrase
    impacts = IMPACT_PHRASES.get(primitive_type, ["& System Operations"])
    impact = random.choice(impacts)

    return f"{verb} {domain} {impact}"


def _infer_domain(primitives: List[DiscoveredPrimitive], hint: str) -> str:
    """Infer the domain from primitives."""
    # Check primitive names and file paths for domain keywords
    all_text = " ".join([
        p.name.lower() + " " + p.file_path.lower() + " " + p.description.lower()
        for p in primitives
    ])

    # Match against domain phrases
    for keyword, domain in DOMAIN_PHRASES.items():
        if keyword in all_text or keyword == hint:
            return domain

    # Use hint if available
    if hint and hint in DOMAIN_PHRASES:
        return DOMAIN_PHRASES[hint]

    return "System Operations"


def _build_ingress_description(primitives: List[DiscoveredPrimitive]) -> str:
    """Build description for ingress section."""
    if not primitives:
        return "Document the entry points where data enters the system."

    entry_types = set(p.description for p in primitives[:5])
    return f"Document the entry points: {', '.join(entry_types)}. Trace request flow from ingress to handler."


def _build_egress_description(primitives: List[DiscoveredPrimitive], egress_type: str) -> str:
    """Build description for egress section."""
    if egress_type == "database":
        return "Document database operations, transaction boundaries, connection management, and query patterns."
    elif egress_type == "api":
        return "Document external API calls, client implementations, retry logic, and circuit breaker patterns."
    else:
        return "Document external service integrations, SDK usage, and side effect management."


def format_section_for_prompt(section: DynamicSection) -> str:
    """Format a section for the LLM prompt."""
    subsections_text = "\n".join([f"  - {sub}" for sub in section.subsections])
    primitives_text = ", ".join(
        section.primitives[:5]) if section.primitives else "Discovered from analysis"

    return f"""
## {section.title}

**Section ID:** {section.id}
**Priority:** {section.priority}/100
**Description:** {section.description}
**Related Components:** {primitives_text}

**Required Subsections:**
{subsections_text}

---
""".strip()
