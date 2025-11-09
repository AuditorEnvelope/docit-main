from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4, ConfigDict


class DocumentationStatus(str, Enum):
    """Status of documentation publication"""
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class DocumentationBase(BaseModel):
    """Base schema for documentation"""
    user_id: str = Field(..., description="ID of the user who triggered the publication")
    org_id: str = Field(..., description="Organization ID")
    repo_name: str = Field(..., description="Name of the source repository")
    commit_sha: str = Field(..., description="Git commit SHA of the documentation source")
    status: DocumentationStatus = Field(
        default=DocumentationStatus.PENDING,
        description="Current status of the documentation publication"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the publication failed"
    )
    docs_dir: str = Field(
        "docs",
        description="Directory containing the documentation source files"
    )
    published_at: Optional[datetime] = Field(
        None,
        description="When the documentation was published"
    )


class DocumentationCreate(DocumentationBase):
    """Schema for creating a new documentation"""
    pass


class DocumentationUpdate(BaseModel):
    """Schema for updating documentation"""
    status: Optional[DocumentationStatus] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None


class DocumentationResponse(DocumentationBase):
    """Response schema for documentation"""
    id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class DocumentationListResponse(BaseModel):
    """Response schema for listing documentation"""
    items: List[DocumentationResponse]
    total: int


class ManualGenerationRequest(BaseModel):
    """Schema for triggering manual documentation generation."""

    repo_full_name: str = Field(..., description="Repository in the form org/repo")
    doc_persona: str = Field("internal", description="Documentation persona to apply during generation")
    commit_sha: Optional[str] = Field(None, description="Optional commit SHA for logging the publication")
    commit_message: Optional[str] = Field(None, description="Optional commit message override for docbook staging push")


class ManualGenerationResponse(BaseModel):
    """Schema returned after manual documentation generation."""

    status: str
    message: str
    docbook_repo: Optional[str] = None
    branch: Optional[str] = None
    review_url: Optional[str] = None
