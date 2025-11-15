"""Docbook service helpers."""

from typing import Optional

from sqlalchemy import select
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.docbook import DocbookRepo


class DocbookService:
    """Database helpers for managing docbook repositories."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_repo(self, user_id: str | UUID, org_id: str) -> Optional[DocbookRepo]:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

        stmt = select(DocbookRepo).where(DocbookRepo.user_id == user_uuid, DocbookRepo.org_id == org_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_repo_by_org(self, org_id: str) -> Optional[DocbookRepo]:
        stmt = select(DocbookRepo).where(DocbookRepo.org_id == org_id, DocbookRepo.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_repo(
        self,
        *,
        user_id: str | UUID,
        org_id: str,
        repo_name: str,
        full_name: str,
        repo_id: int,
        url: str,
    ) -> DocbookRepo:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

        repo = await self.get_repo(user_uuid, org_id)
        if repo:
            repo.docbook_repo_name = repo_name
            repo.docbook_full_name = full_name
            repo.docbook_repo_id = repo_id
            repo.docbook_url = url
            repo.is_active = True
        else:
            repo = DocbookRepo(
                user_id=user_uuid,
                org_id=org_id,
                docbook_repo_name=repo_name,
                docbook_full_name=full_name,
                docbook_repo_id=repo_id,
                docbook_url=url,
            )
            self.db.add(repo)

        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def get_tracked_branch(self, user_id: str | UUID, org_id: str) -> Optional[str]:
        repo = await self.get_repo(user_id, org_id)
        if not repo:
            return None
        tracked = (repo.tracked_branch or "").strip()
        return tracked or None

    async def update_tracked_branch(
        self,
        *,
        user_id: str | UUID,
        org_id: str,
        tracked_branch: str,
    ) -> DocbookRepo:
        repo = await self.get_repo(user_id, org_id)
        if not repo:
            raise ValueError("Docbook repository not linked for this organization")

        repo.tracked_branch = tracked_branch.strip() or "main"
        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def get_tracked_branches_for_orgs(self, org_ids: list[str]) -> dict[str, str]:
        if not org_ids:
            return {}

        stmt = select(DocbookRepo.org_id, DocbookRepo.tracked_branch).where(
            DocbookRepo.org_id.in_(org_ids),
            DocbookRepo.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return {
            row.org_id: (row.tracked_branch or "main").strip() or "main"
            for row in result.all()
        }
