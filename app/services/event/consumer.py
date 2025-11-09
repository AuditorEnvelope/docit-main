"""
Event Consumer Service

This module implements the event consumer that processes events from the event bus.
It's responsible for handling different types of events and delegating them to
appropriate handlers.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.core.event_bus import EventBus, Event, EventType, event_handler
from app.core.config import settings
from app.db.session import get_db
import app.models.events as models
import app.schemas.events as schemas
from app.services.event.service import EventService

logger = logging.getLogger(__name__)

class EventConsumer:
    """Event consumer that processes events from the event bus"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.is_running = False
        self._tasks = []
    
    async def start(self) -> None:
        """Start the event consumer"""
        if self.is_running:
            logger.warning("Event consumer is already running")
            return
            
        logger.info("Starting event consumer...")
        self.is_running = True
        
        # Register event handlers
        await self._register_handlers()
        
        # Start the event bus if not already running
        if not self.event_bus._is_running:
            await self.event_bus.start(worker_count=settings.EVENT_WORKER_COUNT)
        
        logger.info("Event consumer started")
    
    async def stop(self) -> None:
        """Stop the event consumer"""
        if not self.is_running:
            return
            
        logger.info("Stopping event consumer...")
        self.is_running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("Event consumer stopped")
    
    async def _register_handlers(self) -> None:
        """Register all event handlers"""
        # GitHub Events
        self.event_bus.subscribe(EventType.GITHUB_PUSH, self.handle_github_push)
        self.event_bus.subscribe(EventType.GITHUB_INSTALLATION, self.handle_github_installation)
        
        # Document Events
        self.event_bus.subscribe(EventType.DOCUMENT_GENERATED, self.handle_document_generated)
        self.event_bus.subscribe(EventType.DOCUMENT_PUBLISHED, self.handle_document_published)
        
        # Error Events
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self.handle_error)
        
        logger.debug("Registered all event handlers")
    
    # Event Handlers
    
    async def handle_github_push(self, event: Event) -> None:
        """Handle GitHub push event"""
        logger.info(f"Processing GitHub push event: {event.event_id}")
        
        try:
            # Log the event to the database
            async with get_db() as db:
                event_service = EventService(db)
                
                # Create event record
                event_in = schemas.EventCreate(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    status=event.status.value,
                    payload=event.data,
                    metadata={
                        "repository": event.data.get("repository", {}).get("full_name"),
                        "ref": event.data.get("ref"),
                        "commit_count": len(event.data.get("commits", [])),
                        "sender": event.data.get("sender", {}).get("login"),
                        **event.metadata
                    }
                )
                
                await event_service.create_event(event_in)
                
                # Process the push event
                # This would typically call other services to handle the push
                # For example:
                # - Index the repository
                # - Generate documentation
                # - Update search index
                # - Trigger notifications
                
                # Update event status
                await event_service.update_event_status(
                    event_id=event.event_id,
                    status=schemas.EventStatus.COMPLETED,
                    metadata={"processed_at": datetime.now(timezone.utc).isoformat()}
                )
                
        except Exception as e:
            logger.error(f"Error processing GitHub push event {event.event_id}: {str(e)}", exc_info=True)
            raise
    
    async def handle_github_installation(self, event: Event) -> None:
        """Handle GitHub app installation event"""
        logger.info(f"Processing GitHub installation event: {event.event_id}")
        
        try:
            action = event.data.get("action")
            installation = event.data.get("installation", {})
            repositories = event.data.get("repositories", [])
            
            logger.info(f"GitHub app {action} for installation {installation.get('id')}")
            
            # Log the event to the database
            async with get_db() as db:
                event_service = EventService(db)
                
                # Create event record
                event_in = schemas.EventCreate(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    status=event.status.value,
                    payload=event.data,
                    metadata={
                        "action": action,
                        "installation_id": installation.get("id"),
                        "account": installation.get("account", {}).get("login"),
                        "repository_count": len(repositories),
                        **event.metadata
                    }
                )
                
                await event_service.create_event(event_in)
                
                # Handle different installation actions
                if action == "created":
                    # New installation - setup repositories
                    pass
                elif action == "deleted":
                    # Installation removed - cleanup
                    pass
                
                # Update event status
                await event_service.update_event_status(
                    event_id=event.event_id,
                    status=schemas.EventStatus.COMPLETED,
                    metadata={"processed_at": datetime.now(timezone.ustcnow()).isoformat()}
                )
                
        except Exception as e:
            logger.error(f"Error processing GitHub installation event {event.event_id}: {str(e)}", exc_info=True)
            raise
    
    async def handle_document_generated(self, event: Event) -> None:
        """Handle document generated event"""
        logger.info(f"Processing document generated event: {event.event_id}")
        
        try:
            # Process the document generation event
            # This might involve:
            # - Storing the generated document
            # - Updating the document index
            # - Triggering notifications
            
            async with get_db() as db:
                event_service = EventService(db)
                
                # Update event status
                await event_service.update_event_status(
                    event_id=event.event_id,
                    status=schemas.EventStatus.COMPLETED,
                    metadata={
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "document_id": event.data.get("document_id")
                    }
                )
                
        except Exception as e:
            logger.error(f"Error processing document generated event {event.event_id}: {str(e)}", exc_info=True)
            raise
    
    async def handle_document_published(self, event: Event) -> None:
        """Handle document published event"""
        logger.info(f"Processing document published event: {event.event_id}")
        
        try:
            # Process the document published event
            # This might involve:
            # - Updating the document status
            # - Triggering notifications
            # - Updating search indexes
            
            async with get_db() as db:
                event_service = EventService(db)
                
                # Update event status
                await event_service.update_event_status(
                    event_id=event.event_id,
                    status=schemas.EventStatus.COMPLETED,
                    metadata={
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "document_id": event.data.get("document_id"),
                        "published_url": event.data.get("published_url")
                    }
                )
                
        except Exception as e:
            logger.error(f"Error processing document published event {event.event_id}: {str(e)}", exc_info=True)
            raise
    
    async def handle_error(self, event: Event) -> None:
        """Handle error events"""
        logger.error(f"Processing error event: {event.event_id}")
        
        try:
            original_event = event.data.get("original_event", {})
            error = event.data.get("error")
            
            logger.error(
                f"Error processing event {original_event.get('event_id')}: {error}",
                extra={
                    "original_event": original_event,
                    "error": error,
                    "handler": event.data.get("handler")
                }
            )
            
            # Log the error to the database
            async with get_db() as db:
                event_service = EventService(db)
                
                # Create error event record
                error_event = schemas.EventCreate(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    status=event.status.value,
                    payload=event.data,
                    metadata={
                        "original_event_id": original_event.get("event_id"),
                        "error": str(error),
                        "handler": event.data.get("handler"),
                        "retry_count": original_event.get("retry_count", 0),
                        "max_retries": original_event.get("max_retries", 3),
                        **event.metadata
                    }
                )
                
                await event_service.create_event(error_event)
                
                # Update the original event status if it exists
                if original_event.get("event_id"):
                    await event_service.update_event_status(
                        event_id=original_event["event_id"],
                        status=schemas.EventStatus.FAILED,
                        metadata={
                            "error": str(error),
                            "failed_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                
        except Exception as e:
            logger.critical(f"Error processing error event {event.event_id}: {str(e)}", exc_info=True)
            # If we can't even log the error, there's not much we can do
            pass

# Global consumer instance
_consumer = None

async def get_consumer() -> EventConsumer:
    """Get the global event consumer instance"""
    global _consumer
    if _consumer is None:
        _consumer = EventConsumer()
        await _consumer.start()
    return _consumer

async def start_consumer() -> None:
    """Start the global event consumer"""
    consumer = await get_consumer()
    await consumer.start()

async def stop_consumer() -> None:
    """Stop the global event consumer"""
    global _consumer
    if _consumer is not None:
        await _consumer.stop()
        _consumer = None
