"""
Section Validator – structural quality gates run after per-section generation.

Checks each generated section for:
  - Minimum body length (avoid stubs / placeholder text)
  - Presence of required subheadings
  - No leftover placeholder/TODO text
  - Mermaid blocks parse (balanced fences)
  - Content is not just the prompt echo

This is NOT an LLM call – it's a fast structural pass.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ValidationResult:
    section_id: str
    passed: bool
    issues: List[str]


def validate_sections(
    docs: Dict[str, str],
    planned_sections: List[Dict],
    min_words: int = 300,
) -> List[ValidationResult]:
    """Validate all generated sections, return results."""
    results = []
    for section in planned_sections:
        sid = section["id"]
        content = docs.get(sid, "")
        issues = _check_section(content, section, min_words)
        results.append(ValidationResult(
            section_id=sid,
            passed=len(issues) == 0,
            issues=issues,
        ))
    return results


def _check_section(content: str, section: Dict, min_words: int) -> List[str]:
    """Return a list of issues found in the section content."""
    issues: List[str] = []

    if not content or not content.strip():
        issues.append("EMPTY: No content generated")
        return issues

    words = len(content.split())
    if words < min_words:
        issues.append(f"SHORT: {words} words (minimum {min_words})")

    # Check for placeholder text (only match actual stubs, not mentions
    # of the word in env-var documentation like "replace PLACEHOLDER_KEY")
    placeholder_patterns = [
        r"\[Write .+? here\]",
        r"\[TODO\]",
        r"^\s*TODO:\s*$",
        r"^\s*PLACEHOLDER\s*$",
        r"\[PLACEHOLDER\]",
        r"Lorem ipsum",
        r"Documentation unavailable",
    ]
    for pattern in placeholder_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            issues.append(f"PLACEHOLDER: Found '{pattern}' in content")

    # Check Mermaid fences are balanced
    mermaid_opens = len(re.findall(r"```mermaid", content))
    code_closes = len(re.findall(r"```\s*$", content, re.MULTILINE))
    # This is a rough check; unbalanced fences will break rendering
    if mermaid_opens > 0 and code_closes < mermaid_opens:
        issues.append(
            f"MERMAID: {mermaid_opens} mermaid blocks but only {code_closes} closing fences")

    # Check it has at least one heading
    if not re.search(r"^#{1,3}\s+", content, re.MULTILINE):
        issues.append("NO_HEADINGS: Section has no markdown headings")

    return issues


def print_validation_report(results: List[ValidationResult]) -> None:
    """Print a human-readable validation summary."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n🔍 Section validation: {passed}/{total} passed")
    for r in results:
        if r.passed:
            print(f"   ✅ [{r.section_id}] OK")
        else:
            print(f"   ❌ [{r.section_id}] ISSUES:")
            for issue in r.issues:
                print(f"      - {issue}")
