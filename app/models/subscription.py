"""
Subscription Models

Database models for subscription management and billing
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Numeric, Enum as SQLEnum, func, Text
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
import uuid

from .base import Base


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    """Subscription plan types"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Subscription(Base):
    """
    User subscription management

    Tracks subscription plans, billing, and usage limits
    """
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True,
                     nullable=False, index=True)

    # Plan details
    plan = Column(SQLEnum(SubscriptionPlan),
                  default=SubscriptionPlan.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus),
                    default=SubscriptionStatus.ACTIVE, nullable=False)

    # Billing
    stripe_customer_id = Column(String(100), nullable=True, index=True)
    stripe_subscription_id = Column(String(100), nullable=True, index=True)

    # Usage limits (based on plan)
    max_repositories = Column(Integer, default=1)  # Free=1, Pro=unlimited
    max_docs_per_month = Column(Integer, default=100)  # Generation limit

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
                        onupdate=func.now(), server_default=func.now())
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Subscription(user='{self.user_id}', plan='{self.plan}', status='{self.status}')>"


class SubscriptionPlanConfig(Base):
    """
    Subscription plan configuration

    Defines features and limits for each plan
    """
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    # free, pro, enterprise
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Numeric(10, 2), default=0)
    price_yearly = Column(Numeric(10, 2), default=0)

    # Features
    max_repositories = Column(Integer, default=1)
    max_docs_per_month = Column(Integer, default=100)
    max_team_members = Column(Integer, default=1)

    # Feature flags
    has_priority_support = Column(Boolean, default=False)
    has_custom_templates = Column(Boolean, default=False)
    has_api_access = Column(Boolean, default=False)
    has_advanced_analytics = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<SubscriptionPlanConfig(name='{self.name}', price=${self.price_monthly})>"


class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Payment(Base):
    """
    Payment record for tracking all payment transactions

    Stores complete payment history with raw payload for audit purposes
    """
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    # Reference to user who made payment
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Razorpay specific identifiers
    razorpay_order_id = Column(String(100), nullable=True, index=True)
    # UNIQUE constraint for idempotency
    razorpay_payment_id = Column(
        String(100), unique=True, nullable=True, index=True)
    razorpay_subscription_id = Column(String(100), nullable=True, index=True)
    razorpay_customer_id = Column(String(100), nullable=True, index=True)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)  # Amount in INR
    currency = Column(String(3), default="INR", nullable=False)
    status = Column(SQLEnum(PaymentStatus),
                    default=PaymentStatus.PENDING, nullable=False)

    # Plan associated with this payment
    # Reference to subscription_plans.id
    plan_id = Column(Integer, nullable=True)
    plan_name = Column(String(50), nullable=True)  # Name of the plan

    # Raw payload for audit and debugging
    raw_payload = Column(Text, nullable=True)  # Store the full webhook payload

    # Billing cycle information
    billing_start_date = Column(DateTime(timezone=True), nullable=True)
    billing_end_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())
    # When payment was processed
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Payment(id='{self.id}', user_id='{self.user_id}', amount={self.amount}, status='{self.status}')>"


__all__ = ["Subscription", "SubscriptionPlanConfig",
           "SubscriptionStatus", "SubscriptionPlan", "Payment", "PaymentStatus"]
