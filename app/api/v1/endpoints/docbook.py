"""Docbook helper endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.docbook import DocbookRepo, DocbookReview, DocbookStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.docbook.service import DocbookService
from app.services.auth import AuthService

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


class DocbookBranchesResponse(BaseModel):
    org_id: str
    repo: str
    branches: List[str]


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
        raw_user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        if not raw_user_id:
            raise HTTPException(status_code=401, detail="User context missing")

        try:
            user_uuid = UUID(str(raw_user_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user identifier")

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
