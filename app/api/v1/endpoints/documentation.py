from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from pydantic import UUID4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.base import DocumentationPublication
from app.schemas.documentation import (
    DocumentationResponse,
    DocumentationCreate,
    ManualGenerationRequest,
    ManualGenerationResponse,
)
from app.services.documentation.service import DocumentationService
from app.services.auth import get_current_user
from app.models.user import User
from app.services.documentation.manual_generation import ManualDocGenerator
from app.services.docbook.publisher import DocbookPublisher
from app.utils.github_dual_app import GitHubDualAppHelper

router = APIRouter()

@router.get("", response_model=List[DocumentationResponse])
async def list_documentation(
    repo_name: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all documentation publications with optional filtering"""
    service = DocumentationService(db)
    return await service.list_publications(repo_name=repo_name, status=status)

@router.get("/{doc_id}", response_model=DocumentationResponse)
async def get_documentation(
    doc_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific documentation by ID"""
    service = DocumentationService(db)
    doc = await service.get_publication(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documentation not found")
    return doc

@router.post("", response_model=DocumentationResponse, status_code=status.HTTP_201_CREATED)
async def create_documentation(
    doc_in: DocumentationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new documentation entry"""
    service = DocumentationService(db)
    return await service.create_publication(doc_in)

@router.post("/publish/{doc_id}", response_model=DocumentationResponse)
async def publish_documentation(
    doc_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    """Publish documentation to docbook"""
    service = DocumentationService(db)
    doc = await service.publish_documentation(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documentation not found or already published")
    return doc


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found for user")
    return token


def _parse_repo_full_name(repo_full_name: str) -> tuple[str, str]:
    repo_full_name = repo_full_name.strip()
    if "/" not in repo_full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="repo_full_name must be in the form org/repo")
    org, repo = repo_full_name.split("/", 1)
    if not org or not repo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid repo_full_name provided")
    return org, repo


@router.post("/manual-generate", response_model=ManualGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def manual_generate_documentation(
    payload: ManualGenerationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually generate documentation and publish to docbook staging."""

    github_token = _require_github_token(user)
    org_id, repo_name = _parse_repo_full_name(payload.repo_full_name)

    generator = ManualDocGenerator(doc_persona=payload.doc_persona)
    dual_app_helper = GitHubDualAppHelper()
    publisher = DocbookPublisher(dual_app=dual_app_helper, db_session=db)

    commit_message = payload.commit_message or f"docs: Manual documentation generation for {repo_name}"

    generation_result = await generator.generate(payload.repo_full_name, github_token)

    try:
        publish_result = await publisher.publish_to_docbook(
            user_id=str(user.id) if isinstance(user.id, UUID) else user.id,
            org_id=org_id,
            source_repo_name=repo_name,
            docs_dir=generation_result.docs_dir,
            commit_message=commit_message,
            commit_sha=payload.commit_sha,
        )
    finally:
        generation_result.cleanup()

    if publish_result.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=publish_result.get("message", "Docbook publication failed"))

    return ManualGenerationResponse(
        status=publish_result.get("status", "published_to_staging"),
        message=publish_result.get("message", "Manual documentation published"),
        docbook_repo=publish_result.get("docbook_repo"),
        branch=publish_result.get("branch"),
        review_url=publish_result.get("review_url"),
    )
