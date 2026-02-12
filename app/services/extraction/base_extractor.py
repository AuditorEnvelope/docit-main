"""
Base Extractor Interface - Phase 3

Defines the contract for all semantic extractors.
Each extractor is lightweight, deterministic, and focused on a single concern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class ExtractionResult:
    """
    Result from a single extractor.

    Contains extracted signals and metadata about the extraction process.
    """
    success: bool = True
    extractor_name: str = ""
    signals: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 0.0-1.0 confidence in extraction
    error_message: Optional[str] = None
    files_scanned: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "extractor": self.extractor_name,
            "signals": self.signals,
            "confidence": self.confidence,
            "files_scanned": self.files_scanned,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


class BaseExtractor(ABC):
    """
    Abstract base class for all semantic extractors.

    Design Principles:
    - Fast: Target <50ms per extractor
    - Safe: Never raise exceptions to caller
    - Focused: Single responsibility per extractor
    - Deterministic: Same input → same output
    """

    # Maximum file size to read (bytes) - prevents reading huge files
    MAX_FILE_SIZE = 100 * 1024  # 100KB

    # Maximum lines to scan per file
    MAX_LINES_PER_FILE = 200

    def __init__(self):
        """Initialize extractor."""
        self.name = self.__class__.__name__

    @abstractmethod
    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """
        Check if this extractor can run on the given repository.

        Args:
            repo_analysis: Repository analysis from comprehensive.py

        Returns:
            True if extractor should run, False otherwise
        """
        pass

    @abstractmethod
    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """
        Extract semantic signals from repository.

        Args:
            repo_path: Path to repository root
            repo_analysis: Repository analysis data

        Returns:
            ExtractionResult with signals

        Safety:
            Must never raise exceptions. Return ExtractionResult(success=False) on error.
        """
        pass

    def get_target_files(self, repo_path: Path) -> List[Path]:
        """
        Get list of files to scan.

        Override in subclasses to target specific file patterns.
        Default implementation returns empty list (subclasses must override).
        """
        return []

    def safe_read_file(self, file_path: Path, max_bytes: Optional[int] = None) -> str:
        """
        Safely read file contents with size limits.

        Args:
            file_path: Path to file
            max_bytes: Maximum bytes to read (default: MAX_FILE_SIZE)

        Returns:
            File contents or empty string if error
        """
        try:
            max_bytes = max_bytes or self.MAX_FILE_SIZE

            # Check file size first
            if file_path.stat().st_size > max_bytes:
                # Read only first N bytes
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(max_bytes)

            # Read full file
            return file_path.read_text(encoding='utf-8', errors='ignore')

        except Exception as e:
            # Silent failure - return empty
            return ""

    def scan_file_lines(
        self,
        file_path: Path,
        patterns: Dict[str, str],
    ) -> Dict[str, List[str]]:
        """
        Scan file for regex patterns, line by line.

        Efficient for large files - stops after MAX_LINES_PER_FILE.

        Args:
            file_path: Path to file
            patterns: Dict of {pattern_name: regex_pattern}

        Returns:
            Dict of {pattern_name: [matching_lines]}
        """
        import re
        results = {name: [] for name in patterns.keys()}
        compiled = {name: re.compile(pattern, re.IGNORECASE)
                    for name, pattern in patterns.items()}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= self.MAX_LINES_PER_FILE:
                        break

                    for name, regex in compiled.items():
                        if regex.search(line):
                            results[name].append(line.strip())

        except Exception:
            pass

        return results

    def find_files_by_patterns(
        self,
        repo_path: Path,
        include_patterns: List[str],
        exclude_dirs: Optional[Set[str]] = None,
        max_files: int = 20,
    ) -> List[Path]:
        """
        Find files matching patterns, with limits.

        Args:
            repo_path: Repository root
            include_patterns: Glob patterns to include (e.g., "*.py", "routes/*.js")
            exclude_dirs: Directory names to exclude
            max_files: Maximum files to return

        Returns:
            List of file paths
        """
        exclude_dirs = exclude_dirs or {
            'node_modules', '.git', '__pycache__', 'venv', 'env',
            'dist', 'build', '.pytest_cache', '.mypy_cache'
        }

        found = []

        try:
            for pattern in include_patterns:
                for file_path in repo_path.rglob(pattern):
                    # Skip excluded directories
                    if any(part in exclude_dirs for part in file_path.parts):
                        continue

                    if file_path.is_file():
                        found.append(file_path)

                        if len(found) >= max_files:
                            return found

        except Exception:
            pass

        return found

    def run_extraction(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """
        Wrapper that handles timing and error handling.

        Args:
            repo_path: Repository path
            repo_analysis: Analysis data

        Returns:
            ExtractionResult (never raises)
        """
        import time

        start_time = time.time()

        try:
            result = self.extract(repo_path, repo_analysis)
            result.extractor_name = self.name
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            # Never fail - return error result
            return ExtractionResult(
                success=False,
                extractor_name=self.name,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
