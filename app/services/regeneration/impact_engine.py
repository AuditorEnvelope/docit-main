"""
Section Impact Engine - Phase 4

Determines which sections need regeneration based on:
- Fingerprint changes
- Dependency matches
- Semantic structural shifts

Deterministic rule-based engine (no ML).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from app.services.documentation.tree_models import DocumentTree, compare_section_fingerprints
from app.services.regeneration.diff_analyzer import ChangeAnalysis
from app.services.regeneration.dependency_resolver import DependencyResolution


@dataclass
class SectionImpact:
    """
    Impact assessment for a single section.
    """
    section_id: str
    section_title: str
    should_regenerate: bool = False
    impact_reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_title": self.section_title,
            "should_regenerate": self.should_regenerate,
            "impact_reasons": self.impact_reasons,
            "confidence": self.confidence,
        }


@dataclass
class ImpactAnalysis:
    """
    Complete impact analysis for a regeneration decision.

    Phase 4.5: Added confidence scoring for safety.
    """
    regenerate_sections: List[SectionImpact] = field(default_factory=list)
    reuse_sections: List[SectionImpact] = field(default_factory=list)
    full_regeneration: bool = False
    full_regeneration_reason: str = ""

    # Statistics
    total_sections: int = 0
    affected_count: int = 0
    unaffected_count: int = 0

    # Phase 4.5: Confidence scoring
    confidence_score: float = 1.0  # 0.0-1.0 overall confidence
    confidence_factors: Dict[str, float] = field(default_factory=dict)

    def get_regenerate_ids(self) -> List[str]:
        """Get IDs of sections to regenerate."""
        return [s.section_id for s in self.regenerate_sections]

    def get_reuse_ids(self) -> List[str]:
        """Get IDs of sections to reuse."""
        return [s.section_id for s in self.reuse_sections]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regenerate_sections": [s.to_dict() for s in self.regenerate_sections],
            "reuse_sections": [s.to_dict() for s in self.reuse_sections],
            "full_regeneration": self.full_regeneration,
            "full_regeneration_reason": self.full_regeneration_reason,
            "total_sections": self.total_sections,
            "affected_count": self.affected_count,
            "unaffected_count": self.unaffected_count,
            "confidence_score": round(self.confidence_score, 2),
            "confidence_factors": self.confidence_factors,
        }


class SectionImpactEngine:
    """
    Analyzes impact of changes on document sections.

    Phase 4.5: Added structural influence map and confidence scoring.

    Decision Rules:
    1. Dependency match → regenerate (primary signal)
    2. Structural influence → propagate to related sections
    3. Structural shift detected → regenerate affected sections
    4. >50% sections affected → full regeneration
    5. Confidence < 0.6 → full regeneration (safety)
    """

    # Phase 4.5: Structural influence map
    # Defines which section types influence others
    SECTION_INFLUENCE_MAP = {
        "auth": ["architecture", "api"],
        "api": ["architecture"],
        "infra": ["architecture"],
        "data": ["architecture", "api"],
    }

    # Structural shift indicators
    STRUCTURAL_SHIFTS = {
        "framework_change": [
            "primary_framework",
        ],
        "auth_introduced": [
            "auth_patterns",
        ],
        "infra_added": [
            "infra_features",
        ],
        "data_layer_change": [
            "data_layer",
            "database_type",
        ],
    }

    # Phase 4.5: Confidence thresholds
    CONFIDENCE_THRESHOLD_FULL_REGEN = 0.6  # Below this = full regeneration

    def analyze_impact(
        self,
        old_tree: Optional[DocumentTree],
        new_tree: DocumentTree,
        change_analysis: ChangeAnalysis,
        dependency_resolution: DependencyResolution,
        old_semantic_snapshot: Optional[Dict[str, Any]] = None,
        new_semantic_snapshot: Optional[Dict[str, Any]] = None,
    ) -> ImpactAnalysis:
        """
        Analyze impact and determine which sections to regenerate.

        Args:
            old_tree: Previous document tree (None for first generation)
            new_tree: Current document tree
            change_analysis: Analysis of commit changes
            dependency_resolution: File-to-section dependency matches
            old_semantic_snapshot: Previous semantic snapshot
            new_semantic_snapshot: Current semantic snapshot

        Returns:
            ImpactAnalysis with regeneration decisions
        """
        analysis = ImpactAnalysis()
        analysis.total_sections = len(new_tree.sections)

        # Check for full regeneration triggers
        full_regen_reason = self._check_full_regeneration_triggers(
            old_tree,
            change_analysis,
            old_semantic_snapshot,
            new_semantic_snapshot,
        )

        if full_regen_reason:
            analysis.full_regeneration = True
            analysis.full_regeneration_reason = full_regen_reason
            analysis.regenerate_sections = [
                SectionImpact(
                    section_id=section.id,
                    section_title=section.title,
                    should_regenerate=True,
                    impact_reasons=["full_regeneration_triggered"],
                )
                for section in new_tree.sections
            ]
            analysis.affected_count = len(new_tree.sections)
            return analysis

        # Phase 4.5: Get dependency-affected sections (primary signal)
        dependency_affected = set(
            dependency_resolution.get_affected_section_ids())

        # Phase 4.5: Expand affected sections using structural influence map
        expanded_affected = self._expand_affected_sections(
            dependency_affected,
            new_tree,
            change_analysis.domains_detected,
        )

        # Phase 4.5: Fingerprint comparison for reuse validation only
        fingerprint_comparison = compare_section_fingerprints(
            old_tree, new_tree)
        fingerprint_mismatched = set(fingerprint_comparison.get("changed", []))

        # Analyze each section
        confidence_factors = {}
        section_confidences = []

        for section in new_tree.sections:
            impact = self._analyze_section_impact(
                section,
                expanded_affected,
                fingerprint_mismatched,
                old_semantic_snapshot,
                new_semantic_snapshot,
            )

            section_confidences.append(impact.confidence)

            if impact.should_regenerate:
                analysis.regenerate_sections.append(impact)
                analysis.affected_count += 1
            else:
                analysis.reuse_sections.append(impact)
                analysis.unaffected_count += 1

        # Phase 4.5: Calculate overall confidence score
        analysis.confidence_score = self._calculate_confidence_score(
            section_confidences,
            len(new_tree.sections),
            change_analysis,
            dependency_resolution,
        )
        analysis.confidence_factors = confidence_factors

        # Phase 4.5: Check confidence threshold
        if analysis.confidence_score < self.CONFIDENCE_THRESHOLD_FULL_REGEN:
            analysis.full_regeneration = True
            analysis.full_regeneration_reason = f"low_confidence_{analysis.confidence_score:.2f}"
            # Convert all to regenerate
            analysis.regenerate_sections.extend(analysis.reuse_sections)
            for impact in analysis.reuse_sections:
                impact.should_regenerate = True
                impact.impact_reasons.append("low_confidence_fallback")
            analysis.reuse_sections = []
            analysis.affected_count = analysis.total_sections
            analysis.unaffected_count = 0
            return analysis

        # Check if we crossed the threshold for full regeneration
        if analysis.affected_count > analysis.total_sections * 0.5:
            analysis.full_regeneration = True
            analysis.full_regeneration_reason = "threshold_crossed"
            # Convert all to regenerate
            analysis.regenerate_sections.extend(analysis.reuse_sections)
            for impact in analysis.reuse_sections:
                impact.should_regenerate = True
                impact.impact_reasons.append("threshold_crossed")
            analysis.reuse_sections = []
            analysis.affected_count = analysis.total_sections
            analysis.unaffected_count = 0

        return analysis

    def _check_full_regeneration_triggers(
        self,
        old_tree: Optional[DocumentTree],
        change_analysis: ChangeAnalysis,
        old_snapshot: Optional[Dict[str, Any]],
        new_snapshot: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Check if full regeneration should be triggered.

        Returns reason string if full regeneration needed, None otherwise.
        """
        # First generation
        if old_tree is None:
            return "first_generation"

        # Large change magnitude
        magnitude = change_analysis.total_files_changed
        if magnitude > 20:
            return f"large_change_{magnitude}_files"

        # Structural semantic shifts
        if old_snapshot and new_snapshot:
            shift = self._detect_structural_shift(old_snapshot, new_snapshot)
            if shift:
                return f"structural_shift_{shift}"

        return None

    def _detect_structural_shift(
        self,
        old_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any],
    ) -> Optional[str]:
        """
        Detect if there's a structural shift in the codebase.

        Returns shift type if detected, None otherwise.
        """
        for shift_name, keys in self.STRUCTURAL_SHIFTS.items():
            for key in keys:
                old_val = old_snapshot.get(key)
                new_val = new_snapshot.get(key)

                # Check if value changed significantly
                if old_val != new_val:
                    # For lists, check if items were added/removed
                    if isinstance(old_val, list) and isinstance(new_val, list):
                        old_set = set(str(x) for x in old_val)
                        new_set = set(str(x) for x in new_val)
                        if old_set != new_set:
                            return shift_name
                    else:
                        return shift_name

        return None

    def _expand_affected_sections(
        self,
        directly_affected: Set[str],
        tree: DocumentTree,
        domains_detected: List[str],
    ) -> Set[str]:
        """
        Phase 4.5: Expand affected sections using structural influence map.

        If 'auth' domain changed, also affect 'architecture' and 'api' sections.
        """
        expanded = set(directly_affected)

        for section in tree.sections:
            # Check if this section type should be influenced by detected domains
            for domain in domains_detected:
                influenced_types = self.SECTION_INFLUENCE_MAP.get(domain, [])
                if section.section_type in influenced_types:
                    expanded.add(section.id)

        return expanded

    def _calculate_confidence_score(
        self,
        section_confidences: List[float],
        total_sections: int,
        change_analysis,
        dependency_resolution,
    ) -> float:
        """
        Phase 4.5: Calculate overall confidence score for selective regeneration.

        Factors:
        - Average section confidence
        - Dependency match coverage
        - Change magnitude
        """
        if not section_confidences:
            return 0.0

        # Base confidence: average of section confidences
        avg_confidence = sum(section_confidences) / len(section_confidences)

        # Adjust based on dependency resolution coverage
        matched_ratio = len(
            dependency_resolution.affected_sections) / max(total_sections, 1)
        coverage_factor = min(1.0, matched_ratio * 2)  # Boost if good coverage

        # Adjust based on change magnitude
        files_changed = change_analysis.total_files_changed
        if files_changed <= 3:
            magnitude_factor = 1.0
        elif files_changed <= 10:
            magnitude_factor = 0.9
        else:
            magnitude_factor = 0.7

        # Weighted combination
        confidence = avg_confidence * 0.5 + coverage_factor * 0.3 + magnitude_factor * 0.2

        return round(min(1.0, confidence), 2)

    def _analyze_section_impact(
        self,
        section,
        affected_ids: Set[str],
        fingerprint_mismatched: Set[str],
        old_snapshot: Optional[Dict[str, Any]],
        new_snapshot: Optional[Dict[str, Any]],
    ) -> SectionImpact:
        """
        Phase 4.5: Analyze impact on a single section.

        Fingerprint mismatches now only affect confidence, not regeneration decision.
        """
        impact = SectionImpact(
            section_id=section.id,
            section_title=section.title,
        )

        reasons = []
        confidence_factors = []

        # Check 1: Dependency affected (primary signal)
        if section.id in affected_ids:
            impact.should_regenerate = True
            reasons.append("dependency_affected")
            confidence_factors.append(1.0)

        # Check 2: Semantic structural shift affecting this section type
        if old_snapshot and new_snapshot:
            if self._section_affected_by_shift(
                section.section_type,
                old_snapshot,
                new_snapshot,
            ):
                impact.should_regenerate = True
                reasons.append("semantic_structural_shift")
                confidence_factors.append(0.9)

        # Phase 4.5: Fingerprint mismatch affects confidence only
        if section.id in fingerprint_mismatched:
            confidence_factors.append(0.7)  # Slightly lower confidence
            if not impact.should_regenerate:
                # Only log for debugging - don't trigger regeneration
                reasons.append("fingerprint_mismatch_noted")

        impact.impact_reasons = reasons

        # Calculate confidence
        if confidence_factors:
            impact.confidence = sum(confidence_factors) / \
                len(confidence_factors)
        else:
            impact.confidence = 1.0  # No concerns = high confidence

        return impact

    def _section_affected_by_shift(
        self,
        section_type: str,
        old_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any],
    ) -> bool:
        """Check if a section type is affected by semantic shifts."""
        # Map section types to relevant snapshot keys
        type_to_keys = {
            "api": ["primary_framework", "detected_routes", "api_patterns"],
            "architecture": ["primary_framework", "auth_patterns", "data_layer"],
            "workflow": ["infra_features", "testing_frameworks"],
        }

        relevant_keys = type_to_keys.get(section_type, [])

        for key in relevant_keys:
            if old_snapshot.get(key) != new_snapshot.get(key):
                return True

        return False


# ============================================================================
# Convenience Functions
# ============================================================================

_engine_instance: Optional[SectionImpactEngine] = None


def get_impact_engine() -> SectionImpactEngine:
    """Get singleton impact engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SectionImpactEngine()
    return _engine_instance


def analyze_section_impact(
    old_tree: Optional[DocumentTree],
    new_tree: DocumentTree,
    change_analysis: ChangeAnalysis,
    dependency_resolution: DependencyResolution,
    old_semantic_snapshot: Optional[Dict[str, Any]] = None,
    new_semantic_snapshot: Optional[Dict[str, Any]] = None,
) -> ImpactAnalysis:
    """
    Convenience function for impact analysis.

    This is the main entry point.
    """
    try:
        engine = get_impact_engine()
        return engine.analyze_impact(
            old_tree=old_tree,
            new_tree=new_tree,
            change_analysis=change_analysis,
            dependency_resolution=dependency_resolution,
            old_semantic_snapshot=old_semantic_snapshot,
            new_semantic_snapshot=new_semantic_snapshot,
        )
    except Exception as e:
        print(f"⚠️ Impact analysis failed (non-fatal): {e}")
        # Fallback: full regeneration
        return ImpactAnalysis(
            full_regeneration=True,
            full_regeneration_reason=f"error_fallback: {e}",
            regenerate_sections=[
                SectionImpact(
                    section_id=section.id,
                    section_title=section.title,
                    should_regenerate=True,
                    impact_reasons=["error_fallback"],
                )
                for section in new_tree.sections
            ],
            total_sections=len(new_tree.sections),
            affected_count=len(new_tree.sections),
        )
