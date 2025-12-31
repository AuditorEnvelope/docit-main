"""
Workspace API endpoints for Unified Canvas Editor
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter()


class FileNode(BaseModel):
    id: str
    type: str  # 'folder' or 'page'
    title: str
    parentId: str | None
    position: int
    children: List['FileNode'] = []
    path: str | None = None
    createdAt: str
    updatedAt: str


class SyncPayload(BaseModel):
    org_id: str
    repo_id: str
    treeStructure: FileNode
    modifiedFiles: List[Dict[str, Any]]
    deletedNodes: List[str]
    tempIdMapping: Optional[Dict[str, str]] = None


@router.get("/workspace/{org_id}/{repo_id}/tree")
async def get_workspace_tree(
    org_id: str,
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Load workspace tree structure from docbook repo staging branch
    
    Returns tree structure built from actual docbook repository
    """
    
    try:
        # Get docbook repo for this organization
        from app.services.docbook.service import DocbookService
        import httpx
        
        docbook_service = DocbookService(db)
        
        # Get GitHub token first (same pattern as docbook.py)
        token = current_user.github_access_token
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not available")
        
        # Get docbook repository
        docbook_repo = await docbook_service.get_repo_by_org(org_id)
        
        if not docbook_repo:
            print(f"[workspace] No docbook repo found for org={org_id}")
            # No docbook repo linked - return empty tree
            return {
                "tree": {
                    "id": "root",
                    "type": "folder",
                    "title": f"{repo_id} Documentation",
                    "parentId": None,
                    "position": 0,
                    "children": [],
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-01T00:00:00Z"
                }
            }
        
        # Fetch docbook structure from GitHub (same as EnhancedSidebar)
        # Use the same helper function pattern as docbook.py
        async with httpx.AsyncClient(timeout=10.0) as client:
            async def fetch_folder_contents(path: str, branch: str = "staging"):
                """
                Fetch folder contents recursively - matches docbook.py pattern exactly
                """
                base_url = f"https://api.github.com/repos/{docbook_repo.docbook_full_name}/contents"
                normalized_path = path.lstrip("/")
                url = base_url if not normalized_path else f"{base_url}/{normalized_path}"
                
                headers = {
                    "Authorization": f"Bearer {token}",  # Use Bearer, not token
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                }
                
                response = await client.get(url, headers=headers, params={"ref": branch})
                
                print(f"[workspace] GitHub API call: {url} -> {response.status_code}")
                
                if response.status_code == 404:
                    print(f"[workspace] Path not found: {path}")
                    return []
                
                if response.status_code != 200:
                    print(f"[workspace] GitHub API error ({response.status_code}): {response.text[:200]}")
                    return []
                
                contents = response.json()
                result = []
                
                for item in contents:
                    item_type = item.get("type")
                    name = item.get("name")
                    item_path = item.get("path")  # Use path from GitHub response
                    
                    if item_type == "dir":
                        # Recursively fetch folder contents using the path from GitHub
                        children = await fetch_folder_contents(item_path, branch)
                        result.append({
                            "name": name,
                            "type": "folder",
                            "path": item_path,
                            "files": children
                        })
                    elif item_type == "file" and name.endswith(".md"):
                        # Only include .md files
                        result.append({
                            "name": name,
                            "type": "file",
                            "path": item_path
                        })
                
                return result
            
            # Fetch from /{repoId}/docs path
            # This matches the docbook structure: jaishreram/docs/
            base_path = f"{repo_id}/docs"
            print(f"[workspace] Fetching docbook structure for org={org_id}, repo={repo_id}")
            print(f"[workspace] Docbook repo: {docbook_repo.docbook_full_name}")
            print(f"[workspace] Base path: {base_path}")
            
            folders = await fetch_folder_contents(base_path, "staging")
            
            # If no results, try fetching from root to debug
            if not folders:
                print(f"[workspace] No results from {base_path}, trying root path...")
                root_folders = await fetch_folder_contents("", "staging")
                print(f"[workspace] Root path returned {len(root_folders)} items")
                if root_folders:
                    print(f"[workspace] Root items: {[f.get('name') for f in root_folders[:5]]}")
            
            print(f"[workspace] Fetched {len(folders)} top-level items from {base_path}")
        
        if not folders:
            # Return empty tree if no docs exist
            return {
                "tree": {
                    "id": "root",
                    "type": "folder",
                    "title": f"{repo_id} Documentation",
                    "parentId": None,
                    "position": 0,
                    "children": [],
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-01T00:00:00Z"
                }
            }
        
        # Convert docbook structure to workspace tree format
        def convert_to_tree_node(item, parent_id="root", position=0):
            node_id = f"{parent_id}/{item['name']}" if parent_id != "root" else item['name']
            
            if item['type'] == 'folder':
                children = [
                    convert_to_tree_node(child, node_id, idx)
                    for idx, child in enumerate(item.get('files', []))
                ]
                return {
                    "id": node_id,
                    "type": "folder",
                    "title": item['name'],
                    "parentId": parent_id,
                    "position": position,
                    "children": children,
                    "path": item.get('path'),  # Include full path from GitHub
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-01T00:00:00Z"
                }
            else:
                # File node - use path from GitHub response
                file_path = item.get('path', f"docs/{item['name']}")
                return {
                    "id": node_id,
                    "type": "page",
                    "title": item['name'].replace('.md', '').replace('.MD', ''),
                    "parentId": parent_id,
                    "position": position,
                    "children": [],
                    "path": file_path,  # Use actual path from GitHub
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-01T00:00:00Z"
                }
        
        # Build children from top-level folders
        children = [
            convert_to_tree_node(item, "root", idx)
            for idx, item in enumerate(folders)
        ]
        
        return {
            "tree": {
                "id": "root",
                "type": "folder",
                "title": f"{repo_id} Documentation",
                "parentId": None,
                "position": 0,
                "children": children,
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z"
            }
        }
        
    except Exception as e:
        # Log error and return empty tree
        print(f"Error loading workspace tree: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "tree": {
                "id": "root",
                "type": "folder",
                "title": f"{repo_id} Documentation",
                "parentId": None,
                "position": 0,
                "children": [],
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z"
            }
        }


@router.post("/workspace/sync")
async def sync_workspace(
    payload: SyncPayload,
    commit_message: str = Query(..., description="Commit message for all changes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sync workspace changes to backend and commit all changes in one commit
    
    Processes:
    - New pages/folders (with temp IDs)
    - Modified content
    - Deleted nodes
    - Tree structure changes
    
    Commits all changes to staging branch in a single commit
    """
    import httpx
    import base64
    from app.services.docbook.service import DocbookService
    
    try:
        # Get docbook repo
        docbook_service = DocbookService(db)
        docbook_repo = await docbook_service.get_repo_by_org(payload.org_id)
        
        if not docbook_repo:
            raise HTTPException(status_code=404, detail="Docbook repository not found")
        
        # Get GitHub token
        token = current_user.github_access_token
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not available")
        
        # Get user info for commit author
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                }
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch user information")
            
            user_data = user_response.json()
            author_name = user_data.get("name") or user_data.get("login", "Pustak User")
            author_email = user_data.get("email") or f"{user_data.get('id', '')}+{user_data.get('login', 'user')}@users.norever.github.com"
            
            repo_full_name = docbook_repo.docbook_full_name
            branch = "staging"
            
            # Collect all file changes
            file_changes = []
            temp_id_mapping = {}
            
            # Process modified files
            for file_data in payload.modifiedFiles:
                page_id = file_data.get('pageId')
                file_path = file_data.get('path', '')
                content = file_data.get('content', '')
                action = file_data.get('action', 'update')
                
                # If it's a temp ID, generate real UUID
                if page_id and page_id.startswith('temp-'):
                    import uuid
                    real_id = str(uuid.uuid4())
                    temp_id_mapping[page_id] = real_id
                
                # Get current file SHA if it exists
                file_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
                file_response = await client.get(
                    file_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    params={"ref": branch}
                )
                
                sha = None
                if file_response.status_code == 200:
                    sha = file_response.json().get("sha")
                elif file_response.status_code != 404:
                    print(f"[workspace] Warning: Failed to check file {file_path}: {file_response.status_code}")
                
                # Encode content
                content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                
                file_changes.append({
                    "path": file_path,
                    "content": content_base64,
                    "sha": sha,
                    "action": action
                })
            
            # Process deletions
            for deleted_path in payload.deletedNodes:
                # Get file SHA for deletion
                file_url = f"https://api.github.com/repos/{repo_full_name}/contents/{deleted_path}"
                file_response = await client.get(
                    file_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    params={"ref": branch}
                )
                
                if file_response.status_code == 200:
                    sha = file_response.json().get("sha")
                    file_changes.append({
                        "path": deleted_path,
                        "sha": sha,
                        "action": "delete"
                    })
            
            # Commit all changes in one commit using GitHub's create-tree API
            if file_changes:
                # Get base tree SHA
                ref_response = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/git/ref/heads/{branch}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    }
                )
                
                if ref_response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to get branch reference")
                
                base_sha = ref_response.json()["object"]["sha"]
                
                # Get base tree
                commit_response = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/git/commits/{base_sha}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    }
                )
                
                if commit_response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to get base commit")
                
                base_tree_sha = commit_response.json()["tree"]["sha"]
                
                # Create tree with all changes
                tree_items = []
                for change in file_changes:
                    if change["action"] == "delete":
                        tree_items.append({
                            "path": change["path"],
                            "mode": "100644",
                            "type": "blob",
                            "sha": None  # None means delete
                        })
                    else:
                        # Create blob for new/updated file
                        blob_response = await client.post(
                            f"https://api.github.com/repos/{repo_full_name}/git/blobs",
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/vnd.github.v3+json",
                                "User-Agent": "Pustak-AI"
                            },
                            json={
                                "content": change["content"],
                                "encoding": "base64"
                            }
                        )
                        
                        if blob_response.status_code not in (200, 201):
                            raise HTTPException(status_code=500, detail=f"Failed to create blob for {change['path']}")
                        
                        blob_sha = blob_response.json()["sha"]
                        tree_items.append({
                            "path": change["path"],
                            "mode": "100644",
                            "type": "blob",
                            "sha": blob_sha
                        })
                
                # Create tree
                tree_response = await client.post(
                    f"https://api.github.com/repos/{repo_full_name}/git/trees",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    json={
                        "base_tree": base_tree_sha,
                        "tree": tree_items
                    }
                )
                
                if tree_response.status_code not in (200, 201):
                    raise HTTPException(status_code=500, detail="Failed to create tree")
                
                new_tree_sha = tree_response.json()["sha"]
                
                # Create commit
                commit_response = await client.post(
                    f"https://api.github.com/repos/{repo_full_name}/git/commits",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    json={
                        "message": commit_message,
                        "tree": new_tree_sha,
                        "parents": [base_sha],
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
                
                if commit_response.status_code not in (200, 201):
                    raise HTTPException(status_code=500, detail="Failed to create commit")
                
                new_commit_sha = commit_response.json()["sha"]
                
                # Update branch reference
                update_response = await client.patch(
                    f"https://api.github.com/repos/{repo_full_name}/git/refs/heads/{branch}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    json={"sha": new_commit_sha}
                )
                
                if update_response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to update branch")
                
                print(f"[workspace] ✅ Committed {len(file_changes)} changes to {branch} branch")
                
                return {
                    "success": True,
                    "temp_id_mapping": temp_id_mapping,
                    "commit_sha": new_commit_sha,
                    "message": f"Successfully committed {len(file_changes)} changes",
                    "files_changed": len(file_changes)
                }
            else:
                return {
                    "success": True,
                    "temp_id_mapping": temp_id_mapping,
                    "message": "No changes to commit"
                }
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[workspace] Error syncing workspace: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error syncing workspace: {str(e)}")


@router.get("/workspace/{org_id}/{repo_id}/page")
async def get_page_content(
    org_id: str,
    repo_id: str,
    path: str = Query(..., description="File path in docbook repo (e.g., 'jaishreram/docs/dev/api.md')"),
    branch: str = Query("staging", description="Branch to fetch from"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Load content for a specific page from docbook repository
    
    Fetches file content from GitHub using the path from the FileNode
    """
    try:
        # Get docbook repo
        from app.services.docbook.service import DocbookService
        import httpx
        import base64
        
        docbook_service = DocbookService(db)
        docbook_repo = await docbook_service.get_repo_by_org(org_id)
        
        if not docbook_repo:
            raise HTTPException(status_code=404, detail="Docbook repository not found")
        
        # Get GitHub token
        token = current_user.github_access_token
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not available")
        
        # Fetch file from GitHub
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://api.github.com/repos/{docbook_repo.docbook_full_name}/contents/{path}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Pustak-AI"
            }
            
            response = await client.get(url, headers=headers, params={"ref": branch})
            
            print(f"[workspace] Fetching file content: {path} -> {response.status_code}")
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"File not found: {path}")
            
            if response.status_code != 200:
                print(f"[workspace] GitHub API error ({response.status_code}): {response.text[:200]}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch file: {response.status_code}"
                )
            
            data = response.json()
            
            # Decode base64 content
            if data.get("encoding") == "base64" and data.get("content"):
                content = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
            else:
                content = data.get("content", "")
            
            return {
                "content": content,
                "path": path,
                "updatedAt": data.get("commit", {}).get("commit", {}).get("committer", {}).get("date", "2025-01-01T00:00:00Z")
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[workspace] Error fetching page content: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching file content: {str(e)}")
