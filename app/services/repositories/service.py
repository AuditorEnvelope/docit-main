"""Repository service helpers for per-repo configuration."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models.repository import Repository


SAFE_REPOSITORY_COLUMNS = (
    Repository.id,
    Repository.repo_id,
    Repository.name,
    Repository.full_name,
    Repository.git_url,
    Repository.default_branch,
    Repository.tracked_branch,
    Repository.enabled,
    Repository.indexing_frequency,
    Repository.auto_generate_docs,
    Repository.subscription_id,
    Repository.repo_metadata,
    Repository.created_at,
    Repository.updated_at,
    Repository.last_indexed_at,
)

SAFE_REPOSITORY_ATTRIBUTE_NAMES = [
    "id",
    "repo_id",
    "name",
    "full_name",
    "git_url",
    "default_branch",
    "tracked_branch",
    "enabled",
    "indexing_frequency",
    "auto_generate_docs",
    "subscription_id",
    "repo_metadata",
    "created_at",
    "updated_at",
    "last_indexed_at",
]


class RepositoryService:
    """Database helpers for managing source repository settings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_full_name(self, repo_full_name: str) -> Optional[Repository]:
        repo_identifier = repo_full_name.strip()
        stmt = (
            select(Repository)
                .options(load_only(*SAFE_REPOSITORY_COLUMNS))
                .where(
                    (Repository.full_name == repo_identifier)
                    | (Repository.repo_id == repo_identifier)
                )
                .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tracked_branch(self, repo_full_name: str) -> Optional[str]:
        repo = await self.get_by_full_name(repo_full_name)
        if not repo:
            return None
        branch = (repo.tracked_branch or "").strip()
        return branch or None

    async def upsert_tracked_branch(
        self,
        repo_full_name: str,
        *,
        tracked_branch: str,
        default_branch: Optional[str] = None,
    ) -> Repository:
        repo_identifier = repo_full_name.strip()
        branch_value = (tracked_branch or "").strip() or "main"
        default_branch_value = (default_branch or "").strip() or "main"

        repo = await self.get_by_full_name(repo_identifier)
        if repo:
            repo.tracked_branch = branch_value
            if default_branch_value and not (repo.default_branch or "").strip():
                repo.default_branch = default_branch_value
            await self.db.commit()
            await self.db.refresh(repo, attribute_names=SAFE_REPOSITORY_ATTRIBUTE_NAMES)
            return repo

        insert_stmt = text(
            """
            INSERT INTO repositories (
                repo_id,
                name,
                full_name,
                tracked_branch,
                default_branch,
                enabled,
                indexing_frequency,
                auto_generate_docs
            )
            VALUES (
                :repo_id,
                :name,
                :full_name,
                :tracked_branch,
                :default_branch,
                TRUE,
                'realtime',
                TRUE
            )
            ON CONFLICT (repo_id) DO UPDATE
            SET tracked_branch = EXCLUDED.tracked_branch,
                default_branch = COALESCE(NULLIF(repositories.default_branch, ''), EXCLUDED.default_branch)
            RETURNING repo_id
            """
        )

        await self.db.execute(
            insert_stmt,
            {
                "repo_id": repo_identifier,
                "name": repo_identifier.split("/")[-1]
                if "/" in repo_identifier
                else repo_identifier,
                "full_name": repo_identifier,
                "tracked_branch": branch_value,
                "default_branch": default_branch_value,
            },
        )
        await self.db.commit()

        repo = await self.get_by_full_name(repo_identifier)
        if repo:
            return repo

        raise RuntimeError("Failed to upsert repository tracked branch")
