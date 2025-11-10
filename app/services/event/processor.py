"""
Event Processor

Handles the actual processing of different types of events.
This module contains the business logic for processing events.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.core.config import settings
from app.models.base import GitHubInstallation
from app.models.events import Event, EventStatus, EventProcessingLog
from app.models.repository import Repository, DocPersona
from app.schemas.events import EventUpdate
from app.utils.github_dual_app import GitHubDualAppHelper
from app.services.event.smart_processor import handle_push_event

logger = logging.getLogger(__name__)

class EventProcessor:
    """Processes events based on their type"""
    
    def __init__(self, db: AsyncSession, dual_app: Optional[GitHubDualAppHelper] = None):
        self.db = db
        self.dual_app = dual_app or GitHubDualAppHelper()
    
    async def process(self, event: Event) -> bool:
        """
        Process an event based on its type.
        
        Args:
            event: The event to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            logger.info(f"Processing event {event.id} of type {event.event_type}")

            normalized_type = (event.event_type or "").lower()
            handler_overrides = {
                "github.installation": self._handle_installation,
            }

            handler = handler_overrides.get(normalized_type)
            if handler is None:
                handler_name = f"_handle_{normalized_type}"
                handler = getattr(self, handler_name, self._handle_unknown_event)
            
            # Process the event
            success = await handler(event)
            
            if success:
                logger.info(f"Successfully processed event {event.id}")
            else:
                logger.warning(f"Failed to process event {event.id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {str(e)}", exc_info=True)
            return False
    
    async def _handle_push(self, event: Event) -> bool:
        """Handle push events by generating documentation and publishing to docbook."""
        payload = event.payload or {}

        repo_info = payload.get("repository", {})
        repo_full_name = repo_info.get("full_name")
        commit_sha = payload.get("after")

        if not repo_full_name or not commit_sha:
            raise ValueError("Push event missing repository full name or commit SHA")

        if "/" not in repo_full_name:
            raise ValueError(f"Invalid repository name: {repo_full_name}")

        org_id = repo_full_name.split("/", 1)[0]

        # Get db_pool from payload (like old codebase) - use it for database queries to avoid greenlet_spawn errors
        db_pool = payload.get("_db_pool")
        
        installation_id = payload.get("installation", {}).get("id")
        if installation_id is None:
            installation_id = await self._lookup_installation_id(org_id, db_pool=db_pool)

        if installation_id is None:
            raise ValueError(f"No GitHub App installation found for org {org_id}")

        reader_token = await self.dual_app.get_reader_token(installation_id)
        if not reader_token:
            raise RuntimeError("Failed to resolve reader token for documentation generation")

        doc_persona = await self._resolve_doc_persona(repo_full_name, db_pool=db_pool)

        # Attach user/org context for downstream publisher/logging
        payload["_user_id"] = payload.get("_user_id")
        payload["_org_id"] = payload.get("_org_id") or org_id
        payload["_installation_id"] = installation_id
        payload["_db_pool"] = db_pool  # Pass asyncpg pool (like old codebase) instead of SQLAlchemy session

        logger.info("📥 Delegating push processing to legacy smart processor for %s@%s", repo_full_name, commit_sha[:7])
        await handle_push_event(payload, github_token=reader_token, doc_persona=doc_persona)

        # Update repository state (non-critical, won't fail if it errors)
        try:
            await self._update_repository_state(repo_full_name, commit_sha)
        except Exception as e:
            # Log but don't fail - repository update is optional
            logger.debug("Repository state update skipped: %s", str(e))
        
        logger.info("✅ Documentation published to docbook for %s", repo_full_name)
        return True
    
    async def _handle_installation(self, event: Event) -> bool:
        """Handle installation events"""
        try:
            action = event.payload.get('action')
            installation = event.payload.get('installation', {})
            
            if action == 'created':
                # New installation
                await self._handle_new_installation(installation)
            elif action == 'deleted':
                # Installation removed
                await self._handle_installation_removal(installation)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling installation event: {str(e)}", exc_info=True)
            raise
    
    async def _handle_unknown_event(self, event: Event) -> bool:
        """Handle unknown event types"""
        logger.warning(f"No handler for event type: {event.event_type}")
        return False
    
    async def _handle_new_installation(self, installation: Dict[str, Any]) -> None:
        """Handle new GitHub App installation"""
        org_id = (installation.get("account") or {}).get("login")
        installation_id = installation.get("id")
        app_id = installation.get("app_id")

        if not org_id or installation_id is None or app_id is None:
            raise ValueError("Installation payload missing org_id, installation_id, or app_id")

        result = await self.db.execute(
            select(GitHubInstallation).where(GitHubInstallation.org_id == org_id)
        )
        record = result.scalar_one_or_none()

        if record:
            record.installation_id = installation_id
            record.app_id = app_id
            record.updated_at = datetime.utcnow()
            logger.info("🔄 Updated GitHub installation for %s (id=%s)", org_id, installation_id)
        else:
            record = GitHubInstallation(
                org_id=org_id,
                installation_id=installation_id,
                app_id=app_id,
            )
            self.db.add(record)
            logger.info("➕ Stored new GitHub installation for %s (id=%s)", org_id, installation_id)

        await self.db.flush()
    
    async def _handle_installation_removal(self, installation: Dict[str, Any]) -> None:
        """Handle GitHub App uninstallation"""
        org_id = (installation.get("account") or {}).get("login")
        if not org_id:
            raise ValueError("Installation removal payload missing org_id")

        result = await self.db.execute(
            select(GitHubInstallation).where(GitHubInstallation.org_id == org_id)
        )
        record = result.scalar_one_or_none()

        if record:
            await self.db.delete(record)
            await self.db.flush()
            logger.info("🗑️ Removed GitHub installation for %s", org_id)
        else:
            logger.warning("⚠️ Attempted to remove unknown installation for %s", org_id)

    async def _lookup_installation_id(self, org_id: str, db_pool=None) -> Optional[int]:
        """Lookup installation ID - uses asyncpg pool if available to avoid greenlet_spawn errors"""
        if db_pool:
            # Use asyncpg pool (like old codebase) to avoid greenlet_spawn errors
            try:
                async with db_pool.acquire() as conn:
                    result = await conn.fetchval("""
                        SELECT installation_id FROM github_installations
                        WHERE org_id = $1
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, org_id)
                    return result
            except Exception as e:
                logger.warning(f"Error looking up installation_id with db_pool: {e}")
                # Fall back to SQLAlchemy session
                pass
        
        # Fallback to SQLAlchemy session
        try:
            result = await self.db.execute(
                select(GitHubInstallation.installation_id)
                .where(GitHubInstallation.org_id == org_id)
                .order_by(GitHubInstallation.updated_at.desc())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"Error looking up installation_id with SQLAlchemy: {e}")
            return None

    async def _resolve_doc_persona(self, repo_full_name: str, db_pool=None) -> str:
        """Resolve doc persona for a repository - uses asyncpg pool if available to avoid greenlet_spawn errors"""
        if db_pool:
            # Use asyncpg pool (like old codebase) to avoid greenlet_spawn errors
            try:
                async with db_pool.acquire() as conn:
                    result = await conn.fetchval("""
                        SELECT doc_persona FROM repositories
                        WHERE full_name = $1 OR repo_id = $1
                        LIMIT 1
                    """, repo_full_name)
                    if result:
                        persona = result
                        if isinstance(persona, str):
                            logger.debug("Found doc_persona %s for %s", persona, repo_full_name)
                            return persona
                        # If it's an enum, get the value
                        if hasattr(persona, 'value'):
                            return persona.value
                        return str(persona)
            except Exception as e:
                logger.warning(f"Error resolving doc_persona with db_pool: {e}")
                # Fall back to SQLAlchemy session
                pass
        
        # Fallback to SQLAlchemy session
        try:
            from sqlalchemy import text
            
            # Use raw SQL to avoid loading columns that don't exist (like user_id, org_id)
            result = await self.db.execute(
                text("""
                    SELECT doc_persona FROM repositories
                    WHERE full_name = :repo_full_name OR repo_id = :repo_full_name
                    LIMIT 1
                """),
                {"repo_full_name": repo_full_name}
            )
            row = result.fetchone()
            if row and row[0]:
                persona = row[0]
                if isinstance(persona, DocPersona):
                    return persona.value
                if isinstance(persona, str):
                    return persona
                logger.debug("Found doc_persona %s for %s", persona, repo_full_name)
                return str(persona)
        except Exception as e:
            logger.warning("Error resolving doc_persona for %s: %s", repo_full_name, str(e))
        
        fallback = settings.DEFAULT_DOC_PERSONA or "internal"
        logger.debug("Persona not configured for %s. Falling back to %s", repo_full_name, fallback)
        return fallback

    async def _update_repository_state(self, repo_full_name: str, commit_sha: str) -> None:
        """Update repository state after processing (optional - repo may not exist)"""
        # Skip repository state update - the actual database schema doesn't have these columns
        # The repositories table from schema.sql only has: id, repo_id, name, full_name, git_url,
        # default_branch, enabled, indexing_frequency, auto_generate_docs, subscription_id, metadata, timestamps
        # It doesn't have last_commit_sha or last_documented_at
        logger.debug("Skipping repository state update - columns not in database schema")
        return
