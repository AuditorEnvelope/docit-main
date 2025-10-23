"""
Commit Bus Service - Durable event store for all git commits
Ensures no commits are lost during downtime with replay capability
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from datetime import datetime
import asyncpg

class CommitEvent(BaseModel):
    """Canonical commit event schema"""
    repo_id: str
    commit_sha: str
    parent_sha: List[str]
    author_name: str
    author_email: str
    timestamp: datetime
    branch: str
    files_changed: List[dict]  # [{path, status, patch}]
    commit_message: str
    push_id: Optional[str] = None
    source: str = "github"  # github|gitlab|cli
    metadata: Optional[dict] = {}
    
    # Multi-org support fields (optional for backward compatibility)
    user_id: Optional[str] = None  # UUID of user who owns the repo
    org_id: Optional[str] = None  # Organization name
    github_token_id: Optional[str] = None  # Reference to encrypted token
    webhook_secret: Optional[str] = None  # Org's webhook secret

class CommitBusService:
    """
    Commit Bus - Reliable event store for commits
    
    Features:
    - Durable storage (PostgreSQL)
    - Ordered processing
    - Replay/backfill capability
    - Idempotent (duplicate commits handled)
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def init_pool(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
    
    async def store_event(self, event: CommitEvent) -> str:
        """
        Store commit event in event store
        Returns: event_id
        
        Idempotent: If event with same repo_id+commit_sha exists, updates metadata
        """
        async with self.pool.acquire() as conn:
            event_id = await conn.fetchval("""
                INSERT INTO commit_events (
                    repo_id, commit_sha, parent_sha, author_name, author_email,
                    timestamp, branch, files_changed, commit_message, push_id,
                    source, metadata, user_id, org_id, github_token_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (repo_id, commit_sha) DO UPDATE
                SET metadata = EXCLUDED.metadata, updated_at = NOW()
                RETURNING event_id
            """, 
                event.repo_id, event.commit_sha, event.parent_sha,
                event.author_name, event.author_email, event.timestamp,
                event.branch, json.dumps(event.files_changed),
                event.commit_message, event.push_id, event.source,
                json.dumps(event.metadata),
                event.user_id, event.org_id, event.github_token_id
            )
            return str(event_id)
    
    async def get_unprocessed_events(
        self, 
        repo_id: Optional[str] = None, 
        limit: int = 100
    ) -> List[dict]:
        """
        Get unprocessed events in chronological order
        
        Args:
            repo_id: Filter by repository (optional)
            limit: Max events to return
        
        Returns: List of event dictionaries
        """
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    event_id, repo_id, commit_sha, parent_sha, author_name,
                    author_email, timestamp, branch, files_changed, commit_message,
                    push_id, source, metadata, created_at,
                    user_id, org_id, github_token_id
                FROM commit_events
                WHERE processed = FALSE AND retry_count < 3
            """
            params = []
            
            if repo_id:
                query += " AND repo_id = $1"
                params.append(repo_id)
            
            query += " ORDER BY timestamp ASC"
            
            if limit:
                query += f" LIMIT ${len(params) + 1}"
                params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def mark_processed(
        self, 
        event_id: str, 
        success: bool = True, 
        error: str = None
    ):
        """
        Mark event as processed or failed
        
        Args:
            event_id: Event UUID
            success: True if processed successfully
            error: Error message if failed
        """
        async with self.pool.acquire() as conn:
            if success:
                await conn.execute("""
                    UPDATE commit_events
                    SET processed = TRUE, processed_at = NOW()
                    WHERE event_id = $1
                """, event_id)
            else:
                await conn.execute("""
                    UPDATE commit_events
                    SET retry_count = retry_count + 1, 
                        error_message = $2,
                        updated_at = NOW()
                    WHERE event_id = $1
                """, event_id, error)
    
    async def replay_events(
        self, 
        repo_id: str, 
        from_timestamp: Optional[datetime] = None
    ):
        """
        Replay events from a specific timestamp
        Resets processed flag so events are reprocessed
        
        Args:
            repo_id: Repository to replay
            from_timestamp: Start time (optional, defaults to all)
        """
        async with self.pool.acquire() as conn:
            query = """
                UPDATE commit_events
                SET processed = FALSE, processed_at = NULL, retry_count = 0
                WHERE repo_id = $1
            """
            params = [repo_id]
            
            if from_timestamp:
                query += " AND timestamp >= $2"
                params.append(from_timestamp)
            
            result = await conn.execute(query, *params)
            count = int(result.split()[-1])
            return count
    
    async def get_event_stats(self, repo_id: Optional[str] = None) -> dict:
        """Get statistics about events"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                    COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                    COUNT(*) FILTER (WHERE retry_count > 0) as failed
                FROM commit_events
            """
            params = []
            
            if repo_id:
                query += " WHERE repo_id = $1"
                params.append(repo_id)
            
            row = await conn.fetchrow(query, *params)
            return dict(row)

# FastAPI app
app = FastAPI(title="Commit Bus Service", version="1.0.0")

# Global service instance
bus = None

@app.on_event("startup")
async def startup():
    """Initialize service on startup"""
    global bus
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    bus = CommitBusService(db_url)
    await bus.init_pool()
    print("✅ Commit Bus Service started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    if bus and bus.pool:
        await bus.pool.close()
    print("👋 Commit Bus Service stopped")

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Commit Bus",
        "status": "ok",
        "version": "1.0.0"
    }

@app.post("/events")
async def create_event(event: CommitEvent):
    """
    Store a commit event
    
    Returns: event_id and status
    """
    try:
        event_id = await bus.store_event(event)
        return {
            "event_id": event_id,
            "status": "stored",
            "repo_id": event.repo_id,
            "commit_sha": event.commit_sha
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events")
async def list_events(
    repo_id: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 100
):
    """
    List events
    
    Query params:
    - repo_id: Filter by repository
    - processed: Filter by processed status
    - limit: Max results (default 100)
    """
    try:
        if processed is False:
            events = await bus.get_unprocessed_events(repo_id, limit)
        else:
            # TODO: Add query for processed events
            events = await bus.get_unprocessed_events(repo_id, limit)
        
        return {
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/replay")
async def replay(
    repo_id: str,
    from_timestamp: Optional[datetime] = None
):
    """
    Replay events for a repository
    
    Resets processed flag so events are reprocessed
    Useful after downtime or code changes
    
    Body:
    - repo_id: Repository to replay
    - from_timestamp: Start time (optional)
    """
    try:
        count = await bus.replay_events(repo_id, from_timestamp)
        return {
            "status": "replay_started",
            "repo_id": repo_id,
            "events_reset": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats(repo_id: Optional[str] = None):
    """
    Get event statistics
    
    Query params:
    - repo_id: Filter by repository (optional)
    """
    try:
        stats = await bus.get_event_stats(repo_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
