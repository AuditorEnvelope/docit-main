"""
Semantic Extraction Layer - Phase 3: Lightweight signal extraction

Provides structured semantic signals for improved documentation planning,
dynamic headings, and future selective regeneration.

Design Principles:
- LIGHTWEIGHT: <200ms typical execution
- DETERMINISTIC: No LLM calls, pure Python
- SAFE: Never fails generation, graceful fallback
- INTERNAL: Backward compatible, no external changes

Extractors:
- APIExtractor: Detects routes, endpoints, frameworks
- AuthExtractor: Detects auth patterns (JWT, OAuth, etc.)
- InfraExtractor: Detects deployment infrastructure
- DataExtractor: Detects database/ORM patterns
- FrontendExtractor: Detects React, Vue, Angular frontend patterns
"""

from .semantic_snapshot import SemanticSnapshot, merge_snapshots
from .extractor_runner import ExtractorRunner, get_extractor_runner, build_semantic_snapshot
from .base_extractor import BaseExtractor, ExtractionResult

__all__ = [
    "SemanticSnapshot",
    "merge_snapshots",
    "build_semantic_snapshot",
    "ExtractorRunner",
    "get_extractor_runner",
    "BaseExtractor",
    "ExtractionResult",
]
