"""
Discovery-Based Documentation Integration

This module integrates the discovery scanner with the documentation generation pipeline.
It replaces template-based documentation with autonomous, discovery-driven generation.
"""

import json
from pathlib import Path
from typing import Dict, Tuple, Optional, List

from app.services.documentation.discovery_scanner import (
    discover_repository,
    DiscoveryReport,
    DiscoveredPrimitive,
    PrimitiveType,
)
from app.services.documentation.dynamic_sections import (
    generate_sections_from_discovery,
    format_section_for_prompt,
    DynamicSection,
)
from app.services.documentation.archetype_detector import (
    detect_archetype,
    get_archetype_sections,
    get_archetype_context,
    Archetype,
    ArchetypeSection,
)


def run_discovery_and_generate_sections(
    repo_dir: Path,
    analysis: Dict,
    persona: str
) -> Tuple[DiscoveryReport, List[DynamicSection], Archetype]:
    """
    Run the discovery scan and generate dynamic sections.

    Returns:
        - DiscoveryReport: Full scan results
        - List[DynamicSection]: Generated sections
        - Archetype: Detected archetype (fallback)
    """
    # Run discovery scan
    discovery_report = discover_repository(repo_dir, analysis)

    # Generate dynamic sections from discovery
    dynamic_sections = generate_sections_from_discovery(
        discovery_report, persona)

    # Fallback to archetype if no sections discovered
    archetype = detect_archetype(analysis)

    if not dynamic_sections:
        # Convert archetype sections to dynamic sections
        archetype_sections = get_archetype_sections(archetype, persona)
        dynamic_sections = [
            DynamicSection(
                id=s.id,
                title=s.title,
                description=s.description,
                primitives=[],
                subsections=s.subsections,
                priority=70,
                persona=persona,
            )
            for s in archetype_sections
        ]

    return discovery_report, dynamic_sections, archetype


def build_discovery_prompt(
    project_name: str,
    analysis: dict,
    recent_changes: dict,
    persona: str,
    archetype: Archetype,
    discovery_report: DiscoveryReport,
    dynamic_sections: List[DynamicSection],
) -> str:
    """
    Build a discovery-based prompt that treats the codebase as a unique organism.

    NO templates. NO assumptions. Pure discovery-driven documentation.
    """
    # Determine display name
    package_name = analysis.get("package_name", "")
    analysis_project_name = analysis.get("project_name", "")

    clean_project_name = project_name
    if "/" in project_name:
        clean_project_name = project_name.split("/")[-1]

    if package_name and not package_name.startswith("docai") and len(package_name) > 2:
        display_name = package_name
    elif clean_project_name and not clean_project_name.startswith("docai"):
        display_name = clean_project_name
    elif analysis_project_name and not analysis_project_name.startswith("docai"):
        display_name = analysis_project_name
    else:
        display_name = project_name

    # Build discovery context
    discovery_context = build_discovery_context(discovery_report)

    # Build dynamic section specifications
    section_specs = "\n\n".join([
        format_section_for_prompt(s) for s in dynamic_sections
    ])

    # Build output format
    output_format = build_output_format_from_dynamic(dynamic_sections)

    # Build evidence context
    evidence_context = build_evidence_context(analysis)

    # Get archetype context for additional flavor
    archetype_context = get_archetype_context(archetype)

    print(f"🤖 Building Discovery Prompt for: {display_name}")
    print(f"   Persona: {persona}")
    print(f"   Sections: {len(dynamic_sections)}")

    prompt = f"""You are a Principal Systems Architect performing a deep-tissue analysis of a codebase.

═══════════════════════════════════════════════════════════════════════════════════════════
🎯 THE MASTER PROMPT: AUTONOMOUS SYSTEM DOCUMENTATION
═══════════════════════════════════════════════════════════════════════════════════════════

You do NOT use templates. You do NOT assume the repo type. 
You treat this codebase as a UNIQUE BIOLOGICAL ORGANISM.

Your task: Generate First-Principles Documentation that reveals the SOUL of this code.

═══════════════════════════════════════════════════════════════════════════════════════════
📋 PROJECT CONTEXT
═══════════════════════════════════════════════════════════════════════════════════════════
Repository: {display_name}
Persona: {persona.upper()} {"(Surgeon Manual - Document the guts)" if persona == "internal" else "(Owner Manual - Document the surface)"}
Archetype: {archetype.value.upper()}

{archetype_context}

═══════════════════════════════════════════════════════════════════════════════════════════
🔭 DISCOVERY SCAN RESULTS
═══════════════════════════════════════════════════════════════════════════════════════════
{discovery_context}

═══════════════════════════════════════════════════════════════════════════════════════════
⚖️ EVIDENCE-BASED LOGIC (NO HALLUCINATIONS)
═══════════════════════════════════════════════════════════════════════════════════════════
EXTRACTION OVER INFERENCE:
- Only state a rationale if you find evidence in: ADR files, commit messages, code comments
- If no rationale is found, describe Observed Behavior with extreme technical precision
- BAD: "Redis is used because it is fast."
- GOOD: "Redis serves as a write-through cache for session data, configured with 10 max connections."

{evidence_context}

═══════════════════════════════════════════════════════════════════════════════════════════
📂 REPOSITORY ANALYSIS (RAW EVIDENCE)
═══════════════════════════════════════════════════════════════════════════════════════════
{json.dumps(analysis, indent=2, default=str)[:15000]}

═══════════════════════════════════════════════════════════════════════════════════════════
📝 DOCUMENTATION SECTIONS (DERIVED FROM DISCOVERY)
═══════════════════════════════════════════════════════════════════════════════════════════
{section_specs}

═══════════════════════════════════════════════════════════════════════════════════════════
📤 OUTPUT FORMAT (EXACT STRUCTURE REQUIRED)
═══════════════════════════════════════════════════════════════════════════════════════════
{output_format}

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 CRITICAL RULES
═══════════════════════════════════════════════════════════════════════════════════════════
1. Generate EXACTLY the sections listed above - no more, no less
2. Use the EXACT section tags provided (<SECTION_ID_START>...<SECTION_ID_END>)
3. ONLY document what actually exists in the codebase
4. NEVER invent technologies, files, or features not in the analysis
5. Use SPECIFIC file names and code patterns from the repository
6. Every section must be DETAILED enough to debug production issues
7. Include code snippets, file paths, and concrete examples

═══════════════════════════════════════════════════════════════════════════════════════════
📊 MERMAID DIAGRAM RULES (STRICT SYNTAX)
═══════════════════════════════════════════════════════════════════════════════════════════
If you include Mermaid diagrams, follow these EXACT syntax rules:

1. NO parentheses anywhere in diagrams:
   BAD: Frontend[React Client (client/)]
   GOOD: Frontend[React Client]

2. NO special characters in labels:
   BAD: A --> |HTTP/HTTPS| B
   GOOD: A --> |HTTP Request| B

═══════════════════════════════════════════════════════════════════════════════════════════
🚫 NAMING RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════════════════
1. NEVER use temp directory names like "docai_manual_xxx" in documentation
2. Use the ACTUAL project name: "{display_name}"
3. The project name is "{display_name}" - use this throughout the documentation

═══════════════════════════════════════════════════════════════════════════════════════════
⚡ THE "SO WHAT?" EXECUTION RULES
═══════════════════════════════════════════════════════════════════════════════════════════
- NO Summaries: Do not tell me what a file is. Tell me what it DOES to the rest of the system.
- Trace the Data: Pick the most complex data object and document its entire journey.
- Dependency Rationale: Identify exactly which functions are imported and what part of the State they manage.

═══════════════════════════════════════════════════════════════════════════════════════════
🚫 THE FORBIDDEN BEHAVIORS
═══════════════════════════════════════════════════════════════════════════════════════════
- NO "This folder contains..." - Explain the ORCHESTRATION of the folder instead
- NO Generic Paragraphs - If a section is less than 300 words, find more technical nuance
- NO Template Fallbacks - If the repo is unusual, document its unique patterns
- NO "Overview" or generic titles - Use intent-based titles from the sections above

DO NOT output generic descriptions.
DO NOT invent technologies not present in the codebase.
DO NOT write anything that fails the "So What?" test.
DO NOT use temp directory names - use "{display_name}" as the project name.
"""

    return prompt


def build_discovery_context(report: DiscoveryReport) -> str:
    """Build a human-readable context from discovery report."""
    lines = []

    # Ingress points
    if report.ingress_points:
        lines.append("INGRESS POINTS (Where data enters the system):")
        for p in report.ingress_points[:8]:
            lines.append(f"   - {p.name} in {p.file_path}: {p.description}")

    # Egress points
    if report.egress_points:
        lines.append("\nEGRESS POINTS (Where the system affects the world):")
        for p in report.egress_points[:8]:
            lines.append(f"   - {p.name} in {p.file_path}: {p.description}")

    # State models
    if report.state_models:
        lines.append("\nSTATE MODELS (How the system remembers):")
        for p in report.state_models[:8]:
            lines.append(f"   - {p.name} in {p.file_path}")

    # Orchestrators
    if report.orchestrators:
        lines.append("\nORCHESTRATORS (High-centrality system hearts):")
        for p in report.orchestrators[:5]:
            lines.append(
                f"   - {p.name} (centrality: {p.centrality_score:.2f}): {p.description}")

    # Data journeys
    if report.data_journeys:
        lines.append("\nDATA JOURNEYS (Critical data flows):")
        for j in report.data_journeys[:3]:
            lines.append(f"   - {j.data_type}: {j.journey_description}")

    # Constraints
    if report.constraints:
        lines.append("\nCONSTRAINTS (System limitations):")
        for c in report.constraints[:5]:
            lines.append(f"   - {c[:100]}")

    # Brittle points
    if report.brittle_points:
        lines.append("\nBRITTLE POINTS (Complex or risky code):")
        for b in report.brittle_points[:5]:
            lines.append(f"   - {b}")

    return "\n".join(lines)


def build_output_format_from_dynamic(sections: List[DynamicSection]) -> str:
    """Build output format specification from dynamic sections."""
    lines = ["Generate each section with EXACT tags:"]

    for section in sections:
        lines.append(f"\n<{section.id}_START>")
        lines.append(f"# {section.title}")
        lines.append(f"[Full documentation content for this section]")
        lines.append(f"<{section.id}_END>")

    lines.append("\n\nIMPORTANT: Each section MUST:")
    lines.append("- Be at least 300 words of TECHNICAL DENSITY")
    lines.append("- Include specific file paths and code references")
    lines.append("- Document INTERACTIONS, not just descriptions")
    lines.append("- Trace data flow through the system")

    return "\n".join(lines)


def build_evidence_context(analysis: dict) -> str:
    """Build evidence context from analysis."""
    lines = ["Analysis evidence available:"]

    if analysis.get("frameworks"):
        lines.append(f"- Frameworks: {', '.join(analysis['frameworks'])}")
    if analysis.get("languages"):
        lines.append(f"- Languages: {', '.join(analysis['languages'])}")
    if analysis.get("dependencies"):
        lines.append(
            f"- Dependencies: {len(analysis['dependencies'])} packages")
    if analysis.get("source_files"):
        lines.append(f"- Source files: {len(analysis['source_files'])} files")

    return "\n".join(lines)
