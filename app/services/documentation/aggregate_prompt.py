import json
from typing import Dict, Tuple, Optional
from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section
# Phase 1: Import planner
from app.services.documentation.planner import DocumentationPlan, get_planner


async def generate_all_docs_in_single_call(
    repo_dir, analysis, recent_changes, persona, plan: Optional[DocumentationPlan] = None, repo_name: str = None
) -> Tuple[Dict[str, str], Dict[str, any]]:
    """
    Generate SUMMARY + ARCHITECTURE + WORKFLOW + API in a single LLM call.

    Phase 1 Enhancement: Accepts optional DocumentationPlan for structured prompting.
    Phase 6 Enhancement: Returns (docs_dict, token_data) tuple.

    Args:
        repo_dir: Path to repository
        analysis: Repository analysis dict
        recent_changes: Recent changes dict
        persona: Documentation persona
        plan: Optional DocumentationPlan for structured section guidance
        repo_name: Actual repository name (e.g., "org/repo"), defaults to repo_dir.name

    Returns:
        Tuple containing:
        - docs_dict: {"summary": str, "architecture": str, "workflow": str, "api": str}
        - token_data: {"input_tokens": int, "output_tokens": int, "model_name": str}
    """
    project_name = repo_name or repo_dir.name

    # Phase 1: Build dynamic prompt using plan if available
    prompt = _build_prompt(project_name, analysis,
                           recent_changes, persona, plan)

    rotator = get_rotator()
    llm_result = rotator.generate_with_rotation(prompt)

    if not llm_result:
        # Fallback if all providers fail
        empty_docs = {
            "summary": "# Documentation Generation Failed\n\nAll LLM providers failed. Please try again later.",
            "architecture": "# Architecture\n\nUnavailable",
            "workflow": "# Workflow\n\nUnavailable",
            "api": "# API\n\nUnavailable",
        }
        token_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "model_name": "unknown",
        }
        return empty_docs, token_data

    # Extract content and token data
    raw = llm_result.content
    token_data = {
        "input_tokens": llm_result.input_tokens,
        "output_tokens": llm_result.output_tokens,
        "model_name": llm_result.model_name,
    }

    # Extract sections dynamically based on plan
    docs = _extract_dynamic_sections(raw, plan)

    return docs, token_data


def _extract_dynamic_sections(raw: str, plan: Optional[DocumentationPlan]) -> Dict[str, str]:
    """
    Extract sections dynamically based on the documentation plan.

    Falls back to default sections if plan is not available.
    """
    if not plan or not plan.sections:
        # Fallback to default 4 sections
        return {
            "summary": extract_section(raw, "SUMMARY"),
            "architecture": extract_section(raw, "ARCHITECTURE"),
            "workflow": extract_section(raw, "WORKFLOW"),
            "api": extract_section(raw, "API"),
        }

    docs = {}
    for section in plan.sections:
        section_id = section.id.lower()
        section_content = extract_section(raw, section.id.upper())
        docs[section_id] = section_content

    return docs


def _build_prompt(
    project_name: str,
    analysis: dict,
    recent_changes: dict,
    persona: str,
    plan: Optional[DocumentationPlan] = None
) -> str:
    """
    Build the documentation generation prompt.

    Phase 1: Uses DocumentationPlan to structure the prompt dynamically
    while maintaining backward-compatible output format.
    """
    # Build section guidance from plan
    section_guidance = ""
    repo_type_context = ""
    if plan and plan.sections:
        section_guidance = _build_section_guidance(plan)
        # Add specific context based on repo type
        if plan.repo_type == "frontend-app":
            repo_type_context = """
=========================
PROJECT TYPE CONTEXT
=========================
This is a FRONTEND WEB APPLICATION project (React/Vue/Angular/Next.js).

CRITICAL RULES - STRICT COMPLIANCE REQUIRED:

1. USE ONLY DATA FROM THE JSON ANALYSIS BELOW
   - If a file/dependency is NOT in the analysis, DO NOT mention it
   - If data IS in the analysis, you MUST use it specifically

2. BANNED PHRASES - DO NOT USE:
   - "not detailed in the provided analysis"
   - "not available in the analysis"
   - "would typically"
   - "might include"
   - "could contain"
   - "is likely to"
   - "e.g.," (giving generic examples)
   - ANY hypothetical or inferred content

3. REQUIRED - YOU MUST:
   - Use EXACT project name from analysis
   - List SPECIFIC file names from source_files array
   - Name SPECIFIC dependencies from dependencies object
   - Quote SPECIFIC npm scripts from scripts object
   - Name SPECIFIC components from component_files array

4. FORBIDDEN TOPICS (unless explicitly in analysis):
   - Docker/containerization
   - Kubernetes/orchestration
   - Cloud providers (AWS, GCP, Azure)
   - Microservices architecture
   - CI/CD pipelines (unless .github/workflows files found)
   - Database layers
   - Generic system descriptions

5. PROJECT NAME: Use the EXACT name from package_name or project_name field.
   NEVER use temp directory names like "docai_manual_XXXXX".
"""

    # Use package_name from analysis if available, otherwise use project_name
    display_name = analysis.get("package_name") or analysis.get(
        "project_name") or project_name

    # Debug: Log what's being passed to LLM
    print(f"🤖 Building prompt for: {display_name}")
    print(
        f"   Source files in analysis: {len(analysis.get('source_files', []))}")
    print(
        f"   Components in analysis: {len(analysis.get('component_files', []))}")
    print(
        f"   Dependencies in analysis: {len(analysis.get('dependencies', {}))}")

    prompt = f"""You are DocAI, an expert technical documentation system.
Generate documentation sections in ONE response.

Persona: {persona}
Repository: {display_name}
{repo_type_context}
=========================
REPOSITORY ANALYSIS (JSON)
=========================
{json.dumps(analysis, indent=2)[:18000]}   # Increased limit for source files

=========================
RECENT CHANGES
=========================
{json.dumps(recent_changes, indent=2)}

IMPORTANT: The project name is '{display_name}'. Use this name throughout.
LIST ACTUAL FILE NAMES from source_files array in your response.
NAME SPECIFIC DEPENDENCIES from the dependencies object.
"""

    # Phase 1: Add dynamic section guidance if available
    if section_guidance:
        prompt += f"""
=========================
DOCUMENTATION STRUCTURE GUIDANCE
=========================
{section_guidance}

Focus on the sections most relevant to this repository type ({plan.repo_type if plan else 'generic'}).
"""

    # Build dynamic output format based on plan sections
    output_format = _build_dynamic_output_format(plan, persona)

    prompt += f"""
=========================
OUTPUT FORMAT (MANDATORY)
=========================

{output_format}

CRITICAL OUTPUT RULES:
1. Generate EXACTLY the sections listed above - no more, no less
2. Use the EXACT section tags provided (<SECTION_NAME_START>...<SECTION_NAME_END>)
3. ONLY document what actually exists in the codebase
4. NEVER invent technologies, files, or features
5. Use specific file names and code patterns found in the repository
6. For INTERNAL persona: Focus on code architecture and implementation
7. For DEV persona: Focus on functionality and usage

DO NOT output anything outside the specified sections.
DO NOT invent technologies not present in the codebase.
"""

    return prompt


def _build_section_guidance(plan: DocumentationPlan) -> str:
    """
    Build section guidance text from documentation plan.

    This provides hints to the LLM about what content to emphasize
    without changing the output structure.
    """
    lines = []

    # Add repo type context
    lines.append(f"Repository Type: {plan.repo_type}")
    lines.append(f"Complexity Score: {plan.complexity_score}/10")
    lines.append("")

    # Group sections by type
    summary_sections = plan.get_sections_by_type("summary")
    arch_sections = plan.get_sections_by_type("architecture")
    workflow_sections = plan.get_sections_by_type("workflow")
    api_sections = plan.get_sections_by_type("api")

    # Summary guidance
    if summary_sections:
        lines.append("SUMMARY section should include:")
        for s in summary_sections:
            lines.append(f"  - {s.title}")
        lines.append("")

    # Architecture guidance
    if arch_sections:
        lines.append("ARCHITECTURE section should cover:")
        for s in arch_sections:
            if s.required:
                lines.append(f"  - {s.title} (essential)")
            else:
                lines.append(f"  - {s.title} (if applicable)")
        lines.append("")

    # Workflow guidance
    if workflow_sections:
        lines.append("WORKFLOW section should describe:")
        for s in workflow_sections:
            lines.append(f"  - {s.title}")
        lines.append("")

    # API guidance
    if api_sections:
        lines.append("API section should document:")
        for s in api_sections:
            lines.append(f"  - {s.title}")
        lines.append("")

    # Add conditional section hints
    conditional = [s for s in plan.sections if not s.required]
    if conditional:
        lines.append("Additional topics to cover if present in codebase:")
        for s in conditional[:5]:  # Limit to top 5
            lines.append(
                f"  - {s.title}: Look for patterns like {', '.join(s.dependencies[:3])}")

    return "\n".join(lines)


def _build_dynamic_output_format(plan: Optional[DocumentationPlan], persona: str) -> str:
    """
    Build dynamic output format based on plan sections.

    Creates section tags dynamically based on what sections are planned.
    """
    if not plan or not plan.sections:
        # Fallback to default 4 sections
        return """<OVERVIEW_START>
... project overview ...
<OVERVIEW_END>

<ARCHITECTURE_START>
... architecture documentation ...
<ARCHITECTURE_END>

<WORKFLOW_START>
... development workflow ...
<WORKFLOW_END>

<API_START>
... API or usage documentation ...
<API_END>"""

    lines = []

    for section in plan.sections:
        section_id = section.id.upper()
        lines.append(f"<{section_id}_START>")
        lines.append(f"# {section.title}")
        if section.description:
            lines.append(f"# Description: {section.description}")
        lines.append(f"... {section.type} documentation ...")
        lines.append(f"<{section_id}_END>")
        lines.append("")

    return "\n".join(lines)
