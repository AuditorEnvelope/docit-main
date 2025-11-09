"""Repository documentation endpoints."""

from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()


def _require_token(user: User) -> str:
    token = user.github_access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub token not found")
    return token


async def _fetch_github(
    url: str,
    token: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Pustak-AI",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers, params=params)
    return response


async def _build_tree(
    repo_full_name: str,
    path: str,
    branch: str,
    token: str,
    depth: int = 0,
) -> List[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}" if path else f"https://api.github.com/repos/{repo_full_name}/contents"
    response = await _fetch_github(url, token, params={"ref": branch})

    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch contents ({response.status_code})")

    items = response.json()
    children: List[Dict[str, Any]] = []

    for item in items:
        node_path = item.get("path", "")
        node = {
            "id": node_path,
            "name": item.get("name"),
            "type": "folder" if item.get("type") == "dir" else "file",
            "path": node_path,
            "depth": depth,
            "size": item.get("size"),
        }

        if item.get("type") == "dir":
            node["children"] = await _build_tree(repo_full_name, node_path, branch, token, depth + 1)
        children.append(node)

    return children


@router.get("/repos/{repo_name}/tree")
async def get_repository_tree(
    repo_name: str,
    branch: str = Query("staging", description="Branch to inspect"),
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    token = _require_token(user)
    contents = await _build_tree(repo_name, "", branch, token)
    return {
        "id": repo_name,
        "type": "root",
        "name": repo_name,
        "path": "/",
        "depth": 0,
        "children": contents,
    }


@router.get("/repos/{repo_name}/node/{path:path}")
async def get_node_details(
    repo_name: str,
    path: str,
    branch: str = Query("staging", description="Branch to inspect"),
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    token = _require_token(user)
    url = f"https://api.github.com/repos/{repo_name}/contents/{path}"
    response = await _fetch_github(url, token, params={"ref": branch})

    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch node")

    data = response.json()
    node: Dict[str, Any] = {
        "id": data.get("path"),
        "name": data.get("name"),
        "path": data.get("path"),
        "type": "folder" if data.get("type") == "dir" else "file",
        "size": data.get("size"),
    }

    if data.get("encoding") == "base64" and data.get("content"):
        import base64

        decoded = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
        node["content"] = decoded

    return node


@router.get("/repos/{repo_name}/search")
async def search_repository_documentation(
    repo_name: str,
    query: str = Query(..., min_length=2, description="Search query"),
    branch: str = Query("staging", description="Branch to search"),
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    token = _require_token(user)
    url = f"https://api.github.com/repos/{repo_name}/code/search"
    params = {
        "q": f"{query} repo:{repo_name} path:docs/",
        "ref": branch,
    }
    response = await _fetch_github(url, token, params=params, timeout=15.0)

    if response.status_code == 422:
        # GitHub returns 422 when search index is empty; treat as no results
        return []
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Search failed")

    data = response.json()
    items = data.get("items", [])

    results: List[Dict[str, Any]] = []
    for item in items:
        path = item.get("path")
        results.append(
            {
                "name": item.get("name"),
                "path": path,
                "url": item.get("html_url"),
                "score": item.get("score"),
            }
        )

    return results


@router.get("/search")
async def search_all_documentation(
    query: str = Query(..., min_length=2, description="Search query"),
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    token = _require_token(user)
    url = "https://api.github.com/search/code"
    params = {
        "q": f"{query} user:{user.username} path:docs/",
    }
    response = await _fetch_github(url, token, params=params, timeout=15.0)

    if response.status_code == 422:
        return []
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Search failed")

    data = response.json()
    items = data.get("items", [])

    results: List[Dict[str, Any]] = []
    for item in items:
        metadata = item.get("repository", {})
        results.append(
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "repo": metadata.get("full_name"),
                "url": item.get("html_url"),
                "score": item.get("score"),
            }
        )

    return results
