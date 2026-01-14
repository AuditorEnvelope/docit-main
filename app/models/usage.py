"""
Usage Ledger Models - Immutable Usage Tracking

This module defines the ORM model for the subscription_usage table,
which implements a ledger-based billing architecture.

Key Principles:
--------------
1. APPEND-ONLY: Never update or delete usage records
2. TIME-WINDOWED: Usage is calculated by querying within entitlement windows
3. AUTOMATIC RESET: When a new billing cycle starts, old usage is ignored by queries
4. AUDIT TRAIL: Every consumption event is permanently recorded

Usage Pattern:
-------------
    # Record usage (append to ledger)
    usage = SubscriptionUsage(
        subscription_id=active_subscription.id,
        user_id=user.id,
        resource_type='docs_generated',
        amount=1,
        resource_id=str(document.id),
    )
    db.add(usage)
    await db.commit()
    
    # Calculate current usage (time-window query)
    total_used = db.query(func.sum(SubscriptionUsage.amount))\\
        .filter(
            SubscriptionUsage.subscription_id == active_sub.id,
            SubscriptionUsage.consumed_at >= active_sub.entitlement_start,
            SubscriptionUsage.consumed_at < active_sub.entitlement_end,
            SubscriptionUsage.resource_type == 'docs_generated',
        )\\
        .scalar() or 0
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base


class SubscriptionUsage(Base):
    """
    Immutable usage ledger for subscription-based billing.

    Each row represents a single consumption event (e.g., "User X generated
    a document at time T"). Usage is NEVER updated or deleted - only appended.

    This design enables:
    - Automatic usage "resets" when billing cycles change (via time-window queries)
    - Complete audit trail of all consumption
    - No race conditions from concurrent updates
    - Historical usage analysis

    Schema Details:
    ---------------
    - subscription_id: Links usage to a specific billing cycle (subscription phase)
    - user_id: Denormalized for fast user-level queries
    - resource_type: What was consumed (docs_generated, api_calls, etc.)
    - amount: Quantity consumed (typically 1 for discrete resources)
    - resource_id: Optional identifier of the specific resource (for auditing)
    - consumed_at: Timestamp used in time-window calculations

    Invariants:
    -----------
    - NEVER update amount or consumed_at after insert
    - NEVER delete rows (unless cascading from subscription/user deletion)
    - amount MUST be positive (enforced by DB constraint)
    - resource_type MUST be in allowed list (enforced by DB constraint)
    """

    __tablename__ = "subscription_usage"

    # ========================================================================
    # PRIMARY COLUMNS
    # ========================================================================

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Unique identifier for this usage event",
    )

    # ========================================================================
    # FOREIGN KEYS - What billing cycle and user is this tied to?
    # ========================================================================

    subscription_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Links usage to a specific billing cycle (subscription phase). "
                "When a new cycle starts (e.g., renewal or upgrade), this changes, "
                "automatically 'resetting' usage calculations.",
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Denormalized user reference for fast user-level queries and analytics",
    )

    # ========================================================================
    # USAGE METADATA - What was consumed?
    # ========================================================================

    resource_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of resource consumed. Valid values: "
                "'docs_generated', 'repos_connected', 'api_calls', "
                "'pages_processed', 'tokens_used'",
    )

    amount = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Quantity consumed. Typically 1 for discrete resources "
                "(docs, repos), but can be N for metered resources "
                "(tokens, pages, API calls)",
    )

    resource_id = Column(
        String(255),
        nullable=True,
        comment="Optional: ID of the specific resource created/consumed "
                "(e.g., document UUID, repository ID, API call ID). "
                "Used for audit trail and detailed analytics.",
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================

    consumed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="Timestamp when the resource was consumed. "
                "Used in time-window queries to calculate usage within "
                "the active billing cycle (entitlement window).",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Record creation timestamp for audit purposes",
    )

    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================

    # Many-to-one: SubscriptionUsage -> Subscription
    subscription = relationship(
        "Subscription",
        back_populates="usage_events",
        lazy="joined",
    )

    # Many-to-one: SubscriptionUsage -> User
    user = relationship(
        "User",
        back_populates="usage_events",
        lazy="joined",
    )

    # ========================================================================
    # TABLE-LEVEL CONSTRAINTS
    # ========================================================================

    __table_args__ = (
        # Ensure amount is always positive
        CheckConstraint(
            "amount > 0",
            name="chk_usage_positive_amount",
        ),

        # Ensure resource_type is in allowed list
        CheckConstraint(
            "resource_type IN ('docs_generated', 'repos_connected', 'api_calls', 'pages_processed', 'tokens_used')",
            name="chk_usage_valid_resource_type",
        ),

        # Composite indexes for common query patterns
        Index(
            "idx_usage_subscription_time",
            "subscription_id",
            "consumed_at",
            postgresql_using="btree",
        ),
        Index(
            "idx_usage_user_resource",
            "user_id",
            "resource_type",
            "consumed_at",
            postgresql_using="btree",
        ),

        {"comment": "Immutable usage ledger. Each row represents a consumption event. "
                    "Never UPDATE or DELETE rows - only INSERT. Usage 'resets' are "
                    "handled by time-window queries against entitlement_start/end."}
    )

    # ========================================================================
    # METHODS
    # ========================================================================

    def __repr__(self) -> str:
        return (
            f"<SubscriptionUsage("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"resource_type={self.resource_type}, "
            f"amount={self.amount}, "
            f"consumed_at={self.consumed_at}"
            f")>"
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API responses.
        """
        return {
            "id": str(self.id),
            "subscription_id": str(self.subscription_id),
            "user_id": str(self.user_id),
            "resource_type": self.resource_type,
            "amount": self.amount,
            "resource_id": self.resource_id,
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# RESOURCE TYPE ENUM (for type safety in service layer)
# ============================================================================

class ResourceType:
    """
    Enumeration of valid resource types for usage tracking.

    Note: Not using Python Enum to match the DB VARCHAR + CHECK constraint
    pattern used elsewhere in the codebase (see subscription.py).
    """

    DOCS_GENERATED = "docs_generated"
    REPOS_CONNECTED = "repos_connected"
    API_CALLS = "api_calls"
    PAGES_PROCESSED = "pages_processed"
    TOKENS_USED = "tokens_used"

    @classmethod
    def all(cls) -> list[str]:
        """Return all valid resource types."""
        return [
            cls.DOCS_GENERATED,
            cls.REPOS_CONNECTED,
            cls.API_CALLS,
            cls.PAGES_PROCESSED,
            cls.TOKENS_USED,
        ]

    @classmethod
    def is_valid(cls, resource_type: str) -> bool:
        """Check if a resource type is valid."""
        return resource_type in cls.all()
