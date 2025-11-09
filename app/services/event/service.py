"""
Event Processing Service

Handles the processing of events from the commit bus, including:
- Polling for new events
- Processing events with retry logic
- Tracking event status
- Error handling and logging
"""

import asyncio
import copy
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.models.events import Event, EventProcessingLog, EventStatus
from app.db.session import get_db
from app.core.config import settings
from app.schemas.events import EventCreate, EventUpdate

class EventProcessingError(Exception):
    """Custom exception for event processing errors"""
    pass

class EventService:
    """Service for processing events from the commit bus"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.processing = False
        self.batch_size = settings.EVENT_BATCH_SIZE
        self.max_retries = settings.EVENT_MAX_RETRIES
        self.poll_interval = settings.EVENT_POLL_INTERVAL
    
    async def get_pending_events(self) -> List[Event]:
        """Fetch a batch of pending events"""
        result = await self.db.execute(
            select(Event)
            .where(Event.status == EventStatus.PENDING)
            .order_by(Event.created_at.asc())
            .limit(self.batch_size)
        )
        return result.scalars().all()

    async def create_event(
        self,
        event_in: Optional[EventCreate] = None,
        *,
        event_type: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> Event:
        """Persist a new event record."""

        if event_in is None:
            if event_type is None or payload is None:
                raise ValueError("Must provide event_in or both event_type and payload")
            event_type_value = event_type
            raw_payload = payload
        else:
            event_type_value = event_in.event_type
            raw_payload = event_in.payload

        payload_copy: Dict[str, Any] = copy.deepcopy(raw_payload) if raw_payload else {}

        if source:
            meta: Dict[str, Any] = {}
            existing_meta = payload_copy.get("_meta")
            if isinstance(existing_meta, dict):
                meta.update(existing_meta)
            meta["source"] = source
            payload_copy["_meta"] = meta

        event = Event(
            id=str(uuid.uuid4()),
            event_type=event_type_value,
            payload=payload_copy,
            status=EventStatus.PENDING,
            retry_count=0,
            error=None,
        )
        self.db.add(event)
        await self.db.flush()

        log = EventProcessingLog(
            event_id=event.id,
            status=EventStatus.PENDING,
            error=None,
            retry_count=0,
        )
        self.db.add(log)
        await self.db.flush()

        return event

    async def get_event(self, event_id: str, *, for_update: bool = False) -> Optional[Event]:
        """Fetch a single event by ID."""
        stmt = select(Event).where(Event.id == event_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_event(self, event_id: str, update_data: EventUpdate) -> Optional[Event]:
        """Update an event with the provided data."""
        event = await self.get_event(event_id)
        if not event:
            return None

        payload = update_data.model_dump(exclude_unset=True)
        if not payload:
            return event

        for field, value in payload.items():
            setattr(event, field, value)

        event.updated_at = datetime.utcnow()
        await self.db.flush()
        return event
    
    async def process_event(self, event: Event) -> bool:
        """Process a single event with retry logic"""
        if event.retry_count >= self.max_retries:
            await self._mark_event_failed(event, "Max retries exceeded")
            return False
            
        try:
            # Update event status to PROCESSING
            await self._update_event_status(event, EventStatus.PROCESSING)
            
            # Process the event based on its type
            if event.event_type == 'push':
                await self._process_push_event(event)
            elif event.event_type == 'installation':
                await self._process_installation_event(event)
            else:
                raise EventProcessingError(f"Unknown event type: {event.event_type}")
            
            # Mark as completed if successful
            await self._mark_event_completed(event)
            return True
            
        except Exception as e:
            await self._handle_processing_error(event, str(e))
            return False
    
    async def _process_push_event(self, event: Event):
        """Handle push events"""
        payload = event.payload
        # TODO: Implement push event processing
        await asyncio.sleep(1)  # Simulate processing
    
    async def _process_installation_event(self, event: Event):
        """Handle installation events"""
        payload = event.payload
        # TODO: Implement installation event processing
        await asyncio.sleep(1)  # Simulate processing
    
    async def _update_event_status(
        self, 
        event: Event, 
        status: EventStatus,
        error: Optional[str] = None
    ) -> None:
        """Update event status and log the change"""
        event.status = status
        if error:
            event.error = error
        
        # Log the status change
        log = EventProcessingLog(
            event_id=event.id,
            status=status,
            error=error,
            retry_count=event.retry_count
        )
        
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(event)
    
    async def _mark_event_completed(self, event: Event) -> None:
        """Mark an event as successfully completed"""
        event.completed_at = datetime.utcnow()
        await self._update_event_status(event, EventStatus.COMPLETED)
    
    async def _mark_event_failed(self, event: Event, error: str) -> None:
        """Mark an event as failed"""
        event.retry_count += 1
        event.last_attempt_at = datetime.utcnow()
        await self._update_event_status(event, EventStatus.FAILED, error)
    
    async def _handle_processing_error(self, event: Event, error: str) -> None:
        """Handle errors during event processing"""
        event.retry_count += 1
        event.last_attempt_at = datetime.utcnow()
        
        if event.retry_count >= self.max_retries:
            await self._update_event_status(event, EventStatus.FAILED, error)
        else:
            # Schedule for retry
            retry_at = datetime.utcnow() + timedelta(
                minutes=min(60, 5 * (2 ** event.retry_count))  # Exponential backoff
            )
            event.retry_at = retry_at
            await self._update_event_status(event, EventStatus.RETRYING, error)
    
    async def process_events_forever(self) -> None:
        """Continuously process events until stopped"""
        self.processing = True
        
        while self.processing:
            try:
                # Get pending events
                events = await self.get_pending_events()
                
                # Process events in parallel
                tasks = [self.process_event(event) for event in events]
                await asyncio.gather(*tasks)
                
                # Wait before polling again
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                self.processing = False
                break
            except Exception as e:
                # Log the error but keep the service running
                print(f"Error in event processing loop: {str(e)}")
                await asyncio.sleep(5)  # Back off on error
    
    async def stop_processing(self) -> None:
        """Gracefully stop the event processing loop"""
        self.processing = False
