"""
Git Diff Analyzer - Phase 4

Lightweight analysis of commit changes to detect impacted files and domains.
Deterministic, fast, no heavy parsing.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ChangeAnalysis:
    """
    Structured analysis of a git commit's changes.

    Lightweight representation for impact detection.
    """
    added_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)

    # Semantic grouping (optional, for advanced impact detection)
    domains_detected: List[str] = field(default_factory=list)

    # Metadata
    total_files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    commit_message: str = ""
    commit_sha: str = ""

    def get_all_changed_files(self) -> List[str]:
        """Get union of all changed files."""
        return self.added_files + self.modified_files + self.deleted_files

    def has_changes_in_domain(self, domain: str) -> bool:
        """Check if changes affect a specific domain (api, auth, etc.)."""
        return domain in self.domains_detected

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "added_files": self.added_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "domains_detected": self.domains_detected,
            "total_files_changed": self.total_files_changed,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "commit_message": self.commit_message,
            "commit_sha": self.commit_sha,
        }


class GitDiffAnalyzer:
    """
    Analyzes git commit changes for impact detection.

    Design:
    - Lightweight: No heavy diff parsing
    - Deterministic: Same commit → same analysis
    - Fast: <10ms typical
    """

    # Domain detection patterns
    DOMAIN_PATTERNS = {
        "api": [r"api", r"routes", r"endpoints", r"controllers", r"handlers"],
        "auth": [r"auth", r"login", r"oauth", r"jwt", r"session", r"security"],
        "database": [r"models", r"schema", r"migration", r"db", r"orm"],
        "infra": [r"docker", r"k8s", r"terraform", r"deploy", r"\.github"],
        "frontend": [r"components", r"pages", r"ui", r"css", r"scss"],
        "config": [r"config", r"settings", r"\.env", r"requirements", r"package\.json"],
        "tests": [r"test", r"spec", r"__tests__"],
    }

    def analyze_commit(
        self,
        changed_files: List[str],
        commit_message: str = "",
        commit_sha: str = "",
        lines_added: int = 0,
        lines_deleted: int = 0,
    ) -> ChangeAnalysis:
        """
        Analyze a commit's changes.

        Args:
            changed_files: List of changed file paths
            commit_message: Commit message for semantic hints
            commit_sha: Commit SHA for tracking
            lines_added: Lines added (if available)
            lines_deleted: Lines deleted (if available)

        Returns:
            ChangeAnalysis with categorized changes
        """
        analysis = ChangeAnalysis(
            commit_message=commit_message,
            commit_sha=commit_sha,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
        )

        # Categorize files
        for file_path in changed_files:
            # Determine if added, modified, or deleted
            # (This would come from actual git diff in production)
            if self._is_likely_new_file(file_path, commit_message):
                analysis.added_files.append(file_path)
            elif self._is_likely_deleted_file(file_path, commit_message):
                analysis.deleted_files.append(file_path)
            else:
                analysis.modified_files.append(file_path)

        # Detect domains
        analysis.domains_detected = self._detect_domains(
            analysis.get_all_changed_files(),
            commit_message
        )

        analysis.total_files_changed = len(changed_files)

        return analysis

    def _is_likely_new_file(self, file_path: str, commit_message: str) -> bool:
        """Heuristic: is this likely a new file?"""
        new_indicators = ["add", "create", "introduce", "new"]
        return any(ind in commit_message.lower() for ind in new_indicators)

    def _is_likely_deleted_file(self, file_path: str, commit_message: str) -> bool:
        """Heuristic: is this likely a deleted file?"""
        delete_indicators = ["remove", "delete", "drop", "cleanup"]
        return any(ind in commit_message.lower() for ind in delete_indicators)

    def _detect_domains(
        self,
        file_paths: List[str],
        commit_message: str,
    ) -> List[str]:
        """Detect which domains are affected by changes."""
        domains = set()

        # Check file paths
        for file_path in file_paths:
            path_lower = file_path.lower()
            for domain, patterns in self.DOMAIN_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, path_lower):
                        domains.add(domain)
                        break

        # Check commit message for hints
        message_lower = commit_message.lower()
        for domain in self.DOMAIN_PATTERNS.keys():
            if domain in message_lower:
                domains.add(domain)

        return sorted(list(domains))

    def estimate_change_magnitude(
        self,
        analysis: ChangeAnalysis,
    ) -> str:
        """
        Estimate the magnitude of changes.

        Returns: "small", "medium", "large"
        """
        total = analysis.total_files_changed

        if total <= 3:
            return "small"
        elif total <= 10:
            return "medium"
        else:
            return "large"


# ============================================================================
# Convenience Functions
# ============================================================================

_analyzer_instance: Optional[GitDiffAnalyzer] = None


def get_diff_analyzer() -> GitDiffAnalyzer:
    """Get singleton diff analyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GitDiffAnalyzer()
    return _analyzer_instance


def analyze_commit_changes(
    changed_files: List[str],
    commit_message: str = "",
    commit_sha: str = "",
    **kwargs
) -> ChangeAnalysis:
    """
    Convenience function to analyze commit changes.

    This is the main entry point for diff analysis.
    """
    try:
        analyzer = get_diff_analyzer()
        return analyzer.analyze_commit(
            changed_files=changed_files,
            commit_message=commit_message,
            commit_sha=commit_sha,
            **kwargs
        )
    except Exception as e:
        # Non-fatal fallback
        print(f"⚠️ Diff analysis failed (non-fatal): {e}")
        return ChangeAnalysis(
            modified_files=changed_files,
            commit_message=commit_message,
            commit_sha=commit_sha,
        )
