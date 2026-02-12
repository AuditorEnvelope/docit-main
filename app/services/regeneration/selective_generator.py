"""
Selective Generator - Phase 4

Generates individual sections with proper context.
Maintains consistency with full generation output.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.llm.rotator import get_rotator
from app.services.documentation.tree_models import DocumentSection


@dataclass
class GenerationContext:
    """
    Context for generating a single section.

    Ensures generated content is consistent with overall document.
    """
    repo_name: str = ""
    repo_analysis: Dict[str, Any] = field(default_factory=dict)
    semantic_snapshot: Dict[str, Any] = field(default_factory=dict)
    document_plan: Dict[str, Any] = field(default_factory=dict)

    # High-level summaries for consistency
    project_summary: str = ""  # Brief project description
    architecture_summary: str = ""  # Key architectural decisions
    existing_sections: Dict[str, str] = field(
        default_factory=dict)  # Other sections content

    def to_prompt_context(self) -> str:
        """Convert to string for LLM prompt."""
        context_parts = [
            f"Project: {self.repo_name}",
            f"Summary: {self.project_summary[:200]}" if self.project_summary else "",
        ]

        if self.architecture_summary:
            context_parts.append(
                f"Architecture: {self.architecture_summary[:300]}")

        # Add relevant existing sections for consistency
        if self.existing_sections:
            context_parts.append("\nRelated sections:")
            for section_type, content in list(self.existing_sections.items())[:2]:
                preview = content[:150].replace('\n', ' ')
                context_parts.append(f"  {section_type}: {preview}...")

        return "\n".join(filter(None, context_parts))


class SelectiveGenerator:
    """
    Generates individual document sections.

    Uses context from other sections to maintain consistency.
    """

    # Section type to prompt template mapping
    SECTION_TEMPLATES = {
        "summary": """Generate a project overview section.

Context:
{context}

Repository Analysis:
{repo_analysis}

Generate a concise project summary (200-400 words) covering:
- What the project does
- Key features
- Technology stack
- Target audience

Format as markdown.""",

        "architecture": """Generate an architecture section.

Context:
{context}

Repository Analysis:
{repo_analysis}

Semantic Signals:
{semantic_signals}

Generate an architecture overview (300-600 words) covering:
- System components
- Data flow
- Key design decisions
- Integration points

Format as markdown with headings.""",

        "workflow": """Generate a development workflow section.

Context:
{context}

Repository Analysis:
{repo_analysis}

Generate workflow documentation (200-400 words) covering:
- Setup instructions
- Development process
- Testing approach
- Deployment steps

Format as markdown with steps.""",

        "api": """Generate an API documentation section.

Context:
{context}

Repository Analysis:
{repo_analysis}

Semantic Signals (Routes):
{semantic_signals}

Generate API documentation (300-600 words) covering:
- Authentication (if applicable)
- Base URL
- Key endpoints
- Request/response examples

Format as markdown with code blocks.""",
    }

    def generate_section(
        self,
        section: DocumentSection,
        context: GenerationContext,
        repo_path: Path,
    ) -> str:
        """
        Generate content for a single section.

        Args:
            section: Section to generate
            context: Generation context for consistency
            repo_path: Repository path

        Returns:
            Generated markdown content
        """
        # Build prompt
        prompt = self._build_prompt(section, context)

        # Generate with LLM
        rotator = get_rotator()
        result = rotator.generate_with_rotation(prompt)

        if result and result.content:
            return result.content
        else:
            # Fallback: return placeholder
            return f"# {section.title}\n\nContent generation failed. Please regenerate."

    def _build_prompt(
        self,
        section: DocumentSection,
        context: GenerationContext,
    ) -> str:
        """Build generation prompt for section."""
        template = self.SECTION_TEMPLATES.get(
            section.section_type,
            self.SECTION_TEMPLATES["summary"]  # Default fallback
        )

        # Truncate analysis to avoid token bloat
        repo_analysis_str = json.dumps(context.repo_analysis, indent=2)[:2000]
        semantic_signals_str = json.dumps(
            context.semantic_snapshot, indent=2)[:1500]

        return template.format(
            context=context.to_prompt_context(),
            repo_analysis=repo_analysis_str,
            semantic_signals=semantic_signals_str,
        )

    def generate_multiple_sections(
        self,
        sections: List[DocumentSection],
        context: GenerationContext,
        repo_path: Path,
    ) -> Dict[str, str]:
        """
        Generate multiple sections efficiently.

        Updates context with generated sections for consistency.
        """
        results = {}

        for section in sections:
            content = self.generate_section(section, context, repo_path)
            results[section.id] = content

            # Update context for subsequent sections
            context.existing_sections[section.section_type] = content

        return results


# ============================================================================
# Convenience Functions
# ============================================================================

_generator_instance: Optional[SelectiveGenerator] = None


def get_selective_generator() -> SelectiveGenerator:
    """Get singleton selective generator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SelectiveGenerator()
    return _generator_instance


def generate_single_section(
    section: DocumentSection,
    context: GenerationContext,
    repo_path: Path,
) -> str:
    """
    Convenience function to generate a single section.

    This is the main entry point.
    """
    try:
        generator = get_selective_generator()
        return generator.generate_section(section, context, repo_path)
    except Exception as e:
        print(f"⚠️ Section generation failed for {section.id}: {e}")
        # Return fallback content
        return f"# {section.title}\n\nError generating content: {e}\n\nPlease regenerate this section."


def build_generation_context(
    repo_name: str,
    repo_analysis: Dict[str, Any],
    semantic_snapshot: Dict[str, Any],
    document_plan: Dict[str, Any],
    existing_sections: Optional[Dict[str, str]] = None,
) -> GenerationContext:
    """
    Build generation context from available data.

    Extracts high-level summaries for consistency.
    """
    context = GenerationContext(
        repo_name=repo_name,
        repo_analysis=repo_analysis,
        semantic_snapshot=semantic_snapshot,
        document_plan=document_plan,
        existing_sections=existing_sections or {},
    )

    # Extract project summary from repo analysis
    if "description" in repo_analysis:
        context.project_summary = repo_analysis["description"]
    elif "readme_preview" in repo_analysis:
        context.project_summary = repo_analysis["readme_preview"][:500]

    # Extract architecture summary from semantic snapshot
    if semantic_snapshot:
        framework = semantic_snapshot.get("primary_framework", "")
        infra = ", ".join(semantic_snapshot.get("infra_features", [])[:3])
        if framework or infra:
            context.architecture_summary = f"Built with {framework}. Infrastructure: {infra}"

    return context
