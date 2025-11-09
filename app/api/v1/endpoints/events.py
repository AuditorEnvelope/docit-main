"""
Event API Endpoints

Provides REST API endpoints for managing and processing events.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.events import Event, EventStatus, EventProcessingLog
from app.schemas.events import (
    EventCreate, EventUpdate, EventResponse,
    EventWithLogs
)
from app.services.event.service import EventService
from app.services.event.processor import EventProcessor

router = APIRouter()

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new event
    
    This endpoint creates a new event and optionally starts processing it.
    """
    try:
        event_service = EventService(db)
        event = await event_service.create_event(event_in)
        
        # Start processing the event in the background
        background_tasks.add_task(process_event_background, event.id, db)
        
        return {
            "success": True,
            "message": "Event created successfully",
            "data": {"event_id": event.id}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{event_id}", response_model=EventWithLogs)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get event by ID with processing logs"""
    event_service = EventService(db)
    event = await event_service.get_event_with_logs(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event

@router.get("/", response_model=List[EventResponse])
async def list_events(
    status: Optional[EventStatus] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List events with optional filtering"""
    event_service = EventService(db)
    return await event_service.list_events(
        status=status,
        event_type=event_type,
        limit=limit,
        offset=offset
    )

@router.post("/{event_id}/retry", response_model=EventResponse)
async def retry_event(
    event_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry processing a failed event"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.status not in [EventStatus.FAILED, EventStatus.RETRYING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or retrying events can be retried"
        )
    
    # Update event status to retrying
    await event_service.update_event(
        event_id,
        EventUpdate(status=EventStatus.RETRYING)
    )
    
    # Process the event in the background
    background_tasks.add_task(process_event_background, event_id, db)
    
    return {
        "success": True,
        "message": "Event queued for retry",
        "data": {"event_id": event_id}
    }

async def process_event_background(event_id: str, db: AsyncSession) -> None:
    """Background task to process an event"""
    try:
        event_service = EventService(db)
        event_processor = EventProcessor(db)
        
        # Get the event with a fresh session
        async with db.begin():
            event = await event_service.get_event(event_id, for_update=True)
            if not event:
                logger.error(f"Event {event_id} not found for processing")
                return
            
            # Process the event
            success = await event_processor.process(event)
            
            # Update event status
            status = EventStatus.COMPLETED if success else EventStatus.FAILED
            await event_service.update_event(
                event_id,
                EventUpdate(
                    status=status,
                    processed_at=datetime.utcnow()
                )
            )
            
    except Exception as e:
        logger.error(f"Error processing event {event_id} in background: {str(e)}", exc_info=True)
        # Update event status to failed
        try:
            await event_service.update_event(
                event_id,
                EventUpdate(
                    status=EventStatus.FAILED,
                    error=str(e),
                    processed_at=datetime.utcnow()
                )
            )
        except Exception as update_error:
            logger.error(f"Failed to update event status: {str(update_error)}")
    finally:
        await db.close()

# Include this router in your main FastAPI app
# app.include_router(events_router, prefix="/api/v1/events", tags=["events"])
