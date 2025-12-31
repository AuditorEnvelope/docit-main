"""Docbook helper endpoints."""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import aiohttp
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.docbook import DocbookRepo, DocbookReview, DocbookStatus, DocbookPublishEvent
from app.models.user import User
from app.services.auth import get_current_user
from app.services.docbook.service import DocbookService
from app.services.auth import AuthService
from app.services.org_members import OrgMembershipService
from app.utils.github_dual_app import GitHubDualAppHelper

logger = logging.getLogger(__name__)

router = APIRouter()


class LinkDocbookRepoRequest(BaseModel):
    """Request body for linking a docbook repository."""

    org_id: str
    docbook_repo_name: str


class DocbookTrackedBranchResponse(BaseModel):
    org_id: str
    tracked_branch: str
class DocbookTrackedBranchUpdate(BaseModel):
    tracked_branch: str


class DocbookTrackedBranchResponse(BaseModel):
    org_id: str
    repo: str
    branches: List[str]


class DocbookBranchesResponse(BaseModel):
    org_id: str
    repo: str
    branches: List[str]


async def _ensure_internal_access(
    *, db: AsyncSession, org_id: str, user: Optional[User]
) -> None:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access internal documentation.",
        )

    membership_service = OrgMembershipService(db)
    is_member = await membership_service.ensure_member(org_id, user)

    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to the internal documentation for this organization.",
        )


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


async def _fetch_repo_branches(org_id: str, repo_name: str, token: str) -> List[str]:
    url = f"https://api.github.com/repos/{org_id}/{repo_name}/branches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    branches: List[str] = []
    page = 1

    logger.debug(
        "🌿 Fetching repo branches",
        extra={
            "org_id": org_id,
            "repo_name": repo_name,
            "url": url,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )

                logger.debug(
                    "📡 GitHub branch response",
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
            "❌ GitHub branches request failed",
            extra={
                "org_id": org_id,
                "repo_name": repo_name,
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}")

    unique_branches: List[str] = []
    for branch in branches:
        if branch not in unique_branches:
            unique_branches.append(branch)

    return unique_branches


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

    membership_service = OrgMembershipService(db)
    await membership_service.upsert_member(
        org_id=org_id,
        user=user,
        role="owner",
        is_owner=True,
        is_active=True,
    )

    # Ensure background workers discover this org
    await db.execute(
        text(
            """
            INSERT INTO org_registrations (user_id, org_id, registered_at)
            VALUES (:user_id, :org_id, NOW())
            ON CONFLICT (user_id, org_id) DO UPDATE
            SET registered_at = NOW()
            """
        ),
        {"user_id": str(saved.user_id), "org_id": saved.org_id},
    )
    await db.commit()

    return {
        "status": "linked",
        "org_id": saved.org_id,
        "docbook_repo": saved.docbook_full_name,
        "docbook_url": saved.docbook_url,
        "message": f"Successfully linked {saved.docbook_full_name}",
    }


async def _get_user_github_token(
    db: AsyncSession,
    user_id: str | UUID,
    token_id: Optional[str] = None,
) -> Optional[str]:
    """Fetch user's GitHub token (primary or fallback org token)."""

    try:
        user_uuid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user identifier")

    result = await db.execute(
        text(
            """
            SELECT github_access_token FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": str(user_uuid)},
    )

    primary_token = result.scalar_one_or_none()
    if primary_token:
        return primary_token

    if token_id and token_id != "00000000-0000-0000-0000-000000000000":
        result = await db.execute(
            text(
                """
                SELECT github_token FROM user_github_tokens
                WHERE user_id = :user_id AND token_id = :token_id AND is_active = TRUE
                """
            ),
            {"user_id": str(user_uuid), "token_id": token_id},
        )
        fallback_token = result.scalar_one_or_none()
        if fallback_token:
            return fallback_token

    return None


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


async def _mark_docbook_review_approved(
    db: AsyncSession,
    *,
    user_id: str | UUID,
    org_id: str,
    docbook_full_name: str,
) -> None:
    try:
        user_uuid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user identifier")

    await db.execute(
        text(
            """
            UPDATE docbook_reviews
            SET status = :approved_status
            WHERE user_id = :user_id
              AND org_id = :org_id
              AND docbook_full_name = :docbook_full_name
              AND status = :pending_status
            """
        ),
        {
            "approved_status": DocbookStatus.APPROVED.value,
            "user_id": str(user_uuid),
            "org_id": org_id,
            "docbook_full_name": docbook_full_name,
            "pending_status": DocbookStatus.PENDING_REVIEW.value,
        },
    )
    await db.commit()


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


def _normalize_sidebar_items(
    contents: List[Dict[str, Any]],
    repo_id: str,
    base_path: str = "",
    persona: str = "dev",
) -> List[Dict[str, Any]]:
    """Convert GitHub API content listing into a hierarchical sidebar."""

    sidebar: List[Dict[str, Any]] = []
    for item in contents:
        current_path = f"{base_path}/{item['name']}" if base_path else item["name"]
        
        # Extract the path after the persona folder
        if "docs/" in current_path and f"/{persona}/" in current_path:
            parts = current_path.split(f"docs/{persona}/", 1)
            if len(parts) > 1:
                display_path = parts[1]
                normalized_path = f"/{repo_id}/{persona}/{display_path}".replace("//", "/")
            else:
                normalized_path = f"/{repo_id}/{persona}/{current_path}".replace("//", "/")
        else:
            normalized_path = f"/{repo_id}/{persona}/{current_path}".replace("//", "/")

        if item["type"] == "folder":
            children = _normalize_sidebar_items(
                item.get("files", []),
                repo_id,
                current_path,
                persona,
            )
            sidebar.append(
                {
                    "id": normalized_path,
                    "name": item["name"],
                    "type": "folder",
                    "path": normalized_path,
                    "source_path": normalized_path,
                    "children": children,
                }
            )
        elif item["type"] == "file" and item["name"].lower().endswith(".md"):
            display_path = normalized_path.rsplit(".md", 1)[0]
            sidebar.append(
                {
                    "id": display_path,
                    "name": item["name"].rsplit(".md", 1)[0],
                    "type": "file",
                    "path": display_path,
                    "source_path": normalized_path,
                    "parent": f"/{repo_id}/{base_path}".replace("//", "/") if base_path else None,
                }
            )
    return sidebar


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
            "message": f"No docbook linked for {org_id}. Create pustak-docbook-{org_id.lower()} and link it.",
        }
    
    # Verify the repository actually exists on GitHub
    token = _require_github_token(user)
    
    # Extract org and repo name from full name
    if repo.docbook_full_name and "/" in repo.docbook_full_name:
        repo_org, repo_name = repo.docbook_full_name.split("/", 1)
    else:
        repo_org = org_id
        repo_name = repo.docbook_repo_name
    
    # Check if repo exists on GitHub
    repo_data = await _fetch_repo_data(repo_org, repo_name, token)
    
    if not repo_data:
        logger.warning(
            "🚨 Docbook repo in database but not found on GitHub",
            extra={
                "org_id": org_id,
                "repo_full_name": repo.docbook_full_name,
                "user_id": str(user.id),
            },
        )
        return {
            "exists": False,
            "org_id": org_id,
            "docbook_repo": repo.docbook_full_name,
            "docbook_url": repo.docbook_url,
            "message": f"Repository {repo.docbook_full_name} not found on GitHub. Please create it or link a different repository.",
        }

    return {
        "exists": True,
        "org_id": org_id,
        "docbook_repo": repo.docbook_full_name,
        "docbook_url": repo.docbook_url,
    }


@router.get("/docbook/{org_id}/branches", response_model=DocbookBranchesResponse)
async def list_docbook_branches(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await _get_docbook_repo(db, user, org_id)
    token = _require_github_token(user)

    if repo.docbook_full_name and "/" in repo.docbook_full_name:
        owner, repo_name = repo.docbook_full_name.split("/", 1)
    else:
        owner = org_id
        repo_name = repo.docbook_repo_name

    branches = await _fetch_repo_branches(owner, repo_name, token)

    return DocbookBranchesResponse(
        org_id=org_id,
        repo=repo.docbook_full_name or f"{owner}/{repo_name}",
        branches=branches,
    )


@router.get("/docbook/{org_id}/tracked-branch", response_model=DocbookTrackedBranchResponse)
async def get_docbook_tracked_branch(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocbookService(db)
    repo = await service.get_repo(user_id=user.id, org_id=org_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Docbook repository not linked")

    tracked = (repo.tracked_branch or repo.main_branch or "main").strip() or "main"
    return DocbookTrackedBranchResponse(org_id=org_id, tracked_branch=tracked)


@router.post("/docbook/{org_id}/tracked-branch", response_model=DocbookTrackedBranchResponse)
async def update_docbook_tracked_branch(
    org_id: str,
    payload: DocbookTrackedBranchUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    branch_value = (payload.tracked_branch or "").strip()
    if not branch_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tracked branch cannot be empty")

    service = DocbookService(db)
    try:
        repo = await service.update_tracked_branch(user_id=user.id, org_id=org_id, tracked_branch=branch_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocbookTrackedBranchResponse(org_id=org_id, tracked_branch=repo.tracked_branch or repo.main_branch or "main")


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


@router.get("/docbook/pending-reviews")
async def get_pending_reviews(
    org_id: str,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending documentation reviews for an organization
    
    Returns:
    - reviews: List of pending reviews waiting for user approval
    """
    try:
        raw_user_id = user.id if hasattr(user, "id") else user.get("id")
        if not raw_user_id:
            raise HTTPException(status_code=401, detail="User context missing")

        try:
            user_uuid = UUID(str(raw_user_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user identifier")

        await _ensure_internal_access(db=db, org_id=org_id, user=user)

        result = await db.execute(
            text(
                """
                SELECT id, source_repo_name, docbook_full_name, status, commit_message, created_at
                FROM docbook_reviews
                WHERE user_id = :user_id
                  AND org_id = :org_id
                  AND status = :status
                ORDER BY created_at DESC
                """
            ),
            {
                "user_id": str(user_uuid),
                "org_id": org_id,
                "status": DocbookStatus.PENDING_REVIEW.value,
            },
        )
        rows = result.mappings().all()

        reviews = [
            {
                "id": row["id"],
                "source_repo_name": row["source_repo_name"],
                "docbook_full_name": row["docbook_full_name"],
                "status": row["status"],
                "commit_message": row["commit_message"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

        return {
            "org_id": org_id,
            "reviews": reviews,
            "count": len(reviews)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))



class MergeDocbookRequest(BaseModel):
    org_id: str
    repo_name: str  # Source repo name
    message: str = "docs: Approve and merge documentation"  # Merge commit message


@router.post("/docbook/approve-and-merge")
async def approve_and_merge_docbook(
    request: MergeDocbookRequest,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve and merge documentation from staging to main branch
    
    This endpoint:
    1. Gets the linked docbook repo
    2. Creates a pull request from staging → main
    3. Merges the PR (auto-merge)
    4. Returns confirmation
    """
    try:
        user_obj = user if hasattr(user, "id") else None
        user_id = str(getattr(user_obj, "id")) if user_obj else user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User context missing")

        org_id = request.org_id
        repo_name = request.repo_name
        merge_message = request.message

        # Resolve user's GitHub token
        github_token = await _get_user_github_token(db, user_id)
        if not github_token:
            raise HTTPException(status_code=401, detail="No GitHub token found")

        # Fetch linked docbook repo via service
        docbook_service = DocbookService(db)
        docbook_repo = await docbook_service.get_repo(user_id=user_id, org_id=org_id)
        if not docbook_repo or not docbook_repo.is_active:
            raise HTTPException(status_code=404, detail=f"No docbook linked for {org_id}")

        docbook_full_name = docbook_repo.docbook_full_name
        
        # Merge staging → main using GitHub API
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Create merge commit
            merge_payload = {
                "base": "main",
                "head": "staging",
                "commit_message": merge_message
            }
            
            async with session.post(
                f'https://api.github.com/repos/{docbook_full_name}/merges',
                headers=headers,
                json=merge_payload
            ) as resp:
                if resp.status == 201:
                    merge_data = await resp.json()
                    await _mark_docbook_review_approved(
                        db,
                        user_id=user_id,
                        org_id=org_id,
                        docbook_full_name=docbook_full_name,
                    )
                    print(f"✅ Merged staging → main in {docbook_full_name}")
                    return {
                        "status": "merged",
                        "org_id": org_id,
                        "repo_name": repo_name,
                        "docbook_repo": docbook_full_name,
                        "commit_sha": merge_data.get('sha'),
                        "message": "Documentation approved and merged to main branch!"
                    }
                elif resp.status == 204:
                    # No changes to merge
                    await _mark_docbook_review_approved(
                        db,
                        user_id=user_id,
                        org_id=org_id,
                        docbook_full_name=docbook_full_name,
                    )
                    print(f"⚠️  No changes to merge in {docbook_full_name}")
                    return {
                        "status": "no_changes",
                        "org_id": org_id,
                        "message": "No changes to merge between staging and main"
                    }
                elif resp.status == 409:
                    # Conflict
                    error = await resp.text()
                    print(f"❌ Merge conflict in {docbook_full_name}")
                    raise HTTPException(
                        status_code=409,
                        detail=f"Merge conflict detected. Please resolve manually on GitHub."
                    )
                else:
                    error = await resp.text()
                    print(f"❌ Failed to merge: {resp.status} - {error}")
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to merge documentation: {error}"
                    )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error merging docbook: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LIVE PUBLISHING ENDPOINTS ====================


class PublishLiveRequest(BaseModel):
    """Request body for publishing docs to live."""
    org_id: str
    repo_id: str


class PublishLiveResponse(BaseModel):
    """Response from publish-live endpoint."""
    job_id: str
    status: str
    live_url: str
    message: str


class LiveOrgStatusResponse(BaseModel):
    """Response for checking if an org has a live docbook."""

    org_id: str
    exists: bool
    live_url: Optional[str]
    repos: List[str] = Field(default_factory=list, description="List of available repositories for this org")


@router.post("/docbook/publish-live", response_model=PublishLiveResponse)
async def publish_docs_live(
    request: PublishLiveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish documentation to the live site.
    
    Workflow:
    1. Verify docbook exists and is linked
    2. Check for pending reviews (fail if any exist)
    3. Fetch main branch HEAD commit
    4. Create publish event record
    5. Update docbook_repo with live URL and commit
    6. Return success with live URL
    """
    print(f"\n{'=' * 80}")
    print(f"📢 Publishing docs live for {request.repo_id}")
    print(f"👤 User: {user.id}, Org: {request.org_id}")
    print(f"{'=' * 80}\n")
    
    logger.info(
        "[publish-live] start",
        extra={
            "org_id": request.org_id,
            "repo_id": request.repo_id,
            "user_id": str(user.id),
        },
    )

    try:
        # Get docbook repo
        docbook_service = DocbookService(db)
        docbook_repo = await docbook_service.get_repo(user.id, request.org_id)

        if not docbook_repo:
            logger.warning(
                "[publish-live] docbook repo missing",
                extra={
                    "org_id": request.org_id,
                    "repo_id": request.repo_id,
                    "user_id": str(user.id),
                },
            )
            raise HTTPException(
                status_code=404,
                detail=f"No docbook repository linked for organization {request.org_id}"
            )

        docbook_full_name = docbook_repo.docbook_full_name

        logger.info(
            "[publish-live] using docbook repo",
            extra={
                "org_id": request.org_id,
                "repo_id": request.repo_id,
                "docbook_full_name": docbook_full_name,
                "docbook_user_id": str(docbook_repo.user_id),
                "tracked_branch": docbook_repo.tracked_branch,
                "is_active": docbook_repo.is_active,
            },
        )

        # Check for pending reviews
        pending_review_check = await db.execute(
            text(
                """
                SELECT COUNT(*) AS pending_count
                FROM docbook_reviews
                WHERE org_id = :org_id
                  AND status = :status
                """
            ),
            {
                "org_id": request.org_id,
                "status": DocbookStatus.PENDING_REVIEW.value,
            },
        )
        pending_count = pending_review_check.scalar_one()

        if pending_count:
            logger.warning(
                "[publish-live] pending reviews block publish",
                extra={
                    "org_id": request.org_id,
                    "repo_id": request.repo_id,
                    "pending_count": pending_count,
                },
            )
            raise HTTPException(
                status_code=400,
                detail=f"Cannot publish live: {pending_count} pending review(s) must be approved first"
            )

        # Get GitHub token
        token = _require_github_token(user)

        # Fetch main branch HEAD
        url = f"https://api.github.com/repos/{docbook_full_name}/git/ref/heads/main"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Pustak-AI",
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(
                "[publish-live] failed to fetch main branch",
                extra={
                    "org_id": request.org_id,
                    "repo_id": request.repo_id,
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch main branch: {response.text}"
            )

        ref_data = response.json()
        main_commit = ref_data["object"]["sha"]
        
        # Create publish event
        publish_event = DocbookPublishEvent(
            user_id=user.id,
            org_id=request.org_id,
            repo_id=request.repo_id,
            main_commit=main_commit,
            published_by=user.id,
            status="success"
        )
        publish_event.mark_completed()
        
        db.add(publish_event)
        
        # Update docbook repo with live info
        live_url = f"https://{request.org_id}.docbook.site/{request.repo_id}"
        docbook_repo.last_published_at = publish_event.completed_at
        docbook_repo.last_published_commit = main_commit
        docbook_repo.live_url = live_url
        
        await db.commit()
        await db.refresh(publish_event)

        print(f"✅ Published {request.repo_id} to live")
        print(f"🔗 Live URL: {live_url}")
        print(f"📦 Commit: {main_commit[:8]}")

        logger.info(
            "[publish-live] success",
            extra={
                "org_id": request.org_id,
                "repo_id": request.repo_id,
                "live_url": live_url,
                "commit": main_commit,
                "publish_event_id": str(publish_event.id),
            },
        )

        return PublishLiveResponse(
            job_id=str(publish_event.id),
            status="success",
            live_url=live_url,
            message=f"Documentation published successfully to {live_url}"
        )
        
    except HTTPException:
        logger.exception(
            "[publish-live] HTTPException",
            extra={
                "org_id": request.org_id,
                "repo_id": request.repo_id,
                "user_id": str(user.id),
            },
        )
        raise
    except Exception as e:
        print(f"❌ Error publishing live: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        logger.exception(
            "[publish-live] unexpected error",
            extra={
                "org_id": request.org_id,
                "repo_id": request.repo_id,
                "user_id": str(user.id),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LIVE MANIFEST ENDPOINTS ====================


async def _resolve_docbook_repo(
    *,
    db: AsyncSession,
    org_id: str,
    user_id: Optional[UUID],
) -> DocbookRepo:
    service = DocbookService(db)
    repo: Optional[DocbookRepo]
    if user_id:
        repo = await service.get_repo(user_id, org_id)
    else:
        repo = await service.get_repo_by_org(org_id)
    if not repo:
        raise HTTPException(
            status_code=404,
            detail=f"No docbook repository linked for organization {org_id}",
        )
    # Note: We no longer require last_published_commit since we use main_branch for public access
    # This allows viewing latest content even if publish-live hasn't been called
    return repo


async def _resolve_app_installation_token(
    *,
    db: AsyncSession,
    org_id: str,
) -> str:
    from app.services.github.app_installation_service import AppInstallationService

    helper = GitHubDualAppHelper()
    installation_service = AppInstallationService(db_session=db)

    candidates: List[Tuple[str, Optional[str]]] = []
    if helper.dual_app_mode:
        candidates.append(("reader", helper.reader_app_id))
        candidates.append(("writer", helper.writer_app_id))
    else:
        candidates.append(("single", helper.github_app_id))

    errors: List[str] = []

    for app_type, app_id_value in candidates:
        if not app_id_value:
            continue
        try:
            app_id = int(str(app_id_value))
        except (TypeError, ValueError):
            errors.append(f"Invalid {app_type} app id: {app_id_value}")
            continue

        installation_id = await installation_service.get_app_installation_id(org_id, app_id)
        if installation_id is None:
            errors.append(
                f"No installation recorded for {app_type} GitHub App (id={app_id}) in org {org_id}"
            )
            continue

        try:
            if app_type == "writer" and helper.dual_app_mode:
                token = await helper.get_writer_token(installation_id)
            else:
                token = await helper.get_reader_token(installation_id)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"GitHub token fetch failed for {app_type} app: {exc}")
            continue

        if token:
            return token
        errors.append(f"GitHub returned empty token for {app_type} app (installation {installation_id})")

    raise HTTPException(
        status_code=502,
        detail={"message": "Unable to resolve GitHub token for docbook", "errors": errors},
    )


async def _build_live_manifest(
    *,
    db: AsyncSession,
    org_id: str,
    repo_id: str,
    user: Optional[User],
    persona: str = "dev",
) -> Dict[str, Any]:
    if persona == "internal":
        await _ensure_internal_access(db=db, org_id=org_id, user=user)

    user_uuid = user.id if user else None
    docbook_repo = await _resolve_docbook_repo(db=db, org_id=org_id, user_id=user_uuid)

    if user:
        token = _require_github_token(user)
    else:
        token = await _resolve_app_installation_token(db=db, org_id=org_id)

    docbook_full_name = docbook_repo.docbook_full_name
    
    # IMPORTANT: Always use 'main' branch for live docs to show latest content
    # This ensures published site reflects current state, not a frozen snapshot
    branch_ref = "main"
    
    # Include persona in the path
    repo_path = f"{repo_id}/docs/{persona}"
    print(f"📚 Accessing manifest for path: {repo_path} with persona: {persona}")
    print(f"📝 Debug: org_id={org_id}, repo_id={repo_id}, persona={persona}")
    print(f"🔖 Using branch: {branch_ref} (always use main for live content)")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First check if the persona folder exists
            try:
                await _fetch_github_file(
                    client=client,
                    repo_full_name=docbook_full_name,
                    path=repo_path,
                    ref=branch_ref,
                    token=token,
                )
            except HTTPException as e:
                if e.status_code == 404:
                    # Persona folder doesn't exist
                    if persona == "internal":
                        # For internal persona, suggest trying dev
                        raise HTTPException(
                            status_code=404,
                            detail=f"Internal documentation not available for {repo_id}. Try accessing the dev documentation instead."
                        )
                    else:
                        # For dev persona
                        raise HTTPException(
                            status_code=404,
                            detail=f"Documentation not available for {repo_id}."
                        )
                else:
                    # Other error
                    raise e
                    
            # If we get here, the persona folder exists, fetch its contents
            folder_tree = await _fetch_folder_contents(
                client,
                docbook_full_name,
                repo_path,
                branch_ref,  # Use main branch, not last_published_commit
                token,
            )
    except Exception as e:
        if not isinstance(e, HTTPException):
            print(f"❌ Error fetching folder contents: {e}")
        raise

    if not folder_tree:
        raise HTTPException(
            status_code=404,
            detail=f"No published documentation found for repo {repo_id}",
        )

    sidebar_items = _normalize_sidebar_items(folder_tree, repo_id, persona=persona)

    def flatten_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flat: List[Dict[str, Any]] = []
        for entry in items:
            flat.append(entry)
            if entry.get("children"):
                flat.extend(flatten_items(entry["children"]))
        return flat

    flat_sidebar = [item for item in flatten_items(sidebar_items) if item["type"] == "file"]

    navigation = {}
    for idx, entry in enumerate(flat_sidebar):
        prev_item = flat_sidebar[idx - 1] if idx > 0 else None
        next_item = flat_sidebar[idx + 1] if idx + 1 < len(flat_sidebar) else None
        navigation[entry["path"]] = {
            "previous": {
                "path": prev_item["path"],
                "source_path": prev_item.get("source_path"),
                "name": prev_item["name"],
            }
            if prev_item
            else None,
            "next": {
                "path": next_item["path"],
                "source_path": next_item.get("source_path"),
                "name": next_item["name"],
            }
            if next_item
            else None,
        }

    manifest = {
        "org_id": org_id,
        "repo_id": repo_id,
        "persona": persona,
        "title": repo_id.replace("-", " ").replace("_", " ").title(),
        "description": f"{persona.capitalize()} documentation for {repo_id}",
        "commit_sha": branch_ref,  # Using branch name since we're always on latest
        "published_at": docbook_repo.last_published_at.isoformat()
        if docbook_repo.last_published_at
        else None,
        "live_url": docbook_repo.live_url,
        "sidebar": sidebar_items,
        "navigation": navigation,
        "breadcrumbs": [
            {
                "label": org_id,
                "path": f"/docs/{org_id}",
            },
            {
                "label": repo_id,
                "path": f"/docs/{org_id}/{repo_id}",
            },
            {
                "label": persona.capitalize(),
                "path": f"/docs/{org_id}/{repo_id}/{persona}",
            },
        ],
        "stats": {
            "page_count": len(flat_sidebar),
            "persona": persona,
            "last_published_at": docbook_repo.last_published_at.isoformat()
            if docbook_repo.last_published_at
            else None,
        },
        "theme": docbook_repo.live_theme
        or {
            "primary": "#3b82f6",
            "secondary": "#8b5cf6",
            "background": "#0f172a",
            "foreground": "#f8fafc",
        },
    }

    logger.info(
        "[live-manifest] generated",
        extra={
            "org_id": org_id,
            "repo_id": repo_id,
            "sidebar_items": len(flat_sidebar),
            "public": not bool(user),
        },
    )
    return manifest


async def _fetch_github_file(
    *,
    client: httpx.AsyncClient,
    repo_full_name: str,
    path: str,
    ref: str,
    token: str,
) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }

    response = await client.get(url, headers=headers, params={"ref": ref})

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="File not found")
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Access denied to published documentation")
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error fetching file: {response.text}",
        )

    return response.json()


async def _fetch_live_page(
    *,
    db: AsyncSession,
    org_id: str,
    repo_id: str,
    slug: List[str],
    user: Optional[User],
    persona: str = "dev",
) -> Dict[str, Any]:
    if persona == "internal":
        await _ensure_internal_access(db=db, org_id=org_id, user=user)

    docbook_repo = await _resolve_docbook_repo(
        db=db,
        org_id=org_id,
        user_id=user.id if user else None,
    )

    if user:
        token = _require_github_token(user)
    else:
        token = await _resolve_app_installation_token(db=db, org_id=org_id)
    
    # Special case for persona/file.md pattern - remove redundant persona prefix
    if len(slug) >= 2 and slug[0] == persona:
        print(f"🔍 Detected persona/{slug[1]} pattern - fixing path by removing redundant persona")
        slug = slug[1:] # Remove the persona prefix
    
    relative_path = "/".join(part.strip("/") for part in slug if part)
    if not relative_path:
        relative_path = "README.md"

    if not relative_path.lower().endswith(".md"):
        relative_path = f"{relative_path}.md"

    # Include persona in the path
    repo_path = f"{repo_id}/docs/{persona}/{relative_path}" if repo_id else f"docs/{persona}/{relative_path}"
    
    print(f"📄 Accessing content at path: {repo_path} with persona: {persona}")

    # IMPORTANT: Always use 'main' branch for live docs to show latest content
    # This ensures published site reflects current state, not a frozen snapshot
    ref_to_use = "main"
    print(f"📌 Using branch: {ref_to_use} (always use main for live content)")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            file_data = await _fetch_github_file(
                client=client,
                repo_full_name=docbook_repo.docbook_full_name,
                path=repo_path,
                ref=ref_to_use,
                token=token,
            )
    except HTTPException as e:
        if e.status_code == 404:
            # Check if the persona folder exists
            try:
                # Try to check if the persona folder exists
                persona_path = f"{repo_id}/docs/{persona}"
                await _fetch_github_file(
                    client=httpx.AsyncClient(timeout=10.0),
                    repo_full_name=docbook_repo.docbook_full_name,
                    path=persona_path,
                    ref=ref_to_use,
                    token=token,
                )
                # Persona folder exists, but the specific file doesn't
                raise HTTPException(
                    status_code=404,
                    detail=f"Content not found: {relative_path}"
                )
            except HTTPException as persona_error:
                if persona_error.status_code == 404:
                    # Persona folder doesn't exist
                    if persona == "internal":
                        # For internal persona, suggest trying dev
                        raise HTTPException(
                            status_code=404,
                            detail=f"Internal documentation not available for {repo_id}. Try accessing the dev documentation instead."
                        )
                    else:
                        # For dev persona
                        raise HTTPException(
                            status_code=404,
                            detail=f"Documentation not available for {repo_id}."
                        )
                else:
                    # Other error
                    raise persona_error
        else:
            # Other error
            raise e

    content = file_data.get("content", "")
    if file_data.get("encoding") == "base64" and content:
        import base64

        content = base64.b64decode(content.replace("\n", "")).decode("utf-8")

    return {
        "org_id": org_id,
        "repo_id": repo_id,
        "path": repo_path,
        "slug": slug,
        "content": content,
        "sha": file_data.get("sha"),
        "size": file_data.get("size"),
        "commit_sha": docbook_repo.last_published_commit,
        "updated_at": docbook_repo.last_published_at.isoformat()
        if docbook_repo.last_published_at
        else None,
    }


@router.get("/docbook/live-manifest")
async def get_live_manifest(
    org_id: str = Query(...),
    repo_id: str = Query(...),
    persona: str = Query("dev", description="Documentation persona (internal or dev)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the manifest for a live docs site.
    
    Returns:
    - Sidebar structure (folders, pages)
    - Metadata (title, description, persona)
    - Theme configuration
    """
    print(f"📋 Fetching live manifest for {org_id}/{repo_id}")
    
    try:
        # Special case for www as org_id - this should be handled by middleware but just in case
        if org_id.lower() == "www":
            print(f"⚠️ 'www' detected as org_id - this is likely a middleware routing issue")
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID 'www'. This appears to be a routing issue. Please access this content through the main application."
            )
            
        # Special case for settings persona - redirect to dev persona
        if persona == "settings":
            print(f"⚠️ Settings persona requested - using dev instead")
            persona = "dev"  # Use dev persona instead of failing
            
        # Check if persona is valid
        if persona not in ["internal", "dev"]:
            print(f"⚠️ Invalid persona '{persona}' requested - using dev instead")
            persona = "dev"  # Default to dev if invalid
            
        print(f"📋 Using persona: {persona}")
        
        return await _build_live_manifest(
            db=db,
            org_id=org_id,
            repo_id=repo_id,
            user=user,
            persona=persona,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching manifest: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docbook/live-org-status", response_model=LiveOrgStatusResponse)
async def get_live_org_status(
    org_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint to validate if an org has a published live docbook."""

    normalized_org = org_id.strip()
    if not normalized_org:
        raise HTTPException(status_code=400, detail="org_id is required")

    docbook_service = DocbookService(db)
    repo = await docbook_service.get_repo_by_org(normalized_org)

    if not repo or not repo.live_url:
        raise HTTPException(status_code=404, detail="Live docs not found for org")
    
    # Fetch available repositories for this organization
    available_repos = []
    try:
        # Extract repo name from live_url
        if repo.live_url:
            # Parse the URL properly to handle both full URLs and path-only URLs
            if repo.live_url.startswith('http'):
                # It's a full URL, extract the path
                from urllib.parse import urlparse
                parsed_url = urlparse(repo.live_url)
                path = parsed_url.path.strip('/')
            else:
                # It's already a path
                path = repo.live_url.strip('/')
                
            # Extract the first path segment as the repo name
            path_parts = path.split('/')
            if path_parts:
                repo_name = path_parts[0]
                available_repos.append(repo_name)
                logger.info(f"[live-org-status] Found repo from live_url: {repo_name}")
            else:
                logger.warning(f"[live-org-status] No path segments found in URL: {repo.live_url}")
        else:
            logger.warning("[live-org-status] No live URL found for repo")

    except Exception as e:
        logger.warning(f"[live-org-status] Error extracting repos: {str(e)}")

    return LiveOrgStatusResponse(
        org_id=repo.org_id,
        exists=True,
        live_url=repo.live_url,
        repos=available_repos,
    )


@router.get("/docbook/live-manifest/public")
async def get_live_manifest_public(
    org_id: str = Query(...),
    repo_id: str = Query(...),
    persona: str = Query("dev", description="Documentation persona (internal or dev)"),
    db: AsyncSession = Depends(get_db),
):
    """Public manifest endpoint without authentication."""

    print(f"🌐 Fetching PUBLIC live manifest for {org_id}/{repo_id}")
    
    # No compatibility fixes - trust the frontend's repo_id parameter
    print(f"✅ Using repo_id directly from frontend: {repo_id}")

    try:
        # Special case for www as org_id - this should be handled by middleware but just in case
        if org_id.lower() == "www":
            print(f"⚠️ 'www' detected as org_id - this is likely a middleware routing issue")
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID 'www'. This appears to be a routing issue. Please access this content through the main application."
            )
            
        # Special case for settings persona - redirect to dev persona
        if persona == "settings":
            print(f"⚠️ Settings persona requested for {org_id}/{repo_id} - using dev instead")
            persona = "dev"  # Use dev persona instead of failing
            
        # Check if persona is valid
        if persona not in ["internal", "dev"]:
            print(f"⚠️ Invalid persona '{persona}' requested - using dev instead")
            persona = "dev"  # Default to dev if invalid
            
        print(f"📋 Using persona: {persona} for public access")
        
        # For public access, block internal persona
        if persona == "internal":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal documentation requires authentication")
        
        return await _build_live_manifest(
            db=db,
            org_id=org_id,
            repo_id=repo_id,
            user=None,
            persona=persona,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching public manifest: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docbook/live-content")
async def get_live_content(
    org_id: str = Query(...),
    repo_id: str = Query(...),
    persona: str = Query("dev", description="Documentation persona (internal or dev)"),
    slug: List[str] = Query([], description="Path segments inside the published repo"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch rendered markdown content for authenticated viewers."""

    print(f"📔 Fetching live content for {org_id}/{repo_id} slug={slug}")

    try:
        # Special case for www as org_id - this should be handled by middleware but just in case
        if org_id.lower() == "www":
            print(f"⚠️ 'www' detected as org_id - this is likely a middleware routing issue")
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID 'www'. This appears to be a routing issue. Please access this content through the main application."
            )
            
        # Special case for settings persona - redirect to dev persona
        if persona == "settings":
            print(f"⚠️ Settings persona requested - using dev instead")
            persona = "dev"  # Use dev persona instead of failing
            
        # Check if persona is valid
        if persona not in ["internal", "dev"]:
            print(f"⚠️ Invalid persona '{persona}' requested - using dev instead")
            persona = "dev"  # Default to dev if invalid
            
        print(f"📋 Using persona: {persona}")
        
        return await _fetch_live_page(
            db=db,
            org_id=org_id,
            repo_id=repo_id,
            slug=slug,
            user=user,
            persona=persona,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching live content: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docbook/live-content/public")
async def get_live_content_public(
    org_id: str = Query(...),
    repo_id: str = Query(...),
    persona: str = Query("dev", description="Documentation persona (internal or dev)"),
    slug: List[str] = Query([], description="Path segments inside the published repo"),
    db: AsyncSession = Depends(get_db),
):
    """Public live content endpoint without authentication."""

    print("=" * 80)
    print(f"🌐 Fetching PUBLIC live content for {org_id}/{repo_id}")
    print(f"🔢 Raw slug list: {slug}")

    # No compatibility fixes - trust the frontend's repo_id parameter
    print(f"✅ Using repo_id directly from frontend: {repo_id}")

    original_slug = list(slug)
    cleaned_slug = [segment for segment in slug if segment]

    # Remove common redundant prefixes
    prefixes_to_strip = ["docs", org_id, repo_id]
    while cleaned_slug and cleaned_slug[0] in prefixes_to_strip:
        removed = cleaned_slug.pop(0)
        print(f"🧹 Removed redundant slug prefix: {removed}")

    # Handle persona segment if present
    if cleaned_slug and cleaned_slug[0] == persona:
        cleaned_slug.pop(0)
        print(f"🧹 Removed persona segment from slug (persona={persona})")

    # Special handling for deployed frontend variants
    if (len(cleaned_slug) >= 2 and
            cleaned_slug[0] == repo_id and
            cleaned_slug[1] == persona):
        print("🧭 Detected repo/persona slug tuple – trimming")
        cleaned_slug = cleaned_slug[2:]

    if cleaned_slug:
        if cleaned_slug[0].upper() == "SUMMARY":
            cleaned_slug[0] = "SUMMARY.md"
    else:
        cleaned_slug = ["SUMMARY.md"]
        print("🧭 Empty slug after normalization – defaulting to SUMMARY.md")

    if cleaned_slug != original_slug:
        print(f"🔧 Normalized slug from {original_slug} -> {cleaned_slug}")

    slug = cleaned_slug

    try:
        # Special case for www as org_id - this should be handled by middleware but just in case
        if org_id.lower() == "www":
            print(f"⚠️ 'www' detected as org_id - this is likely a middleware routing issue")
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID 'www'. This appears to be a routing issue. Please access this content through the main application."
            )
            
        # Special case for settings persona - redirect to dev persona
        if persona == "settings":
            print(f"⚠️ Settings persona requested for public content - using dev instead")
            persona = "dev"  # Use dev persona instead of failing
            
        # Check if persona is valid
        if persona not in ["internal", "dev"]:
            print(f"⚠️ Invalid persona '{persona}' requested - using dev instead")
            persona = "dev"  # Default to dev if invalid
            
        print(f"📋 Using persona: {persona} for public access")
        
        # For public access, force dev persona for internal requests
        if persona == "internal":
            # Check if user is authenticated
            print(f"⚠️ Forcing dev persona for public access to internal docs")
            persona = "dev"
        
        return await _fetch_live_page(
            db=db,
            org_id=org_id,
            repo_id=repo_id,
            slug=slug,
            user=None,
            persona=persona,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching public live content: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docbook/publish-history")
async def get_publish_history(
    org_id: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get publishing history for an organization."""
    print(f"📜 Fetching publish history for {org_id}")
    
    try:
        result = await db.execute(
            select(DocbookPublishEvent)
            .where(
                DocbookPublishEvent.org_id == org_id,
                DocbookPublishEvent.user_id == user.id
            )
            .order_by(DocbookPublishEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        
        history = [
            {
                "id": str(event.id),
                "repo_id": event.repo_id,
                "main_commit": event.main_commit,
                "status": event.status,
                "created_at": event.created_at.isoformat(),
                "completed_at": event.completed_at.isoformat() if event.completed_at else None,
                "error_message": event.error_message
            }
            for event in events
        ]
        
        print(f"✅ Found {len(history)} publish events")
        return {"org_id": org_id, "history": history}
        
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
