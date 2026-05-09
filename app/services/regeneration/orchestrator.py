"""
Selective Regeneration Orchestrator - Phase 4

Main entry point for intelligent selective regeneration.
Orchestrates the entire pipeline from commit to updated documentation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.documentation.tree_models import DocumentTree, get_cached_tree, cache_tree
from app.services.extraction import build_semantic_snapshot
from app.services.regeneration.diff_analyzer import analyze_commit_changes, ChangeAnalysis
from app.services.regeneration.dependency_resolver import match_changed_files_to_sections
from app.services.regeneration.impact_engine import analyze_section_impact
from app.services.regeneration.regeneration_planner import create_regeneration_plan, is_selective_regeneration_enabled
from app.services.regeneration.selective_generator import build_generation_context
from app.services.regeneration.tree_updater import update_document_tree

# Phase 4.5: Safety imports
from app.services.regeneration.consistency_validator import validate_document_consistency
from app.services.regeneration.chain_limiter import (
    get_chain_limiter,
    record_regeneration_completed,
)


@dataclass
class RegenerationResult:
    """
    Complete result of selective regeneration process.

    Phase 4.5: Added safety metrics.
    """
    success: bool = True
    strategy: str = "full"  # "full" or "selective"
    tree: Optional[DocumentTree] = None
    sections_regenerated: List[str] = field(default_factory=list)
    sections_reused: List[str] = field(default_factory=list)
    token_savings: int = 0
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    # Phase 4.5: Safety metrics
    confidence_score: float = 1.0
    consistency_check_passed: bool = True
    chain_position: int = 0  # Position in selective regeneration chain
    safety_fallback_reason: str = ""  # Why fallback occurred

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy,
            "sections_regenerated": self.sections_regenerated,
            "sections_reused": self.sections_reused,
            "token_savings": self.token_savings,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error_count": len(self.errors),
            "confidence_score": self.confidence_score,
            "consistency_check_passed": self.consistency_check_passed,
            "chain_position": self.chain_position,
            "safety_fallback_reason": self.safety_fallback_reason,
        }


class SelectiveRegenerationOrchestrator:
    """
    Orchestrates the complete selective regeneration pipeline.

    Pipeline:
        1. Analyze commit changes
        2. Build semantic snapshot
        3. Match dependencies
        4. Analyze impact
        5. Plan regeneration
        6. Execute generation
        7. Update tree
    """

    def regenerate(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
        changed_files: List[str],
        commit_message: str = "",
        commit_sha: str = "",
        persona: str = "internal",
        old_tree: Optional[DocumentTree] = None,
    ) -> RegenerationResult:
        """
        Execute selective regeneration pipeline.

        Args:
            repo_path: Path to repository
            repo_analysis: Repository analysis
            changed_files: List of changed file paths
            commit_message: Commit message
            commit_sha: Commit SHA
            persona: Documentation persona
            old_tree: Previous document tree (if available)

        Returns:
            RegenerationResult with updated tree
        """
        import time
        start_time = time.time()

        result = RegenerationResult()

        try:
            print("=" * 60)
            print("🔄 Phase 4.5: Selective Regeneration Pipeline (with Safety)")
            print("=" * 60)

            # Phase 4.5: Check chain limit before proceeding
            print("\n🔗 Step 0: Checking regeneration chain limit...")
            limiter = get_chain_limiter()
            chain_allowed, chain_reason = limiter.check_and_update(
                repo_id=str(repo_path.name),
                persona=persona,
                commit_sha=commit_sha,
                is_selective=True,  # Assume selective for pre-check
            )

            if not chain_allowed:
                print(f"   ⚠️ Chain limit reached: {chain_reason}")
                print("   → Forcing full regeneration")
                result.safety_fallback_reason = chain_reason
                result.strategy = "full"
                # Continue with full regeneration
            else:
                print(f"   Chain status: {chain_reason}")
                result.chain_position = limiter.get_chain_state(
                    str(repo_path.name), persona
                ).selective_regen_count if limiter.get_chain_state(
                    str(repo_path.name), persona
                ) else 0

            # Step 1: Analyze commit changes
            print("\n📊 Step 1: Analyzing commit changes...")
            change_analysis = analyze_commit_changes(
                changed_files=changed_files,
                commit_message=commit_message,
                commit_sha=commit_sha,
            )
            print(f"   Files changed: {change_analysis.total_files_changed}")
            print(
                f"   Domains: {', '.join(change_analysis.domains_detected) or 'none'}")

            # Step 2: Build semantic snapshot
            print("\n🔎 Step 2: Building semantic snapshot...")
            new_semantic_snapshot = build_semantic_snapshot(
                repo_path, repo_analysis)
            old_semantic_snapshot = (
                old_tree.plan_snapshot if old_tree else None
            )

            # Step 3: Get or create new tree structure
            print("\n🌳 Step 3: Preparing document tree...")
            if old_tree:
                # Clone old tree as base
                from app.services.regeneration.tree_updater import get_tree_updater
                new_tree = get_tree_updater().clone_tree(old_tree)
                print(f"   Cloned existing tree: {new_tree.id[:8]}")
            else:
                # Build new tree from scratch
                from app.services.documentation.tree_builder import build_document_tree
                from app.services.documentation.planner import get_planner

                planner = get_planner()
                plan = planner.create_plan(
                    repo_analysis,
                    semantic_snapshot=new_semantic_snapshot.to_dict()
                )

                # Create minimal tree structure
                new_tree = DocumentTree(
                    repo_id=str(repo_path.name),
                    persona=persona,
                    repo_type=plan.repo_type,
                    complexity_score=plan.complexity_score,
                    commit_sha=commit_sha,
                    plan_snapshot=plan.to_dict() if hasattr(plan, 'to_dict') else {},
                )

                # Add sections from plan
                for section_plan in plan.sections:
                    from app.services.documentation.tree_models import DocumentSection
                    section = DocumentSection(
                        id=section_plan.id,
                        section_type=section_plan.type,
                        title=section_plan.title,
                        content="",  # Will be generated
                        dependencies=section_plan.dependencies,
                    )
                    new_tree.add_section(section)

                print(f"   Created new tree: {new_tree.id[:8]}")

            # Step 4: Match dependencies
            print("\n🔗 Step 4: Resolving dependencies...")
            dependency_resolution = match_changed_files_to_sections(
                changed_files=changed_files,
                document_tree=new_tree,
            )
            print(
                f"   Affected sections: {len(dependency_resolution.affected_sections)}")
            print(
                f"   Unaffected sections: {len(dependency_resolution.unaffected_sections)}")

            # Step 5: Analyze impact
            print("\n💥 Step 5: Analyzing section impact...")
            impact_analysis = analyze_section_impact(
                old_tree=old_tree,
                new_tree=new_tree,
                change_analysis=change_analysis,
                dependency_resolution=dependency_resolution,
                old_semantic_snapshot=old_semantic_snapshot,
                new_semantic_snapshot=new_semantic_snapshot.to_dict(),
            )
            print(
                f"   Sections to regenerate: {impact_analysis.affected_count}")
            print(f"   Sections to reuse: {impact_analysis.unaffected_count}")
            print(
                f"   Confidence score: {impact_analysis.confidence_score:.2f}")

            if impact_analysis.full_regeneration:
                print(
                    f"   ⚠️ Full regeneration triggered: {impact_analysis.full_regeneration_reason}")
                result.safety_fallback_reason = impact_analysis.full_regeneration_reason

            # Store confidence score
            result.confidence_score = impact_analysis.confidence_score

            # Step 6: Create regeneration plan
            print("\n📋 Step 6: Creating regeneration plan...")

            # Calculate content lengths for savings estimation
            content_lengths = {}
            if old_tree:
                for section in old_tree.sections:
                    content_lengths[section.id] = len(section.content)

            plan = create_regeneration_plan(impact_analysis, content_lengths)
            result.strategy = plan.strategy
            result.token_savings = plan.estimated_token_savings

            print(f"   Strategy: {plan.strategy}")
            print(f"   Reason: {plan.reason}")
            if plan.strategy == "selective":
                print(
                    f"   Estimated token savings: ~{plan.estimated_token_savings} tokens")

            # Step 7: Execute generation
            print("\n⚙️ Step 7: Executing regeneration...")

            # Phase 4.5: Force full if chain limit was reached
            if result.safety_fallback_reason.startswith("chain_limit"):
                plan.strategy = "full"
                plan.reason = result.safety_fallback_reason

            if plan.strategy == "full" or not is_selective_regeneration_enabled():
                # Full regeneration - use existing flow
                print("   Using full regeneration flow")
                result = self._execute_full_regeneration(
                    repo_path, repo_analysis, new_tree, result
                )

                # Phase 4.5: Record full regeneration for chain tracking
                record_regeneration_completed(
                    repo_id=str(repo_path.name),
                    persona=persona,
                    commit_sha=commit_sha,
                    was_selective=False,
                )
            else:
                # Selective regeneration
                print("   Using selective regeneration")
                context = build_generation_context(
                    repo_name=str(repo_path.name),
                    repo_analysis=repo_analysis,
                    semantic_snapshot=new_semantic_snapshot.to_dict(),
                    document_plan=new_tree.plan_snapshot or {},
                )

                update_result = update_document_tree(
                    old_tree=old_tree,
                    new_tree=new_tree,
                    plan=plan,
                    context=context,
                    repo_path=repo_path,
                )

                result.tree = update_result.updated_tree
                result.sections_regenerated = update_result.sections_regenerated
                result.sections_reused = update_result.sections_reused
                result.errors.extend(update_result.errors)

                # Phase 4.5: Run consistency validation
                print("\n✅ Step 8: Validating consistency...")
                consistency_result = validate_document_consistency(
                    tree=result.tree,
                    sections_regenerated=result.sections_regenerated,
                )

                print(
                    f"   Checks performed: {consistency_result.checks_performed}")
                print(
                    f"   Contradictions: {consistency_result.contradictions_found}")
                print(
                    f"   Recommendation: {consistency_result.recommendation}")

                result.consistency_check_passed = consistency_result.is_consistent

                # Phase 4.5: If consistency check fails, fallback to full
                if consistency_result.recommendation == "regenerate":
                    print(
                        "   ⚠️ Consistency check failed! Falling back to full regeneration...")
                    result.safety_fallback_reason = "consistency_check_failed"
                    result = self._execute_full_regeneration(
                        repo_path, repo_analysis, new_tree, result
                    )
                    record_regeneration_completed(
                        repo_id=str(repo_path.name),
                        persona=persona,
                        commit_sha=commit_sha,
                        was_selective=False,
                    )
                else:
                    # Record selective regeneration
                    record_regeneration_completed(
                        repo_id=str(repo_path.name),
                        persona=persona,
                        commit_sha=commit_sha,
                        was_selective=True,
                    )

            # Cache the updated tree
            if result.tree:
                cache_tree(result.tree)

            # Calculate execution time
            result.execution_time_ms = (time.time() - start_time) * 1000

            print("\n" + "=" * 60)
            print(f"✅ Regeneration complete: {result.strategy}")
            print(
                f"   Regenerated: {len(result.sections_regenerated)} sections")
            print(f"   Reused: {len(result.sections_reused)} sections")
            if result.token_savings > 0:
                print(f"   💰 Token savings: ~{result.token_savings} tokens")
            print(f"   Confidence: {result.confidence_score:.2f}")
            print(
                f"   Consistency: {'✓' if result.consistency_check_passed else '✗'}")
            if result.safety_fallback_reason:
                print(f"   Safety fallback: {result.safety_fallback_reason}")
            print(f"   Time: {result.execution_time_ms:.1f}ms")
            print("=" * 60)

            return result

        except Exception as e:
            error_msg = f"Selective regeneration failed: {e}"
            print(f"⚠️ {error_msg}")
            result.success = False
            result.errors.append(error_msg)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

    def _execute_full_regeneration(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
        new_tree: DocumentTree,
        result: RegenerationResult,
    ) -> RegenerationResult:
        """Execute full regeneration using existing flow."""
        # This would integrate with existing ComprehensiveDocBuilder
        # For now, mark all sections as regenerated
        result.tree = new_tree
        result.sections_regenerated = [s.id for s in new_tree.sections]
        result.sections_reused = []
        return result


# ============================================================================
# Main Entry Point
# ============================================================================

_orchestrator_instance: Optional[SelectiveRegenerationOrchestrator] = None


def get_orchestrator() -> SelectiveRegenerationOrchestrator:
    """Get singleton orchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = SelectiveRegenerationOrchestrator()
    return _orchestrator_instance


def run_selective_regeneration(
    repo_path: Path,
    repo_analysis: Dict[str, Any],
    changed_files: List[str],
    commit_message: str = "",
    commit_sha: str = "",
    persona: str = "internal",
    old_tree: Optional[DocumentTree] = None,
) -> RegenerationResult:
    """
    Main entry point for selective regeneration.

    This is the function to call from webhook handlers or API endpoints.
    """
    orchestrator = get_orchestrator()
    return orchestrator.regenerate(
        repo_path=repo_path,
        repo_analysis=repo_analysis,
        changed_files=changed_files,
        commit_message=commit_message,
        commit_sha=commit_sha,
        persona=persona,
        old_tree=old_tree,
    )
