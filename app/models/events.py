"""
Event Models

Defines the database models for event processing:
- Event: Represents an event in the system
- EventProcessingLog: Tracks processing history of events
- EventStatus: Enum for event statuses
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class EventStatus(str, Enum):
    """Status of an event in the processing pipeline"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class Event(Base):
    """
    Represents an event in the system that needs to be processed.
    
    Events can be of different types (e.g., 'push', 'installation') and contain
    a JSON payload with event-specific data.
    """
    __tablename__ = "events"
    
    id = Column(String(36), primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(SQLEnum(EventStatus), default=EventStatus.PENDING, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    retry_at = Column(DateTime, nullable=True)
    
    # Relationships
    logs = relationship("EventProcessingLog", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event(id='{self.id}', type='{self.event_type}', status='{self.status}')>"
    
    @property
    def should_retry(self) -> bool:
        """Check if the event should be retried"""
        if self.status != EventStatus.FAILED:
            return False
        return self.retry_count < self.max_retries


class EventProcessingLog(Base):
    """
    Logs the processing history of events for auditing and debugging.
    """
    __tablename__ = "event_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    status = Column(SQLEnum(EventStatus), nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    event = relationship("Event", back_populates="logs")
    
    def __repr__(self):
        return f"<EventProcessingLog(event_id='{self.event_id}', status='{self.status}')>"


# Import all models to ensure they're registered with SQLAlchemy
__all__ = ["Event", "EventProcessingLog", "EventStatus"]
