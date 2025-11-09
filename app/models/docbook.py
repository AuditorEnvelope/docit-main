"""Docbook-related SQLAlchemy models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class DocbookStatus(str, Enum):
    """Review status for docbook publications."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocbookRepo(Base):
    """Stores linked docbook repositories for organizations."""

    __tablename__ = "docbook_repos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    org_id = Column(String(255), nullable=False, unique=True, index=True)

    docbook_repo_name = Column(String(255), nullable=False)
    docbook_full_name = Column(String(255), nullable=False)
    docbook_repo_id = Column(Integer, nullable=True)
    docbook_url = Column(String(500), nullable=False)

    staging_branch = Column(String(100), default="staging", nullable=False)
    main_branch = Column(String(100), default="main", nullable=False)
    auto_merge = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    last_published_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<DocbookRepo(org='{self.org_id}', repo='{self.docbook_full_name}')>"


class DocbookReview(Base):
    """Tracks pending docbook reviews for staging publications."""

    __tablename__ = "docbook_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    org_id = Column(String(255), nullable=False, index=True)

    source_repo_name = Column(String(255), nullable=False)
    docbook_full_name = Column(String(255), nullable=False)

    commit_message = Column(Text, nullable=True)
    status = Column(SQLEnum(DocbookStatus, name="docbook_status"), default=DocbookStatus.PENDING_REVIEW, nullable=False)
    review_metadata = Column(JSONB(astext_type=Text()), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)

    def mark_approved(self, approver_id: str) -> None:
        """Mark the review as approved."""

        self.status = DocbookStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.approved_by = approver_id

    def mark_rejected(self) -> None:
        """Mark the review as rejected."""

        self.status = DocbookStatus.REJECTED


__all__ = ["DocbookRepo", "DocbookReview", "DocbookStatus"]
