"""
Documentation selection logic for diff-aware updates.

This module determines which documentation sections need to be updated
based on the changes in the repository, minimizing unnecessary LLM calls.
"""
import os
from typing import Dict, List, Any
from app.services.documentation.quality_integration import run_quality_checks

async def determine_docs_to_update(
    repo_dir: str,
    changed_files: List[str],
    analysis: Dict[str, Any],
) -> Dict[str, bool]:
    """Determine which documentation files to update based on file changes and quality checks."""
    docs_dir = os.path.join(repo_dir, "docs")

    # Rule 1: If docs folder is empty, generate everything.
    if not os.path.exists(docs_dir) or not os.listdir(docs_dir):
        return {"summary": True, "architecture": True, "workflow": True, "api": True}

    # Rule 2: If docs exist, run quality checks to find outdated sections.
    quality_needs = await run_quality_checks(repo_dir, analysis)

    # Rule 3: For manual generation (no changed files), rely solely on quality checks.
    if not changed_files:
        return quality_needs

    # Rule 4: For webhook events, combine quality needs with change analysis.
    needs_update = quality_needs.copy()
    for file_path in changed_files:
        if not needs_update.get("architecture") and _is_architecture_change(file_path):
            needs_update["architecture"] = True
        if not needs_update.get("workflow") and _is_workflow_change(file_path):
            needs_update["workflow"] = True
        if not needs_update.get("api") and _is_api_change(file_path):
            needs_update["api"] = True

    # Rule 5: Always update summary if any other section is updated.
    if any(v for k, v in needs_update.items() if k != 'summary'):
        needs_update["summary"] = True

    return needs_update

def _is_architecture_change(file_path: str) -> bool:
    return any(keyword in file_path for keyword in ["requirements.txt", "package.json", "pyproject.toml", "go.mod", "Dockerfile"])

def _is_workflow_change(file_path: str) -> bool:
    return any(keyword in file_path for keyword in [".github/workflows", "docker-compose"])

def _is_api_change(file_path: str) -> bool:
    return any(keyword in file_path for keyword in ["/api/", "/routes/", "/controllers/", "/endpoints/"])
