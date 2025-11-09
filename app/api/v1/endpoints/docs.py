from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Tuple
from uuid import UUID
from urllib.parse import unquote

import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.documentation import ManualGenerationResponse
from app.services.auth import get_current_user
from app.services.docbook.publisher import DocbookPublisher
from app.services.documentation.manual_generation import ManualDocGenerator
from app.utils.github_dual_app import GitHubDualAppHelper

router = APIRouter()


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found for user")
    return token


def _parse_repo_full_name(repo_full_name: str) -> Tuple[str, str]:
    repo_full_name = repo_full_name.strip()
    if "/" not in repo_full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="repo_name must be in the form org/repo")
    org, repo = repo_full_name.split("/", 1)
    if not org or not repo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid repo name provided")
    return org, repo


@router.post("/generate-v4", response_model=ManualGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_documentation_v4(
    repo_name: str = Query(..., description="Repository in the form org/repo"),
    doc_persona: str = Query("internal", description="Documentation persona to apply"),
    commit_message: str | None = Query(None, description="Optional commit message override"),
    commit_sha: str | None = Query(None, description="Optional commit SHA for logging"),
    installation_id: int | None = Query(None, description="Writer app installation ID (optional)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ManualGenerationResponse:
    """Generate documentation manually and publish to docbook staging (legacy-compatible endpoint)."""

    github_token = _require_github_token(user)
    org_id, source_repo = _parse_repo_full_name(repo_name)

    generator = ManualDocGenerator(doc_persona=doc_persona)
    dual_app_helper = GitHubDualAppHelper()
    publisher = DocbookPublisher(dual_app=dual_app_helper, db_session=db)

    message = commit_message or f"docs: Manual documentation generation for {source_repo}"

    generation_result = await generator.generate(repo_name, github_token)

    try:
        publish_result = await publisher.publish_to_docbook(
            user_id=str(user.id) if isinstance(user.id, UUID) else user.id,
            org_id=org_id,
            source_repo_name=source_repo,
            docs_dir=generation_result.docs_dir,
            commit_message=message,
            commit_sha=commit_sha,
            installation_id=installation_id,
        )
    finally:
        generation_result.cleanup()

    if publish_result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=publish_result.get("message", "Docbook publication failed"),
        )

    return ManualGenerationResponse(
        status=publish_result.get("status", "published_to_staging"),
        message=publish_result.get("message", "Manual documentation published"),
        docbook_repo=publish_result.get("docbook_repo"),
        branch=publish_result.get("branch"),
        review_url=publish_result.get("review_url"),
    )


@router.get("/fetch-file")
async def fetch_file_from_github(
    repo: str = Query(..., description="Repository in the form org/repo"),
    filePath: str = Query(..., description="Path to the file in the repository"),
    branch: str = Query("staging", description="Branch to fetch from"),
    user: User = Depends(get_current_user),
) -> dict:
    """Fetch a file from GitHub using user's token (like old codebase)"""
    github_token = _require_github_token(user)
    
    try:
        # Normalize and decode the file path
        normalized_path = unquote(filePath or "").strip("/")
        if not normalized_path:
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Legacy aliases (pre-docbook folder structure) - like old codebase
        legacy_map = {
            "summary": "docs/summary.md",
            "api": "docs/api.md",
            "architecture": "docs/architecture/current.md",
            "workflow": "docs/workflow/current.md",
            "changelog": "CHANGELOG.md",
            "readme": "README.md",
            "quality_report": "docs/QUALITY_REPORT.md",
        }

        legacy_key = normalized_path.lower()
        if legacy_key in legacy_map:
            normalized_path = legacy_map[legacy_key]

        # Fetch file from GitHub API
        async with httpx.AsyncClient(timeout=10.0) as client:
            request_url = f"https://api.github.com/repos/{repo}/contents/{normalized_path}"
            response = await client.get(
                request_url,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                },
                params={"ref": branch}
            )

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="File not found")
            if response.status_code in (401, 403):
                raise HTTPException(status_code=403, detail="Access denied")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch file: {response.status_code}"
                )

            data = response.json()

            # Decode base64 content if present
            if data.get("encoding") == "base64" and data.get("content"):
                import base64
                content = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
                return {"content": content, "fileName": normalized_path}

            return {"content": data.get("content", ""), "fileName": normalized_path}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching file: {str(e)}")
