"""
Event Schemas

Defines Pydantic models for event-related request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models.events import EventStatus

class EventBase(BaseModel):
    """Base schema for event data"""
    event_type: str = Field(..., description="Type of the event (e.g., 'push', 'installation')")
    payload: Dict[str, Any] = Field(..., description="Event payload as a JSON object")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "push",
                "payload": {
                    "repository": "user/repo",
                    "branch": "main",
                    "commit_sha": "abc123"
                }
            }
        }
    )

class EventCreate(EventBase):
    """Schema for creating a new event"""
    pass

class EventUpdate(BaseModel):
    """Schema for updating an existing event"""
    status: Optional[EventStatus] = None
    error: Optional[str] = None
    retry_count: Optional[int] = None
    retry_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "error": None,
                "retry_count": 0
            }
        }
    )

class EventInDBBase(EventBase):
    """Base schema for event data in the database"""
    id: str
    status: EventStatus
    retry_count: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    source: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class Event(EventInDBBase):
    """Schema for returning event data"""
    pass

class EventProcessingLogBase(BaseModel):
    """Base schema for event processing logs"""
    status: EventStatus
    error: Optional[str] = None
    retry_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class EventProcessingLogCreate(EventProcessingLogBase):
    """Schema for creating a new event processing log"""
    event_id: str

class EventProcessingLog(EventProcessingLogBase):
    """Schema for returning event processing log data"""
    id: int
    event_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class EventWithLogs(Event):
    """Schema for event data including processing logs"""
    logs: List[EventProcessingLog] = []

# Response models
class EventResponse(BaseModel):
    """Standard response model for event operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Event processed successfully",
                "data": {
                    "event_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }
    )

# Webhook specific models
class WebhookEvent(BaseModel):
    """Base model for webhook events"""
    event: str
    payload: Dict[str, Any]
    signature: Optional[str] = None
    
    @field_validator('event')
    @classmethod
    def validate_event_type(cls, v):
        valid_events = ['push', 'installation', 'installation_repositories', 'ping']
        if v not in valid_events:
            raise ValueError(f"Invalid event type. Must be one of: {', '.join(valid_events)}")
        return v

# Import all schemas to make them easily importable
__all__ = [
    'EventBase', 'EventCreate', 'EventUpdate', 'Event', 'EventInDBBase',
    'EventProcessingLogBase', 'EventProcessingLogCreate', 'EventProcessingLog',
    'EventWithLogs', 'EventResponse', 'WebhookEvent'
]
