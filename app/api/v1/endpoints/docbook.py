"""Docbook helper endpoints."""

from typing import Any, Dict, List, Optional

import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.docbook import DocbookRepo
from app.models.user import User
from app.services.auth import get_current_user
from app.services.docbook.service import DocbookService

logger = logging.getLogger(__name__)

router = APIRouter()


class LinkDocbookRepoRequest(BaseModel):
    """Request body for linking a docbook repository."""

    org_id: str
    docbook_repo_name: str


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found")
    return token


async def _fetch_repo_data(org_id: str, repo_name: str, token: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{org_id}/{repo_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    logger.debug("🔍 GitHub repo lookup", extra={
        "org_id": org_id,
        "repo_name": repo_name,
        "url": url,
    })

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("❌ GitHub request failed", extra={
            "org_id": org_id,
            "repo_name": repo_name,
            "error": str(exc),
        })
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    logger.debug(
        "📡 GitHub response",
        extra={
            "org_id": org_id,
            "repo_name": repo_name,
            "status_code": response.status_code,
            "x_github_request_id": response.headers.get("X-GitHub-Request-Id"),
        },
    )

    if response.status_code == 200:
        data = response.json()
        logger.debug(
            "✅ Repo visible",
            extra={
                "org_id": org_id,
                "repo_name": repo_name,
                "full_name": data.get("full_name"),
                "private": data.get("private"),
            },
        )
        return data

    if response.status_code == 404:
        logger.info(
            "🔒 Repo not visible (404)",
            extra={
                "org_id": org_id,
                "repo_name": repo_name,
            },
        )
        return None

    if response.status_code == 401:
        logger.warning(
            "🚫 GitHub token unauthorized",
            extra={
                "org_id": org_id,
                "repo_name": repo_name,
            },
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token unauthorized")

    detail = response.text
    logger.warning(
        "⚠️ Unexpected GitHub error",
        extra={
            "org_id": org_id,
            "repo_name": repo_name,
            "status_code": response.status_code,
            "response": detail[:500],
        },
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"GitHub API error ({response.status_code}): {detail}",
    )


async def link_docbook_repo_logic(
    *,
    user: User,
    db: AsyncSession,
    request: LinkDocbookRepoRequest,
) -> Dict[str, Any]:
    token = _require_github_token(user)

    org_id = request.org_id.strip()
    repo_name = request.docbook_repo_name.strip()
    if not org_id or not repo_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org_id and docbook_repo_name are required")

    repo_data = await _fetch_repo_data(org_id, repo_name, token)
    if not repo_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {org_id}/{repo_name} not found on GitHub",
        )

    service = DocbookService(db)
    saved = await service.upsert_repo(
        user_id=user.id,
        org_id=org_id,
        repo_name=repo_name,
        full_name=repo_data.get("full_name", f"{org_id}/{repo_name}"),
        repo_id=repo_data.get("id"),
        url=repo_data.get("html_url", ""),
    )

    return {
        "status": "linked",
        "org_id": saved.org_id,
        "docbook_repo": saved.docbook_full_name,
        "docbook_url": saved.docbook_url,
        "message": f"Successfully linked {saved.docbook_full_name}",
    }


async def _get_docbook_repo(
    db: AsyncSession,
    user: User,
    org_id: str,
) -> DocbookRepo:
    service = DocbookService(db)
    repo = await service.get_repo(user_id=user.id, org_id=org_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No docbook linked for {org_id}",
        )
    return repo


async def _fetch_folder_contents(
    client: httpx.AsyncClient,
    repo_full_name: str,
    path: str,
    branch: str,
    token: str,
) -> List[Dict[str, Any]]:
    base_url = f"https://api.github.com/repos/{repo_full_name}/contents"
    normalized_path = path.lstrip("/")
    url = base_url if not normalized_path else f"{base_url}/{normalized_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Pustak-AI",
    }

    response = await client.get(url, headers=headers, params={"ref": branch})

    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch folder contents (status {response.status_code})",
        )

    contents = response.json()
    result: List[Dict[str, Any]] = []

    for item in contents:
        item_type = item.get("type")
        name = item.get("name")
        item_path = item.get("path")
        if item_type == "dir":
            children = await _fetch_folder_contents(
                client,
                repo_full_name,
                item_path,
                branch,
                token,
            )
            result.append(
                {
                    "name": name,
                    "type": "folder",
                    "path": item_path,
                    "files": children,
                }
            )
        else:
            result.append(
                {
                    "name": name,
                    "type": "file",
                    "path": item_path,
                }
            )

    return result


@router.get("/docbook/check-github-repo")
async def check_docbook_repo_on_github(
    org_id: str,
    repo_name: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    token = _require_github_token(user)
    repo_data = await _fetch_repo_data(org_id, repo_name, token)

    if repo_data:
        return {
            "exists": True,
            "status": "exists",
            "org_id": org_id,
            "repo_name": repo_name,
            "full_name": repo_data.get("full_name"),
            "url": repo_data.get("html_url"),
        }

    return {
        "exists": False,
        "status": "not_found",
        "org_id": org_id,
        "repo_name": repo_name,
    }


@router.get("/docbook/check-exists")
async def check_docbook_exists(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = DocbookService(db)
    repo = await service.get_repo(user_id=user.id, org_id=org_id)

    if not repo:
        return {
            "exists": False,
            "org_id": org_id,
            "message": f"No docbook linked for {org_id}. Create lekhak-docbook-org-{{ORG_ID}} and link it.",
        }

    return {
        "exists": True,
        "org_id": org_id,
        "docbook_repo": repo.docbook_full_name,
        "docbook_url": repo.docbook_url,
    }


@router.get("/docbook/{org_id}/structure")
async def get_docbook_structure(
    org_id: str,
    branch: str = Query("staging", description="Branch to inspect"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    token = _require_github_token(user)
    docbook_repo = await _get_docbook_repo(db, user, org_id)

    async with httpx.AsyncClient(timeout=10.0) as client:
        folders = await _fetch_folder_contents(
            client,
            docbook_repo.docbook_full_name,
            "",
            branch,
            token,
        )

    return {
        "org_id": org_id,
        "repo": docbook_repo.docbook_full_name,
        "branch": branch,
        "folders": folders,
    }


@router.post("/docbook/link-repo", status_code=status.HTTP_200_OK)
async def link_docbook_repo(
    request: LinkDocbookRepoRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await link_docbook_repo_logic(user=user, db=db, request=request)
