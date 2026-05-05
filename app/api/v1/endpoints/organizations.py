"""Organization-related API endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
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
logger = logging.getLogger(__name__)


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found")
    return token


def _normalize_repo_key(value: Optional[str]) -> str:
    return (value or "").strip().lower()


async def _get_user_orgs(github_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DocIt-AI",
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
        "User-Agent": "DocIt-AI",
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


def _sanitize_commit_message(message: Optional[str]) -> str:
    if not message:
        return ""
    return message.strip().split("\n", 1)[0].strip()[:220]


def _normalize_github_commit(full_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    sha = item.get("sha") or ""
    gh_author = item.get("author") or {}
    inner = item.get("commit") or {}
    author_blob = inner.get("author") or {}
    login = gh_author.get("login")
    name = author_blob.get("name") or login or "Unknown"
    date = author_blob.get("date") or ""
    return {
        "sha": sha[:40] if isinstance(sha, str) else "",
        "short_sha": sha[:7] if isinstance(sha, str) else "",
        "message": _sanitize_commit_message(inner.get("message")),
        "author_login": login,
        "author_name": name,
        "author_avatar_url": gh_author.get("avatar_url"),
        "committed_at": date,
        "html_url": item.get("html_url")
        or (
            f"https://github.com/{full_name}/commit/{sha[:7]}"
            if isinstance(sha, str) and len(sha) >= 7
            else None
        ),
    }


async def _fetch_repo_commits_for_branch(
    installation_token: str,
    full_name: str,
    branch: str,
    *,
    per_page: int,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return normalized commits newest-first, plus optional GitHub error string."""
    key = _normalize_repo_key(full_name)
    parts = full_name.split("/", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return [], "invalid_repository_name"
    owner, repo_slug = parts[0].strip(), parts[1].strip()
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "DocIt-AI",
    }
    url = f"https://api.github.com/repos/{owner}/{repo_slug}/commits"
    params: Dict[str, Any] = {"sha": branch or "main", "per_page": min(per_page, 30)}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        logger.warning("[recent-commits] httpx error %s %s", key, exc)
        return [], f"github_http_error:{exc}"

    if response.status_code != 200:
        logger.info(
            "[recent-commits] non-200 for %s branch=%s status=%s body=%s",
            key,
            branch,
            response.status_code,
            (response.text or "")[:200],
        )
        return [], f"github_status_{response.status_code}"

    raw = response.json()
    if not isinstance(raw, list):
        return [], "invalid_github_response"

    out: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("sha"):
            out.append(_normalize_github_commit(full_name, item))
    return out, None


class RepoActivityRef(BaseModel):
    full_name: str
    branch: str


class RecentCommitsBatchRequest(BaseModel):
    repos: List[RepoActivityRef] = Field(default_factory=list, max_length=40)
    per_repo_limit: int = Field(default=12, ge=1, le=30)


async def _list_installation_repos(installation_token: str) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "DocIt-AI",
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
    repo_metadata_map: Dict[str, Dict[str, Any]] = {}

    if repo_full_names:
        unique_repo_ids = {name for name in repo_full_names if name}
        logger.info("[repo-summary] unique repo ids from GitHub: %s", sorted(unique_repo_ids))

        for full_name in unique_repo_ids:
            normalized_name = _normalize_repo_key(full_name)
            repo_obj = None

            try:
                repo_obj = await repo_service.get_by_full_name(full_name)
            except Exception as exc:
                logger.warning("[repo-summary] get_by_full_name error for %s: %s", full_name, exc)

            if not repo_obj and full_name.lower() != full_name:
                # Retry with lower-case identifier as fallback
                try:
                    repo_obj = await repo_service.get_by_full_name(full_name.lower())
                except Exception as exc:
                    logger.warning(
                        "[repo-summary] lowercase retry failed for %s: %s",
                        full_name,
                        exc,
                    )

            if not repo_obj:
                logger.info("[repo-summary] repository metadata missing for %s", full_name)
                continue

            key = _normalize_repo_key(repo_obj.full_name or repo_obj.repo_id or full_name)
            if not key:
                logger.info("[repo-summary] repository key empty for %s", full_name)
                continue

            branch = (repo_obj.tracked_branch or "").strip()
            if branch:
                repo_tracked_map[key] = branch

            repo_metadata_map[key] = {
                "doc_persona": repo_obj.doc_persona,
                "last_documented_at": repo_obj.last_documented_at.isoformat() if repo_obj.last_documented_at else None,
            }

            logger.info(
                "[repo-summary] metadata loaded",
                extra={
                    "full_name": repo_obj.full_name,
                    "normalized_key": key,
                    "doc_persona": repo_obj.doc_persona,
                    "last_documented_at": repo_metadata_map[key]["last_documented_at"],
                },
            )

        logger.info(
            "[repo-summary] metadata map keys: %s",
            sorted(repo_metadata_map.keys()),
        )

    summaries: List[Dict[str, Any]] = []
    for repo in repos:
        full_name = repo.get("full_name") or (
            f"{org_id}/{repo.get('name')}" if repo.get("name") else None
        )
        if not full_name:
            continue

        meta = db_metadata.get(full_name) or {}
        normalized_name = _normalize_repo_key(full_name)
        repo_meta = repo_metadata_map.get(normalized_name, {})

        summaries.append(
            {
                "full_name": full_name,
                "name": repo.get("name"),
                "description": repo.get("description"),
                "default_branch": repo.get("default_branch"),
                "private": repo.get("private", False),
                "doc_persona": repo_meta.get("doc_persona"),
                "last_documented_at": repo_meta.get("last_documented_at"),
                "pending_reviews": pending_map.get(full_name, 0),
                "docbook_tracked_branch": docbook_tracked_branch,
                "tracked_branch": repo_tracked_map.get(normalized_name, docbook_tracked_branch),
                "tracked_branch_source": "repository"
                if normalized_name in repo_tracked_map
                else "docbook",
            }
        )

    return {
        "org_id": org_id,
        "docbook_tracked_branch": docbook_tracked_branch,
        "repositories": summaries,
        "total": len(summaries),
    }


@router.post("/org/{org_id}/repositories/recent-commits")
async def batch_repository_recent_commits(
    org_id: str,
    body: RecentCommitsBatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch recent commits on the tracked branch for multiple repos in one call
    (Reader installation token). Used by the dashboard activity feed + polling.
    """
    reader_token, _dual = await _resolve_reader_installation_token(org_id, user, db)
    if not reader_token:
        return {
            "org_id": org_id,
            "by_repo": {},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "error": "reader_app_not_available",
        }

    unique_refs: List[RepoActivityRef] = []
    seen: set[str] = set()
    for ref in body.repos:
        k = _normalize_repo_key(ref.full_name)
        if not k or k in seen:
            continue
        seen.add(k)
        unique_refs.append(ref)

    sem = asyncio.Semaphore(8)

    async def one(ref: RepoActivityRef) -> Tuple[str, Dict[str, Any]]:
        async with sem:
            commits, err = await _fetch_repo_commits_for_branch(
                reader_token,
                ref.full_name.strip(),
                (ref.branch or "main").strip(),
                per_page=body.per_repo_limit,
            )
        return _normalize_repo_key(ref.full_name), {
            "full_name": ref.full_name.strip(),
            "branch": (ref.branch or "main").strip(),
            "commits": commits,
            "error": err,
        }

    pairs = await asyncio.gather(*(one(r) for r in unique_refs)) if unique_refs else []
    by_repo = {key: payload for key, payload in pairs}
    return {
        "org_id": org_id,
        "by_repo": by_repo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
