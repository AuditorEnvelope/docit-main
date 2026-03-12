"""
Archetype Detection System - Staff Engineer Documentation Framework

Detects repository archetype based on tech stack signals to generate
high-fidelity, meaningful documentation sections.

Archetypes:
- BACKEND_API: FastAPI, Django, Express, Go services
- FRONTEND_UI: React, Vue, Angular, Next.js
- MONOREPO: turbo.json, apps/, packages/
- DEVOPS_INFRA: Dockerfile, terraform, k8s manifests
- LIBRARY: npm package, PyPI module
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum


class Archetype(str, Enum):
    """Repository archetypes for meaningful documentation."""
    BACKEND_API = "backend_api"
    FRONTEND_UI = "frontend_ui"
    MONOREPO = "monorepo"
    DEVOPS_INFRA = "devops_infra"
    LIBRARY = "library"
    FULLSTACK = "fullstack"
    UNKNOWN = "unknown"


@dataclass
class ArchetypeSection:
    """
    A meaningful documentation section for a specific archetype.

    NO generic titles like "Overview" or "Architecture" allowed.
    """
    id: str
    title: str
    description: str
    required: bool = True
    subsections: List[str] = field(default_factory=list)


# ============================================================================
# ARCHETYPE-SPECIFIC MEANINGFUL SECTIONS
# ============================================================================

BACKEND_API_SECTIONS = {
    "internal": [
        ArchetypeSection(
            id="request_lifecycle",
            title="Request-Response Lifecycle & Middleware Chain",
            description="Trace a request from ingress to response. Document middleware order, auth checks, rate limiting, request validation, response serialization.",
            subsections=[
                "Entry Points & Route Registration",
                "Middleware Stack Execution Order",
                "Request Validation & Schema Enforcement",
                "Response Serialization & Error Formatting",
            ]
        ),
        ArchetypeSection(
            id="data_persistence",
            title="Data Persistence & Entity State Machine",
            description="Document database transactions, ORM patterns, migration strategy, connection pooling, query optimization, and state transitions.",
            subsections=[
                "Entity Relationship Map",
                "Transaction Boundaries & Atomicity",
                "Migration Strategy & Schema Evolution",
                "Query Patterns & N+1 Prevention",
            ]
        ),
        ArchetypeSection(
            id="security_perimeter",
            title="Security Perimeter & Access Control",
            description="Document authentication flows, authorization rules, token lifecycle, secret management, and security boundaries.",
            subsections=[
                "Authentication Flow & Token Lifecycle",
                "Authorization Rules & Permission Model",
                "Secret Management & Rotation",
                "Input Sanitization & Injection Prevention",
            ]
        ),
        ArchetypeSection(
            id="service_integration",
            title="External Service Integration & Circuit Breakers",
            description="Document third-party API calls, retry logic, circuit breaker patterns, timeout configurations, and fallback strategies.",
            subsections=[
                "External API Client Implementations",
                "Retry & Backoff Strategies",
                "Circuit Breaker State Machine",
                "Fallback & Degradation Modes",
            ]
        ),
        ArchetypeSection(
            id="error_taxonomy",
            title="Error Taxonomy & Exception Handling",
            description="Document error codes, exception hierarchy, error propagation, logging patterns, and recovery procedures.",
            subsections=[
                "Error Code Registry",
                "Exception Hierarchy & Handling",
                "Error Propagation & Logging",
                "Recovery & Retry Procedures",
            ]
        ),
    ],
    "public": [
        ArchetypeSection(
            id="quickstart",
            title="60-Second Quickstart",
            description="Get a working API call in under 60 seconds. Minimal setup, immediate value.",
            subsections=[
                "Authentication Setup",
                "First API Call",
                "Response Interpretation",
            ]
        ),
        ArchetypeSection(
            id="api_reference",
            title="API Reference & Endpoint Catalog",
            description="Complete endpoint documentation with request/response schemas, status codes, and examples.",
            subsections=[
                "Endpoint Catalog by Resource",
                "Request/Response Schemas",
                "Status Codes & Error Responses",
            ]
        ),
        ArchetypeSection(
            id="integration_patterns",
            title="Integration Patterns & SDKs",
            description="How to integrate this API into your application. Webhooks, callbacks, polling strategies.",
            subsections=[
                "Webhook Configuration",
                "Idempotency & Retry Handling",
                "Rate Limiting & Quotas",
            ]
        ),
    ]
}


FRONTEND_UI_SECTIONS = {
    "internal": [
        ArchetypeSection(
            id="component_hierarchy",
            title="Component Hierarchy & Atomic Design Breakdown",
            description="Document the component tree from atoms to pages. Show prop drilling paths, composition patterns, and render boundaries.",
            subsections=[
                "Atomic Design Layers (Atoms → Molecules → Organisms → Templates → Pages)",
                "Component Dependency Graph",
                "Prop Interface Contracts",
                "Render Boundary Optimization",
            ]
        ),
        ArchetypeSection(
            id="state_management",
            title="State Management & Data Hydration",
            description="Document global state architecture, local state patterns, server state caching, and hydration strategies.",
            subsections=[
                "Global State Architecture (Redux/Zustand/Context)",
                "Server State & Cache Invalidation",
                "Optimistic Updates & Rollback",
                "Hydration & SSR State Transfer",
            ]
        ),
        ArchetypeSection(
            id="user_journey",
            title="User Journey Flows & Route Guards",
            description="Document navigation flows, route protection, deep linking, and state persistence across navigation.",
            subsections=[
                "Route Tree & Navigation Graph",
                "Authentication Guards & Redirects",
                "Deep Link Resolution",
                "Navigation State Persistence",
            ]
        ),
        ArchetypeSection(
            id="api_integration",
            title="API Integration Layer & Error Boundaries",
            description="Document API client setup, request interceptors, response transformers, and error boundary placement.",
            subsections=[
                "API Client Configuration",
                "Request/Response Interceptors",
                "Error Boundary Placement & Recovery",
                "Loading State Management",
            ]
        ),
        ArchetypeSection(
            id="build_pipeline",
            title="Build Pipeline & Bundle Analysis",
            description="Document build configuration, code splitting strategy, lazy loading, and bundle optimization.",
            subsections=[
                "Build Configuration & Environment Variables",
                "Code Splitting & Lazy Loading",
                "Bundle Size Analysis & Optimization",
                "Asset Pipeline & CDN Strategy",
            ]
        ),
    ],
    "public": [
        ArchetypeSection(
            id="quickstart",
            title="60-Second Setup",
            description="Get the app running locally in under 60 seconds.",
            subsections=[
                "Prerequisites",
                "Installation",
                "Running the App",
            ]
        ),
        ArchetypeSection(
            id="component_usage",
            title="Component Library & Usage Guide",
            description="How to use the provided components in your own code.",
            subsections=[
                "Available Components",
                "Props & Configuration",
                "Theming & Customization",
            ]
        ),
        ArchetypeSection(
            id="configuration",
            title="Configuration & Environment Variables",
            description="All configuration options and environment variables.",
            subsections=[
                "Required Environment Variables",
                "Optional Configuration",
                "Feature Flags",
            ]
        ),
    ]
}


MONOREPO_SECTIONS = {
    "internal": [
        ArchetypeSection(
            id="workspace_topology",
            title="Global Workspace Topology & Package Map",
            description="Document the monorepo structure, workspace configuration, and package organization strategy.",
            subsections=[
                "Workspace Root Configuration",
                "Package Catalog & Purposes",
                "Shared Configuration Inheritance",
                "Workspace-Level Scripts & Tasks",
            ]
        ),
        ArchetypeSection(
            id="dependency_graph",
            title="Inter-Package Dependency Graph & Version Constraints",
            description="Document how packages depend on each other, version constraints, and circular dependency prevention.",
            subsections=[
                "Package Dependency Matrix",
                "Version Constraint Strategy",
                "Circular Dependency Prevention",
                "Peer Dependency Management",
            ]
        ),
        ArchetypeSection(
            id="build_orchestration",
            title="Build Order & Task Orchestration",
            description="Document build pipeline, task caching, parallel execution, and CI/CD integration.",
            subsections=[
                "Build Order & Topological Sort",
                "Task Caching & Invalidation",
                "Parallel Execution Strategy",
                "CI/CD Pipeline Integration",
            ]
        ),
        ArchetypeSection(
            id="cross_package_patterns",
            title="Cross-Package Communication & Shared Contracts",
            description="Document how packages communicate, shared types, and API contracts between packages.",
            subsections=[
                "Shared Type Definitions",
                "Inter-Package API Contracts",
                "Event Bus & Message Passing",
                "Testing Across Package Boundaries",
            ]
        ),
    ],
    "public": [
        ArchetypeSection(
            id="quickstart",
            title="Monorepo Quickstart",
            description="Get the entire monorepo running locally.",
            subsections=[
                "Prerequisites",
                "Installation",
                "Running All Services",
            ]
        ),
        ArchetypeSection(
            id="package_guide",
            title="Package-by-Package Guide",
            description="Individual documentation for each package/app.",
            subsections=[
                "Apps Directory",
                "Packages Directory",
                "Shared Libraries",
            ]
        ),
    ]
}


DEVOPS_INFRA_SECTIONS = {
    "internal": [
        ArchetypeSection(
            id="deployment_topology",
            title="Deployment Topology & Service Mesh",
            description="Document infrastructure architecture, service discovery, load balancing, and network topology.",
            subsections=[
                "Infrastructure Architecture Diagram",
                "Service Discovery & Registration",
                "Load Balancing & Traffic Routing",
                "Network Policies & Segmentation",
            ]
        ),
        ArchetypeSection(
            id="secret_management",
            title="Secret Management & Credential Rotation",
            description="Document secret storage, injection, rotation policies, and access audit.",
            subsections=[
                "Secret Storage Backend",
                "Injection Mechanism",
                "Rotation Policy & Automation",
                "Access Audit & Logging",
            ]
        ),
        ArchetypeSection(
            id="observability",
            title="Observability Stack & Health Monitoring",
            description="Document logging, metrics, tracing, alerting, and health check endpoints.",
            subsections=[
                "Logging Pipeline & Aggregation",
                "Metrics Collection & Dashboards",
                "Distributed Tracing",
                "Alerting Rules & Escalation",
            ]
        ),
        ArchetypeSection(
            id="disaster_recovery",
            title="Disaster Recovery & Failover Procedures",
            description="Document backup strategy, failover procedures, and recovery time objectives.",
            subsections=[
                "Backup Strategy & Retention",
                "Failover Procedures",
                "Recovery Time Objectives (RTO/RPO)",
                "Incident Response Runbooks",
            ]
        ),
    ],
    "public": [
        ArchetypeSection(
            id="quickstart",
            title="Deployment Quickstart",
            description="Deploy the application in your environment.",
            subsections=[
                "Prerequisites",
                "Configuration",
                "Deployment Steps",
            ]
        ),
        ArchetypeSection(
            id="configuration",
            title="Infrastructure Configuration",
            description="All configuration options for deployment.",
            subsections=[
                "Environment Variables",
                "Secrets Configuration",
                "Resource Requirements",
            ]
        ),
    ]
}


# ============================================================================
# FULLSTACK SECTIONS (Backend + Frontend in same repo)
# ============================================================================

FULLSTACK_SECTIONS = {
    "internal": [
        ArchetypeSection(
            id="system_architecture",
            title="Full-Stack System Architecture & Data Flow",
            description="Document the complete system architecture showing how backend and frontend interact. Include API contracts, data flow, and integration points.",
            subsections=[
                "System Architecture Diagram",
                "Backend-Frontend Integration Points",
                "API Contract & Data Flow",
                "Shared Types & Contracts",
            ]
        ),
        ArchetypeSection(
            id="backend_service",
            title="Backend Service Layer & API Implementation",
            description="Document the backend service architecture, API endpoints, middleware, and data persistence.",
            subsections=[
                "Service Architecture & Module Organization",
                "API Endpoints & Route Handlers",
                "Middleware Chain & Request Processing",
                "Database Models & Persistence Layer",
            ]
        ),
        ArchetypeSection(
            id="frontend_components",
            title="Frontend Component Architecture & State",
            description="Document the frontend component hierarchy, state management, and UI patterns.",
            subsections=[
                "Component Hierarchy & Organization",
                "State Management & Data Fetching",
                "UI Patterns & Design System",
                "Client-Side Routing & Navigation",
            ]
        ),
        ArchetypeSection(
            id="api_integration",
            title="API Integration & Client-Server Communication",
            description="Document how frontend communicates with backend, including authentication, error handling, and data transformation.",
            subsections=[
                "API Client Configuration",
                "Authentication Flow (Frontend ↔ Backend)",
                "Request/Response Transformation",
                "Error Handling & Recovery",
            ]
        ),
        ArchetypeSection(
            id="development_workflow",
            title="Development Workflow & Local Setup",
            description="Document how to run both backend and frontend locally, including environment setup and development scripts.",
            subsections=[
                "Prerequisites & Environment Setup",
                "Running Backend Locally",
                "Running Frontend Locally",
                "Full-Stack Development Mode",
            ]
        ),
    ],
    "public": [
        ArchetypeSection(
            id="quickstart",
            title="Full-Stack Quickstart",
            description="Get the complete application running locally.",
            subsections=[
                "Prerequisites",
                "Backend Setup",
                "Frontend Setup",
                "Running the Application",
            ]
        ),
        ArchetypeSection(
            id="api_reference",
            title="API Reference",
            description="Backend API documentation for integration.",
            subsections=[
                "Authentication",
                "Endpoints",
                "Data Models",
            ]
        ),
        ArchetypeSection(
            id="configuration",
            title="Configuration Guide",
            description="Configuration options for both backend and frontend.",
            subsections=[
                "Backend Configuration",
                "Frontend Configuration",
                "Environment Variables",
            ]
        ),
    ]
}


# ============================================================================
# ARCHETYPE DETECTION LOGIC
# ============================================================================

def detect_archetype(analysis: Dict[str, Any]) -> Archetype:
    """
    Detect repository archetype based on tech stack signals.

    Uses adaptive detection - works with ANY repo structure.
    Prioritizes subproject info from comprehensive analysis.

    Returns the most specific archetype match.
    """
    languages = set(analysis.get("languages", []))
    frameworks = set(f.lower() for f in analysis.get("frameworks", []))
    directories = " ".join(analysis.get("main_directories", []))
    dependencies = analysis.get("dependencies", {})
    dep_names = set(d.lower() for d in dependencies.keys())

    # PRIORITY CHECK: Use subprojects from adaptive repo structure detection
    # This is the most reliable indicator - it actually analyzed each folder
    subprojects = analysis.get("subprojects", {})
    detected_structure = analysis.get("repo_structure_type", "")

    if subprojects:
        # Count project types from adaptive detection
        types_found = set()
        for sp in subprojects.values():
            sp_type = sp.get("subproject_type") or sp.get("type", "")
            if sp_type:
                types_found.add(sp_type.lower())

        has_backend = any(t in ["backend", "api", "service"]
                          for t in types_found)
        has_frontend = any(t in ["frontend", "web", "ui", "app"]
                           for t in types_found)
        has_mobile = any(t in ["mobile"] for t in types_found)
        has_devops = any(t in ["devops", "infrastructure"]
                         for t in types_found)

        if has_backend and has_frontend:
            print(f"   🎯 Detected FULLSTACK from subprojects: {types_found}")
            return Archetype.FULLSTACK
        elif len(subprojects) >= 2:
            print(
                f"   🎯 Detected MONOREPO with {len(subprojects)} projects: {types_found}")
            return Archetype.MONOREPO
        elif has_devops:
            return Archetype.DEVOPS_INFRA
        elif has_frontend:
            return Archetype.FRONTEND_UI
        elif has_backend:
            return Archetype.BACKEND_API

    # Check for REAL monorepo signals (explicit tooling)
    monorepo_signals = [
        "turbo.json" in directories,
        "lerna.json" in directories,
        "pnpm-workspace.yaml" in directories,
        "/apps/" in directories and directories.count("/apps/") >= 1,
        "/packages/" in directories and directories.count("/packages/") >= 1,
        "workspaces" in str(dependencies) and len(subprojects) >= 2,
    ]
    if sum(monorepo_signals) >= 2:
        return Archetype.MONOREPO

    # Check for DevOps/Infra - need ACTUAL infra files, not just a mention
    devops_signals = [
        "dockerfile" in directories.lower() or "Dockerfile" in str(
            analysis.get("source_files", [])),
        ".tf" in directories or "terraform" in directories.lower(),
        "k8s" in directories.lower() or "kubernetes" in directories.lower(),
        "helm" in directories.lower(),
        ".github/workflows" in directories and analysis.get(
            "deployment_tech", []),
    ]
    if sum(devops_signals) >= 2:
        return Archetype.DEVOPS_INFRA

    # Check for Backend API
    backend_frameworks = {"fastapi", "django", "flask",
                          "express", "nestjs", "gin", "echo", "fiber"}
    backend_signals = [
        bool(backend_frameworks & frameworks),
        bool(backend_frameworks & dep_names),
        "py" in languages and ("app" in directories or "api" in directories),
        "sqlalchemy" in dep_names or "prisma" in dep_names or "typeorm" in dep_names,
        "alembic" in dep_names or "migrate" in directories,
    ]

    # Check for Frontend UI
    frontend_frameworks = {"react", "vue", "angular",
                           "svelte", "nextjs", "nuxt", "gatsby"}
    frontend_signals = [
        bool(frontend_frameworks & frameworks),
        bool(frontend_frameworks & dep_names),
        "react" in dep_names or "react-dom" in dep_names,
        "next" in dep_names,
        "components" in directories or bool(
            analysis.get("component_files", [])),
        ("pages" in directories or "app" in directories) and (
            "tsx" in languages or "jsx" in languages),
    ]

    backend_score = sum(backend_signals)
    frontend_score = sum(frontend_signals)

    # Fullstack detection - needs STRONG signals for BOTH
    if backend_score >= 3 and frontend_score >= 3:
        return Archetype.FULLSTACK

    # Frontend detection - prioritize if React/Vue/Angular detected
    if frontend_score > backend_score and frontend_score >= 2:
        return Archetype.FRONTEND_UI

    if backend_score >= 2:
        return Archetype.BACKEND_API

    # Check for Library
    library_signals = [
        "setup.py" in directories or "pyproject.toml" in directories,
        analysis.get("file_count", 0) < 50,
        "lib" in directories or "src" in directories,
    ]
    if sum(library_signals) >= 2:
        return Archetype.LIBRARY

    # Default to frontend if React-like signals exist
    if frontend_score >= 1:
        return Archetype.FRONTEND_UI

    return Archetype.UNKNOWN


def get_archetype_sections(archetype: Archetype, persona: str) -> List[ArchetypeSection]:
    """
    Get meaningful sections for an archetype and persona.

    Returns sections that pass the "So What?" test - every section
    helps an engineer debugging at 2 AM.
    """
    section_map = {
        Archetype.BACKEND_API: BACKEND_API_SECTIONS,
        Archetype.FRONTEND_UI: FRONTEND_UI_SECTIONS,
        Archetype.MONOREPO: MONOREPO_SECTIONS,
        Archetype.DEVOPS_INFRA: DEVOPS_INFRA_SECTIONS,
        Archetype.FULLSTACK: FULLSTACK_SECTIONS,  # Dedicated fullstack sections
        Archetype.LIBRARY: BACKEND_API_SECTIONS,  # Libraries follow similar patterns
        Archetype.UNKNOWN: BACKEND_API_SECTIONS,  # Default to backend patterns
    }

    persona_key = "internal" if persona == "internal" else "public"
    sections = section_map.get(archetype, BACKEND_API_SECTIONS)

    return sections.get(persona_key, sections.get("internal", []))


def get_archetype_context(archetype: Archetype) -> str:
    """
    Get archetype-specific context for the LLM prompt.
    """
    contexts = {
        Archetype.BACKEND_API: """
THIS IS A BACKEND/API SERVICE.

Your documentation must answer these questions for a 2 AM debugging engineer:
1. REQUEST LIFECYCLE: Where does a request enter? What middleware touches it? How is it validated?
2. DATA FLOW: Where does data get persisted? What transactions wrap operations?
3. SECURITY: How is authentication performed? What authorizes each endpoint?
4. FAILURES: What happens when external services fail? What are the fallback paths?

DO NOT write generic descriptions. Write SPECIFIC technical details.""",

        Archetype.FRONTEND_UI: """
THIS IS A FRONTEND/UI APPLICATION.

Your documentation must answer these questions for a 2 AM debugging engineer:
1. COMPONENT TREE: What renders what? Where are the composition boundaries?
2. STATE: Where is state stored? How does it flow between components?
3. DATA FETCHING: How does data get from the API to the UI? What caches it?
4. NAVIGATION: How do routes map to components? What guards protect routes?

DO NOT write generic descriptions. Write SPECIFIC technical details about THIS codebase.""",

        Archetype.MONOREPO: """
THIS IS A MONOREPO with multiple packages/apps.

Your documentation must answer these questions for a 2 AM debugging engineer:
1. TOPOLOGY: What packages exist? What does each one do?
2. DEPENDENCIES: How do packages depend on each other? What's the build order?
3. COMMUNICATION: How do packages share code and types?
4. BUILD: How does the build pipeline orchestrate across packages?

DO NOT flatten the monorepo. Document EACH package's purpose and its relationships.""",

        Archetype.DEVOPS_INFRA: """
THIS IS A DEVOPS/INFRASTRUCTURE CODEBASE.

Your documentation must answer these questions for a 2 AM incident responder:
1. TOPOLOGY: What services run where? How do they discover each other?
2. SECRETS: Where are credentials stored? How are they injected?
3. MONITORING: What logs/metrics/traces exist? Where are the dashboards?
4. RECOVERY: What's the disaster recovery procedure? What are the RTOs?

DO NOT write generic cloud descriptions. Write SPECIFIC runbook-quality documentation.""",

        Archetype.FULLSTACK: """
THIS IS A FULLSTACK APPLICATION with BOTH backend and frontend in the same repository.

Your documentation must cover BOTH parts comprehensively:

BACKEND:
1. SERVICE LAYER: What are the API endpoints? How is the service organized?
2. DATA FLOW: Where does data get persisted? What database/ORM is used?
3. AUTHENTICATION: How does the backend authenticate requests from the frontend?

FRONTEND:
4. COMPONENT TREE: What components exist? How are they organized?
5. STATE MANAGEMENT: Where is state stored? How does it sync with the backend?
6. API INTEGRATION: How does the frontend call the backend APIs?

INTEGRATION:
7. API CONTRACT: What is the interface between frontend and backend?
8. DEVELOPMENT: How do you run both backend and frontend locally?

DO NOT focus on just one side. Document BOTH backend AND frontend equally.""",
    }

    return contexts.get(archetype, contexts[Archetype.BACKEND_API])


def slugify_section_title(title: str) -> str:
    """
    Convert a section title to a URL-safe folder name.

    "Request-Response Lifecycle & Middleware Chain" -> "request-response-lifecycle"
    "Component Hierarchy & Atomic Design" -> "component-hierarchy"
    """
    import re
    # Take first part before & or :
    title = title.split("&")[0].split(":")[0].strip()
    # Lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
    # Remove leading/trailing hyphens and collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug).strip('-')
    # Limit length
    return slug[:50]


def filter_sections_by_evidence(
    sections: List[ArchetypeSection],
    analysis: Dict[str, Any]
) -> List[ArchetypeSection]:
    """
    Filter sections based on actual evidence in the codebase.

    CRITICAL: Do NOT generate sections for features that don't exist.
    Example: Don't generate "Deployment Topology" if there's no Dockerfile, terraform, k8s.

    Returns only sections that have supporting evidence.
    """
    directories = " ".join(analysis.get("main_directories", [])).lower()
    source_files = " ".join(analysis.get("source_files", [])).lower()
    dependencies = analysis.get("dependencies", {})
    dep_names = set(d.lower() for d in dependencies.keys())
    deployment_tech = analysis.get("deployment_tech", [])

    filtered = []

    for section in sections:
        section_id = section.id.lower()

        # Evidence rules for each section type
        if "deployment" in section_id or "build_order" in section_id:
            # Only include if there's ACTUAL deployment infrastructure
            has_deployment_evidence = (
                "dockerfile" in directories or "dockerfile" in source_files or
                "terraform" in directories or ".tf" in source_files or
                "k8s" in directories or "kubernetes" in directories or
                "helm" in directories or
                ".github/workflows" in directories or
                "docker-compose" in source_files or
                "vercel.json" in source_files or
                "netlify.toml" in source_files or
                bool(deployment_tech)
            )
            if not has_deployment_evidence:
                continue

        if "database" in section_id or "persistence" in section_id or "data_model" in section_id:
            # Only include if there's database/ORM evidence
            has_db_evidence = (
                "sqlalchemy" in dep_names or "prisma" in dep_names or
                "typeorm" in dep_names or "sequelize" in dep_names or
                "mongoose" in dep_names or "django" in dep_names or
                "alembic" in dep_names or "migrations" in directories or
                analysis.get("database_tech", [])
            )
            if not has_db_evidence:
                continue

        if "auth" in section_id or "security" in section_id:
            # Only include if there's auth evidence
            has_auth_evidence = (
                "jwt" in dep_names or "passport" in dep_names or
                "auth" in directories or "oauth" in dep_names or
                "bcrypt" in dep_names or "argon2" in dep_names or
                "session" in dep_names or "cookie" in directories
            )
            if not has_auth_evidence:
                continue

        if "test" in section_id:
            # Only include if there's testing evidence
            has_test_evidence = (
                "jest" in dep_names or "pytest" in dep_names or
                "mocha" in dep_names or "vitest" in dep_names or
                "test" in directories or "__tests__" in directories
            )
            if not has_test_evidence:
                continue

        if "workspace" in section_id or "cross_package" in section_id or "dependency_graph" in section_id:
            # Only include for REAL monorepos
            subprojects = analysis.get("subprojects", {})
            if len(subprojects) < 2:
                continue

        # Section passed all evidence checks
        filtered.append(section)

    return filtered


def get_evidence_based_sections(
    archetype: Archetype,
    persona: str,
    analysis: Dict[str, Any]
) -> List[ArchetypeSection]:
    """
    Get sections that are BOTH appropriate for the archetype AND have supporting evidence.

    This is the main entry point for getting sections - combines archetype detection
    with evidence filtering.
    """
    # Get archetype-appropriate sections
    sections = get_archetype_sections(archetype, persona)

    # Filter to only sections with evidence
    return filter_sections_by_evidence(sections, analysis)
