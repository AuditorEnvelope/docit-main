"""Organization-related API endpoints."""

from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_current_user
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
        return {"org_id": org_id, "repositories": [], "total": 0}

    installation_id = reader_inst.get("id")
    reader_token = await dual_app.get_reader_token(installation_id)
    if not reader_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get reader installation token")

    repos = await _list_installation_repos(reader_token)

    return {
        "org_id": org_id,
        "repositories": repos,
        "total": len(repos),
    }
