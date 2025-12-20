from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Tuple, List, Dict, Any, Optional
from uuid import UUID
from urllib.parse import unquote
import base64

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


class CommitFileRequest(BaseModel):
    repo: str
    file_path: str
    content: str
    commit_message: str
    branch: str = "staging"


class BatchFileOperation(BaseModel):
    """Single file operation in a batch"""
    action: str  # 'create', 'update', 'delete', 'move'
    path: str
    content: Optional[str] = None
    new_path: Optional[str] = None  # For move operation


class BatchCommitRequest(BaseModel):
    """Batch commit multiple file operations"""
    repo: str
    operations: List[BatchFileOperation]
    commit_message: str
    branch: str = "staging"


class CreatePageRequest(BaseModel):
    """Create a new documentation page"""
    repo: str
    path: str  # e.g., "docs/dev/new-page.md"
    content: str = "# New Page\n\nContent goes here..."
    commit_message: str = "docs: Create new page"
    branch: str = "staging"


class DeletePageRequest(BaseModel):
    """Delete a documentation page"""
    repo: str
    path: str
    commit_message: str = "docs: Delete page"
    branch: str = "staging"


class MovePageRequest(BaseModel):
    """Move/rename a documentation page"""
    repo: str
    old_path: str
    new_path: str
    commit_message: str = "docs: Move page"
    branch: str = "staging"


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
                (Repository.full_name == repo_name) | (Repository.repo_id == repo_name)
            )
            result = await db.execute(stmt)
            db_persona = result.scalar_one_or_none()
            
            if db_persona and db_persona in valid_personas:
                print(f"✅ Using database doc_persona: {db_persona}")
                doc_persona = db_persona
            else:
                print(f"⚠️ Invalid doc_persona: {doc_persona}, falling back to 'internal'")
                doc_persona = "internal"
        except Exception as e:
            print(f"⚠️ Error fetching doc_persona from database: {e}")
            print(f"⚠️ Falling back to 'internal'")
            doc_persona = "internal"
    
    # Map 'developer' to 'dev' for compatibility
    if doc_persona == "developer":
        doc_persona = "dev"
        print(f"🔄 Mapped 'developer' to 'dev' for compatibility")
    
    print(f"📝 Using doc_persona: {doc_persona} for {repo_name}")

    # Create generator with validated persona
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
    
    # Update last_documented_at timestamp in repositories table
    from datetime import datetime, timezone
    from sqlalchemy import select, update
    from app.models.repository import Repository
    from app.services.repositories.service import RepositoryService
    
    try:
        # Upsert repository record to ensure it exists
        repo_service = RepositoryService(db)
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
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount > 0:
            print(f"✅ Updated last_documented_at for {repo_name}")
        else:
            print(f"⚠️ No repository found to update last_documented_at for {repo_name}")
    except Exception as e:
        print(f"⚠️ Failed to update last_documented_at: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        # Don't fail the whole request if this update fails

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
            raise HTTPException(status_code=400, detail="Repository must be in org/repo format")
        
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
                    "User-Agent": "Pustak-AI"
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch user information from GitHub"
                )
            
            user_data = user_response.json()
            author_name = user_data.get("name") or user_data.get("login", "Pustak User")
            author_email = user_data.get("email") or f"{user_data.get('id', '')}+{user_data.get('login', 'user')}@users.noreply.github.com"
            
            # Get current file SHA (required for update)
            file_url = f"https://api.github.com/repos/{request.repo}/contents/{normalized_path}"
            file_response = await client.get(
                file_url,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
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
                    "User-Agent": "Pustak-AI"
                },
                json=commit_payload
            )
            
            if commit_response.status_code not in (200, 201):
                error_data = commit_response.json() if commit_response.headers.get("content-type", "").startswith("application/json") else {}
                error_message = error_data.get("message", f"Failed to commit file: {commit_response.status_code}")
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
        raise HTTPException(status_code=500, detail=f"Error committing file: {str(e)}")


# ==================== HELPER FUNCTIONS ====================


async def _fetch_github_user(client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
    """Fetch GitHub user information"""
    response = await client.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Pustak-AI"
        }
    )
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch user info")
    return response.json()


async def _get_branch_head(client: httpx.AsyncClient, repo: str, branch: str, token: str) -> Dict[str, Any]:
    """Get the latest commit on a branch"""
    response = await client.get(
        f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Pustak-AI"
        }
    )
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail=f"Branch {branch} not found")
    
    ref_data = response.json()
    commit_sha = ref_data["object"]["sha"]
    
    # Fetch commit details
    commit_response = await client.get(
        f"https://api.github.com/repos/{repo}/git/commits/{commit_sha}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Pustak-AI"
        }
    )
    if commit_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch commit")
    
    return {"sha": commit_sha, "commit": commit_response.json()}


async def _fetch_file_content(client: httpx.AsyncClient, repo: str, path: str, branch: str, token: str) -> str:
    """Fetch file content from GitHub"""
    response = await client.get(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Pustak-AI"
        },
        params={"ref": branch}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail=f"File {path} not found")
    
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
    return data.get("content", "")


# ==================== BATCH OPERATIONS ENDPOINTS ====================


@router.post("/batch-commit")
async def batch_commit_files(
    request: BatchCommitRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """
    Commit multiple file operations in a single atomic commit.
    Uses GitHub Tree API for batch operations.
    """
    github_token = _require_github_token(user)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get user identity
            user_data = await _fetch_github_user(client, github_token)
            author_name = user_data.get("name") or user_data.get("login", "Pustak User")
            author_email = user_data.get("email") or f"{user_data.get('id')}+{user_data.get('login')}@users.noreply.github.com"
            
            # Get base commit SHA
            base_commit = await _get_branch_head(client, request.repo, request.branch, github_token)
            base_tree_sha = base_commit["commit"]["tree"]["sha"]
            
            # Build tree for all operations
            tree_items = []
            for op in request.operations:
                if op.action in ["create", "update"]:
                    if not op.content:
                        raise HTTPException(status_code=400, detail=f"Content required for {op.action} operation")
                    tree_items.append({
                        "path": op.path,
                        "mode": "100644",
                        "type": "blob",
                        "content": op.content
                    })
                elif op.action == "delete":
                    tree_items.append({
                        "path": op.path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": None  # null SHA deletes the file
                    })
                elif op.action == "move":
                    if not op.new_path:
                        raise HTTPException(status_code=400, detail="new_path required for move operation")
                    # Fetch original file content
                    file_content = await _fetch_file_content(client, request.repo, op.path, request.branch, github_token)
                    # Delete old, create new
                    tree_items.append({"path": op.path, "sha": None})
                    tree_items.append({
                        "path": op.new_path,
                        "mode": "100644",
                        "type": "blob",
                        "content": file_content
                    })
            
            # Create new tree
            tree_response = await client.post(
                f"https://api.github.com/repos/{request.repo}/git/trees",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                },
                json={
                    "base_tree": base_tree_sha,
                    "tree": tree_items
                }
            )
            
            if tree_response.status_code != 201:
                error_detail = tree_response.text
                raise HTTPException(status_code=500, detail=f"Failed to create tree: {error_detail}")
            
            new_tree_sha = tree_response.json()["sha"]
            
            # Create commit
            commit_response = await client.post(
                f"https://api.github.com/repos/{request.repo}/git/commits",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                },
                json={
                    "message": request.commit_message,
                    "tree": new_tree_sha,
                    "parents": [base_commit["sha"]],
                    "author": {
                        "name": author_name,
                        "email": author_email
                    },
                    "committer": {
                        "name": author_name,
                        "email": author_email
                    }
                }
            )
            
            if commit_response.status_code != 201:
                error_detail = commit_response.text
                raise HTTPException(status_code=500, detail=f"Failed to create commit: {error_detail}")
            
            new_commit_sha = commit_response.json()["sha"]
            
            # Update branch reference
            ref_response = await client.patch(
                f"https://api.github.com/repos/{request.repo}/git/refs/heads/{request.branch}",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                },
                json={"sha": new_commit_sha}
            )
            
            if ref_response.status_code != 200:
                error_detail = ref_response.text
                raise HTTPException(status_code=500, detail=f"Failed to update branch: {error_detail}")
            
            return {
                "success": True,
                "commit_sha": new_commit_sha,
                "operations_count": len(request.operations),
                "message": f"Successfully committed {len(request.operations)} operations"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch commit failed: {str(e)}")


@router.post("/create-page")
async def create_page(
    request: CreatePageRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new documentation page"""
    batch_req = BatchCommitRequest(
        repo=request.repo,
        operations=[BatchFileOperation(
            action="create",
            path=request.path,
            content=request.content
        )],
        commit_message=request.commit_message,
        branch=request.branch
    )
    return await batch_commit_files(batch_req, user)


@router.post("/delete-page")
async def delete_page(
    request: DeletePageRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Delete a documentation page"""
    batch_req = BatchCommitRequest(
        repo=request.repo,
        operations=[BatchFileOperation(
            action="delete",
            path=request.path
        )],
        commit_message=request.commit_message,
        branch=request.branch
    )
    return await batch_commit_files(batch_req, user)


@router.post("/move-page")
async def move_page(
    request: MovePageRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Move/rename a documentation page"""
    batch_req = BatchCommitRequest(
        repo=request.repo,
        operations=[BatchFileOperation(
            action="move",
            path=request.old_path,
            new_path=request.new_path
        )],
        commit_message=request.commit_message,
        branch=request.branch
    )
    return await batch_commit_files(batch_req, user)
