"""
Staff Engineer Documentation Prompt Builder

Generates high-fidelity, high-density technical documentation that serves
as a source of truth for engineers debugging at 2 AM.

Core Philosophy:
- Internal Docs (Surgeon's Manual): The guts - private methods, transactions, race conditions
- Public Docs (Owner's Manual): The surface - entry points, API contracts, quickstarts

Anti-Vague Mandate:
- BANNED: "Overview", "Components", "Architecture", "Workflow"
- REQUIRED: Interaction, Transformation, Persistence, Error Handling
"""

import json
from typing import Dict, Tuple, Optional, List
from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section
from app.services.documentation.planner import DocumentationPlan
from app.services.documentation.archetype_detector import (
    detect_archetype,
    get_archetype_sections,
    get_archetype_context,
    Archetype,
    ArchetypeSection,
)


async def generate_all_docs_in_single_call(
    repo_dir, analysis, recent_changes, persona, plan: Optional[DocumentationPlan] = None, repo_name: str = None
) -> Tuple[Dict[str, str], Dict[str, any]]:
    """
    Generate Staff Engineer quality documentation in a single LLM call.

    This is NOT a summary generator. This is a knowledge engineering system
    that produces documentation dense enough to debug production issues.
    """
    project_name = repo_name or repo_dir.name

    # Detect archetype for meaningful section generation
    archetype = detect_archetype(analysis)
    print(f"🎭 Detected archetype: {archetype.value}")

    # Build Staff Engineer prompt
    prompt = _build_staff_engineer_prompt(
        project_name, analysis, recent_changes, persona, archetype, plan
    )

    rotator = get_rotator()
    llm_result = rotator.generate_with_rotation(prompt)

    if not llm_result:
        return _get_fallback_docs(archetype, persona), _get_empty_token_data()

    # Extract content and token data
    raw = llm_result.content
    token_data = {
        "input_tokens": llm_result.input_tokens,
        "output_tokens": llm_result.output_tokens,
        "model_name": llm_result.model_name,
    }

    # Extract sections based on archetype
    docs = _extract_archetype_sections(raw, archetype, persona)

    # Post-process: Sanitize Mermaid diagrams to prevent parse errors
    docs = _sanitize_mermaid_diagrams(docs)

    return docs, token_data


def _sanitize_mermaid_diagrams(docs: Dict[str, str]) -> Dict[str, str]:
    """
    Post-process documentation to fix Mermaid syntax issues.

    Fixes common LLM mistakes:
    - Parentheses in node labels: [Text (path/)] -> [Text - path dir]
    - Parentheses in edge labels: |Action (tool)| -> |Action via tool|
    - Slashes in labels: HTTP/HTTPS -> HTTP or HTTPS
    """
    import re

    def fix_mermaid_block(match):
        """Fix a single mermaid code block."""
        content = match.group(1)

        # Fix node labels with parentheses: [Text (stuff)] -> [Text - stuff]
        # Match: [anything (anything)] but not [(database)]
        content = re.sub(
            r'\[([^\[\]()]+)\s*\(([^)]+)\)\]',
            lambda m: f'[{m.group(1).strip()} - {m.group(2).replace("/", " ").strip()}]',
            content
        )

        # Fix edge labels with parentheses: |Text (stuff)| -> |Text via stuff|
        content = re.sub(
            r'\|([^|()]+)\s*\(([^)]+)\)\|',
            lambda m: f'|{m.group(1).strip()} via {m.group(2).replace("/", " and ").strip()}|',
            content
        )

        # Fix slashes in edge labels: |HTTP/HTTPS| -> |HTTP and HTTPS|
        content = re.sub(
            r'\|([^|]*)/([^|]*)\|',
            lambda m: f'|{m.group(1).strip()} and {m.group(2).strip()}|',
            content
        )

        return f'```mermaid\n{content}\n```'

    sanitized = {}
    for key, value in docs.items():
        if isinstance(value, str) and '```mermaid' in value:
            # Find and fix all mermaid blocks
            value = re.sub(
                r'```mermaid\n(.*?)\n```',
                fix_mermaid_block,
                value,
                flags=re.DOTALL
            )
        sanitized[key] = value

    return sanitized


def _build_staff_engineer_prompt(
    project_name: str,
    analysis: dict,
    recent_changes: dict,
    persona: str,
    archetype: Archetype,
    plan: Optional[DocumentationPlan] = None
) -> str:
    """
    Build a Staff Engineer quality documentation prompt.

    This prompt enforces:
    1. Archetype-specific meaningful sections (no generic titles)
    2. Evidence-based content (no hallucinations)
    3. Technical density (the "So What?" test)
    4. Persona-appropriate depth
    """
    # Determine display name with proper priority:
    # 1. Package name from package.json (most accurate for npm projects)
    # 2. Repo name passed from caller (e.g., "org/repo-name" -> "repo-name")
    # 3. Project name from analysis (last resort)
    # NEVER use temp directory names like "docai_manual_xxx"

    package_name = analysis.get("package_name", "")
    analysis_project_name = analysis.get("project_name", "")

    # Extract clean repo name (e.g., "org/mode" -> "mode")
    clean_project_name = project_name
    if "/" in project_name:
        clean_project_name = project_name.split("/")[-1]

    # Determine best display name - avoid temp directory names
    if package_name and not package_name.startswith("docai") and len(package_name) > 2:
        display_name = package_name
    elif clean_project_name and not clean_project_name.startswith("docai"):
        display_name = clean_project_name
    elif analysis_project_name and not analysis_project_name.startswith("docai"):
        display_name = analysis_project_name
    else:
        # Last resort - use the full repo name
        display_name = project_name

    # Get archetype-specific sections
    sections = get_archetype_sections(archetype, persona)
    archetype_context = get_archetype_context(archetype)

    # Build section specifications
    section_specs = _build_section_specifications(sections, persona)

    # Build output format
    output_format = _build_output_format(sections)

    # Build evidence context (ADRs, commit messages, etc.)
    evidence_context = _build_evidence_context(analysis)

    # Debug logging
    print(f"🤖 Building Staff Engineer prompt for: {display_name}")
    print(f"   Archetype: {archetype.value}")
    print(f"   Persona: {persona}")
    print(f"   Sections: {len(sections)}")
    print(f"   Source files: {len(analysis.get('source_files', []))}")

    prompt = f"""You are a Staff Software Engineer (Meta L6 / SDE 3) producing documentation.
You do NOT summarize. You ENGINEER KNOWLEDGE.

Your documentation must be high-fidelity, high-density, and technical enough to serve as 
a source of truth for an engineer debugging at 2 AM.

═══════════════════════════════════════════════════════════════════════════════════════════
🛑 THE "ANTI-VAGUE" MANDATE
═══════════════════════════════════════════════════════════════════════════════════════════
You are FORBIDDEN from writing vague or one-paragraph sections.

BANNED WORDS: Overview, Components, Architecture, Workflow, Deployment, Vague

If you find yourself writing "This folder contains logic for X," you are FAILING.
Instead, you MUST explain:
  • INTERACTION: How does this module talk to others?
  • TRANSFORMATION: What does it do to the data?
  • PERSISTENCE: Where does the state end up?
  • ERROR HANDLING: What happens when the "Happy Path" fails?

The "So What?" Test: For EVERY sentence, ask: "If I were an engineer on-call at 2 AM 
trying to fix this, would this sentence help me?" If NOT, delete it and write specifics.

═══════════════════════════════════════════════════════════════════════════════════════════
📋 PROJECT CONTEXT
═══════════════════════════════════════════════════════════════════════════════════════════
Repository: {display_name}
Persona: {persona.upper()} {"(Surgeon's Manual - Document the guts)" if persona == "internal" else "(Owner's Manual - Document the surface)"}
Archetype: {archetype.value.upper()}

{archetype_context}

═══════════════════════════════════════════════════════════════════════════════════════════
⚖️ EVIDENCE-BASED LOGIC (NO HALLUCINATIONS)
═══════════════════════════════════════════════════════════════════════════════════════════
EXTRACTION OVER INFERENCE:
- Only state a rationale (e.g., "We chose Redis for latency") if you find evidence in:
  • ADR files (docs/adr, decisions/)
  • Commit messages in recent_changes
  • Code comments explicitly stating "why"
  
THE TECHNICAL DEFAULT:
- If no rationale is found, stay OBJECTIVE
- BAD: "Redis is used because it's fast."
- GOOD: "Redis serves as a write-through cache for session data, reducing PostgreSQL 
        I/O during peak traffic. Connection pooling configured with 10 max connections."

{evidence_context}

═══════════════════════════════════════════════════════════════════════════════════════════
📂 REPOSITORY ANALYSIS (EVIDENCE)
═══════════════════════════════════════════════════════════════════════════════════════════
{json.dumps(analysis, indent=2, default=str)[:20000]}

═══════════════════════════════════════════════════════════════════════════════════════════
🔄 RECENT CHANGES (CONTEXT)
═══════════════════════════════════════════════════════════════════════════════════════════
{json.dumps(recent_changes, indent=2)}

═══════════════════════════════════════════════════════════════════════════════════════════
📝 DOCUMENTATION SECTIONS (MANDATORY)
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
8. For INTERNAL: Focus on implementation details, edge cases, failure modes
9. For PUBLIC: Focus on time-to-value, clear examples, integration patterns

═══════════════════════════════════════════════════════════════════════════════════════════
📊 MERMAID DIAGRAM RULES (STRICT SYNTAX)
═══════════════════════════════════════════════════════════════════════════════════════════
If you include Mermaid diagrams, follow these EXACT syntax rules:

1. NO parentheses anywhere in diagrams (nodes OR edge labels):
   - BAD: Frontend[React Client (client/)]
   - BAD: A --> |Connect (Wagmi)| B
   - GOOD: Frontend[React Client]
   - GOOD: A --> |Connect via Wagmi| B

2. NO special characters in labels (no /, backslash, parentheses):
   - BAD: A --> |HTTP/HTTPS| B
   - GOOD: A --> |HTTP Request| B

3. Keep edge labels simple - no slashes or parens:
   - BAD: Client --> |Wallet Connect (Wagmi/Ethers)| Blockchain
   - GOOD: Client --> |Wallet Connection| Blockchain

4. Use simple graph syntax only:
   ```mermaid
   graph TD
       A[Component A] --> B[Component B]
       A --> |Data Flow| C[Component C]
   ```

5. NO styling, classDef, fill colors, or custom CSS

═══════════════════════════════════════════════════════════════════════════════════════════
🚫 NAMING RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════════════════
1. NEVER use temp directory names like "docai_manual_xxx" in documentation
2. Use the ACTUAL project name: "{display_name}"
3. When referring to the project, use "{display_name}" - NOT the temp folder path
4. The project name is "{display_name}" - use this throughout the documentation

DO NOT output generic descriptions.
DO NOT invent technologies not present in the codebase.
DO NOT write anything that fails the "So What?" test.
DO NOT use temp directory names - use "{display_name}" as the project name.
"""

    return prompt


def _build_section_specifications(sections: List[ArchetypeSection], persona: str) -> str:
    """
    Build detailed specifications for each section.

    Each section spec tells the LLM exactly what technical content is expected.
    """
    lines = []

    persona_context = "INTERNAL (Surgeon's Manual)" if persona == "internal" else "PUBLIC (Owner's Manual)"
    lines.append(f"Generating {persona_context} documentation.\n")

    for i, section in enumerate(sections, 1):
        lines.append(f"SECTION {i}: {section.title}")
        lines.append(f"  ID: {section.id}")
        lines.append(f"  Purpose: {section.description}")
        lines.append(
            f"  Required: {'YES' if section.required else 'ONLY IF EVIDENCE EXISTS'}")

        if section.subsections:
            lines.append("  Must Cover:")
            for sub in section.subsections:
                lines.append(f"    • {sub}")

        lines.append("")

    return "\n".join(lines)


def _build_output_format(sections: List[ArchetypeSection]) -> str:
    """
    Build the exact output format with section tags.
    """
    lines = []

    for section in sections:
        section_id = section.id.upper()
        lines.append(f"<{section_id}_START>")
        lines.append(f"# {section.title}")
        lines.append("")
        lines.append(
            f"[Detailed technical documentation covering: {section.description}]")
        lines.append("")
        if section.subsections:
            for sub in section.subsections:
                lines.append(f"## {sub}")
                lines.append(
                    "[Specific technical content with code snippets and file references]")
                lines.append("")
        lines.append(f"<{section_id}_END>")
        lines.append("")

    return "\n".join(lines)


def _build_evidence_context(analysis: dict) -> str:
    """
    Build context about available evidence for rationale extraction.
    """
    evidence_found = []

    # Check for ADR directory
    directories = analysis.get("main_directories", [])
    dir_str = " ".join(directories)

    if "adr" in dir_str.lower() or "decisions" in dir_str.lower():
        evidence_found.append(
            "• ADR/Decision Records found - extract rationale from these")

    if "changelog" in dir_str.lower():
        evidence_found.append("• CHANGELOG found - use for historical context")

    if ".github" in dir_str:
        evidence_found.append(
            "• GitHub workflows found - document CI/CD based on actual configs")

    if not evidence_found:
        evidence_found.append(
            "• No explicit rationale documents found - stay objective and technical")

    return "AVAILABLE EVIDENCE:\n" + "\n".join(evidence_found)


def _extract_archetype_sections(raw: str, archetype: Archetype, persona: str) -> Dict[str, str]:
    """
    Extract sections based on archetype and persona.

    IMPORTANT: Returns sections with MEANINGFUL IDs (slugified titles),
    NOT generic keys like "architecture", "deployment".

    Example output:
        {
            "component-hierarchy": "# Component Hierarchy & Atomic Design...",
            "state-management": "# State Management & Data Hydration...",
            "user-journey": "# User Journey Flows & Route Guards...",
        }
    """
    from app.services.documentation.archetype_detector import slugify_section_title

    sections = get_archetype_sections(archetype, persona)

    docs = {}

    # Extract each section using its MEANINGFUL ID
    for section in sections:
        section_id = section.id  # e.g., "component_hierarchy"
        section_slug = slugify_section_title(
            section.title)  # e.g., "component-hierarchy"

        # Try multiple extraction patterns
        content = (
            extract_section(raw, section_id.upper()) or
            extract_section(raw, section_slug.upper().replace("-", "_")) or
            extract_section(raw, section.title.upper().split("&")[0].strip()) or
            ""
        )

        if content:
            docs[section_slug] = content

    # Also extract by generic names for backward compatibility
    # but store under meaningful names if we have a plan
    generic_fallbacks = {
        "overview": ["OVERVIEW", "SUMMARY", "QUICKSTART", "PROJECT_OVERVIEW"],
        "architecture": ["ARCHITECTURE", "REQUEST_LIFECYCLE", "COMPONENT_HIERARCHY"],
        "workflow": ["WORKFLOW", "DEVELOPMENT", "USER_JOURNEY"],
        "api": ["API", "API_REFERENCE", "SERVICE_INTEGRATION"],
        "components": ["COMPONENTS", "COMPONENT_USAGE"],
        "dependencies": ["DEPENDENCIES", "DEPENDENCY_GRAPH"],
        "deployment": ["DEPLOYMENT", "BUILD_PIPELINE", "DEPLOYMENT_TOPOLOGY"],
    }

    # Only add generic sections if we didn't get meaningful ones
    for generic_key, patterns in generic_fallbacks.items():
        if generic_key not in docs:
            for pattern in patterns:
                content = extract_section(raw, pattern)
                if content:
                    docs[generic_key] = content
                    break

    return docs


def _get_fallback_docs(archetype: Archetype, persona: str) -> Dict[str, str]:
    """
    Return fallback documentation if LLM fails.
    """
    return {
        "overview": f"# Documentation Generation Failed\n\nLLM providers unavailable. Archetype: {archetype.value}, Persona: {persona}",
        "architecture": "# Technical Architecture\n\nUnavailable - retry documentation generation.",
        "workflow": "# Development Workflow\n\nUnavailable - retry documentation generation.",
        "api": "# API Reference\n\nUnavailable - retry documentation generation.",
        "components": "",
        "dependencies": "",
        "deployment": "",
    }


def _get_empty_token_data() -> Dict[str, any]:
    """Return empty token data for fallback cases."""
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "model_name": "unknown",
    }


# Backward compatibility - keep old function name working
def _build_prompt(
    project_name: str,
    analysis: dict,
    recent_changes: dict,
    persona: str,
    plan: Optional[DocumentationPlan] = None
) -> str:
    """
    Backward compatible wrapper for the Staff Engineer prompt builder.
    """
    archetype = detect_archetype(analysis)
    return _build_staff_engineer_prompt(
        project_name, analysis, recent_changes, persona, archetype, plan
    )
