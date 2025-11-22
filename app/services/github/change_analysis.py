"""Legacy-inspired change analysis for documentation significance."""

import json
import os
import re
from pathlib import Path
from typing import Iterable, Set, Dict, Any

# FIX: point to the new rotator in app services instead of legacy src path
from app.services.llm.rotator import get_rotator

# --- Added: robust parsing and fallback helpers ---
ALLOWED_TYPES = {
    "feature", "bug_fix", "refactor", "breaking_change",
    "security", "performance", "chore", "docs"
}

def _compute_significance(file_analysis: Dict[str, Any]) -> int:
    """Heuristic significance score 1-10 based on detected patterns and counts."""
    score = 3
    patterns = set(file_analysis.get("detected_patterns", []))
    file_count = int(file_analysis.get("file_count", 0))
    removed_count = int(file_analysis.get("removed_count", 0))
    if file_analysis.get("is_major_change"):
        score += 4
    if "auth" in patterns or "database" in patterns:
        score += 2
    if file_count > 20:
        score += 1
    if removed_count > 5:
        score += 1
    return max(1, min(10, score))

def _default_title_summary(detected_patterns: Set[str], changed_files: Set[str]) -> Dict[str, str]:
    """Generate a simple title/summary when LLM fails."""
    if "auth" in detected_patterns:
        return {
            "title": "Authentication Changes",
            "summary": "Authentication-related updates detected in the codebase."
        }
    if "database" in detected_patterns:
        return {
            "title": "Database Schema/Model Changes",
            "summary": "Database-related updates including schema or models."
        }
    if "api" in detected_patterns:
        return {
            "title": "API Endpoint/Route Changes",
            "summary": "API-related updates including endpoints or controllers."
        }
    if "docs" in detected_patterns:
        return {
            "title": "Documentation Updates",
            "summary": "Documentation-related changes detected."
        }
    # Fallback generic
    some_file = next(iter(changed_files), "multiple files")
    return {
        "title": f"Code Changes in {some_file}",
        "summary": "Code changes detected across the repository."
    }

def _build_default_analysis(
    payload: Dict[str, Any],
    file_analysis: Dict[str, Any],
    changed_files: Set[str],
    removed_files: Set[str],
) -> Dict[str, Any]:
    """Fallback analysis when LLM parsing fails."""
    significance = _compute_significance(file_analysis)
    detected_patterns = set(file_analysis.get("detected_patterns", []))
    title_summary = _default_title_summary(detected_patterns, changed_files)
    impact_scope = sorted(list(detected_patterns)) or ["general"]
    affected_components = sorted(list({f.split("/")[0] + "/" for f in changed_files if "/" in f}))[:10]
    return {
        "type": "docs" if "docs" in detected_patterns else "feature",
        "significance": significance,
        "is_significant": significance >= 7,
        "title": title_summary["title"],
        "summary": title_summary["summary"],
        "impact_scope": impact_scope,
        "affected_components": affected_components,
        "breaking_changes": False,
        "new_features": [],
        "technical_details": "",
        "documentation_needs": {
            "update_readme": True,
            "create_changelog": True,
            "update_api_docs": "api" in detected_patterns,
            "create_migration_guide": False
        },
        "reason": "Heuristic fallback analysis based on file patterns and change magnitude."
    }

async def _parse_llm_json(response: str) -> Dict[str, Any] | None:
    """Extract and parse JSON from LLM output with sanitization."""
    if not response:
        return None
    # Capture the largest JSON-looking block
    start = response.find("{")
    end = response.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    json_str = response[start:end+1]
    # Sanitize common issues
    json_str = json_str.replace("\\n", "\\\\n").replace("\\t", "\\\\t").replace("\\r", "\\\\r")
    json_str = re.sub(r"\\(?![\"\\/bfnrtu])", r"\\\\", json_str)  # non-escape backslashes
    # Attempt strict parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Light cleanup: convert Python booleans to JSON booleans, single quotes to double quotes safely
        cleaned = re.sub(r'\bTrue\b', 'true', json_str)
        cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
        cleaned = re.sub(r'\bNone\b', 'null', cleaned)
        # Replace single-quoted strings/keys in a conservative way
        cleaned = re.sub(r"(?<!\\)'", '"', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

async def _coerce_analysis_result(
    result: Dict[str, Any],
    payload: Dict[str, Any],
    file_analysis: Dict[str, Any],
    changed_files: Set[str],
    removed_files: Set[str],
) -> Dict[str, Any]:
    """Ensure required fields, fix types, clamp values, and fill defaults."""
    if not isinstance(result, dict):
        return await _build_default_analysis(payload, file_analysis, changed_files, removed_files)

    # Type normalization
    type_val = str(result.get("type", "feature")).strip().lower()
    if type_val not in ALLOWED_TYPES:
        type_val = "feature"

    try:
        significance = int(result.get("significance", await _compute_significance(file_analysis)))
    except Exception:
        significance = await _compute_significance(file_analysis)
    significance = max(1, min(10, significance))

    is_significant = bool(result.get("is_significant", significance >= 7))

    title = str(result.get("title") or "").strip()
    summary = str(result.get("summary") or "").strip()

    impact_scope = result.get("impact_scope") or []
    if not isinstance(impact_scope, list):
        impact_scope = [str(impact_scope)]
    impact_scope = [str(x) for x in impact_scope] or (file_analysis.get("detected_patterns") or ["general"])

    affected_components = result.get("affected_components") or []
    if not isinstance(affected_components, list):
        affected_components = [str(affected_components)]
    if not affected_components:
        affected_components = sorted(list({f.split("/")[0] + "/" for f in changed_files if "/" in f}))[:10]

    breaking_changes = bool(result.get("breaking_changes", False))

    new_features = result.get("new_features") or []
    if not isinstance(new_features, list):
        new_features = [str(new_features)]

    technical_details = str(result.get("technical_details") or "")

    documentation_needs = result.get("documentation_needs") or {}
    if not isinstance(documentation_needs, dict):
        documentation_needs = {}
    documentation_needs.setdefault("update_readme", True)
    documentation_needs.setdefault("create_changelog", True)
    documentation_needs.setdefault("update_api_docs", "api" in (file_analysis.get("detected_patterns") or []))
    documentation_needs.setdefault("create_migration_guide", False)

    reason = str(result.get("reason") or "")

    # Fill minimal defaults if missing
    if not title or not summary:
        ts = await _default_title_summary(set(file_analysis.get("detected_patterns") or []), changed_files)
        title = title or ts["title"]
        summary = summary or ts["summary"]

    return {
        "type": type_val,
        "significance": significance,
        "is_significant": is_significant,
        "title": title,
        "summary": summary,
        "impact_scope": impact_scope,
        "affected_components": affected_components,
        "breaking_changes": breaking_changes,
        "new_features": new_features,
        "technical_details": technical_details,
        "documentation_needs": documentation_needs,
        "reason": reason,
    }
# --- End helpers ---

async def smart_analyze_change(
    payload: Dict[str, Any],
    repo_dir: str,
    changed_files: Iterable[str],
    removed_files: Iterable[str],
) -> Dict[str, Any]:
    """Proxy to the legacy smart analyzer with minimal dependencies."""

    changed_files = set(changed_files)
    removed_files = set(removed_files)

    diff_context = get_git_diff_context(repo_dir, changed_files)
    file_analysis = analyze_file_patterns(changed_files, removed_files)
    codebase_context = (
        get_codebase_context(repo_dir, changed_files)
        if file_analysis["is_major_change"]
        else ""
    )

    commits = payload.get("commits", [])
    commit_messages = [commit.get("message", "") for commit in commits]

    analysis_prompt = f"""
You are DocAI, an expert code analysis AI. Analyze this code change comprehensively.

REPOSITORY CONTEXT:
- Repository: {payload.get("repository", {}).get("full_name", "unknown")}
- Branch: {payload.get("ref", "unknown")}
- Commit SHA: {payload.get("after", "unknown")}

COMMIT MESSAGES:
{chr(10).join(f"- {msg}" for msg in commit_messages)}

FILE CHANGES:
Changed files ({len(changed_files)}):
{chr(10).join(f"- {f}" for f in sorted(changed_files))}

Removed files ({len(removed_files)}):
{chr(10).join(f"- {f}" for f in sorted(removed_files))}

FILE PATTERN ANALYSIS:
{json.dumps(file_analysis, indent=2)}

GIT DIFF CONTEXT:
{diff_context}

CODEBASE CONTEXT (for major changes):
{codebase_context}

ANALYSIS REQUIREMENTS:
1. Determine the TYPE of change (feature, bug_fix, refactor, breaking_change, security, performance, etc.)
2. Assess SIGNIFICANCE (1-10 scale) - only document 7+ significant changes
3. Identify the MAIN PURPOSE and impact
4. Understand which parts of the system are affected
5. Determine what documentation needs updating

IMPORTANT: Respond with VALID JSON only. Do NOT use backslashes except for escaping quotes.
Use forward slashes (/) for paths. Keep strings simple and avoid special characters.

Respond in JSON format:
{{
    "type": "feature|bug_fix|refactor|breaking_change|security|performance|chore|docs",
    "significance": 8,
    "is_significant": true,
    "title": "Add OAuth2 Authentication System",
    "summary": "Implemented comprehensive OAuth2 authentication with JWT tokens, user management, and role-based access control",
    "impact_scope": ["authentication", "user_management", "api_security"],
    "affected_components": ["auth/", "api/middleware/", "database/schemas/"],
    "breaking_changes": false,
    "new_features": ["OAuth2 login", "JWT tokens", "Role-based access"],
    "technical_details": "Detailed technical implementation...",
    "documentation_needs": {{
        "update_readme": true,
        "create_changelog": true,
        "update_api_docs": true,
        "create_migration_guide": false
    }},
    "reason": "Major authentication feature affecting core system security"
}}
"""

    rotator = await get_rotator()
    try:
        response = await rotator.generate_with_rotation(analysis_prompt)
    except Exception:
        # Fallback if provider errors
        return _build_default_analysis(payload, file_analysis, changed_files, removed_files)

    if not response:
        return _build_default_analysis(payload, file_analysis, changed_files, removed_files)

    # --- Changed: robust parse and schema coercion ---
    parsed = _parse_llm_json(response)
    if not parsed:
        return _build_default_analysis(payload, file_analysis, changed_files, removed_files)

    return _coerce_analysis_result(parsed, payload, file_analysis, changed_files, removed_files)
    # --- End changed block ---


def analyze_file_patterns(changed_files: Set[str], removed_files: Set[str]) -> Dict[str, Any]:
    patterns = {
        "auth": ["auth", "login", "jwt", "oauth", "session", "user"],
        "api": ["api", "endpoint", "route", "controller"],
        "database": ["migration", "schema", "model", "db"],
        "frontend": ["component", "page", "view", "ui", "css", "jsx"],
        "config": ["config", "env", "docker", "yaml", "json"],
        "test": ["test", "spec", "mock"],
        "docs": ["readme", "docs", "changelog", "guide"],
    }

    detected_patterns = set()
    lower_changed = [f.lower() for f in changed_files]
    for pattern, keywords in patterns.items():
        if any(any(keyword in path for keyword in keywords) for path in lower_changed):
            detected_patterns.add(pattern)

    major_indicators = [
        len(changed_files) > 20,
        "auth" in detected_patterns,
        "database" in detected_patterns,
        any("config" in f for f in lower_changed),
        len(removed_files) > 5,
    ]

    return {
        "detected_patterns": list(detected_patterns),
        "is_major_change": any(major_indicators),
        "file_count": len(changed_files),
        "removed_count": len(removed_files),
    }


def get_git_diff_context(repo_dir: str, changed_files: Set[str]) -> str:
    repo_path = Path(repo_dir)
    diff_context = []
    for file in changed_files:
        try:
            file_path = repo_path / file
            if file_path.exists() and file_path.is_file():
                content = file_path.read_text(errors="ignore")[:2000]
                diff_context.append(f"--- {file}\n{content}")
        except Exception:
            continue  # Ignore files that can't be read
    return "\n".join(diff_context)


def get_codebase_context(repo_dir: str, changed_files: Set[str]) -> str:
    repo_path = Path(repo_dir)
    all_files = []
    try:
        for p in repo_path.rglob("*"):
            if p.is_file():
                parts = p.parts
                if any(part in {".git", "docs", "node_modules", "__pycache__"} for part in parts):
                    continue
                all_files.append(str(p.relative_to(repo_path)))
    except Exception:
        pass # Ignore errors during file traversal
    return "\n".join(all_files[:50])
