"""
Selective Regeneration Engine - Phase 4.5

Intelligent documentation regeneration that only updates affected sections,
reducing token usage by 50%+ for small commits.

Phase 4.5: Added architectural safety guardrails:
- Structural influence map for section propagation
- Confidence scoring with threshold-based fallback
- Consistency validation with lightweight LLM checks
- Chain limiter to prevent error accumulation

Architecture:
    Git Commit → Diff Analyzer → Impact Engine → Regeneration Planner
                                             ↓
                    Old Tree ← Selective Generator → New Tree
                                             ↓
                         Consistency Validator
                                             ↓
                                    File Output (unchanged format)

Safety:
- Feature flag controlled (ENABLE_SELECTIVE_REGEN)
- Confidence threshold (0.6) triggers full regeneration
- Chain limit (3) forces full regeneration
- Consistency validation with fallback
- Graceful fallback to full regeneration
- Deterministic impact detection
- Zero external behavior changes
"""

from .diff_analyzer import GitDiffAnalyzer, analyze_commit_changes
from .dependency_resolver import DependencyResolver, match_changed_files_to_sections
from .impact_engine import SectionImpactEngine, ImpactAnalysis
from .regeneration_planner import RegenerationPlanner, RegenerationPlan
from .selective_generator import SelectiveGenerator, generate_single_section
from .tree_updater import DocumentTreeUpdater, update_document_tree

# Phase 4.5: Safety modules
from .consistency_validator import (
    DocumentConsistencyValidator,
    validate_document_consistency,
    ConsistencyValidationResult,
)
from .chain_limiter import (
    SelectiveRegenerationChainLimiter,
    get_chain_limiter,
    check_selective_regeneration_allowed,
    record_regeneration_completed,
    SELECTIVE_REGEN_CHAIN_LIMIT,
)

__all__ = [
    # Analysis
    "GitDiffAnalyzer",
    "analyze_commit_changes",
    "DependencyResolver",
    "match_changed_files_to_sections",
    # Impact & Planning
    "SectionImpactEngine",
    "ImpactAnalysis",
    "RegenerationPlanner",
    "RegenerationPlan",
    # Generation
    "SelectiveGenerator",
    "generate_single_section",
    # Update
    "DocumentTreeUpdater",
    "update_document_tree",
    # Phase 4.5: Safety
    "DocumentConsistencyValidator",
    "validate_document_consistency",
    "ConsistencyValidationResult",
    "SelectiveRegenerationChainLimiter",
    "get_chain_limiter",
    "check_selective_regeneration_allowed",
    "record_regeneration_completed",
    "SELECTIVE_REGEN_CHAIN_LIMIT",
]
