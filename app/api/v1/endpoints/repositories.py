"""
Repository API Endpoints

Handles repository management and configuration
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import load_only
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.models.user import User
from app.models.repository import Repository, DocPersona
from app.services.auth import get_current_user
from app.services.subscription import SubscriptionService

router = APIRouter()


class RepositoryCreate(BaseModel):
    repo_id: str  # org/repo format
    org_id: str
    full_name: str
    description: Optional[str] = None
    default_branch: str = "main"
    is_private: bool = False
    doc_persona: DocPersona = DocPersona.DEVELOPER
    auto_generate: bool = True


class RepositoryUpdate(BaseModel):
    doc_persona: Optional[DocPersona] = None
    auto_generate: Optional[bool] = None


class RepositoryResponse(BaseModel):
    id: str  # UUID
    repo_id: str  # Alias for repo_full_name for API compatibility
    org_id: str
    full_name: str  # Alias for repo_full_name
    description: Optional[str]
    doc_persona: str
    auto_generate: bool
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, obj):
        """Custom validation to map full_name/repo_id to repo_id and full_name"""
        if isinstance(obj, Repository):
            # Use full_name if available, otherwise fall back to repo_id
            repo_identifier = obj.full_name or obj.repo_id
            return cls(
                id=str(obj.id),
                repo_id=repo_identifier,  # Use full_name or repo_id
                org_id=obj.org_id or "",
                full_name=repo_identifier,  # Use full_name or repo_id
                description=obj.description,
                doc_persona=obj.doc_persona or "internal",
                auto_generate=obj.auto_generate if obj.auto_generate is not None else True,
                is_active=obj.is_active if obj.is_active is not None else True,
            )
        return super().model_validate(obj)


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    org_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all repositories for the authenticated user"""
    # Note: user_id and org_id columns don't exist in database schema (schema.sql)
    # Use load_only() to only select columns that exist in the database
    # Based on schema.sql, repositories table has: id, repo_id, name, full_name, git_url,
    # default_branch, enabled, indexing_frequency, auto_generate_docs, subscription_id,
    # metadata, created_at, updated_at, last_indexed_at, and columns from migration 005
    
    # Load only columns that exist in the actual database schema
    query = select(Repository).options(
        load_only(
            Repository.id,
            Repository.repo_id,
            Repository.name,
            Repository.full_name,
            Repository.git_url,
            Repository.default_branch,
            Repository.enabled,
            Repository.indexing_frequency,
            Repository.auto_generate_docs,
            Repository.subscription_id,
            Repository.doc_persona,
            Repository.doc_persona_updated_at,
            Repository.doc_maintainer_enabled,
            Repository.doc_maintainer_repo_id,
            Repository.github_repo_id,
            Repository.is_private,
            Repository.auto_generate,
            Repository.is_active,
            Repository.last_commit_sha,
            Repository.last_documented_at,
            Repository.config_data,
            Repository.description,
            Repository.repo_url,
            Repository.last_webhook_at,
            Repository.repo_metadata,  # Maps to 'metadata' column
            Repository.created_at,
            Repository.updated_at,
            Repository.last_indexed_at,
        )
    ).where(Repository.is_active == True)
    
    # Note: Can't filter by org_id since that column doesn't exist
    # In the future, filter by subscription_id to get user's repos
    
    result = await db.execute(query)
    repositories = result.scalars().all()
    # Convert to response format with proper field mapping
    return [RepositoryResponse.model_validate(repo) for repo in repositories]


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_in: RepositoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create/register a new repository"""
    # Check subscription limits
    subscription_service = SubscriptionService(db)
    await subscription_service.enforce_repository_limit(user.id)
    
    # Check if repository already exists (use full_name or repo_id which matches DB schema)
    repo_full_name = repo_in.full_name or repo_in.repo_id
    result = await db.execute(
        select(Repository).options(load_only(
            Repository.id, Repository.repo_id, Repository.name, Repository.full_name
        )).where(
            (Repository.full_name == repo_full_name) | (Repository.repo_id == repo_full_name)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Repository already registered"
        )
    
    # Create repository (match database schema from schema.sql)
    # Note: user_id and org_id don't exist in schema.sql, so don't set them
    repository = Repository(
        repo_id=repo_full_name,  # Use repo_id as primary identifier
        name=repo_full_name.split("/")[-1] if "/" in repo_full_name else repo_full_name,
        full_name=repo_full_name,
        description=repo_in.description,
        default_branch=repo_in.default_branch,
        is_private=repo_in.is_private,
        doc_persona=repo_in.doc_persona.value if isinstance(repo_in.doc_persona, DocPersona) else repo_in.doc_persona,
        auto_generate_docs=repo_in.auto_generate,
        enabled=True,
        # user_id and org_id don't exist in database schema - use subscription_id instead
        # subscription_id will be set via subscription relationship
    )
    
    db.add(repository)
    await db.commit()
    await db.refresh(repository)
    
    # Increment repository count
    await subscription_service.increment_repository_count(user.id)
    
    return RepositoryResponse.model_validate(repository)


@router.get("/{repo_id}/doc-persona")
async def get_repository_doc_persona(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get repository documentation persona setting"""
    # repo_id parameter is actually repo_full_name (org/repo format)
    # Note: user_id doesn't exist in database, so can't filter by it
    result = await db.execute(
        select(Repository).options(load_only(
            Repository.id, Repository.repo_id, Repository.full_name, Repository.doc_persona
        )).where(
            (Repository.full_name == repo_id) | (Repository.repo_id == repo_id)
        )
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {
        "repo_id": repository.full_name or repository.repo_id,  # Return as repo_id for API compatibility
        "doc_persona": repository.doc_persona
    }


@router.post("/{repo_id}/doc-persona")
async def update_repository_doc_persona(
    repo_id: str,
    doc_persona: DocPersona,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update repository documentation persona"""
    # repo_id parameter is actually repo_full_name (org/repo format)
    # Note: user_id doesn't exist in database, so can't filter by it
    result = await db.execute(
        select(Repository).options(load_only(
            Repository.id, Repository.repo_id, Repository.full_name, Repository.doc_persona
        )).where(
            (Repository.full_name == repo_id) | (Repository.repo_id == repo_id)
        )
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repository.doc_persona = doc_persona.value if hasattr(doc_persona, 'value') else str(doc_persona)
    repository.doc_persona_updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "status": "updated",
        "repo_id": repository.full_name or repository.repo_id,  # Return as repo_id for API compatibility
        "doc_persona": repository.doc_persona
    }


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete/deactivate a repository"""
    # repo_id parameter is actually repo_full_name (org/repo format)
    # Note: user_id doesn't exist in database, so can't filter by it
    result = await db.execute(
        select(Repository).options(load_only(
            Repository.id, Repository.repo_id, Repository.full_name, Repository.is_active
        )).where(
            (Repository.full_name == repo_id) | (Repository.repo_id == repo_id)
        )
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Soft delete
    repository.is_active = False
    await db.commit()
    
    # Decrement repository count
    subscription_service = SubscriptionService(db)
    await subscription_service.decrement_repository_count(user.id)
    
    return {"status": "deleted", "repo_id": repo_id}


__all__ = ["router"]
