"""
Semantic Section Validator – checks whether generated documentation is
actually system-aware vs generic filler.

This is a fast REGEX/HEURISTIC pass (no LLM call). It evaluates whether
a section references real system components, describes actual flows or
relationships, and avoids boilerplate language.

Returns True if the section is semantically strong, False if it needs
a retry with a stronger prompt.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Any


# ── Generic filler phrases that indicate low-quality output ──────────────

_GENERIC_PHRASES = [
    r"this system is designed to",
    r"provides? scalability and flexibility",
    r"robust and efficient",
    r"designed with modularity in mind",
    r"follows? best practices",
    r"highly configurable",
    r"provides? a seamless experience",
    r"comprehensive solution",
    r"state[- ]of[- ]the[- ]art",
    r"cutting[- ]edge",
    r"leverages? modern",
    r"ensures? data integrity",
    r"built with performance in mind",
    r"provides? a clean api",
    r"well[- ]structured codebase",
    r"easy to maintain",
]

_COMPILED_GENERIC = [
    re.compile(p, re.IGNORECASE) for p in _GENERIC_PHRASES
]


def is_section_semantically_strong(
    section_text: str,
    repo_understanding: Optional[Dict[str, Any]] = None,
    min_concrete_refs: int = 2,
) -> bool:
    """Return True if the section demonstrates real system awareness.

    Checks:
      1. No excessive generic filler phrases (max 2 allowed)
      2. Contains concrete references (file paths, function names, config keys)
      3. Describes at least one flow/relationship (arrow, "calls", "sends to", etc.)
      4. If repo_understanding is provided, checks for component name mentions

    Args:
        section_text: The generated markdown content.
        repo_understanding: Output of build_repo_understanding() — used to
            check that real component names appear in the text.
        min_concrete_refs: Minimum number of concrete references required.

    Returns:
        True if quality is acceptable, False if retry is needed.
    """
    if not section_text or len(section_text.strip()) < 200:
        return False

    issues = get_semantic_issues(
        section_text, repo_understanding, min_concrete_refs)
    # Allow up to 1 minor issue
    return len(issues) <= 1


def get_semantic_issues(
    section_text: str,
    repo_understanding: Optional[Dict[str, Any]] = None,
    min_concrete_refs: int = 2,
) -> List[str]:
    """Return a list of semantic quality issues found in the section."""
    issues: List[str] = []

    # 1. Generic filler check
    generic_count = sum(
        1 for pat in _COMPILED_GENERIC if pat.search(section_text)
    )
    if generic_count >= 3:
        issues.append(
            f"GENERIC_FILLER: {generic_count} boilerplate phrases detected")

    # 2. Concrete reference check (file paths, function names, config keys)
    concrete_patterns = [
        # File path references (e.g., src/App.jsx, app/main.py)
        r'(?:src|app|lib|utils|pages|components|services|api)/[\w/.-]+\.\w+',
        # Function/method calls (e.g., handleSubmit(), createUser, fetchData)
        r'`[a-zA-Z_]\w+(?:\(\))?`',
        # Config keys / env vars (e.g., NEXT_PUBLIC_API_URL, DATABASE_URL)
        r'`[A-Z][A-Z_]{2,}`',
        # Inline code references
        r'`[\w.]+\(.*?\)`',
    ]
    concrete_refs = 0
    for pat in concrete_patterns:
        concrete_refs += len(re.findall(pat, section_text))

    if concrete_refs < min_concrete_refs:
        issues.append(
            f"NO_CONCRETE_REFS: Only {concrete_refs} concrete references "
            f"(need {min_concrete_refs})"
        )

    # 3. Flow/relationship description check
    flow_indicators = [
        r'→|-->|->',                          # arrows
        r'\bcalls?\b',                         # "calls"
        r'\bsends?\s+to\b',                   # "sends to"
        r'\breceives?\s+from\b',              # "receives from"
        r'\bpasses?\s+.*?\bto\b',             # "passes X to"
        r'\breturns?\s+.*?\bto\b',            # "returns X to"
        r'\btriggers?\b',                     # "triggers"
        r'\bpropagates?\b',                   # "propagates"
        r'\bwrites?\s+to\b',                  # "writes to"
        r'\breads?\s+from\b',                 # "reads from"
        r'```mermaid',                         # mermaid diagram
    ]
    flow_count = sum(
        1 for pat in flow_indicators
        if re.search(pat, section_text, re.IGNORECASE)
    )
    if flow_count < 1:
        issues.append(
            "NO_FLOWS: No data flow or relationship descriptions found")

    # 4. Component name check (if understanding available)
    if repo_understanding:
        components = repo_understanding.get("components", [])
        if components:
            component_names = {
                c.get("name", "").lower()
                for c in components
                if c.get("name")
            }
            # Check how many real component names appear in the text
            text_lower = section_text.lower()
            mentioned = sum(
                1 for name in component_names
                if name and len(name) > 2 and name in text_lower
            )
            # Only flag if there are components to reference and none were mentioned
            if len(component_names) >= 3 and mentioned == 0:
                issues.append(
                    "NO_COMPONENT_REFS: No real component names from the codebase mentioned"
                )

    return issues


def build_retry_hint(issues: List[str]) -> str:
    """Build a concise hint string to add to the retry prompt.

    This helps the LLM understand WHY the first attempt failed and
    what to focus on in the retry.
    """
    hints: List[str] = []

    for issue in issues:
        if issue.startswith("GENERIC_FILLER"):
            hints.append(
                "Avoid generic phrases like 'designed to', 'robust and efficient'. "
                "Be specific about WHAT the code does."
            )
        elif issue.startswith("NO_CONCRETE_REFS"):
            hints.append(
                "Reference real file paths, function names, config keys, and "
                "module names from the evidence."
            )
        elif issue.startswith("NO_FLOWS"):
            hints.append(
                "Describe at least one data flow: how data enters, transforms, "
                "and exits. Use arrows or Mermaid diagrams."
            )
        elif issue.startswith("NO_COMPONENT_REFS"):
            hints.append(
                "Mention actual components/modules by name. The system has real "
                "services — reference them."
            )

    if not hints:
        return ""

    return (
        "\n\n⚠️ RETRY GUIDANCE (your previous attempt was too generic):\n"
        + "\n".join(f"- {h}" for h in hints)
    )
