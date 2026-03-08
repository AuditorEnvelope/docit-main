"""
Extractor Runner - Phase 3

Orchestrates multiple extractors and merges their results.
Handles error isolation and performance monitoring.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base_extractor import BaseExtractor, ExtractionResult
from .semantic_snapshot import SemanticSnapshot, merge_snapshots


class ExtractorRunner:
    """
    Runs multiple extractors and merges their results into a SemanticSnapshot.

    Design:
    - Isolates extractor errors (one failure doesn't affect others)
    - Tracks performance per extractor
    - Merges partial results intelligently
    """

    def __init__(self):
        """Initialize runner with empty extractor registry."""
        self._extractors: List[Type[BaseExtractor]] = []
        self._stats = {
            "runs": 0,
            "total_time_ms": 0.0,
            "extractor_results": {},
        }

    def register(self, extractor_class: Type[BaseExtractor]) -> "ExtractorRunner":
        """
        Register an extractor class.

        Args:
            extractor_class: Class inheriting from BaseExtractor

        Returns:
            Self for method chaining
        """
        self._extractors.append(extractor_class)
        return self

    def run_all(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> SemanticSnapshot:
        """
        Run all registered extractors and merge results.

        Args:
            repo_path: Path to repository root
            repo_analysis: Repository analysis data

        Returns:
            SemanticSnapshot with merged signals

        Safety:
            Never fails - returns empty snapshot if all extractors fail
        """
        start_time = time.time()
        snapshots = []
        errors = []
        extractors_run = []

        print("🔎 Running semantic extractors...")

        for extractor_class in self._extractors:
            try:
                # Instantiate extractor
                extractor = extractor_class()

                # Check if can run
                if not extractor.can_run(repo_analysis):
                    continue

                # Run extraction
                result = extractor.run_extraction(repo_path, repo_analysis)
                extractors_run.append(extractor.name)

                # Track stats
                self._stats["extractor_results"][extractor.name] = {
                    "success": result.success,
                    "time_ms": result.execution_time_ms,
                    "files_scanned": result.files_scanned,
                }

                if result.success:
                    # Convert result to snapshot
                    snapshot = self._result_to_snapshot(result)
                    snapshots.append(snapshot)

                    # Log success
                    signal_count = len(result.signals)
                    print(f"✅ {extractor.name}: {signal_count} signals "
                          f"({result.execution_time_ms:.1f}ms)")
                else:
                    error_msg = f"{extractor.name}: {result.error_message}"
                    errors.append(error_msg)
                    print(f"⚠️ {extractor.name} failed: {result.error_message}")

            except Exception as e:
                import traceback
                error_msg = f"{extractor_class.__name__}: {str(e)}"
                errors.append(error_msg)
                print(f"⚠️ {extractor_class.__name__} crashed: {e}")
                print(f"   Full traceback:")
                traceback.print_exc()

        # Merge all snapshots
        if snapshots:
            final_snapshot = merge_snapshots(snapshots)
        else:
            final_snapshot = SemanticSnapshot()

        # Add metadata
        final_snapshot.extractors_run = extractors_run
        final_snapshot.extraction_errors = errors
        final_snapshot.extraction_time_ms = (time.time() - start_time) * 1000

        # Update runner stats
        self._stats["runs"] += 1
        self._stats["total_time_ms"] += final_snapshot.extraction_time_ms

        print(f"📊 Semantic snapshot built: "
              f"{len(final_snapshot.signals)} signals, "
              f"{final_snapshot.extraction_time_ms:.1f}ms")

        return final_snapshot

    def _result_to_snapshot(self, result: ExtractionResult) -> SemanticSnapshot:
        """Convert ExtractionResult to SemanticSnapshot."""
        snapshot = SemanticSnapshot()
        signals = result.signals

        # Map common signal keys to snapshot fields
        if "primary_framework" in signals:
            snapshot.primary_framework = signals["primary_framework"]
        if "framework_version" in signals:
            snapshot.framework_version = signals["framework_version"]
        if "detected_routes" in signals:
            snapshot.detected_routes = signals["detected_routes"]
        if "api_patterns" in signals:
            snapshot.api_patterns = signals["api_patterns"]
        if "auth_patterns" in signals:
            snapshot.auth_patterns = signals["auth_patterns"]
        if "auth_middleware" in signals:
            snapshot.auth_middleware = signals["auth_middleware"]
        if "infra_features" in signals:
            snapshot.infra_features = signals["infra_features"]
        if "deployment_target" in signals:
            snapshot.deployment_target = signals["deployment_target"]
        if "data_layer" in signals:
            snapshot.data_layer = signals["data_layer"]
        if "database_type" in signals:
            snapshot.database_type = signals["database_type"]
        if "orm_patterns" in signals:
            snapshot.orm_patterns = signals["orm_patterns"]
        if "detected_languages" in signals:
            snapshot.detected_languages = signals["detected_languages"]
        if "primary_language" in signals:
            snapshot.primary_language = signals["primary_language"]
        if "testing_frameworks" in signals:
            snapshot.testing_frameworks = signals["testing_frameworks"]

        # Store all signals
        snapshot.signals = signals
        snapshot.extraction_time_ms = result.execution_time_ms
        snapshot.extractors_run = [result.extractor_name]

        return snapshot

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics."""
        return {
            "total_runs": self._stats["runs"],
            "avg_time_ms": (
                self._stats["total_time_ms"] / self._stats["runs"]
                if self._stats["runs"] > 0 else 0
            ),
            "registered_extractors": len(self._extractors),
            "extractor_results": self._stats["extractor_results"],
        }


# ============================================================================
# Global Runner Instance
# ============================================================================

_runner_instance: Optional[ExtractorRunner] = None


def get_extractor_runner() -> ExtractorRunner:
    """
    Get singleton extractor runner with all extractors registered.

    This is the main entry point for extraction.
    """
    global _runner_instance

    if _runner_instance is None:
        _runner_instance = ExtractorRunner()

        # Import and register all extractors
        # (Done here to avoid circular imports)
        try:
            from .api_extractor import APIExtractor
            _runner_instance.register(APIExtractor)
        except ImportError:
            pass

        try:
            from .auth_extractor import AuthExtractor
            _runner_instance.register(AuthExtractor)
        except ImportError:
            pass

        try:
            from .infra_extractor import InfraExtractor
            _runner_instance.register(InfraExtractor)
        except ImportError:
            pass

        try:
            from .data_extractor import DataExtractor
            _runner_instance.register(DataExtractor)
        except ImportError:
            pass

        try:
            from .frontend_extractor import FrontendExtractor
            _runner_instance.register(FrontendExtractor)
        except ImportError:
            pass

    return _runner_instance


def build_semantic_snapshot(
    repo_path: Path,
    repo_analysis: Dict[str, Any],
) -> SemanticSnapshot:
    """
    Convenience function to build semantic snapshot.

    This is the main entry point for Phase 3 extraction.

    Args:
        repo_path: Path to repository
        repo_analysis: Repository analysis data

    Returns:
        SemanticSnapshot (never fails, returns empty on error)
    """
    import traceback
    try:
        print(
            f"🔍 build_semantic_snapshot: Starting extraction for {repo_path}")
        print(f"   Repo analysis keys: {list(repo_analysis.keys())}")
        runner = get_extractor_runner()
        print(
            f"   Got extractor runner with {len(runner._extractors)} extractors")
        result = runner.run_all(repo_path, repo_analysis)
        print(
            f"   Extraction complete: {len(result.signals)} signals, errors: {result.extraction_errors}")
        return result
    except Exception as e:
        # Ultimate fallback - return empty snapshot
        print(f"⚠️ Semantic extraction failed (non-fatal): {e}")
        print(f"   Full traceback:")
        traceback.print_exc()
        return SemanticSnapshot(
            extraction_errors=[str(e)],
        )
