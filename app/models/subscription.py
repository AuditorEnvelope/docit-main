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
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    
    # Plan details
    plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    
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
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
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
    name = Column(String(50), unique=True, nullable=False)  # free, pro, enterprise
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
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    def __repr__(self):
        return f"<SubscriptionPlanConfig(name='{self.name}', price=${self.price_monthly})>"

__all__ = ["Subscription", "SubscriptionPlanConfig", "SubscriptionStatus", "SubscriptionPlan"]
