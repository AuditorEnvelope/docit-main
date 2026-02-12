"""
Document Tree Builder - Phase 2: Structured representation builder

This service builds DocumentTree instances from generated documentation.
It bridges the gap between flat LLM output and structured internal representation.

Phase 2 Behavior:
- Parses flat markdown sections into DocumentSection objects
- Builds DocumentTree with metadata and relationships
- Extracts heading hierarchy for navigation
- Attaches planner dependencies if available
- Caches tree in memory (no DB persistence yet)

Safety:
- NEVER fails - returns None on error, allowing fallback to flat structure
- Does not modify external behavior
- Logging only (no side effects)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.services.documentation.tree_models import (
    DocumentTree,
    DocumentSection,
    create_section_id,
    parse_markdown_headings,
    estimate_section_complexity,
    cache_tree,
)
from app.services.documentation.planner import DocumentationPlan, SectionPlan


class TreeBuilderError(Exception):
    """Custom exception for tree building failures (caught internally)."""
    pass


class DocumentTreeBuilder:
    """
    Builds structured DocumentTree from generated documentation.

    This is an INTERNAL service - external consumers still see flat markdown.
    """

    # Map flat output keys to section types
    KEY_TO_TYPE = {
        "summary": "summary",
        "architecture": "architecture",
        "workflow": "workflow",
        "api": "api",
    }

    # Default titles for each section type
    DEFAULT_TITLES = {
        "summary": "Project Overview",
        "architecture": "System Architecture",
        "workflow": "Development Workflow",
        "api": "API Documentation",
    }

    def __init__(self):
        """Initialize tree builder."""
        self._build_stats = {
            "trees_built": 0,
            "sections_created": 0,
            "headings_extracted": 0,
        }

    def build_tree(
        self,
        flat_docs: Dict[str, str],
        repo_id: Optional[str] = None,
        persona: str = "internal",
        plan: Optional[DocumentationPlan] = None,
        commit_sha: Optional[str] = None,
        model_name: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> Optional[DocumentTree]:
        """
        Build DocumentTree from flat documentation dictionary.

        Args:
            flat_docs: Dict with keys "summary", "architecture", "workflow", "api"
            repo_id: Repository identifier
            persona: Documentation persona
            plan: Optional DocumentationPlan for dependency mapping
            commit_sha: Git commit SHA
            model_name: LLM model used for generation
            token_usage: Token consumption data

        Returns:
            DocumentTree instance or None if build fails

        Safety:
            Never raises - returns None on any error
        """
        try:
            print("🌳 Building document tree...")

            # Validate input
            if not flat_docs or not isinstance(flat_docs, dict):
                print("⚠️ TreeBuilder: Invalid input - empty or not a dict")
                return None

            # Create tree root
            tree = DocumentTree(
                repo_id=repo_id,
                persona=persona,
                repo_type=plan.repo_type if plan else "generic",
                complexity_score=plan.complexity_score if plan else 5,
                commit_sha=commit_sha,
                model_name=model_name,
                token_usage=token_usage or {},
                plan_snapshot=plan.to_dict() if plan else None,
            )

            # Build sections from flat docs
            section_index = 0
            for key, content in flat_docs.items():
                if key in ["token_data", "plan"]:  # Skip metadata keys
                    continue

                section = self._build_section(
                    key=key,
                    content=content,
                    index=section_index,
                    plan=plan,
                )

                if section:
                    tree.add_section(section)
                    section_index += 1
                    self._build_stats["sections_created"] += 1

            # Extract headings for all sections
            for section in tree.sections:
                headings = section.extract_headings()
                self._build_stats["headings_extracted"] += len(headings)

            # Cache tree for later retrieval
            cache_key = cache_tree(tree)

            # Update stats
            self._build_stats["trees_built"] += 1

            # Log success
            stats = tree.get_statistics()
            print(f"✅ Document tree created: {stats['total_sections']} sections, "
                  f"{stats['total_headings']} headings, "
                  f"{stats['total_content_length']} chars")
            print(f"   Cache key: {cache_key}")

            return tree

        except Exception as e:
            # NEVER fail - log and return None
            print(f"⚠️ TreeBuilder error (non-fatal): {e}")
            return None

    def _build_section(
        self,
        key: str,
        content: str,
        index: int,
        plan: Optional[DocumentationPlan],
    ) -> Optional[DocumentSection]:
        """
        Build a single DocumentSection from flat content.

        Args:
            key: Section key (summary, architecture, workflow, api)
            content: Markdown content
            index: Section index for ID generation
            plan: Optional plan for dependency mapping

        Returns:
            DocumentSection or None
        """
        try:
            section_type = self.KEY_TO_TYPE.get(key, "custom")

            # Get title from plan if available, else use default
            title = self._get_section_title(section_type, plan)

            # Generate unique ID
            section_id = create_section_id(section_type, index)

            # Get dependencies from plan if available
            dependencies = self._get_dependencies(section_type, plan)

            # Build section
            section = DocumentSection(
                id=section_id,
                section_type=section_type,
                title=title,
                content=content,
                dependencies=dependencies,
                metadata={
                    "source_key": key,
                    "complexity_score": estimate_section_complexity(content),
                    "word_count": len(content.split()),
                    "line_count": len(content.split('\n')),
                },
            )

            return section

        except Exception as e:
            print(f"⚠️ Failed to build section {key}: {e}")
            return None

    def _get_section_title(self, section_type: str, plan: Optional[DocumentationPlan]) -> str:
        """Get section title from plan or use default."""
        if plan:
            # Find matching section in plan
            for planned_section in plan.sections:
                if planned_section.type == section_type:
                    return planned_section.title

        return self.DEFAULT_TITLES.get(section_type, "Untitled Section")

    def _get_dependencies(self, section_type: str, plan: Optional[DocumentationPlan]) -> List[str]:
        """Get file dependencies from plan for this section type."""
        dependencies = []

        if plan:
            for planned_section in plan.sections:
                if planned_section.type == section_type:
                    dependencies.extend(planned_section.dependencies)

        return dependencies

    def get_stats(self) -> Dict[str, int]:
        """Get builder statistics."""
        return self._build_stats.copy()


# ============================================================================
# Convenience Functions
# ============================================================================

# Singleton instance
_builder_instance: Optional[DocumentTreeBuilder] = None


def get_tree_builder() -> DocumentTreeBuilder:
    """Get singleton instance of DocumentTreeBuilder."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = DocumentTreeBuilder()
    return _builder_instance


def build_document_tree(
    flat_docs: Dict[str, str],
    repo_id: Optional[str] = None,
    persona: str = "internal",
    plan: Optional[DocumentationPlan] = None,
    commit_sha: Optional[str] = None,
    model_name: Optional[str] = None,
    token_usage: Optional[Dict[str, int]] = None,
) -> Optional[DocumentTree]:
    """
    Convenience function to build document tree.

    This is the main entry point for tree building.
    """
    builder = get_tree_builder()
    return builder.build_tree(
        flat_docs=flat_docs,
        repo_id=repo_id,
        persona=persona,
        plan=plan,
        commit_sha=commit_sha,
        model_name=model_name,
        token_usage=token_usage,
    )


def get_tree_for_repo(
    repo_id: str,
    persona: str = "internal",
    commit_sha: str = "latest",
) -> Optional[DocumentTree]:
    """
    Retrieve cached tree for a repository.

    Args:
        repo_id: Repository identifier
        persona: Documentation persona
        commit_sha: Specific commit or "latest"

    Returns:
        DocumentTree if cached, None otherwise
    """
    from app.services.documentation.tree_models import get_cached_tree
    return get_cached_tree(repo_id, persona, commit_sha)


def debug_tree_structure(tree: Optional[DocumentTree]) -> str:
    """
    Generate debug string showing tree structure.

    Useful for logging and debugging.
    """
    if not tree:
        return "No tree available"

    lines = [
        f"Document Tree: {tree.id[:8]}...",
        f"Repository: {tree.repo_id or 'unknown'}",
        f"Persona: {tree.persona}",
        f"Type: {tree.repo_type} (complexity: {tree.complexity_score}/10)",
        "",
        "Sections:",
    ]

    for section in tree.sections:
        heading_count = len(section.headings)
        content_preview = section.content[:50].replace('\n', ' ') + "..."
        lines.append(
            f"  [{section.section_type}] {section.title} "
            f"({heading_count} headings, {len(section.content)} chars)"
        )
        lines.append(f"    Preview: {content_preview}")

    return "\n".join(lines)
