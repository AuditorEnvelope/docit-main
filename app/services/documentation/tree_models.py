"""
Document Tree Models - Phase 2/2.5: Internal structured representation with fingerprints

This module introduces an INTERNAL document tree abstraction that represents
generated documentation as a structured graph without changing external behavior.

Phase 2 Behavior:
- Parses generated markdown into structured sections
- Builds DocumentTree with metadata and relationships
- Stores tree in-memory (no DB migration required)
- Returns original flat structure for backward compatibility

Phase 2.5 Enhancement:
- Section fingerprints for deterministic change detection
- Enables diff-to-section mapping
- Prepares for selective regeneration

Future Phases:
- Phase 3: Persist tree to database
- Phase 4: Use tree for section-level regeneration
- Phase 5: User customization of tree structure

IMPORTANT: This is INTERNAL ONLY. External APIs and file output remain unchanged.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Set
from uuid import uuid4
import hashlib
import json
import re


@dataclass
class DocumentSection:
    """
    Represents a single section within the document tree.

    This is an INTERNAL representation - external consumers still see flat markdown.

    Phase 2.5: Added fingerprint for deterministic change detection.
    """
    id: str  # Unique identifier (e.g., "sec-summary", "sec-arch-auth")
    section_type: Literal["summary",
                          "architecture", "workflow", "api", "custom"]
    title: str  # Display title
    content: str  # Markdown content

    # Hierarchy support (for Phase 4+ nested sections)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)

    # Metadata for regeneration and dependencies
    dependencies: List[str] = field(default_factory=list)  # File patterns
    headings: List[Dict[str, Any]] = field(
        default_factory=list)  # Extracted headings

    # Versioning and tracking
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Phase 2.5: Section fingerprint for change detection
    fingerprint: Optional[str] = None  # SHA256 hash of deterministic content

    # Source tracking (which LLM/model generated this)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary for serialization."""
        return {
            "id": self.id,
            "section_type": self.section_type,
            "title": self.title,
            "content": self.content,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "dependencies": self.dependencies,
            "headings": self.headings,
            "version": self.version,
            "fingerprint": self.fingerprint,  # Phase 2.5
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }

    def extract_headings(self) -> List[Dict[str, Any]]:
        """
        Extract heading hierarchy from content.

        Returns list of dicts: {"level": int, "text": str, "anchor": str}
        """
        headings = []
        # Match markdown headings: ## Heading Text
        pattern = r'^(#{1,6})\s+(.+)$'

        for line in self.content.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                hashes, text = match.groups()
                level = len(hashes)
                # Create anchor (lowercase, hyphenated)
                anchor = re.sub(r'[^\w\s-]', '', text.lower())
                anchor = re.sub(r'[-\s]+', '-', anchor).strip('-')

                headings.append({
                    "level": level,
                    "text": text.strip(),
                    "anchor": anchor,
                })

        self.headings = headings
        return headings


@dataclass
class DocumentTree:
    """
    Complete document tree for a repository + persona combination.

    This is the INTERNAL representation. External systems still receive:
    {"summary": "...", "architecture": "...", "workflow": "...", "api": "..."}
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    repo_id: Optional[str] = None  # Repository identifier
    persona: str = "internal"  # Documentation persona

    # Tree structure
    sections: List[DocumentSection] = field(default_factory=list)

    # Metadata
    repo_type: str = "generic"  # From planner
    complexity_score: int = 5  # From planner
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # Source tracking
    commit_sha: Optional[str] = None
    model_name: Optional[str] = None  # Which LLM generated this
    token_usage: Dict[str, int] = field(default_factory=dict)

    # Planner integration (store the plan that guided generation)
    plan_snapshot: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize any computed fields after creation."""
        if not self.sections:
            self.sections = []

    def get_section_by_id(self, section_id: str) -> Optional[DocumentSection]:
        """Find a section by its unique ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def get_sections_by_type(self, section_type: str) -> List[DocumentSection]:
        """Get all sections of a specific type."""
        return [s for s in self.sections if s.section_type == section_type]

    def get_root_sections(self) -> List[DocumentSection]:
        """Get top-level sections (no parent)."""
        return [s for s in self.sections if s.parent_id is None]

    def get_children(self, parent_id: str) -> List[DocumentSection]:
        """Get all child sections of a given parent."""
        return [s for s in self.sections if s.parent_id == parent_id]

    def add_section(self, section: DocumentSection) -> None:
        """Add a section to the tree."""
        self.sections.append(section)
        # Update parent's children list if applicable
        if section.parent_id:
            parent = self.get_section_by_id(section.parent_id)
            if parent and section.id not in parent.children_ids:
                parent.children_ids.append(section.id)

    def to_flat_dict(self) -> Dict[str, str]:
        """
        Convert tree to flat dictionary format (for backward compatibility).

        Returns: {"summary": "...", "architecture": "...", "workflow": "...", "api": "..."}
        """
        flat = {}

        # Map section types to expected keys
        type_to_key = {
            "summary": "summary",
            "architecture": "architecture",
            "workflow": "workflow",
            "api": "api",
        }

        for section in self.sections:
            key = type_to_key.get(section.section_type)
            if key and key not in flat:
                # Use first section of each type as the main content
                flat[key] = section.content

        return flat

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire tree to dictionary for serialization/debugging."""
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "persona": self.persona,
            "sections": [s.to_dict() for s in self.sections],
            "repo_type": self.repo_type,
            "complexity_score": self.complexity_score,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "commit_sha": self.commit_sha,
            "model_name": self.model_name,
            "token_usage": self.token_usage,
            "plan_snapshot": self.plan_snapshot,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get tree statistics for logging/debugging."""
        return {
            "total_sections": len(self.sections),
            "by_type": {
                "summary": len(self.get_sections_by_type("summary")),
                "architecture": len(self.get_sections_by_type("architecture")),
                "workflow": len(self.get_sections_by_type("workflow")),
                "api": len(self.get_sections_by_type("api")),
                "custom": len(self.get_sections_by_type("custom")),
            },
            "root_sections": len(self.get_root_sections()),
            "total_headings": sum(len(s.headings) for s in self.sections),
            "total_content_length": sum(len(s.content) for s in self.sections),
        }


# ============================================================================
# Tree Builder Helper Functions
# ============================================================================

def create_section_id(section_type: str, index: int = 0, suffix: str = "") -> str:
    """Generate a unique section ID."""
    base = f"sec-{section_type}"
    if index > 0:
        base += f"-{index}"
    if suffix:
        base += f"-{suffix}"
    return base


def parse_markdown_headings(content: str) -> List[Dict[str, Any]]:
    """
    Extract heading hierarchy from markdown content.

    Args:
        content: Markdown text

    Returns:
        List of dicts with keys: level, text, anchor
    """
    headings = []
    pattern = r'^(#{1,6})\s+(.+)$'

    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            hashes, text = match.groups()
            level = len(hashes)
            # Create URL-friendly anchor
            anchor = re.sub(r'[^\w\s-]', '', text.lower())
            anchor = re.sub(r'[-\s]+', '-', anchor).strip('-')

            headings.append({
                "level": level,
                "text": text.strip(),
                "anchor": anchor,
            })

    return headings


def estimate_section_complexity(content: str) -> int:
    """
    Estimate section complexity (1-10) based on content analysis.

    Used for token optimization and regeneration prioritization.
    """
    score = 5  # Default medium

    # Length factor
    length = len(content)
    if length > 5000:
        score += 2
    elif length > 2000:
        score += 1
    elif length < 500:
        score -= 1

    # Heading depth factor (more headings = more complex)
    headings = parse_markdown_headings(content)
    if len(headings) > 10:
        score += 2
    elif len(headings) > 5:
        score += 1

    # Code block factor
    code_blocks = content.count('```')
    if code_blocks > 10:
        score += 1

    # Clamp to 1-10
    return max(1, min(10, score))


# ============================================================================
# In-Memory Tree Cache (Phase 2: No database persistence yet)
# ============================================================================

# Simple in-memory cache for document trees
# Key: f"{repo_id}:{persona}:{commit_sha}"
_tree_cache: Dict[str, DocumentTree] = {}


def cache_tree(tree: DocumentTree) -> str:
    """
    Cache a document tree in memory.

    Returns cache key for retrieval.
    """
    key = f"{tree.repo_id}:{tree.persona}:{tree.commit_sha or 'latest'}"
    _tree_cache[key] = tree
    return key


def get_cached_tree(repo_id: str, persona: str = "internal", commit_sha: str = "latest") -> Optional[DocumentTree]:
    """Retrieve a cached document tree."""
    key = f"{repo_id}:{persona}:{commit_sha}"
    return _tree_cache.get(key)


def clear_tree_cache(repo_id: Optional[str] = None) -> None:
    """Clear tree cache (optionally for specific repo)."""
    global _tree_cache
    if repo_id:
        _tree_cache = {k: v for k, v in _tree_cache.items(
        ) if not k.startswith(f"{repo_id}:")}
    else:
        _tree_cache = {}


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    return {
        "cached_trees": len(_tree_cache),
        "total_sections": sum(len(t.sections) for t in _tree_cache.values()),
    }


# ============================================================================
# Phase 2.5: Section Fingerprint Utilities
# ============================================================================

def build_section_fingerprint(section: DocumentSection) -> Optional[str]:
    """
    Build deterministic fingerprint for a document section.

    Fingerprint is SHA256 hash of:
    - Normalized content (stripped trailing whitespace)
    - Sorted dependencies list
    - Headings structure (level and text only)
    - Section type

    EXCLUDES (non-deterministic):
    - Timestamps
    - UUIDs
    - Version numbers
    - Metadata dict

    Args:
        section: DocumentSection to fingerprint

    Returns:
        Hexadecimal fingerprint string or None if failed

    Performance: O(n) where n = content length
    """
    try:
        # Build deterministic components
        components = []

        # 1. Section type (deterministic)
        components.append(f"type:{section.section_type}")

        # 2. Normalized content (strip trailing whitespace, normalize newlines)
        normalized_content = section.content.rstrip().replace('\r\n', '\n')
        components.append(f"content:{normalized_content}")

        # 3. Sorted dependencies (deterministic ordering)
        sorted_deps = sorted(section.dependencies)
        components.append(f"deps:{','.join(sorted_deps)}")

        # 4. Headings structure (level + text only, no anchors)
        headings_structure = []
        for heading in section.headings:
            # Only include level and text (anchor is derived)
            headings_structure.append(f"{heading['level']}:{heading['text']}")
        components.append(f"headings:{';'.join(headings_structure)}")

        # 5. Title (normalized)
        normalized_title = section.title.strip()
        components.append(f"title:{normalized_title}")

        # Build composite string
        composite = "|".join(components)

        # Generate SHA256 hash
        fingerprint = hashlib.sha256(composite.encode('utf-8')).hexdigest()

        return fingerprint

    except Exception as e:
        # NEVER fail - return None on error
        print(
            f"⚠️ Fingerprint generation failed for section {section.id}: {e}")
        return None


def compare_section_fingerprints(
    old_tree: Optional[DocumentTree],
    new_tree: DocumentTree,
) -> Dict[str, Any]:
    """
    Compare two document trees and identify changed sections.

    This is the foundation for Phase 4 selective regeneration.

    Args:
        old_tree: Previous document tree (None if first generation)
        new_tree: Current document tree

    Returns:
        Dict with keys:
            - changed: List of section IDs with different fingerprints
            - unchanged: List of section IDs with same fingerprints
            - added: List of new section IDs
            - removed: List of removed section IDs
            - summary: Human-readable summary
    """
    result = {
        "changed": [],
        "unchanged": [],
        "added": [],
        "removed": [],
        "summary": {},
    }

    if not new_tree:
        result["summary"] = {"error": "No new tree provided"}
        return result

    # Build fingerprint maps
    old_fingerprints: Dict[str, Optional[str]] = {}
    if old_tree:
        old_fingerprints = {
            s.id: s.fingerprint
            for s in old_tree.sections
            if s.fingerprint
        }

    new_fingerprints: Dict[str, Optional[str]] = {
        s.id: s.fingerprint
        for s in new_tree.sections
        if s.fingerprint
    }

    old_ids = set(old_fingerprints.keys())
    new_ids = set(new_fingerprints.keys())

    # Find added sections (in new, not in old)
    added_ids = new_ids - old_ids
    result["added"] = list(added_ids)

    # Find removed sections (in old, not in new)
    removed_ids = old_ids - new_ids
    result["removed"] = list(removed_ids)

    # Find changed and unchanged sections (in both)
    common_ids = old_ids & new_ids
    for section_id in common_ids:
        old_fp = old_fingerprints.get(section_id)
        new_fp = new_fingerprints.get(section_id)

        if old_fp and new_fp:
            if old_fp == new_fp:
                result["unchanged"].append(section_id)
            else:
                result["changed"].append(section_id)
        else:
            # Missing fingerprint - treat as changed to be safe
            result["changed"].append(section_id)

    # Build summary
    total_old = len(old_ids) if old_tree else 0
    total_new = len(new_ids)

    result["summary"] = {
        "total_old_sections": total_old,
        "total_new_sections": total_new,
        "changed_count": len(result["changed"]),
        "unchanged_count": len(result["unchanged"]),
        "added_count": len(result["added"]),
        "removed_count": len(result["removed"]),
        "change_percentage": (
            round(len(result["changed"]) / total_new * 100, 1)
            if total_new > 0 else 0
        ),
    }

    return result


def get_fingerprint_stats(tree: DocumentTree) -> Dict[str, Any]:
    """
    Get fingerprint statistics for a document tree.

    Useful for debugging and monitoring.
    """
    sections_with_fp = [s for s in tree.sections if s.fingerprint]
    sections_without_fp = [s for s in tree.sections if not s.fingerprint]

    return {
        "total_sections": len(tree.sections),
        "with_fingerprint": len(sections_with_fp),
        "without_fingerprint": len(sections_without_fp),
        "coverage_percentage": (
            round(len(sections_with_fp) / len(tree.sections) * 100, 1)
            if tree.sections else 0
        ),
        "unique_fingerprints": len(set(s.fingerprint for s in sections_with_fp)),
        "sample_fingerprints": [
            {"section_id": s.id, "fingerprint": s.fingerprint[:16] + "..."}
            for s in sections_with_fp[:3]
        ],
    }


def find_section_by_fingerprint(
    tree: DocumentTree,
    fingerprint: str,
) -> Optional[DocumentSection]:
    """
    Find a section by its fingerprint.

    Useful for tracking sections across regenerations.
    """
    for section in tree.sections:
        if section.fingerprint == fingerprint:
            return section
    return None
