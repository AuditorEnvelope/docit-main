"""
Event Bus for asynchronous event processing

This module implements a simple in-memory event bus with support for:
- Publishing events
- Subscribing to event types
- Background task processing
- Error handling and retries
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Type variables for type hints
T = TypeVar('T', bound='Event')
EventHandler = Callable[['Event'], Any]

class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class EventType(str, Enum):
    """Supported event types"""
    GITHUB_PUSH = "github.push"
    GITHUB_INSTALLATION = "github.installation"
    DOCUMENT_GENERATED = "document.generated"
    DOCUMENT_PUBLISHED = "document.published"
    ERROR_OCCURRED = "error.occurred"

class EventProcessingError(Exception):
    """
    Custom exception for event processing errors
    
    Attributes:
        event_id: ID of the event that failed
        handler: Name of the handler that failed
        original_error: The original exception that was raised
    """
    def __init__(self, message: str, event_id: str = None, 
                 handler: str = None, original_error: Exception = None):
        self.event_id = event_id
        self.handler = handler
        self.original_error = original_error
        super().__init__(message)

class Event(BaseModel):
    """Base event class"""
    event_id: str
    event_type: EventType
    data: Dict[str, Any]
    created_at: datetime = None
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    def __init__(self, **data):
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone.utc)
        super().__init__(**data)

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return self.json()

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """Create event from JSON string"""
        return cls.parse_raw(json_str)

class EventBus:
    """
    Enhanced event bus with persistence and dead-letter queue support.
    
    Features:
    - In-memory queue for fast event processing
    - Persistent event storage for reliability
    - Dead-letter queue for failed events
    - Metrics and monitoring
    """
    
    def __init__(self, db_session=None):
        # Event handling
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._event_queue = asyncio.Queue()
        self._dead_letter_queue = asyncio.Queue()
        self._is_running = False
        self._tasks: List[asyncio.Task] = []
        
        # Database session for persistence
        self._db = db_session
        
        # Metrics
        self._metrics = {
            'events_processed': 0,
            'events_failed': 0,
            'events_retried': 0,
            'queue_depth': lambda: self._event_queue.qsize(),
            'dlq_depth': lambda: self._dead_letter_queue.qsize(),
            'active_workers': 0,
            'uptime': time.time()
        }
        
        self._logger = logging.getLogger(f"{__name__}.EventBus")
    
    async def publish(self, event: Event) -> None:
        """Publish an event to the bus"""
        if not isinstance(event, Event):
            raise ValueError("Event must be an instance of Event class")
            
        self._logger.debug(f"Publishing event: {event.event_type} (ID: {event.event_id})")
        await self._event_queue.put(event)
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to events of a specific type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            self._logger.debug(f"Added subscriber for {event_type}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type"""
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                self._logger.debug(f"Removed subscriber for {event_type}")
    
    async def start(self, worker_count: int = 3, recover_events: bool = True):
        """
        Start the event bus with the specified number of worker tasks
        
        Args:
            worker_count: Number of worker tasks to start
            recover_events: Whether to recover pending events from the database
        """
        if self._is_running:
            self._logger.warning("Event bus is already running")
            return
            
        self._is_running = True
        self._logger.info(f"Starting event bus with {worker_count} workers")
        
        # Recover pending events from database if enabled
        if recover_events and self._db:
            await self._recover_pending_events()
        
        # Create worker tasks
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(f"worker-{i+1}"))
            self._tasks.append(task)
        
        # Start dead-letter queue processor
        self._dlq_task = asyncio.create_task(self._process_dead_letter_queue())
            
        self._logger.info("Event bus started")
    
    async def _recover_pending_events(self) -> None:
        """Recover pending events from the database"""
        try:
            # from models.events import Event as EventModel  # WRONG in new structure
            from app.models.events import Event as EventModel  # FIXED
            from sqlalchemy import select
            
            # Get all pending or retrying events
            stmt = select(EventModel).where(
                (EventModel.status.in_([EventStatus.PENDING, EventStatus.RETRYING]))
                & (EventModel.retry_count < EventModel.max_retries)
            ).order_by(EventModel.created_at)
            
            result = await self._db.execute(stmt)
            events = result.scalars().all()
            
            # Add events to the queue
            for event in events:
                await self._event_queue.put(event)
                
            if events:
                self._logger.info(f"Recovered {len(events)} pending events from database")
                
        except Exception as e:
            self._logger.error(f"Failed to recover pending events: {str(e)}", exc_info=True)
    
    async def _process_dead_letter_queue(self) -> None:
        """Process events in the dead-letter queue"""
        self._logger.info("Dead-letter queue processor started")
        
        while self._is_running:
            try:
                event = await self._dead_letter_queue.get()
                
                if event is None:  # Shutdown signal
                    break
                
                # Log the failed event
                self._logger.error(
                    f"Event {event.event_id} moved to dead-letter queue. "
                    f"Error: {event.last_error}"
                )
                
                # TODO: Add alerting/notification for dead-lettered events
                
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                self._logger.error(f"Error in dead-letter queue processor: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Prevent tight loop on errors
            
            finally:
                if self._dead_letter_queue.qsize() > 0:
                    self._dead_letter_queue.task_done()
        
        self._logger.info("Dead-letter queue processor stopped")
    
    async def stop(self) -> None:
        """Stop the event bus and all worker tasks"""
        if not self._is_running:
            return
            
        self._is_running = False
        self._logger.info("Stopping event bus...")
        
        # Wait for all tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        self._logger.info("Event bus stopped")
    
    async def _worker(self, worker_id: str):
        """Worker task that processes events from the queue with enhanced error handling"""
        self._logger.info(f"Worker {worker_id} started")
        self._metrics['active_workers'] += 1
        
        while self._is_running:
            try:
                event = await self._event_queue.get()
                if event is None:  # Shutdown signal
                    break
                
                start_time = time.time()
                
                try:
                    # Process the event
                    await self._process_event(event)
                    self._metrics['events_processed'] += 1
                    
                    # Update event status in database
                    if self._db:
                        await self._update_event_status(event, EventStatus.COMPLETED)
                    
                except Exception as e:
                    self._metrics['events_failed'] += 1
                    self._logger.error(f"Error processing event {event.event_id}: {str(e)}", exc_info=True)
                    
                    # Handle retries
                    if event.retry_count < event.max_retries:
                        event.retry_count += 1
                        event.status = EventStatus.RETRYING
                        event.last_error = str(e)
                        self._metrics['events_retried'] += 1
                        
                        # Exponential backoff
                        delay = min(2 ** event.retry_count, 60)  # Cap at 60 seconds
                        await asyncio.sleep(delay)
                        
                        # Requeue for retry
                        await self._event_queue.put(event)
                        
                        if self._db:
                            await self._update_event_status(event, EventStatus.RETRYING, str(e))
                    else:
                        # Move to dead-letter queue
                        event.status = EventStatus.FAILED
                        event.last_error = str(e)
                        await self._dead_letter_queue.put(event)
                        
                        if self._db:
                            await self._update_event_status(event, EventStatus.FAILED, str(e))
                
            except Exception as e:
                # Handle errors and retries
                event.retry_count += 1
                event.last_error = str(e)
                
                if event.retry_count <= event.max_retries:
                    event.status = EventStatus.RETRYING
                    self._logger.warning(
                        f"Handler {handler.__name__} failed (attempt {event.retry_count}/{event.max_retries}): {str(e)}",
                        exc_info=True
                    )
                    # Re-queue the event for retry
                    await self.publish(event)
                else:
                    event.status = EventStatus.FAILED
                    self._logger.error(
                        f"Handler {handler.__name__} failed after {event.max_retries} attempts: {str(e)}",
                        exc_info=True
                    )
                    
                    # Publish error event
                    error_event = Event(
                        event_id=f"err_{event.event_id}",
                        event_type=EventType.ERROR_OCCURRED,
                        data={
                            "original_event": event.dict(),
                            "error": str(e),
                            "handler": handler.__name__
                        },
                        metadata={"original_event_id": event.event_id}
                    )
                    await self.publish(error_event)
                
                break  # Stop processing this event after first error

# Global event bus instance
_event_bus = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

# Helper functions for common event operations

def create_event(event_type: Union[str, EventType], data: Dict[str, Any], **kwargs) -> Event:
    """Helper to create a new event"""
    if isinstance(event_type, str):
        event_type = EventType(event_type)
        
    return Event(
        # FIX: Event model uses `id` not `event_id`, and `payload` not `data`
        id=kwargs.get('event_id', f"evt_{datetime.now(timezone.utc).timestamp()}"),
        event_type=event_type,
        payload=data,
        **{k: v for k, v in kwargs.items() if k not in ['event_id']}
    )

async def publish_event(event_type: Union[str, EventType], data: Dict[str, Any], **kwargs) -> Event:
    """Helper to create and publish an event"""
    event = create_event(event_type, data, **kwargs)
    await get_event_bus().publish(event)
    return event

def event_handler(event_type: Union[str, EventType]):
    """Decorator to register a function as an event handler"""
    def decorator(func):
        get_event_bus().subscribe(
            event_type if isinstance(event_type, EventType) else EventType(event_type),
            func
        )
        return func
    return decorator

# Example usage:
# @event_handler(EventType.GITHUB_PUSH)
# async def handle_github_push(event: Event):
#     print(f"Processing push event: {event.data}")
#     # Your event handling logic here
