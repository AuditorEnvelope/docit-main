"""
Subscription Models (SAFE Razorpay Extension)

✅ Preserves existing schema & enums
✅ Adds Razorpay support without breaking anything
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Numeric,
    Enum as SQLEnum,
    func,
    Text
)
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
import uuid

from .base import Base


# ============================
# ENUMS (UNCHANGED)
# ============================

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


# ============================
# SUBSCRIPTION
# ============================

class Subscription(Base):
    """
    User subscription management
    """

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True,
                     nullable=False, index=True)

    # Plan & status
    plan = Column(
        SQLEnum(SubscriptionPlan),
        default=SubscriptionPlan.FREE,
        nullable=False
    )
    status = Column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )

    # ========================
    # Razorpay (NEW — SAFE)
    # ========================
    razorpay_customer_id = Column(String(100), nullable=True, index=True)
    razorpay_order_id = Column(String(100), nullable=True, index=True)
    razorpay_payment_id = Column(String(100), nullable=True, index=True)
    razorpay_subscription_id = Column(String(100), nullable=True, index=True)

    # ========================
    # Usage limits
    # ========================
    max_repositories = Column(Integer, default=1)
    max_docs_per_month = Column(Integer, default=100)

    # Current usage
    current_repositories = Column(Integer, default=0)
    docs_generated_this_month = Column(Integer, default=0)

    # Trial
    is_trial = Column(Boolean, default=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Billing cycle
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan={self.plan}, status={self.status})>"


# ============================
# SUBSCRIPTION PLAN CONFIG
# ============================

class SubscriptionPlanConfig(Base):
    """
    Subscription plan configuration
    """

    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Numeric(10, 2), default=0)
    price_yearly = Column(Numeric(10, 2), default=0)

    # Limits
    max_repositories = Column(Integer, default=1)
    max_docs_per_month = Column(Integer, default=100)
    max_team_members = Column(Integer, default=1)

    # Feature flags
    has_priority_support = Column(Boolean, default=False)
    has_custom_templates = Column(Boolean, default=False)
    has_api_access = Column(Boolean, default=False)
    has_advanced_analytics = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SubscriptionPlanConfig(name={self.name}, price={self.price_monthly})>"


# ============================
# PAYMENTS
# ============================

class Payment(Base):
    """
    Payment history (Razorpay)
    """

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Razorpay identifiers
    razorpay_order_id = Column(String(100), nullable=True, index=True)
    razorpay_payment_id = Column(
        String(100), unique=True, nullable=True, index=True)
    razorpay_subscription_id = Column(String(100), nullable=True, index=True)
    razorpay_customer_id = Column(String(100), nullable=True, index=True)

    # Payment info
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    # Store as VARCHAR(20) to match actual DB schema, not PostgreSQL enum
    status = Column(
        String(20),
        default=PaymentStatus.PENDING.value,
        nullable=False
    )

    # Plan snapshot
    plan_id = Column(Integer, nullable=True)
    plan_name = Column(String(50), nullable=True)

    # Audit
    raw_payload = Column(Text, nullable=True)
    billing_start_date = Column(DateTime(timezone=True), nullable=True)
    billing_end_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Payment(id={self.id}, status={self.status}, amount={self.amount})>"


__all__ = [
    "Subscription",
    "SubscriptionPlanConfig",
    "SubscriptionStatus",
    "SubscriptionPlan",
    "Payment",
    "PaymentStatus",
]
