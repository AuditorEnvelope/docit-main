"""
Overlay Service - Admin Edits Without Changing Code
Allows non-code edits to documentation with full provenance
"""

import json
from typing import Dict, Optional, List
from datetime import datetime
import asyncpg
from dataclasses import dataclass

@dataclass
class Overlay:
    """Admin overlay for a doc node"""
    id: str
    node_id: str
    content: Dict
    author_id: str
    author_name: str
    author_email: str
    reason: str
    status: str  # active|archived|pr_created
    pr_url: Optional[str]
    created_at: datetime
    updated_at: datetime

class OverlayService:
    """
    Overlay Service - Manage admin edits
    
    Features:
    - Create/update overlays
    - Merge with base docs
    - Track history
    - Generate PRs (optional)
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def create_overlay(
        self,
        node_id: str,
        content: Dict,
        author_id: str,
        author_name: str,
        author_email: str,
        reason: str = ""
    ) -> str:
        """
        Create or update overlay for a doc node
        
        Args:
            node_id: ID of doc node to overlay
            content: New/modified content
            author_id: User ID
            author_name: User name
            author_email: User email
            reason: Reason for edit
        
        Returns: Overlay ID
        """
        async with self.pool.acquire() as conn:
            # Check if overlay already exists
            existing = await conn.fetchrow("""
                SELECT id FROM doc_overlays
                WHERE node_id = $1 AND status = 'active'
            """, node_id)
            
            if existing:
                # Update existing overlay
                overlay_id = existing['id']
                await conn.execute("""
                    UPDATE doc_overlays
                    SET content = $1, author_id = $2, author_name = $3,
                        author_email = $4, reason = $5, updated_at = NOW()
                    WHERE id = $6
                """, json.dumps(content), author_id, author_name, author_email, reason, overlay_id)
                
                # Log to history
                await conn.execute("""
                    INSERT INTO overlay_history (overlay_id, content, author_id, action)
                    VALUES ($1, $2, $3, 'updated')
                """, overlay_id, json.dumps(content), author_id)
                
                print(f"✏️  Updated overlay {overlay_id} for node {node_id}")
            else:
                # Create new overlay
                overlay_id = await conn.fetchval("""
                    INSERT INTO doc_overlays (
                        node_id, content, author_id, author_name, author_email, reason, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, 'active')
                    RETURNING id
                """, node_id, json.dumps(content), author_id, author_name, author_email, reason)
                
                # Log to history
                await conn.execute("""
                    INSERT INTO overlay_history (overlay_id, content, author_id, action)
                    VALUES ($1, $2, $3, 'created')
                """, overlay_id, json.dumps(content), author_id)
                
                print(f"✨ Created overlay {overlay_id} for node {node_id}")
            
            return str(overlay_id)
    
    async def get_overlay(self, node_id: str) -> Optional[Overlay]:
        """Get active overlay for a node"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM doc_overlays
                WHERE node_id = $1 AND status = 'active'
            """, node_id)
            
            if not row:
                return None
            
            return Overlay(
                id=str(row['id']),
                node_id=row['node_id'],
                content=json.loads(row['content']) if isinstance(row['content'], str) else row['content'],
                author_id=row['author_id'],
                author_name=row['author_name'],
                author_email=row['author_email'],
                reason=row['reason'],
                status=row['status'],
                pr_url=row['pr_url'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
    
    async def get_merged_doc(self, node_id: str) -> Dict:
        """
        Get doc node with overlay merged
        
        Merge strategy:
        1. Start with base doc (generated from code)
        2. Overlay admin edits on top
        3. Add provenance metadata
        
        Returns: Merged document
        """
        async with self.pool.acquire() as conn:
            # Get base doc
            base_row = await conn.fetchrow("""
                SELECT * FROM doc_nodes WHERE id = $1
            """, node_id)
            
            if not base_row:
                return None
            
            base_doc = dict(base_row)
            base_content = json.loads(base_doc['content']) if isinstance(base_doc['content'], str) else base_doc['content']
            
            # Get overlay
            overlay = await self.get_overlay(node_id)
            
            if not overlay:
                # No overlay, return base doc
                return {
                    **base_doc,
                    'content': base_content,
                    '_has_overlay': False
                }
            
            # Merge: overlay overrides base
            merged_content = {**base_content, **overlay.content}
            
            # Add provenance
            return {
                **base_doc,
                'content': merged_content,
                '_has_overlay': True,
                '_overlay_provenance': {
                    'edited_by': overlay.author_name,
                    'edited_at': overlay.updated_at.isoformat(),
                    'reason': overlay.reason,
                    'original_available': True
                }
            }
    
    async def get_overlay_history(self, node_id: str) -> List[Dict]:
        """Get edit history for a node"""
        async with self.pool.acquire() as conn:
            # Get overlay ID
            overlay_row = await conn.fetchrow("""
                SELECT id FROM doc_overlays WHERE node_id = $1
            """, node_id)
            
            if not overlay_row:
                return []
            
            # Get history
            rows = await conn.fetch("""
                SELECT * FROM overlay_history
                WHERE overlay_id = $1
                ORDER BY created_at DESC
            """, overlay_row['id'])
            
            return [dict(row) for row in rows]
    
    async def archive_overlay(self, node_id: str):
        """Archive (soft delete) an overlay"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE doc_overlays
                SET status = 'archived', archived_at = NOW()
                WHERE node_id = $1 AND status = 'active'
            """, node_id)
            
            print(f"🗄️  Archived overlay for node {node_id}")
    
    async def create_pr_from_overlay(
        self,
        node_id: str,
        repo_url: str,
        branch_name: str
    ) -> str:
        """
        Generate a PR from overlay
        
        This would:
        1. Create a new branch
        2. Apply overlay changes to actual code files
        3. Commit changes
        4. Create PR
        
        Returns: PR URL
        """
        # TODO: Implement GitHub API integration
        # For now, just mark as PR created
        
        async with self.pool.acquire() as conn:
            pr_url = f"{repo_url}/pull/new/{branch_name}"
            
            await conn.execute("""
                UPDATE doc_overlays
                SET status = 'pr_created', pr_url = $1
                WHERE node_id = $2 AND status = 'active'
            """, pr_url, node_id)
            
            print(f"🔀 Created PR: {pr_url}")
            return pr_url
    
    async def get_all_overlays(self, repo_id: str) -> List[Dict]:
        """Get all active overlays for a repository"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT o.*, n.title, n.path
                FROM doc_overlays o
                JOIN doc_nodes n ON o.node_id = n.id
                WHERE n.repo_id = $1 AND o.status = 'active'
                ORDER BY o.updated_at DESC
            """, repo_id)
            
            return [dict(row) for row in rows]


# FastAPI endpoints for overlay service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Overlay Service", version="1.0.0")
overlay_service = None

class CreateOverlayRequest(BaseModel):
    node_id: str
    content: Dict
    author_id: str
    author_name: str
    author_email: str
    reason: str = ""

@app.on_event("startup")
async def startup():
    global overlay_service
    import os
    db_url = os.getenv("DATABASE_URL")
    overlay_service = OverlayService(db_url)
    await overlay_service.init_db()
    print("✅ Overlay Service started")

@app.get("/")
async def root():
    return {"service": "Overlay Service", "status": "ok"}

@app.post("/overlay")
async def create_overlay(request: CreateOverlayRequest):
    """Create or update overlay"""
    overlay_id = await overlay_service.create_overlay(
        request.node_id,
        request.content,
        request.author_id,
        request.author_name,
        request.author_email,
        request.reason
    )
    return {"overlay_id": overlay_id, "status": "created"}

@app.get("/doc/{node_id}")
async def get_merged_doc(node_id: str):
    """Get doc with overlay merged"""
    doc = await overlay_service.get_merged_doc(node_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doc not found")
    return doc

@app.get("/overlay/{node_id}/history")
async def get_history(node_id: str):
    """Get overlay edit history"""
    history = await overlay_service.get_overlay_history(node_id)
    return {"history": history}

@app.delete("/overlay/{node_id}")
async def archive_overlay(node_id: str):
    """Archive overlay"""
    await overlay_service.archive_overlay(node_id)
    return {"status": "archived"}

@app.post("/overlay/{node_id}/create-pr")
async def create_pr(node_id: str, repo_url: str, branch_name: str = "overlay-edits"):
    """Create PR from overlay"""
    pr_url = await overlay_service.create_pr_from_overlay(node_id, repo_url, branch_name)
    return {"pr_url": pr_url}

@app.get("/overlays/{repo_id}")
async def list_overlays(repo_id: str):
    """List all overlays for a repo"""
    overlays = await overlay_service.get_all_overlays(repo_id)
    return {"overlays": overlays, "count": len(overlays)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
