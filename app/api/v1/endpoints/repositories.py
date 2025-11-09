"""
Repository API Endpoints

Handles repository management and configuration
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
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
    id: int
    repo_id: str
    org_id: str
    full_name: str
    description: Optional[str]
    doc_persona: str
    auto_generate: bool
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    org_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all repositories for the authenticated user"""
    query = select(Repository).where(
        Repository.user_id == user.id,
        Repository.is_active == True
    )
    
    if org_id:
        query = query.where(Repository.org_id == org_id)
    
    result = await db.execute(query)
    repositories = result.scalars().all()
    return repositories


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
    
    # Check if repository already exists
    result = await db.execute(
        select(Repository).where(Repository.repo_id == repo_in.repo_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Repository already registered"
        )
    
    # Create repository
    repository = Repository(
        repo_id=repo_in.repo_id,
        user_id=user.id,
        org_id=repo_in.org_id,
        full_name=repo_in.full_name,
        description=repo_in.description,
        default_branch=repo_in.default_branch,
        is_private=repo_in.is_private,
        doc_persona=repo_in.doc_persona,
        auto_generate=repo_in.auto_generate,
        is_active=True
    )
    
    db.add(repository)
    await db.commit()
    await db.refresh(repository)
    
    # Increment repository count
    await subscription_service.increment_repository_count(user.id)
    
    return repository


@router.get("/{repo_id}/doc-persona")
async def get_repository_doc_persona(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get repository documentation persona setting"""
    result = await db.execute(
        select(Repository).where(
            Repository.repo_id == repo_id,
            Repository.user_id == user.id
        )
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {
        "repo_id": repository.repo_id,
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
    result = await db.execute(
        select(Repository).where(
            Repository.repo_id == repo_id,
            Repository.user_id == user.id
        )
    )
    repository = result.scalar_one_or_none()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repository.doc_persona = doc_persona
    await db.commit()
    
    return {
        "status": "updated",
        "repo_id": repository.repo_id,
        "doc_persona": repository.doc_persona
    }


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete/deactivate a repository"""
    result = await db.execute(
        select(Repository).where(
            Repository.repo_id == repo_id,
            Repository.user_id == user.id
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
