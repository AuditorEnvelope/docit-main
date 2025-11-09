from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint

Base = declarative_base()

class TimeStampedModel:
    """Base model that adds created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class AppInstallation(Base, TimeStampedModel):
    """Stores GitHub App installation metadata per org/app pair."""

    __tablename__ = "app_installations"

    id = Column(Integer, primary_key=True)
    org_id = Column(String(100), nullable=False)
    app_id = Column(Integer, nullable=False)
    installation_id = Column(Integer, nullable=False)
    repository_selection = Column(String(20))
    user_id = Column(String(100))
    __table_args__ = (
        UniqueConstraint("org_id", "app_id", name="uq_app_installations_org_app"),
    )


class GitHubInstallation(Base, TimeStampedModel):
    """Stores GitHub App installation details."""

    __tablename__ = "github_installations"

    id = Column(Integer, primary_key=True)
    org_id = Column(String(100), nullable=False)
    installation_id = Column(Integer, nullable=False)
    app_id = Column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint("org_id", "app_id", name="uq_github_installations_org_app"),
    )

class DocumentationPublication(Base, TimeStampedModel):
    """Tracks documentation publications"""
    __tablename__ = 'documentation_publications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    org_id = Column(String(100), nullable=False)
    repo_name = Column(String(255), nullable=False)
    commit_sha = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # 'pending', 'published', 'failed'
    published_at = Column(DateTime(timezone=True), server_default=func.now())
