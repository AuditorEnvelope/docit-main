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
from app.services.docbook.publisher import DocbookPublisher
from app.services.documentation.manual_generation import ManualDocGenerator
from app.utils.github_dual_app import GitHubDualAppHelper

logger = logging.getLogger(__name__)

class EventProcessor:
    """Processes events based on their type"""
    
    def __init__(self, db: AsyncSession, dual_app: Optional[GitHubDualAppHelper] = None):
        self.db = db
        self.dual_app = dual_app or GitHubDualAppHelper()
        self.publisher = DocbookPublisher(dual_app=self.dual_app, db_session=db)
    
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
            
            # Route to the appropriate handler based on event type
            handler_name = f"_handle_{event.event_type.lower()}"
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

        org_id, source_repo = repo_full_name.split("/", 1)

        installation_id = payload.get("installation", {}).get("id")
        if installation_id is None:
            installation_id = await self._lookup_installation_id(org_id)

        if installation_id is None:
            raise ValueError(f"No GitHub App installation found for org {org_id}")

        reader_token = await self.dual_app.get_reader_token(installation_id)
        if not reader_token:
            raise RuntimeError("Failed to resolve reader token for documentation generation")

        persona = await self._resolve_doc_persona(repo_full_name)
        generator = ManualDocGenerator(doc_persona=persona)

        logger.info("📥 Generating documentation for %s at %s", repo_full_name, commit_sha[:7])
        generation_result = await generator.generate(repo_full_name, reader_token)

        commit_message = (
            (payload.get("head_commit") or {}).get("message")
            or f"docs: Auto-generated documentation for {commit_sha[:7]}"
        )
        user_id = payload.get("_user_id") or "system"

        try:
            publish_result = await self.publisher.publish_to_docbook(
                user_id=user_id,
                org_id=org_id,
                source_repo_name=source_repo,
                docs_dir=generation_result.docs_dir,
                commit_message=commit_message,
                commit_sha=commit_sha,
                installation_id=installation_id,
            )
        finally:
            generation_result.cleanup()

        if publish_result.get("status") == "error":
            raise RuntimeError(publish_result.get("message", "Docbook publication failed"))

        await self._update_repository_state(repo_full_name, commit_sha)
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

    async def _lookup_installation_id(self, org_id: str) -> Optional[int]:
        result = await self.db.execute(
            select(GitHubInstallation.installation_id)
            .where(GitHubInstallation.org_id == org_id)
            .order_by(GitHubInstallation.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def _resolve_doc_persona(self, repo_full_name: str) -> str:
        result = await self.db.execute(
            select(Repository.doc_persona).where(Repository.repo_id == repo_full_name)
        )
        persona = result.scalar_one_or_none()
        if isinstance(persona, DocPersona):
            return persona.value
        if isinstance(persona, str):
            return persona
        fallback = settings.DEFAULT_DOC_PERSONA or "internal"
        logger.debug("Persona not configured for %s. Falling back to %s", repo_full_name, fallback)
        return fallback

    async def _update_repository_state(self, repo_full_name: str, commit_sha: str) -> None:
        result = await self.db.execute(
            select(Repository).where(Repository.repo_id == repo_full_name)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            return

        repo.last_commit_sha = commit_sha
        repo.last_documented_at = datetime.utcnow()
        await self.db.flush()
