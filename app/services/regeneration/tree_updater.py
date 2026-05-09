"""
Document Tree Updater - Phase 4

Updates DocumentTree with regenerated sections while preserving unchanged content.
Handles fingerprint updates and tree consistency.
"""

import copy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.documentation.tree_models import DocumentTree, DocumentSection, build_section_fingerprint
from app.services.regeneration.regeneration_planner import RegenerationPlan
from app.services.regeneration.selective_generator import (
    SelectiveGenerator,
    GenerationContext,
    build_generation_context,
)


@dataclass
class TreeUpdateResult:
    """
    Result of updating a document tree.
    """
    updated_tree: DocumentTree
    sections_regenerated: List[str] = field(default_factory=list)
    sections_reused: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.updated_tree.id,
            "sections_regenerated": self.sections_regenerated,
            "sections_reused": self.sections_reused,
            "error_count": len(self.errors),
        }


class DocumentTreeUpdater:
    """
    Updates DocumentTree with selective regeneration results.

    Workflow:
    1. Clone old tree
    2. Regenerate affected sections
    3. Copy unaffected sections from old tree
    4. Update fingerprints
    5. Return updated tree
    """

    def update_tree(
        self,
        old_tree: Optional[DocumentTree],
        new_tree: DocumentTree,
        plan: RegenerationPlan,
        context: GenerationContext,
        repo_path: Path,
    ) -> TreeUpdateResult:
        """
        Update tree based on regeneration plan.

        Args:
            old_tree: Previous tree (for reusing sections)
            new_tree: Current tree structure (may have new sections)
            plan: Regeneration plan
            context: Generation context
            repo_path: Repository path

        Returns:
            TreeUpdateResult with updated tree
        """
        result = TreeUpdateResult(updated_tree=new_tree)

        # Get generator
        generator = SelectiveGenerator()

        # Track existing sections for context building
        existing_sections: Dict[str, str] = {}

        # Process each section
        for section in new_tree.sections:
            if section.id in plan.sections_to_regenerate:
                # Regenerate this section
                try:
                    new_content = generator.generate_section(
                        section, context, repo_path
                    )
                    section.content = new_content
                    section.updated_at = datetime.utcnow()

                    # Update fingerprint
                    section.fingerprint = build_section_fingerprint(section)

                    result.sections_regenerated.append(section.id)

                    # Add to existing sections for context
                    existing_sections[section.section_type] = new_content
                    context.existing_sections[section.section_type] = new_content

                except Exception as e:
                    error_msg = f"Failed to regenerate {section.id}: {e}"
                    result.errors.append(error_msg)
                    print(f"⚠️ {error_msg}")

                    # Try to reuse from old tree if available
                    if old_tree:
                        old_section = old_tree.get_section_by_id(section.id)
                        if old_section:
                            section.content = old_section.content
                            section.fingerprint = old_section.fingerprint
                            result.sections_reused.append(section.id)

            elif section.id in plan.sections_to_reuse and old_tree:
                # Reuse from old tree
                old_section = old_tree.get_section_by_id(section.id)
                if old_section:
                    section.content = old_section.content
                    section.fingerprint = old_section.fingerprint
                    # Update timestamp to show it was considered
                    section.updated_at = datetime.utcnow()

                    result.sections_reused.append(section.id)
                    existing_sections[section.section_type] = old_section.content
                    context.existing_sections[section.section_type] = old_section.content
                else:
                    # Old section not found - must regenerate
                    result.sections_regenerated.append(section.id)
                    try:
                        new_content = generator.generate_section(
                            section, context, repo_path
                        )
                        section.content = new_content
                        section.fingerprint = build_section_fingerprint(
                            section)
                    except Exception as e:
                        result.errors.append(
                            f"Failed to generate {section.id}: {e}")

            else:
                # Not in either list - regenerate to be safe
                result.sections_regenerated.append(section.id)
                try:
                    new_content = generator.generate_section(
                        section, context, repo_path
                    )
                    section.content = new_content
                    section.fingerprint = build_section_fingerprint(section)
                except Exception as e:
                    result.errors.append(
                        f"Failed to generate {section.id}: {e}")

        return result

    def clone_tree(self, tree: DocumentTree) -> DocumentTree:
        """
        Create a deep copy of a document tree.

        Used to preserve old tree before modifications.
        """
        # Create new tree with same metadata
        cloned = DocumentTree(
            id=tree.id,  # Same ID for tracking
            repo_id=tree.repo_id,
            persona=tree.persona,
            repo_type=tree.repo_type,
            complexity_score=tree.complexity_score,
            commit_sha=tree.commit_sha,
            model_name=tree.model_name,
            token_usage=copy.deepcopy(tree.token_usage),
            plan_snapshot=copy.deepcopy(tree.plan_snapshot),
        )

        # Deep copy sections
        for section in tree.sections:
            cloned_section = DocumentSection(
                id=section.id,
                section_type=section.section_type,
                title=section.title,
                content=section.content,
                parent_id=section.parent_id,
                children_ids=copy.deepcopy(section.children_ids),
                dependencies=copy.deepcopy(section.dependencies),
                headings=copy.deepcopy(section.headings),
                version=section.version,
                created_at=section.created_at,
                updated_at=section.updated_at,
                fingerprint=section.fingerprint,
                metadata=copy.deepcopy(section.metadata),
            )
            cloned.add_section(cloned_section)

        return cloned


# ============================================================================
# Convenience Functions
# ============================================================================

_updater_instance: Optional[DocumentTreeUpdater] = None


def get_tree_updater() -> DocumentTreeUpdater:
    """Get singleton tree updater."""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = DocumentTreeUpdater()
    return _updater_instance


def update_document_tree(
    old_tree: Optional[DocumentTree],
    new_tree: DocumentTree,
    plan: RegenerationPlan,
    context: GenerationContext,
    repo_path: Path,
) -> TreeUpdateResult:
    """
    Convenience function to update document tree.

    This is the main entry point.
    """
    try:
        updater = get_tree_updater()
        return updater.update_tree(old_tree, new_tree, plan, context, repo_path)
    except Exception as e:
        print(f"⚠️ Tree update failed: {e}")
        # Return new tree as-is (may have partial updates)
        return TreeUpdateResult(
            updated_tree=new_tree,
            errors=[str(e)],
        )
