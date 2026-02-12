"""
Dependency Resolver - Phase 4

Matches changed files to document sections using section dependencies.
Deterministic, rule-based matching (no ML).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import re

from app.services.documentation.tree_models import DocumentTree, DocumentSection


@dataclass
class DependencyMatch:
    """
    Result of matching changed files to a section.
    """
    section_id: str
    section_title: str
    matched_files: List[str] = field(default_factory=list)
    match_reason: str = ""  # Why this section was matched
    confidence: float = 1.0  # 0.0-1.0 match confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_title": self.section_title,
            "matched_files": self.matched_files,
            "match_reason": self.match_reason,
            "confidence": self.confidence,
        }


@dataclass
class DependencyResolution:
    """
    Complete resolution of changed files to sections.
    """
    affected_sections: List[DependencyMatch] = field(default_factory=list)
    unaffected_sections: List[str] = field(default_factory=list)  # Section IDs
    unmatched_files: List[str] = field(default_factory=list)

    def get_affected_section_ids(self) -> List[str]:
        """Get list of affected section IDs."""
        return [m.section_id for m in self.affected_sections]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "affected_sections": [m.to_dict() for m in self.affected_sections],
            "unaffected_sections": self.unaffected_sections,
            "unmatched_files": self.unmatched_files,
        }


class DependencyResolver:
    """
    Resolves file changes to document section impacts.

    Uses DocumentSection.dependencies for matching.

    Matching Strategy:
    1. Direct pattern match: file path contains dependency pattern
    2. Directory match: file is in dependency directory
    3. Semantic match: file extension/type matches section type
    """

    # Section type to file extension mapping
    TYPE_EXTENSIONS = {
        "api": [".py", ".js", ".ts", ".go", ".java"],
        "architecture": [".py", ".js", ".ts", ".go", ".rs"],
        "workflow": [".yml", ".yaml", ".json", ".sh"],
        "summary": [".md", ".rst"],
    }

    def resolve(
        self,
        changed_files: List[str],
        document_tree: DocumentTree,
    ) -> DependencyResolution:
        """
        Resolve changed files to affected sections.

        Args:
            changed_files: List of changed file paths
            document_tree: Current document tree with sections

        Returns:
            DependencyResolution with affected/unaffected sections
        """
        resolution = DependencyResolution()

        # Track which files have been matched
        matched_files: Set[str] = set()

        # Check each section
        for section in document_tree.sections:
            match = self._match_section_to_changes(
                section, changed_files, matched_files
            )

            if match:
                resolution.affected_sections.append(match)
                matched_files.update(match.matched_files)
            else:
                resolution.unaffected_sections.append(section.id)

        # Find unmatched files
        resolution.unmatched_files = [
            f for f in changed_files if f not in matched_files
        ]

        return resolution

    def _match_section_to_changes(
        self,
        section: DocumentSection,
        changed_files: List[str],
        already_matched: Set[str],
    ) -> Optional[DependencyMatch]:
        """
        Check if a section is affected by changed files.

        Returns DependencyMatch if affected, None otherwise.
        """
        matched_files = []
        match_reasons = []

        for file_path in changed_files:
            if file_path in already_matched:
                continue

            # Check 1: Direct dependency pattern match
            if self._matches_dependency_pattern(file_path, section.dependencies):
                matched_files.append(file_path)
                match_reasons.append(f"dependency_pattern_match")
                continue

            # Check 2: Section type semantic match
            if self._matches_section_type(file_path, section.section_type):
                # Lower confidence match
                matched_files.append(file_path)
                match_reasons.append(f"semantic_type_match")
                continue

        if matched_files:
            return DependencyMatch(
                section_id=section.id,
                section_title=section.title,
                matched_files=matched_files,
                match_reason="; ".join(set(match_reasons)),
                confidence=self._calculate_confidence(match_reasons),
            )

        return None

    def _matches_dependency_pattern(
        self,
        file_path: str,
        dependencies: List[str],
    ) -> bool:
        """Check if file matches any dependency pattern."""
        file_lower = file_path.lower()

        for dep in dependencies:
            dep_lower = dep.lower()

            # Direct substring match
            if dep_lower in file_lower:
                return True

            # Regex pattern match (if dep looks like regex)
            if any(c in dep for c in "*.[]()"):
                try:
                    if re.search(dep, file_path, re.IGNORECASE):
                        return True
                except re.error:
                    pass

        return False

    def _matches_section_type(
        self,
        file_path: str,
        section_type: str,
    ) -> bool:
        """Check if file semantically matches section type."""
        file_lower = file_path.lower()
        ext = Path(file_path).suffix.lower()

        # Check file extension
        relevant_exts = self.TYPE_EXTENSIONS.get(section_type, [])
        if ext in relevant_exts:
            # Additional path hints
            type_hints = {
                "api": ["api", "route", "endpoint", "controller"],
                "architecture": ["core", "lib", "src", "model"],
                "workflow": ["script", "ci", "cd", "deploy"],
            }

            hints = type_hints.get(section_type, [])
            if any(hint in file_lower for hint in hints):
                return True

        return False

    def _calculate_confidence(self, match_reasons: List[str]) -> float:
        """Calculate match confidence based on reasons."""
        if not match_reasons:
            return 0.0

        # Direct pattern matches are high confidence
        direct_matches = sum(1 for r in match_reasons if "dependency" in r)
        semantic_matches = sum(1 for r in match_reasons if "semantic" in r)

        # Weighted average
        confidence = (direct_matches * 1.0 + semantic_matches *
                      0.6) / len(match_reasons)
        return min(1.0, confidence)


# ============================================================================
# Convenience Functions
# ============================================================================

_resolver_instance: Optional[DependencyResolver] = None


def get_dependency_resolver() -> DependencyResolver:
    """Get singleton dependency resolver."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = DependencyResolver()
    return _resolver_instance


def match_changed_files_to_sections(
    changed_files: List[str],
    document_tree: DocumentTree,
) -> DependencyResolution:
    """
    Convenience function to match changed files to sections.

    This is the main entry point for dependency resolution.
    """
    try:
        resolver = get_dependency_resolver()
        return resolver.resolve(changed_files, document_tree)
    except Exception as e:
        print(f"⚠️ Dependency resolution failed (non-fatal): {e}")
        # Fallback: mark all sections as affected
        return DependencyResolution(
            affected_sections=[
                DependencyMatch(
                    section_id=section.id,
                    section_title=section.title,
                    matched_files=changed_files,
                    match_reason="fallback_all_affected",
                    confidence=0.5,
                )
                for section in document_tree.sections
            ],
            unaffected_sections=[],
            unmatched_files=[],
        )
