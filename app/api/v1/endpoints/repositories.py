"""
Repository API Endpoints

Handles repository management and configuration
"""

import logging
from typing import List, Optional
from datetime import datetime

import httpx
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
from app.services.docbook.service import DocbookService
from app.services.repositories.service import RepositoryService


logger = logging.getLogger(__name__)

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


class RepositoryTrackedBranchResponse(BaseModel):
    repo_id: str
    tracked_branch: str
    source: str
    fallback_branch: Optional[str] = None
    default_branch: Optional[str] = None


class RepositoryTrackedBranchUpdate(BaseModel):
    tracked_branch: str
    default_branch: Optional[str] = None


class RepositoryBranchesResponse(BaseModel):
    repo_id: str
    org_id: str
    branches: List[str]


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found")
    return token


async def _fetch_branches_for_repo(org_id: str, repo_name: str, token: str) -> List[str]:
    url = f"https://api.github.com/repos/{org_id}/{repo_name}/branches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "DocIt-AI",
    }

    logger.debug(
        "🌿 Fetching repository branches",
        extra={"org_id": org_id, "repo_name": repo_name, "url": url},
    )

    branches: List[str] = []
    page = 1

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )

                logger.debug(
                    "📡 GitHub repo branch response",
                    extra={
                        "org_id": org_id,
                        "repo_name": repo_name,
                        "status_code": response.status_code,
                        "page": page,
                        "x_github_request_id": response.headers.get("X-GitHub-Request-Id"),
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if not isinstance(data, list):
                        break

                    page_branches = [
                        item.get("name")
                        for item in data
                        if isinstance(item, dict) and item.get("name")
                    ]
                    branches.extend(page_branches)

                    if len(data) < 100:
                        break

                    page += 1
                    continue

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Repository or branches not found on GitHub",
                    )

                if response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="GitHub token unauthorized",
                    )

                detail = response.text
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error ({response.status_code}): {detail}",
                )
    except httpx.HTTPError as exc:
        logger.warning(
            "❌ GitHub repo branches request failed",
            extra={"org_id": org_id, "repo_name": repo_name, "error": str(exc)},
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    unique_branches: List[str] = []
    for branch in branches:
        if branch not in unique_branches:
            unique_branches.append(branch)

    return unique_branches


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


@router.get("/{repo_path:path}/doc-persona")
async def get_repository_doc_persona(
    repo_path: str,
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
            (Repository.full_name == repo_path) | (Repository.repo_id == repo_path)
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {
        "repo_id": repository.full_name or repository.repo_id,  # Return as repo_id for API compatibility
        "doc_persona": repository.doc_persona
    }


@router.get("/{repo_path:path}/tracked-branch", response_model=RepositoryTrackedBranchResponse)
async def get_repository_tracked_branch(
    repo_path: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the tracked branch for a repository with docbook fallback."""

    repo_identifier = repo_path.strip()
    repo_service = RepositoryService(db)
    docbook_service = DocbookService(db)

    repo_record = await repo_service.get_by_full_name(repo_identifier)

    repo_tracked = (repo_record.tracked_branch or "").strip() if repo_record else None
    repo_default = (repo_record.default_branch or "").strip() if repo_record else None

    org_id = repo_identifier.split("/")[0] if "/" in repo_identifier else None
    docbook_branch: Optional[str] = None
    if org_id:
        try:
            docbook_branch = await docbook_service.get_tracked_branch(user.id, org_id)
        except Exception:
            docbook_branch = None

    resolved_branch = repo_tracked or docbook_branch or repo_default or "main"
    source = "repository" if repo_tracked else "docbook" if docbook_branch else "default"

    fallback_branch = docbook_branch if repo_tracked else None

    return RepositoryTrackedBranchResponse(
        repo_id=repo_identifier,
        tracked_branch=resolved_branch,
        source=source,
        fallback_branch=fallback_branch,
        default_branch=repo_default or "main",
    )


@router.post("/{repo_path:path}/tracked-branch", response_model=RepositoryTrackedBranchResponse)
async def update_repository_tracked_branch(
    repo_path: str,
    payload: RepositoryTrackedBranchUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a repository-specific tracked branch."""

    branch_value = (payload.tracked_branch or "").strip()
    if not branch_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tracked branch cannot be empty")

    repo_service = RepositoryService(db)
    repo = await repo_service.upsert_tracked_branch(
        repo_path,
        tracked_branch=branch_value,
        default_branch=payload.default_branch,
    )

    resolved_branch = (repo.tracked_branch or "main").strip() or "main"
    default_branch = (repo.default_branch or "main").strip() or "main"

    return RepositoryTrackedBranchResponse(
        repo_id=repo.full_name or repo.repo_id,
        tracked_branch=resolved_branch,
        source="repository",
        fallback_branch=None,
        default_branch=default_branch,
    )


@router.post("/{repo_path:path}/doc-persona")
async def update_repository_doc_persona(
    repo_path: str,
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
            (Repository.full_name == repo_path) | (Repository.repo_id == repo_path)
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


@router.delete("/{repo_path:path}")
async def delete_repository(
    repo_path: str,
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
            (Repository.full_name == repo_path) | (Repository.repo_id == repo_path)
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
    
    return {"status": "deleted", "repo_id": repo_path}


@router.get("/{repo_path:path}/branches", response_model=RepositoryBranchesResponse)
async def list_repository_branches(
    repo_path: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List branches for a source repository using the user's GitHub token."""

    token = _require_github_token(user)
    repo_identifier = repo_path.strip()
    if "/" not in repo_identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository must be in org/repo format")

    org_id, repo_name = repo_identifier.split("/", 1)
    branches = await _fetch_branches_for_repo(org_id, repo_name, token)

    return RepositoryBranchesResponse(
        repo_id=repo_identifier,
        org_id=org_id,
        branches=branches,
    )


__all__ = ["router"]
