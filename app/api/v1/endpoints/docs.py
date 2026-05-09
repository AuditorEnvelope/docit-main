from app.utils.github_dual_app import GitHubDualAppHelper
from app.services.documentation.manual_generation import ManualDocGenerator
from app.services.docbook.publisher import DocbookPublisher
from app.services.auth import get_current_user
from app.schemas.documentation import ManualGenerationResponse
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Tuple
from uuid import UUID
from urllib.parse import unquote
import base64
import logging

import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, async_session

logger = logging.getLogger(__name__)

# Phase 6: Import usage service for limit enforcement and recording
try:
    from app.services.usage import UsageService
    from app.models.usage import ResourceType
    USAGE_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Usage service not available: {e}")
    USAGE_SERVICE_AVAILABLE = False
    UsageService = None
    ResourceType = None

router = APIRouter()

# Log router initialization
logger.info("Docs router initialized, usage service available: %s",
            USAGE_SERVICE_AVAILABLE)


class CommitFileRequest(BaseModel):
    repo: str
    file_path: str
    content: str
    commit_message: str
    branch: str = "staging"


def _require_github_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="GitHub token not found for user")
    return token


def _parse_repo_full_name(repo_full_name: str) -> Tuple[str, str]:
    repo_full_name = repo_full_name.strip()
    if "/" not in repo_full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="repo_name must be in the form org/repo")
    org, repo = repo_full_name.split("/", 1)
    if not org or not repo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid repo name provided")
    return org, repo


@router.post("/generate-v4", response_model=ManualGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_documentation_v4(
    repo_name: str = Query(..., description="Repository in the form org/repo"),
    doc_persona: str = Query(
        "internal", description="Documentation persona to apply"),
    commit_message: str | None = Query(
        None, description="Optional commit message override"),
    commit_sha: str | None = Query(
        None, description="Optional commit SHA for logging"),
    installation_id: int | None = Query(
        None, description="Writer app installation ID (optional)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ManualGenerationResponse:
    """Generate documentation manually and publish to docbook staging (legacy-compatible endpoint).

    Phase 6 Integration: Now enforces usage limits and records token usage.
    """

    # ========================================================================
    # PHASE 6 INTEGRATION: Step A - THE GUARD (Enforce Limit)
    # ========================================================================
    # Check usage limit BEFORE expensive doc generation
    logger.info(f"Checking usage limits for user {user.id} ({user.email})")
    if USAGE_SERVICE_AVAILABLE and UsageService is not None:
        usage_service = UsageService(db)

        try:
            await usage_service.enforce_limit(
                user_id=str(user.id),
                resource_type=ResourceType.DOCS_GENERATED,
            )
            logger.info(f"Usage limit check passed for user {user.id}")
        except HTTPException as limit_error:
            logger.error(
                f"Usage limit check failed for user {user.id}: {limit_error.status_code} - {limit_error.detail}")
            # Handle 404 - no active subscription
            if limit_error.status_code == 404:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "no_active_subscription",
                        "message": "No active subscription found. Your subscription may have expired or entitlement dates need renewal. Please subscribe to a plan or renew your existing subscription.",
                        "action": "subscribe_or_renew",
                        "user_id": str(user.id),
                        "user_email": user.email,
                    }
                )
            # Handle 403 - limit exceeded
            elif limit_error.status_code == 403:
                try:
                    limit_check = await usage_service.check_limit(
                        user_id=str(user.id),
                        resource_type=ResourceType.DOCS_GENERATED,
                    )
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "usage_limit_exceeded",
                            "message": f"Document generation limit reached. You've used {limit_check['used']} of {limit_check['limit']} docs.",
                            "plan": limit_check["plan"],
                            "used": limit_check["used"],
                            "limit": limit_check["limit"],
                            "cycle_end": limit_check["cycle_end"],
                            "action": "upgrade_or_wait",
                        }
                    )
                except:
                    raise limit_error
            else:
                raise
    else:
        logger.warning(
            "Usage service not available, skipping usage limit check")
    # ========================================================================

    github_token = _require_github_token(user)
    org_id, source_repo = _parse_repo_full_name(repo_name)

    # Validate and normalize doc_persona
    valid_personas = ["internal", "developer"]

    # Log the requested persona
    print(f"🔍 Requested doc_persona: {doc_persona}")

    # Check if we need to fetch from database
    if doc_persona not in valid_personas:
        # Try to get the repository's doc_persona from database
        try:
            from sqlalchemy import select
            from app.models.repository import Repository

            stmt = select(Repository.doc_persona).where(
                (Repository.full_name == repo_name) | (
                    Repository.repo_id == repo_name)
            )
            result = await db.execute(stmt)
            db_persona = result.scalar_one_or_none()

            if db_persona and db_persona in valid_personas:
                print(f"✅ Using database doc_persona: {db_persona}")
                doc_persona = db_persona
            else:
                print(
                    f"⚠️ Invalid doc_persona: {doc_persona}, falling back to 'internal'")
                doc_persona = "internal"
        except Exception as e:
            print(f"⚠️ Error fetching doc_persona from database: {e}")
            print(f"⚠️ Falling back to 'internal'")
            doc_persona = "internal"

    print(f"📝 Using doc_persona: {doc_persona} for {repo_name}")

    # Create generator with validated persona
    generator = ManualDocGenerator(doc_persona=doc_persona)
    dual_app_helper = GitHubDualAppHelper()

    message = commit_message or f"docs: Manual documentation generation for {source_repo}"

    # Generate documentation with proper error handling
    try:
        generation_result = await generator.generate(repo_name, github_token)
    except ValueError as ve:
        # Handle specific error cases (repo not found, auth failed, etc.)
        error_msg = str(ve).lower()
        logger.error(f"Generation failed for {repo_name}: {ve}")
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "repository_not_found",
                    "message": str(ve),
                    "repo_name": repo_name,
                }
            )
        elif "authentication" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "authentication_failed",
                    "message": str(ve),
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "generation_failed",
                    "message": str(ve),
                }
            )
    except Exception as e:
        logger.exception("Documentation generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "generation_failed",
                "message": f"Failed to generate documentation: {str(e)}",
            }
        )

    try:
        # Get a FRESH db session for publish — the original request session's
        # connection goes stale during the 5-10 min doc generation.
        # Retry up to 3 times for transient network errors (Neon serverless can be flaky).
        publish_result = None
        last_publish_error = None
        for attempt in range(1, 4):
            try:
                async with async_session() as fresh_db:
                    publisher = DocbookPublisher(
                        dual_app=dual_app_helper, db_session=fresh_db)
                    publish_result = await publisher.publish_to_docbook(
                        user_id=str(user.id) if isinstance(
                            user.id, UUID) else user.id,
                        org_id=org_id,
                        source_repo_name=source_repo,
                        docs_dir=generation_result.docs_dir,
                        commit_message=message,
                        commit_sha=commit_sha,
                        installation_id=installation_id,
                    )
                break  # success
            except OSError as net_err:
                last_publish_error = net_err
                logger.warning(
                    f"Publish attempt {attempt}/3 failed (network): {net_err}")
                if attempt < 3:
                    import asyncio as _aio
                    await _aio.sleep(2 * attempt)  # 2s, 4s backoff
            except Exception as db_err:
                # Non-network error (e.g. stale connection) — retry once
                last_publish_error = db_err
                logger.warning(f"Publish attempt {attempt}/3 failed: {db_err}")
                if attempt < 3:
                    import asyncio as _aio
                    await _aio.sleep(2)

        if publish_result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Docbook publication failed after 3 attempts: {last_publish_error}",
            )
    finally:
        generation_result.cleanup()

    if publish_result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=publish_result.get("message", "Docbook publication failed"),
        )

    # ========================================================================
    # PHASE 6 INTEGRATION: Step B - THE LEDGER (Record Usage)
    # ========================================================================
    # Record usage AFTER successful generation with token data
    if USAGE_SERVICE_AVAILABLE and UsageService is not None:
        try:
            async with async_session() as fresh_db_usage:
                usage_service = UsageService(fresh_db_usage)
                await usage_service.record_usage(
                    user_id=str(user.id),
                    resource_type=ResourceType.DOCS_GENERATED,
                    amount=1,
                    resource_id=str(publish_result.get(
                        "commit_sha", source_repo)),
                    # Phase 6: Shadow token tracking
                    input_tokens=generation_result.input_tokens,
                    output_tokens=generation_result.output_tokens,
                    model_name=generation_result.model_name,
                )
                await fresh_db_usage.commit()
                print(
                    f"✅ Recorded usage: {generation_result.input_tokens} input tokens, {generation_result.output_tokens} output tokens, model: {generation_result.model_name}")
        except Exception as record_error:
            # Log but don't fail the request if usage recording fails
            print(
                f"⚠️ Failed to record usage for user {user.id}: {record_error}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ Usage service not available, skipping usage recording")
    # ========================================================================

    # Update last_documented_at timestamp in repositories table
    from datetime import datetime, timezone
    from sqlalchemy import select, update
    from app.models.repository import Repository
    from app.services.repositories.service import RepositoryService

    try:
        async with async_session() as fresh_db_repo:
            # Upsert repository record to ensure it exists
            repo_service = RepositoryService(fresh_db_repo)
            await repo_service.upsert_tracked_branch(
                repo_name,
                tracked_branch="main",  # Default, will be overridden if already set
                default_branch="main"
            )

            # Update the repository's last_documented_at field
            stmt = (
                update(Repository)
                .where(Repository.full_name == repo_name)
                .values(last_documented_at=datetime.now(timezone.utc))
            )
            result = await fresh_db_repo.execute(stmt)
            await fresh_db_repo.commit()

            if result.rowcount > 0:
                print(f"✅ Updated last_documented_at for {repo_name}")
            else:
                print(
                    f"⚠️ No repository found to update last_documented_at for {repo_name}")
    except Exception as e:
        print(f"⚠️ Failed to update last_documented_at: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        # Don't fail the whole request if this update fails

    return ManualGenerationResponse(
        status=publish_result.get("status", "published_to_staging"),
        message=publish_result.get(
            "message", "Manual documentation published"),
        docbook_repo=publish_result.get("docbook_repo"),
        branch=publish_result.get("branch"),
        review_url=publish_result.get("review_url"),
    )


@router.get("/fetch-file")
async def fetch_file_from_github(
    repo: str = Query(..., description="Repository in the form org/repo"),
    filePath: str = Query(...,
                          description="Path to the file in the repository"),
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
                    "User-Agent": "DocIt-AI"
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
                content = base64.b64decode(
                    data["content"].replace("\n", "")).decode("utf-8")
                return {"content": content, "fileName": normalized_path}

            return {"content": data.get("content", ""), "fileName": normalized_path}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching file: {str(e)}")


@router.post("/commit")
async def commit_file_to_github(
    request: CommitFileRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Commit a file to GitHub repository using user's token and identity."""
    github_token = _require_github_token(user)

    try:
        # Validate repository format
        if "/" not in request.repo:
            raise HTTPException(
                status_code=400, detail="Repository must be in org/repo format")

        # Normalize file path
        normalized_path = unquote(request.file_path or "").strip("/")
        if not normalized_path:
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Get user's GitHub identity for commit author
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "DocIt-AI"
                }
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch user information from GitHub"
                )

            user_data = user_response.json()
            author_name = user_data.get(
                "name") or user_data.get("login", "DocIt User")
            author_email = user_data.get(
                "email") or f"{user_data.get('id', '')}+{user_data.get('login', 'user')}@users.noreply.github.com"

            # Get current file SHA (required for update)
            file_url = f"https://api.github.com/repos/{request.repo}/contents/{normalized_path}"
            file_response = await client.get(
                file_url,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "DocIt-AI"
                },
                params={"ref": request.branch}
            )

            sha = None
            if file_response.status_code == 200:
                file_data = file_response.json()
                sha = file_data.get("sha")
            elif file_response.status_code != 404:
                # If it's not a 404, there's an error
                raise HTTPException(
                    status_code=file_response.status_code,
                    detail=f"Failed to check file existence: {file_response.status_code}"
                )

            # Encode content to base64
            content_bytes = request.content.encode("utf-8")
            content_base64 = base64.b64encode(content_bytes).decode("utf-8")

            # Prepare commit payload
            commit_payload = {
                "message": request.commit_message,
                "content": content_base64,
                "branch": request.branch,
                "author": {
                    "name": author_name,
                    "email": author_email
                },
                "committer": {
                    "name": author_name,
                    "email": author_email
                }
            }

            # Add SHA if file exists (for update)
            if sha:
                commit_payload["sha"] = sha

            # Create/update file via GitHub API
            commit_response = await client.put(
                file_url,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "DocIt-AI"
                },
                json=commit_payload
            )

            if commit_response.status_code not in (200, 201):
                error_data = commit_response.json() if commit_response.headers.get(
                    "content-type", "").startswith("application/json") else {}
                error_message = error_data.get(
                    "message", f"Failed to commit file: {commit_response.status_code}")
                raise HTTPException(
                    status_code=commit_response.status_code,
                    detail=error_message
                )

            commit_data = commit_response.json()

            return {
                "success": True,
                "commit": {
                    "sha": commit_data.get("commit", {}).get("sha"),
                    "message": request.commit_message,
                    "author": {
                        "name": author_name,
                        "email": author_email
                    }
                },
                "content": {
                    "sha": commit_data.get("content", {}).get("sha"),
                    "path": normalized_path
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error committing file: {str(e)}")
