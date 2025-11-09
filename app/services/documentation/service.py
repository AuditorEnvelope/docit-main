from pathlib import Path
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.base import DocumentationPublication
from app.schemas.documentation import DocumentationCreate, DocumentationResponse, DocumentationStatus
from app.services.docbook.publisher import DocbookPublisher

class DocumentationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.publisher = DocbookPublisher()

    async def list_publications(
        self,
        repo_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[DocumentationResponse]:
        """List documentation publications with optional filtering"""
        query = select(DocumentationPublication)
        
        conditions = []
        if repo_name:
            conditions.append(DocumentationPublication.repo_name.ilike(f"%{repo_name}%"))
        if status:
            conditions.append(DocumentationPublication.status == status)
            
        if conditions:
            query = query.where(and_(*conditions))
            
        query = query.order_by(DocumentationPublication.published_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_publication(self, doc_id: UUID) -> Optional[DocumentationResponse]:
        """Get a specific documentation by ID"""
        result = await self.db.get(DocumentationPublication, doc_id)
        return result

    async def create_publication(self, doc_in: DocumentationCreate) -> DocumentationResponse:
        """Create a new documentation entry"""
        doc = DocumentationPublication(**doc_in.dict())
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def publish_documentation(self, doc_id: UUID) -> Optional[DocumentationResponse]:
        """Publish documentation to docbook"""
        doc = await self.get_publication(doc_id)
        if not doc or doc.status != DocumentationStatus.PENDING:
            return None
            
        try:
            # Publish to docbook
            await self.publisher.publish_to_docbook(
                user_id=doc.user_id,
                org_id=doc.org_id,
                source_repo_name=doc.repo_name,
                docs_dir=Path(doc.docs_dir),
                commit_message=f"docs: Publish {doc.repo_name} documentation",
                commit_sha=doc.commit_sha,
            )
            
            # Update status
            doc.status = DocumentationStatus.PUBLISHED
            await self.db.commit()
            await self.db.refresh(doc)
            return doc
            
        except Exception as e:
            doc.status = DocumentationStatus.FAILED
            doc.error_message = str(e)
            await self.db.commit()
            raise
