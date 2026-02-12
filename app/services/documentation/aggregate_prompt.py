import json
from typing import Dict, Tuple, Optional
from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section
# Phase 1: Import planner
from app.services.documentation.planner import DocumentationPlan, get_planner


async def generate_all_docs_in_single_call(
    repo_dir, analysis, recent_changes, persona, plan: Optional[DocumentationPlan] = None
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

    Returns:
        Tuple containing:
        - docs_dict: {"summary": str, "architecture": str, "workflow": str, "api": str}
        - token_data: {"input_tokens": int, "output_tokens": int, "model_name": str}
    """
    project_name = repo_dir.name

    # Phase 1: Build dynamic prompt using plan if available
    prompt = _build_prompt(project_name, analysis, recent_changes, persona, plan)

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

    docs = {
        "summary": extract_section(raw, "SUMMARY"),
        "architecture": extract_section(raw, "ARCHITECTURE"),
        "workflow": extract_section(raw, "WORKFLOW"),
        "api": extract_section(raw, "API"),
    }

    return docs, token_data


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
    if plan and plan.sections:
        section_guidance = _build_section_guidance(plan)

    prompt = f"""You are DocAI, an expert technical documentation system.
Generate 4 documentation sections in ONE response.

Persona: {persona}
Repository: {project_name}

=========================
REPOSITORY ANALYSIS (JSON)
=========================
{json.dumps(analysis, indent=2)[:15000]}   # Truncate for safety

=========================
RECENT CHANGES
=========================
{json.dumps(recent_changes, indent=2)}
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

    # Output format remains EXACTLY the same for backward compatibility
    prompt += """
=========================
OUTPUT FORMAT (MANDATORY)
=========================

<SUMMARY_START>
... summary markdown ...
<SUMMARY_END>

<ARCHITECTURE_START>
... architecture markdown ...
<ARCHITECTURE_END>

<WORKFLOW_START>
... workflow markdown ...
<WORKFLOW_END>

<API_START>
... api markdown ...
<API_END>

DO NOT output anything outside these 4 sections.
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
            lines.append(f"  - {s.title}: Look for patterns like {', '.join(s.dependencies[:3])}")

    return "\n".join(lines)
