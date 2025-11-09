"""
Commit Bus Service

Durable event store for all git commits with idempotent handling
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.dialects.postgresql import insert

from app.models.repository import CommitEvent
from app.core.config import settings

class CommitBusService:
    """
    Commit Bus - Reliable event store for commits
    
    Features:
    - Durable storage (PostgreSQL)
    - Idempotent (ON CONFLICT handling)
    - Ordered processing
    - Replay/backfill capability
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def store_event(self, event_data: Dict[str, Any]):
        """
        Store commit event with idempotent handling
        
        If event with same repo_id+commit_sha exists, updates metadata
        Returns: event_id
        """
        parent_shas = event_data.get("parent_sha", []) or []
        if isinstance(parent_shas, str):
            parent_shas = [parent_shas]

        metadata_payload = event_data.get("metadata", {}) or {}

        def _coerce_uuid(value: Any) -> Optional[UUID]:
            if isinstance(value, UUID):
                return value
            if isinstance(value, str):
                try:
                    return UUID(value)
                except (ValueError, TypeError):
                    return None
            return None

        user_id = _coerce_uuid(event_data.get("user_id"))
        org_id = event_data.get("org_id")
        github_token_id = _coerce_uuid(event_data.get("github_token_id"))

        # Prepare insert statement with ON CONFLICT
        stmt = insert(CommitEvent).values(
            repo_id=event_data.get("repo_id"),
            commit_sha=event_data.get("commit_sha"),
            parent_sha=parent_shas,
            author_name=event_data.get("author_name"),
            author_email=event_data.get("author_email"),
            timestamp=event_data.get("timestamp"),
            branch=event_data.get("branch"),
            commit_message=event_data.get("commit_message"),
            files_changed=event_data.get("files_changed", []),
            push_id=event_data.get("push_id"),
            source=event_data.get("source", "github"),
            user_id=user_id,
            org_id=org_id,
            github_token_id=github_token_id,
            installation_id=event_data.get("installation_id"),
            event_metadata=metadata_payload,
            processed=False
        ).on_conflict_do_update(
            index_elements=['repo_id', 'commit_sha'],
            set_={
                CommitEvent.event_metadata: metadata_payload,
                CommitEvent.updated_at: datetime.utcnow()
            }
        ).returning(CommitEvent.event_id)
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        event_id = result.scalar_one()
        return event_id
    
    async def get_unprocessed_events(
        self,
        repo_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 100
    ) -> List[CommitEvent]:
        """
        Get unprocessed events in chronological order
        """
        query = select(CommitEvent).where(CommitEvent.processed == False)
        
        if repo_id:
            query = query.where(CommitEvent.repo_id == repo_id)
        
        if org_id:
            query = query.where(CommitEvent.org_id == org_id)
        
        query = query.order_by(CommitEvent.timestamp.asc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_processed(self, event_id) -> bool:
        """Mark event as processed
        
        Note: Does not commit - caller must commit the transaction
        """
        stmt = update(CommitEvent).where(
            CommitEvent.event_id == event_id
        ).values(
            processed=True,
            processed_at=datetime.utcnow()
        )
        
        await self.db.execute(stmt)
        # Don't commit here - let the caller handle the transaction
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get commit bus statistics"""
        from sqlalchemy import func
        
        # Total events
        total_result = await self.db.execute(
            select(func.count(CommitEvent.event_id))
        )
        total = total_result.scalar_one()
        
        # Processed events
        processed_result = await self.db.execute(
            select(func.count(CommitEvent.event_id)).where(CommitEvent.processed == True)
        )
        processed = processed_result.scalar_one()
        
        # Pending events
        pending = total - processed
        
        return {
            "total_events": total,
            "processed_events": processed,
            "pending_events": pending,
            "processing_rate": f"{(processed / total * 100):.1f}%" if total > 0 else "0%"
        }
    
    async def replay_events(self, repo_id: Optional[str] = None) -> int:
        """
        Replay (reprocess) events
        
        Marks all processed events as unprocessed for reprocessing
        """
        stmt = update(CommitEvent).values(
            processed=False,
            processed_at=None
        )
        
        if repo_id:
            stmt = stmt.where(CommitEvent.repo_id == repo_id)
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount


__all__ = ["CommitBusService"]
