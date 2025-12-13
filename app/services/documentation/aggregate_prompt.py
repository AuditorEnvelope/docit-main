import json
from app.services.llm.rotator import get_rotator
from app.services.documentation.parsing import extract_section


async def generate_all_docs_in_single_call(repo_dir, analysis, recent_changes, persona):
    """
    Generate SUMMARY + ARCHITECTURE + WORKFLOW + API in a single LLM call.
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
    raw = rotator.generate_with_rotation(prompt)

    return {
        "summary": extract_section(raw, "SUMMARY"),
        "architecture": extract_section(raw, "ARCHITECTURE"),
        "workflow": extract_section(raw, "WORKFLOW"),
        "api": extract_section(raw, "API"),
    }
