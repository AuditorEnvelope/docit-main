import json
from typing import Dict, Tuple
from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section


async def generate_all_docs_in_single_call(
    repo_dir, analysis, recent_changes, persona
) -> Tuple[Dict[str, str], Dict[str, any]]:
    """
    Generate SUMMARY + ARCHITECTURE + WORKFLOW + API in a single LLM call.

    Phase 6 Enhancement: Now returns (docs_dict, token_data) tuple.

    Returns:
        Tuple containing:
        - docs_dict: {"summary": str, "architecture": str, "workflow": str, "api": str}
        - token_data: {"input_tokens": int, "output_tokens": int, "model_name": str}
    """
    project_name = repo_dir.name

    prompt = f"""
You are DocAI, an expert technical documentation system.
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
