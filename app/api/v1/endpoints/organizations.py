"""Organization-related API endpoints."""

from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, cast, String

from app.db.session import get_db
from app.models.user import User
from app.models.repository import Repository
from app.models.docbook import DocbookReview, DocbookStatus
from app.services.auth import get_current_user
from app.services.docbook.service import DocbookService
from app.services.repositories.service import RepositoryService
from app.utils.github_dual_app import GitHubDualAppHelper

router = APIRouter()


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found")
    return token


async def _get_user_orgs(github_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Pustak-AI",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.github.com/user/orgs", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    if response.status_code == 200:
        return response.json()

    if response.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token unauthorized")

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Failed to fetch organizations (status {response.status_code})",
    )


async def _get_org_installations(org_id: str, github_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    url = f"https://api.github.com/orgs/{org_id}/installations"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    if response.status_code == 200:
        data = response.json()
        return data.get("installations", [])

    if response.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token unauthorized")

    if response.status_code == 404:
        return []

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Failed to fetch installations (status {response.status_code})",
    )


def _match_installation(installations: List[Dict[str, Any]], app_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not app_id:
        return None
    for inst in installations:
        if inst.get("app_id") == app_id:
            return inst
    return None


def _dual_app_ids(dual_app: GitHubDualAppHelper) -> Dict[str, Optional[int]]:
    reader_id = int(dual_app.reader_app_id) if dual_app.reader_app_id else None
    writer_id = int(dual_app.writer_app_id) if dual_app.writer_app_id else None
    fallback_id = int(dual_app.github_app_id) if dual_app.github_app_id else None
    return {
        "reader": reader_id or fallback_id,
        "writer": writer_id or fallback_id,
        "is_dual": dual_app.dual_app_mode,
    }


async def _resolve_reader_installation_token(
    org_id: str,
    user: User,
    db: AsyncSession,
) -> tuple[Optional[str], Optional[GitHubDualAppHelper]]:
    github_token = _require_github_token(user)

    try:
        dual_app = GitHubDualAppHelper()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    app_ids = _dual_app_ids(dual_app)
    reader_app_id = app_ids["reader"]
    if not reader_app_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reader app not configured")

    installations = await _get_org_installations(org_id, github_token)
    reader_inst = _match_installation(installations, reader_app_id)

    if not reader_inst:
        return None, dual_app

    installation_id = reader_inst.get("id")
    reader_token = await dual_app.get_reader_token(installation_id)
    if not reader_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get reader installation token")

    return reader_token, dual_app


async def _list_installation_repos(installation_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    repos: List[Dict[str, Any]] = []
    url = "https://api.github.com/installation/repositories?per_page=100"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            next_url: Optional[str] = url
            while next_url:
                response = await client.get(next_url, headers=headers)
                if response.status_code != 200:
                    break
                data = response.json()
                repos.extend(data.get("repositories", []))
                next_url = response.links.get("next", {}).get("url")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    return repos


@router.get("/user/organizations")
async def get_user_organizations(
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
):
    """List GitHub organizations available to the authenticated user."""
    github_token = _require_github_token(user)
    orgs = await _get_user_orgs(github_token)
    return {"organizations": orgs}


@router.get("/org/{org_id}/verify-apps")
async def verify_github_apps(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify GitHub app installations for an organization

    Checks if Reader App and Writer App are installed
    """
    github_token = _require_github_token(user)

    try:
        dual_app = GitHubDualAppHelper()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    app_ids = _dual_app_ids(dual_app)
    installations = await _get_org_installations(org_id, github_token)

    reader_inst = _match_installation(installations, app_ids["reader"])
    writer_inst = _match_installation(installations, app_ids["writer"])

    def _format(inst: Optional[Dict[str, Any]], app_role: str) -> Dict[str, Any]:
        installed = inst is not None
        return {
            "installed": installed,
            "installation_id": inst.get("id") if installed else None,
            "app_id": app_ids[app_role],
            "permissions": inst.get("permissions", {}) if installed else {},
        }

    return {
        "org_id": org_id,
        "dual_app_mode": app_ids["is_dual"],
        "reader_app": _format(reader_inst, "reader"),
        "writer_app": _format(writer_inst, "writer"),
    }


@router.get("/org/{org_id}/verify-writer-app-access")
async def verify_writer_app_access(
    org_id: str,
    repo: str = Query(..., description="Repository name"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Writer App has access to a specific repository

    Checks if the Writer App can write to the docbook repository
    """
    github_token = _require_github_token(user)

    try:
        dual_app = GitHubDualAppHelper()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    app_ids = _dual_app_ids(dual_app)
    writer_app_id = app_ids["writer"]
    if not writer_app_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Writer app not configured")

    installations = await _get_org_installations(org_id, github_token)
    writer_inst = _match_installation(installations, writer_app_id)

    if not writer_inst:
        return {"org_id": org_id, "repo": repo, "installed": False, "has_access": False, "accessible_repos": []}

    installation_id = writer_inst.get("id")
    writer_token = await dual_app.get_writer_token(installation_id)
    if not writer_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get writer installation token")

    repos = await _list_installation_repos(writer_token)
    repo_full_name = repo if "/" in repo else f"{org_id}/{repo}"
    accessible = {item.get("full_name") for item in repos if item.get("full_name")}

    return {
        "org_id": org_id,
        "repo": repo_full_name,
        "installed": True,
        "has_access": repo_full_name in accessible,
        "accessible_repos": sorted(accessible),
    }


@router.get("/org/{org_id}/reader/repositories")
async def get_reader_app_repositories(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all repositories accessible via Reader App for an organization

    Returns list of repositories the Reader App has access to
    """
    reader_token, _ = await _resolve_reader_installation_token(org_id, user, db)

    if not reader_token:
        return {"org_id": org_id, "repositories": [], "total": 0}

    repos = await _list_installation_repos(reader_token)

    return {
        "org_id": org_id,
        "repositories": repos,
        "total": len(repos),
    }


@router.get("/org/{org_id}/repositories/summary")
async def get_org_repository_summary(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return repository cards metadata for an organization."""

    reader_token, dual_app = await _resolve_reader_installation_token(org_id, user, db)

    if not reader_token:
        return {
            "org_id": org_id,
            "docbook_tracked_branch": "main",
            "repositories": [],
            "total": 0,
        }

    repos = await _list_installation_repos(reader_token)
    repo_full_names = [repo.get("full_name") for repo in repos if repo.get("full_name")]

    db_metadata: Dict[str, Dict[str, Any]] = {}

    pending_map: Dict[str, int] = {}
    review_stmt = (
        select(
            DocbookReview.source_repo_name,
            func.count().label("pending"),
        )
        .where(
            DocbookReview.org_id == org_id,
            cast(DocbookReview.status, String) == DocbookStatus.PENDING_REVIEW.value,
        )
        .group_by(DocbookReview.source_repo_name)
    )
    review_result = await db.execute(review_stmt)
    for row in review_result:
        pending_map[row[0]] = row[1]

    docbook_service = DocbookService(db)
    tracked_map = await docbook_service.get_tracked_branches_for_orgs([org_id])
    docbook_tracked_branch = tracked_map.get(org_id, "main")

    repo_service = RepositoryService(db)
    repo_tracked_map: Dict[str, str] = {}
    if repo_full_names:
        for full_name in repo_full_names:
            try:
                repo_branch = await repo_service.get_tracked_branch(full_name)
                if repo_branch:
                    repo_tracked_map[full_name] = repo_branch
            except Exception:
                continue

    summaries: List[Dict[str, Any]] = []
    for repo in repos:
        full_name = repo.get("full_name") or (
            f"{org_id}/{repo.get('name')}" if repo.get("name") else None
        )
        if not full_name:
            continue

        meta = db_metadata.get(full_name) or {}
        summaries.append(
            {
                "full_name": full_name,
                "name": repo.get("name"),
                "description": repo.get("description"),
                "default_branch": repo.get("default_branch"),
                "private": repo.get("private", False),
                "doc_persona": None,
                "last_documented_at": None,
                "last_commit_sha": None,
                "last_webhook_at": None,
                "pending_reviews": pending_map.get(full_name, 0),
                "docbook_tracked_branch": docbook_tracked_branch,
                "tracked_branch": repo_tracked_map.get(full_name, docbook_tracked_branch),
                "tracked_branch_source": "repository"
                if full_name in repo_tracked_map
                else "docbook",
            }
        )

    return {
        "org_id": org_id,
        "docbook_tracked_branch": docbook_tracked_branch,
        "repositories": summaries,
        "total": len(summaries),
    }
