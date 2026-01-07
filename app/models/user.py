"""
User Models

Database models for user authentication and profiles
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, INET
from enum import Enum
import uuid

from .base import Base


class UserPlan(str, Enum):
    """User subscription plans"""
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class User(Base):
    """
    User model for authentication and profile management

    Integrates with GitHub OAuth for authentication
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=False, index=True)
    avatar_url = Column(String(500), nullable=True)
    github_access_token = Column(String(255), nullable=True)

    # Subscription
    plan = Column(String(50),  # Use VARCHAR to match actual DB schema
                  default="free", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    razorpay_customer_id = Column(String(100), nullable=True, index=True)

    # Updated subscription fields
    current_plan = Column(String(50),  # Use VARCHAR to match actual DB schema
                          default="free", nullable=False)
    subscription_status = Column(
        String(50), default="inactive", nullable=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_onboarding_complete = Column(
        Boolean, nullable=False, server_default="false", default=False)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', plan='{self.plan}')>"


class Session(Base):
    """
    User session management

    Tracks active sessions with JWT tokens
    """
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True)
    refresh_token = Column(String(500), nullable=True)

    # Session metadata
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True),
                              server_default=func.now())

    def __repr__(self):
        return f"<Session(id='{self.id}', user_id='{self.user_id}', active='{self.is_active}')>"


__all__ = ["User", "Session", "UserPlan"]
