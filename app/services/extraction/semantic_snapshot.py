"""
Semantic Snapshot Model - Phase 3

Lightweight dataclass representing extracted semantic signals from a repository.
This is the unified output of all extractors, used by DocumentationPlanner.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class SemanticSnapshot:
    """
    Lightweight semantic snapshot of repository structure.

    Contains high-level signals for documentation planning.
    All fields are optional - extractors contribute what they can find.
    """

    # Primary framework detection
    # "fastapi", "express", "django", etc.
    primary_framework: Optional[str] = None
    framework_version: Optional[str] = None

    # API layer signals
    detected_routes: List[Dict[str, Any]] = field(default_factory=list)
    # Example: [{"method": "GET", "path": "/users", "handler": "get_users"}]

    api_patterns: List[str] = field(default_factory=list)
    # Example: ["rest", "graphql", "websocket"]

    # Authentication signals
    auth_patterns: List[str] = field(default_factory=list)
    # Example: ["jwt", "oauth2", "session", "api_key"]

    auth_middleware: List[str] = field(default_factory=list)
    # Example: ["auth_middleware", "jwt_required"]

    # Infrastructure signals
    infra_features: List[str] = field(default_factory=list)
    # Example: ["docker", "kubernetes", "github_actions", "terraform"]

    deployment_target: Optional[str] = None  # "aws", "gcp", "azure", "vercel"

    # Data layer signals
    data_layer: Optional[str] = None  # "sqlalchemy", "prisma", "mongoose"
    database_type: Optional[str] = None  # "postgresql", "mysql", "mongodb"

    orm_patterns: List[str] = field(default_factory=list)
    # Example: ["sqlalchemy", "alembic", "prisma"]

    # Language/runtime signals
    detected_languages: List[str] = field(default_factory=list)
    # Example: ["python", "typescript", "go"]

    primary_language: Optional[str] = None

    # Testing signals
    testing_frameworks: List[str] = field(default_factory=list)
    # Example: ["pytest", "jest", "cypress"]

    # Additional signals (extensible)
    signals: Dict[str, Any] = field(default_factory=dict)
    # Free-form signals from extractors

    # Extraction metadata
    extraction_time_ms: float = 0.0
    extractors_run: List[str] = field(default_factory=list)
    extraction_errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary_framework": self.primary_framework,
            "framework_version": self.framework_version,
            "detected_routes": self.detected_routes,
            "api_patterns": self.api_patterns,
            "auth_patterns": self.auth_patterns,
            "auth_middleware": self.auth_middleware,
            "infra_features": self.infra_features,
            "deployment_target": self.deployment_target,
            "data_layer": self.data_layer,
            "database_type": self.database_type,
            "orm_patterns": self.orm_patterns,
            "detected_languages": self.detected_languages,
            "primary_language": self.primary_language,
            "testing_frameworks": self.testing_frameworks,
            "signals": self.signals,
            "extraction_time_ms": round(self.extraction_time_ms, 2),
            "extractors_run": self.extractors_run,
            "extraction_errors": self.extraction_errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def has_api_layer(self) -> bool:
        """Check if repository has detectable API layer."""
        return bool(
            self.detected_routes or
            self.api_patterns or
            self.primary_framework in ["fastapi", "express", "django", "flask"]
        )

    def has_auth_layer(self) -> bool:
        """Check if repository has authentication."""
        return bool(self.auth_patterns or self.auth_middleware)

    def has_data_layer(self) -> bool:
        """Check if repository has database/ORM layer."""
        return bool(
            self.data_layer or
            self.database_type or
            self.orm_patterns
        )

    def has_deployment_config(self) -> bool:
        """Check if repository has deployment/infrastructure config."""
        return bool(self.infra_features or self.deployment_target)

    def get_complexity_score(self) -> int:
        """
        Estimate repository complexity (1-10) based on signals.

        Used for documentation planning.
        """
        score = 5  # Default medium

        # Framework complexity
        if self.primary_framework:
            score += 1

        # API complexity
        route_count = len(self.detected_routes)
        if route_count > 20:
            score += 2
        elif route_count > 10:
            score += 1

        # Auth complexity
        if self.has_auth_layer():
            score += 1

        # Data complexity
        if self.has_data_layer():
            score += 1

        # Infra complexity
        if self.has_deployment_config():
            score += 1

        # Language diversity
        if len(self.detected_languages) > 2:
            score += 1

        return min(10, score)

    def get_suggested_sections(self) -> List[Dict[str, str]]:
        """
        Get suggested documentation sections based on signals.

        Returns list of dicts with "id", "title", "type" keys.
        """
        suggestions = []

        # API sections
        if self.has_api_layer():
            suggestions.append({
                "id": "api-overview",
                "title": "API Overview",
                "type": "api"
            })

            if self.detected_routes:
                suggestions.append({
                    "id": "api-endpoints",
                    "title": "API Endpoints",
                    "type": "api"
                })

        # Auth sections
        if self.has_auth_layer():
            suggestions.append({
                "id": "authentication",
                "title": "Authentication & Authorization",
                "type": "architecture"
            })

        # Data sections
        if self.has_data_layer():
            suggestions.append({
                "id": "data-layer",
                "title": "Data Layer",
                "type": "architecture"
            })

        # Infra sections
        if self.has_deployment_config():
            suggestions.append({
                "id": "deployment",
                "title": "Deployment & Infrastructure",
                "type": "architecture"
            })

        # Testing sections
        if self.testing_frameworks:
            suggestions.append({
                "id": "testing",
                "title": "Testing Strategy",
                "type": "workflow"
            })

        return suggestions


# ============================================================================
# Convenience Functions
# ============================================================================

def merge_snapshots(snapshots: List[SemanticSnapshot]) -> SemanticSnapshot:
    """
    Merge multiple partial snapshots into one.

    Used when combining results from multiple extractors.
    """
    merged = SemanticSnapshot()

    for snapshot in snapshots:
        # Framework (first non-None wins)
        if not merged.primary_framework and snapshot.primary_framework:
            merged.primary_framework = snapshot.primary_framework
            merged.framework_version = snapshot.framework_version

        # Lists (extend, deduplicate)
        merged.detected_routes.extend(snapshot.detected_routes)
        merged.api_patterns = list(
            set(merged.api_patterns + snapshot.api_patterns))
        merged.auth_patterns = list(
            set(merged.auth_patterns + snapshot.auth_patterns))
        merged.auth_middleware = list(
            set(merged.auth_middleware + snapshot.auth_middleware))
        merged.infra_features = list(
            set(merged.infra_features + snapshot.infra_features))
        merged.orm_patterns = list(
            set(merged.orm_patterns + snapshot.orm_patterns))
        merged.detected_languages = list(
            set(merged.detected_languages + snapshot.detected_languages))
        merged.testing_frameworks = list(
            set(merged.testing_frameworks + snapshot.testing_frameworks))

        # Data layer (first non-None wins)
        if not merged.data_layer and snapshot.data_layer:
            merged.data_layer = snapshot.data_layer
            merged.database_type = snapshot.database_type

        # Deployment (first non-None wins)
        if not merged.deployment_target and snapshot.deployment_target:
            merged.deployment_target = snapshot.deployment_target

        # Primary language (first non-None wins)
        if not merged.primary_language and snapshot.primary_language:
            merged.primary_language = snapshot.primary_language

        # Signals (merge dicts)
        merged.signals.update(snapshot.signals)

        # Metadata
        merged.extractors_run.extend(snapshot.extractors_run)
        merged.extraction_errors.extend(snapshot.extraction_errors)
        merged.extraction_time_ms += snapshot.extraction_time_ms

    # Deduplicate routes
    seen = set()
    unique_routes = []
    for route in merged.detected_routes:
        key = (route.get("method", ""), route.get("path", ""))
        if key not in seen:
            seen.add(key)
            unique_routes.append(route)
    merged.detected_routes = unique_routes

    return merged
