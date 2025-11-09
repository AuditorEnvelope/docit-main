"""
Repository Models

Database models for repository management and configuration
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Enum as SQLEnum, func, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from enum import Enum
import uuid

from .base import Base

class DocPersona(str, Enum):
    """Documentation persona/style"""
    INTERNAL = "internal"  # Internal team documentation
    DEVELOPER = "developer"  # External developer documentation

class Repository(Base):
    """
    Repository model for tracking connected repositories
    
    Matches the actual database schema (from schema.sql, not migration 005)
    The database uses 'full_name' not 'repo_full_name'
    """
    __tablename__ = "repositories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Identification (from schema.sql)
    repo_id = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "AuditorEnvelope/lekhak_ai"
    name = Column(String(255), nullable=False)  # e.g., "lekhak_ai"
    full_name = Column(String(500), nullable=True, index=True)  # e.g., "AuditorEnvelope/lekhak_ai"
    
    # Git configuration
    git_url = Column(String(500), nullable=True)
    default_branch = Column(String(100), default="main", nullable=True)
    
    # Settings
    enabled = Column(Boolean, default=True, nullable=True)
    indexing_frequency = Column(String(50), default="realtime", nullable=True)
    auto_generate_docs = Column(Boolean, default=True, nullable=True)
    
    # Subscription
    subscription_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Documentation configuration (may be added by migration 005)
    doc_persona = Column(String(50), default='internal', nullable=True)
    doc_persona_updated_at = Column(DateTime(timezone=True), nullable=True)
    doc_maintainer_enabled = Column(Boolean, default=False, nullable=True)
    doc_maintainer_repo_id = Column(String(255), nullable=True)
    
    # Legacy fields that might not exist - these columns don't exist in schema.sql
    # They are defined here for compatibility but should not be queried
    # Use load_only() in queries to exclude them
    user_id = Column(PGUUID(as_uuid=True), nullable=True)  # Does not exist in database - for compatibility only
    org_id = Column(String(255), nullable=True)  # Does not exist in database - for compatibility only
    github_repo_id = Column(Integer, nullable=True)  # GitHub's numeric ID
    is_private = Column(Boolean, default=False, nullable=True)
    auto_generate = Column(Boolean, default=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    last_commit_sha = Column(String(100), nullable=True)
    last_documented_at = Column(DateTime(timezone=True), nullable=True)
    config_data = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    repo_url = Column(String(500), nullable=True)
    last_webhook_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata (using 'repo_metadata' to avoid SQLAlchemy reserved name conflict)
    repo_metadata = Column("metadata", JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Repository(full_name='{self.full_name or self.repo_id}', persona='{self.doc_persona}')>"

class CommitEvent(Base):
    """
    Commit event storage for idempotent processing
    
    Stores all commits with deduplication via ON CONFLICT
    """
    __tablename__ = "commit_events"
    
    event_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Commit identity (unique constraint)
    repo_id = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(100), nullable=False, index=True)
    
    # Commit details
    parent_sha = Column(ARRAY(String), nullable=False, default=list)  # Array of parent SHAs
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    branch = Column(String(255), nullable=False)
    commit_message = Column(Text, nullable=False)
    
    # File changes
    files_changed = Column(JSON, nullable=False)  # [{path, status, patch}]
    
    # Source tracking
    push_id = Column(String(100), nullable=True)
    source = Column(String(50), default="github")  # github|gitlab|cli
    
    # Multi-org support
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    org_id = Column(String(255), nullable=True, index=True)
    github_token_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    installation_id = Column(Integer, nullable=True)
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata (backed by legacy `metadata` column name)
    event_metadata = Column("metadata", JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Unique constraint for idempotent commit handling
    __table_args__ = (
        UniqueConstraint('repo_id', 'commit_sha', name='uq_commit_events_repo_sha'),
        Index('idx_commit_events_org_processed', 'org_id', 'processed'),
    )
    
    def __repr__(self):
        return f"<CommitEvent(repo='{self.repo_id}', sha='{self.commit_sha[:8]}')>"

__all__ = ["Repository", "CommitEvent", "DocPersona"]
