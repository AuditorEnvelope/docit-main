"""
Regeneration Planner - Phase 4

Decision logic for selective vs full regeneration.
Considers impact analysis, change magnitude, and safety thresholds.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.regeneration.impact_engine import ImpactAnalysis


@dataclass
class RegenerationPlan:
    """
    Complete regeneration plan with execution instructions.
    """
    # Strategy
    strategy: str = "full"  # "full" or "selective"
    reason: str = ""

    # Sections
    sections_to_regenerate: List[str] = field(default_factory=list)
    sections_to_reuse: List[str] = field(default_factory=list)

    # Context for generation
    context: Dict[str, Any] = field(default_factory=dict)

    # Statistics
    estimated_token_savings: int = 0
    estimated_time_savings_ms: int = 0

    # Safety
    fallback_to_full: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "reason": self.reason,
            "sections_to_regenerate": self.sections_to_regenerate,
            "sections_to_reuse": self.sections_to_reuse,
            "estimated_token_savings": self.estimated_token_savings,
            "estimated_time_savings_ms": self.estimated_time_savings_ms,
            "fallback_to_full": self.fallback_to_full,
        }


class RegenerationPlanner:
    """
    Plans regeneration strategy based on impact analysis.

    Decision Logic:
    1. If impact_analysis.full_regeneration → full regeneration
    2. If affected_sections > 50% → full regeneration
    3. Else → selective regeneration

    Token Savings Estimation:
    - Based on content length of sections to reuse
    - Assumes ~1 token per 4 characters
    """

    # Thresholds
    SELECTIVE_REGEN_THRESHOLD = 0.5  # 50% of sections
    MIN_SECTIONS_FOR_SELECTIVE = 2   # Need at least 2 sections

    def create_plan(
        self,
        impact_analysis: ImpactAnalysis,
        section_content_lengths: Optional[Dict[str, int]] = None,
    ) -> RegenerationPlan:
        """
        Create regeneration plan from impact analysis.

        Args:
            impact_analysis: Result from SectionImpactEngine
            section_content_lengths: Map of section_id to content length (for savings calc)

        Returns:
            RegenerationPlan with execution strategy
        """
        plan = RegenerationPlan()

        # Decision: Full or Selective
        if impact_analysis.full_regeneration:
            plan.strategy = "full"
            plan.reason = impact_analysis.full_regeneration_reason
            plan.sections_to_regenerate = impact_analysis.get_regenerate_ids()
            plan.sections_to_reuse = []
            plan.estimated_token_savings = 0

        elif self._should_use_full_regeneration(impact_analysis):
            plan.strategy = "full"
            plan.reason = "threshold_crossed"
            plan.sections_to_regenerate = (
                impact_analysis.get_regenerate_ids() +
                impact_analysis.get_reuse_ids()
            )
            plan.sections_to_reuse = []
            plan.estimated_token_savings = 0

        else:
            plan.strategy = "selective"
            plan.reason = "partial_impact"
            plan.sections_to_regenerate = impact_analysis.get_regenerate_ids()
            plan.sections_to_reuse = impact_analysis.get_reuse_ids()

            # Calculate savings
            if section_content_lengths:
                plan.estimated_token_savings = self._estimate_token_savings(
                    plan.sections_to_reuse,
                    section_content_lengths,
                )

        # Build context for generation
        plan.context = self._build_generation_context(impact_analysis)

        return plan

    def _should_use_full_regeneration(self, impact_analysis: ImpactAnalysis) -> bool:
        """Determine if full regeneration is more efficient."""
        total = impact_analysis.total_sections
        affected = impact_analysis.affected_count

        # Not enough sections for selective to be worthwhile
        if total < self.MIN_SECTIONS_FOR_SELECTIVE:
            return True

        # Too many sections affected
        if affected / total > self.SELECTIVE_REGEN_THRESHOLD:
            return True

        return False

    def _estimate_token_savings(
        self,
        sections_to_reuse: List[str],
        section_content_lengths: Dict[str, int],
    ) -> int:
        """
        Estimate token savings from selective regeneration.

        Rough estimate: ~1 token per 4 characters
        """
        total_chars = 0
        for section_id in sections_to_reuse:
            length = section_content_lengths.get(section_id, 0)
            total_chars += length

        # ~4 chars per token (rough estimate)
        return total_chars // 4

    def _build_generation_context(
        self,
        impact_analysis: ImpactAnalysis,
    ) -> Dict[str, Any]:
        """Build context dictionary for generation phase."""
        return {
            "total_sections": impact_analysis.total_sections,
            "affected_sections": impact_analysis.affected_count,
            "unaffected_sections": impact_analysis.unaffected_count,
            "full_regeneration_trigger": impact_analysis.full_regeneration_reason,
        }


# ============================================================================
# Feature Flag
# ============================================================================

# Feature flag for selective regeneration
# Set to True to enable, False to always use full regeneration
ENABLE_SELECTIVE_REGEN = False


def is_selective_regeneration_enabled() -> bool:
    """Check if selective regeneration is enabled."""
    return ENABLE_SELECTIVE_REGEN


def set_selective_regeneration_enabled(enabled: bool) -> None:
    """Enable or disable selective regeneration."""
    global ENABLE_SELECTIVE_REGEN
    ENABLE_SELECTIVE_REGEN = enabled


# ============================================================================
# Convenience Functions
# ============================================================================

_planner_instance: Optional[RegenerationPlanner] = None


def get_regeneration_planner() -> RegenerationPlanner:
    """Get singleton regeneration planner."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = RegenerationPlanner()
    return _planner_instance


def create_regeneration_plan(
    impact_analysis: ImpactAnalysis,
    section_content_lengths: Optional[Dict[str, int]] = None,
) -> RegenerationPlan:
    """
    Convenience function to create regeneration plan.

    Respects ENABLE_SELECTIVE_REGEN feature flag.
    """
    try:
        # Check feature flag
        if not is_selective_regeneration_enabled():
            # Force full regeneration
            return RegenerationPlan(
                strategy="full",
                reason="feature_flag_disabled",
                sections_to_regenerate=impact_analysis.get_regenerate_ids() +
                impact_analysis.get_reuse_ids(),
                sections_to_reuse=[],
                estimated_token_savings=0,
            )

        planner = get_regeneration_planner()
        return planner.create_plan(impact_analysis, section_content_lengths)

    except Exception as e:
        print(f"⚠️ Regeneration planning failed (non-fatal): {e}")
        # Fallback to full regeneration
        return RegenerationPlan(
            strategy="full",
            reason=f"error_fallback: {e}",
            sections_to_regenerate=impact_analysis.get_regenerate_ids() +
            impact_analysis.get_reuse_ids(),
            sections_to_reuse=[],
            fallback_to_full=True,
        )
