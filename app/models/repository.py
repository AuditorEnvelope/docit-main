"""
Repository Models

Database models for repository management and configuration
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Enum as SQLEnum, func, JSON, UniqueConstraint, Index
from enum import Enum

from .base import Base

class DocPersona(str, Enum):
    """Documentation persona/style"""
    INTERNAL = "internal"  # Internal team documentation
    DEVELOPER = "developer"  # External developer documentation

class Repository(Base):
    """
    Repository model for tracking connected repositories
    
    Stores repository metadata and documentation configuration
    """
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(String(255), unique=True, nullable=False, index=True)  # org/repo format
    
    # Ownership
    user_id = Column(String(36), nullable=False, index=True)
    org_id = Column(String(100), nullable=False, index=True)
    
    # GitHub details
    github_repo_id = Column(Integer, nullable=True)  # GitHub's numeric ID
    full_name = Column(String(255), nullable=False)  # owner/repo
    description = Column(Text, nullable=True)
    default_branch = Column(String(100), default="main")
    is_private = Column(Boolean, default=False)
    
    # Documentation configuration
    doc_persona = Column(SQLEnum(DocPersona), default=DocPersona.DEVELOPER, nullable=False)
    auto_generate = Column(Boolean, default=True)  # Auto-generate docs on commit
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_commit_sha = Column(String(100), nullable=True)
    last_documented_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    config_data = Column(JSON, nullable=True)  # Additional repo-specific config (renamed from metadata to avoid SQLAlchemy conflict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    def __repr__(self):
        return f"<Repository(id='{self.repo_id}', persona='{self.doc_persona}')>"

class CommitEvent(Base):
    """
    Commit event storage for idempotent processing
    
    Stores all commits with deduplication via ON CONFLICT
    """
    __tablename__ = "commit_events"
    
    event_id = Column(Integer, primary_key=True, index=True)
    
    # Commit identity (unique constraint)
    repo_id = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(100), nullable=False, index=True)
    
    # Commit details
    parent_sha = Column(JSON, nullable=False)  # Array of parent SHAs
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
    user_id = Column(String(36), nullable=True, index=True)
    org_id = Column(String(100), nullable=True, index=True)
    github_token_id = Column(String(100), nullable=True)
    installation_id = Column(Integer, nullable=True)
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True)  # Event-specific metadata (renamed from metadata to avoid SQLAlchemy conflict)
    
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
