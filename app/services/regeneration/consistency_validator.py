"""
Document Consistency Validator - Phase 4.5

Lightweight LLM-based validation of regenerated sections.
Detects contradictions between sections and triggers fallback.

Safety: Never blocks, always returns result.
Performance: <500ms typical, lightweight prompt.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.llm.rotator import get_rotator
from app.services.documentation.tree_models import DocumentTree


@dataclass
class ConsistencyCheck:
    """
    Result of consistency check between two sections.
    """
    section_a: str
    section_b: str
    has_contradiction: bool = False
    contradiction_description: str = ""
    severity: str = "none"  # "none", "minor", "major", "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_a": self.section_a,
            "section_b": self.section_b,
            "has_contradiction": self.has_contradiction,
            "contradiction_description": self.contradiction_description,
            "severity": self.severity,
        }


@dataclass
class ConsistencyValidationResult:
    """
    Complete consistency validation result.
    """
    is_consistent: bool = True
    checks_performed: int = 0
    contradictions_found: int = 0
    critical_issues: int = 0
    checks: List[ConsistencyCheck] = field(default_factory=list)
    recommendation: str = ""  # "proceed", "review", "regenerate"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "checks_performed": self.checks_performed,
            "contradictions_found": self.contradictions_found,
            "critical_issues": self.critical_issues,
            "recommendation": self.recommendation,
            "checks": [c.to_dict() for c in self.checks],
        }


class DocumentConsistencyValidator:
    """
    Validates consistency across document sections.

    Strategy:
    1. Check key section pairs (summary vs architecture, api vs architecture)
    2. Use lightweight LLM prompt for contradiction detection
    3. If critical contradictions → recommend full regeneration

    Performance: Only checks critical pairs, not all combinations.
    """

    # Critical section pairs to validate
    CRITICAL_PAIRS = [
        ("summary", "architecture"),
        ("api", "architecture"),
        ("data", "architecture"),
        ("auth", "api"),
    ]

    # Maximum content length per section for validation
    MAX_CONTENT_LENGTH = 2000  # characters

    def validate(
        self,
        tree: DocumentTree,
        sections_regenerated: List[str],
    ) -> ConsistencyValidationResult:
        """
        Validate consistency of regenerated sections.

        Args:
            tree: Updated document tree
            sections_regenerated: IDs of sections that were regenerated

        Returns:
            ConsistencyValidationResult with recommendations
        """
        result = ConsistencyValidationResult()

        try:
            # Build section lookup
            section_map = {s.section_type: s for s in tree.sections}

            # Check critical pairs
            for type_a, type_b in self.CRITICAL_PAIRS:
                section_a = section_map.get(type_a)
                section_b = section_map.get(type_b)

                if not section_a or not section_b:
                    continue

                # Only check if at least one was regenerated
                if (section_a.id not in sections_regenerated and
                        section_b.id not in sections_regenerated):
                    continue

                # Perform consistency check
                check = self._check_pair_consistency(section_a, section_b)
                result.checks.append(check)
                result.checks_performed += 1

                if check.has_contradiction:
                    result.contradictions_found += 1
                    if check.severity in ["major", "critical"]:
                        result.critical_issues += 1

            # Determine recommendation
            if result.critical_issues > 0:
                result.is_consistent = False
                result.recommendation = "regenerate"
            elif result.contradictions_found > 0:
                result.is_consistent = False
                result.recommendation = "review"
            else:
                result.is_consistent = True
                result.recommendation = "proceed"

            return result

        except Exception as e:
            print(f"⚠️ Consistency validation failed (non-fatal): {e}")
            # Fail open: assume consistent to avoid blocking
            return ConsistencyValidationResult(
                is_consistent=True,
                recommendation="proceed",
            )

    def _check_pair_consistency(self, section_a, section_b) -> ConsistencyCheck:
        """
        Check consistency between two sections using lightweight LLM.
        """
        check = ConsistencyCheck(
            section_a=section_a.title,
            section_b=section_b.title,
        )

        try:
            # Truncate content for efficiency
            content_a = section_a.content[:self.MAX_CONTENT_LENGTH]
            content_b = section_b.content[:self.MAX_CONTENT_LENGTH]

            # Build lightweight prompt
            prompt = self._build_validation_prompt(
                section_a.title, content_a,
                section_b.title, content_b,
            )

            # Call LLM
            rotator = get_rotator()
            llm_result = rotator.generate_with_rotation(prompt, max_tokens=150)

            if not llm_result or not llm_result.content:
                # No response = assume consistent
                return check

            # Parse response
            response = llm_result.content.strip().lower()

            # Check for contradiction indicators
            if "contradiction: yes" in response or "contradiction:true" in response:
                check.has_contradiction = True

                # Extract severity
                if "severity: critical" in response:
                    check.severity = "critical"
                elif "severity: major" in response:
                    check.severity = "major"
                elif "severity: minor" in response:
                    check.severity = "minor"

                # Extract description
                if "description:" in response:
                    parts = response.split("description:", 1)
                    if len(parts) > 1:
                        check.contradiction_description = parts[1].strip()[
                            :200]

            return check

        except Exception as e:
            print(f"⚠️ Pair consistency check failed: {e}")
            # Fail open
            return check

    def _build_validation_prompt(
        self,
        title_a: str, content_a: str,
        title_b: str, content_b: str,
    ) -> str:
        """
        Build lightweight validation prompt.

        Designed for quick yes/no contradiction detection.
        """
        return f"""Check for contradictions between two documentation sections.

Section A ({title_a}):
```
{content_a}
```

Section B ({title_b}):
```
{content_b}
```

Do these sections contradict each other on any factual claims, technology versions, or architectural decisions?

Respond in this exact format:
Contradiction: [Yes/No]
Severity: [None/Minor/Major/Critical]
Description: [Brief description if Yes, else "None"]

Be strict but fair. Minor wording differences are not contradictions."""


# ============================================================================
# Convenience Functions
# ============================================================================

_validator_instance: Optional[DocumentConsistencyValidator] = None


def get_consistency_validator() -> DocumentConsistencyValidator:
    """Get singleton validator."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DocumentConsistencyValidator()
    return _validator_instance


def validate_document_consistency(
    tree: DocumentTree,
    sections_regenerated: List[str],
) -> ConsistencyValidationResult:
    """
    Convenience function for consistency validation.

    This is the main entry point.
    """
    try:
        validator = get_consistency_validator()
        return validator.validate(tree, sections_regenerated)
    except Exception as e:
        print(f"⚠️ Consistency validation failed (non-fatal): {e}")
        # Fail open: assume consistent
        return ConsistencyValidationResult(
            is_consistent=True,
            recommendation="proceed",
        )
