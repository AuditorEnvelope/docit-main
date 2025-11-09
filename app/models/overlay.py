"""
Overlay Models

Database models for documentation overlays and quality tracking
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON, func
from enum import Enum

from .base import Base

class Overlay(Base):
    """
    Documentation overlay system
    
    Allows users to add custom documentation on top of AI-generated docs
    without modifying the source
    """
    __tablename__ = "overlays"
    
    id = Column(String(36), primary_key=True, index=True)  # UUID
    node_id = Column(String(255), nullable=False, index=True)  # Reference to doc node
    
    # Content
    content = Column(JSON, nullable=False)  # Overlay content/modifications
    reason = Column(Text, nullable=True)  # Why was this overlay created
    
    # Author
    author_id = Column(String(36), nullable=False, index=True)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    
    # Version control
    version = Column(Integer, default=1)
    parent_overlay_id = Column(String(36), nullable=True)  # For overlay history
    
    # Status
    is_active = Column(Boolean, default=True)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    def __repr__(self):
        return f"<Overlay(id='{self.id}', node='{self.node_id}', author='{self.author_name}')>"

class QualityScore(Base):
    """
    Documentation quality tracking
    
    Stores quality scores and metrics for documentation
    """
    __tablename__ = "quality_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(String(255), nullable=False, index=True)
    commit_sha = Column(String(100), nullable=True, index=True)
    
    # Overall scores
    overall_score = Column(Float, nullable=False)  # 0-100
    completeness_score = Column(Float, nullable=False)  # 0-100
    clarity_score = Column(Float, nullable=False)  # 0-100
    accuracy_score = Column(Float, nullable=False)  # 0-100
    
    # Coverage metrics
    total_functions = Column(Integer, default=0)
    documented_functions = Column(Integer, default=0)
    total_classes = Column(Integer, default=0)
    documented_classes = Column(Integer, default=0)
    total_modules = Column(Integer, default=0)
    documented_modules = Column(Integer, default=0)
    
    # Code metrics
    lines_of_code = Column(Integer, default=0)
    lines_of_docs = Column(Integer, default=0)
    doc_to_code_ratio = Column(Float, default=0.0)
    
    # Quality issues
    issues_found = Column(JSON, nullable=True)  # List of quality issues
    suggestions = Column(JSON, nullable=True)  # Improvement suggestions
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<QualityScore(repo='{self.repo_id}', score={self.overall_score:.1f})>"

__all__ = ["Overlay", "QualityScore"]
