from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AppInstallationService:
    """Manage GitHub App installation metadata and accessible repositories."""

    def __init__(self, *, db_session: Optional[AsyncSession] = None, db_pool=None) -> None:
        if db_session is None and db_pool is None:
            raise ValueError("Either db_session or db_pool must be provided")
        self.db_session = db_session
        self.db_pool = db_pool

    async def store_installation(
        self,
        *,
        org_id: str,
        app_id: int,
        installation_id: int,
        repository_selection: str,
        repositories: Iterable[dict],
        user_id: Optional[str] = None,
    ) -> None:
        """Upsert installation metadata and replace tracked repositories."""

        repositories = list(repositories or [])

        if self.db_session:
            await self._store_installation_session(
                org_id=org_id,
                app_id=app_id,
                installation_id=installation_id,
                repository_selection=repository_selection,
                user_id=user_id,
            )
            await self._replace_repositories_session(org_id=org_id, app_id=app_id, repositories=repositories)
            await self.db_session.flush()
            return

        async with self.db_pool.acquire() as conn:
            await self._store_installation_conn(
                conn,
                org_id=org_id,
                app_id=app_id,
                installation_id=installation_id,
                repository_selection=repository_selection,
                user_id=user_id,
            )
            await self._replace_repositories_conn(conn, org_id=org_id, app_id=app_id, repositories=repositories)

    async def add_repositories(self, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        repositories = list(repositories or [])
        if not repositories:
            return

        if self.db_session:
            await self._insert_repositories_session(org_id, app_id, repositories)
            await self.db_session.flush()
            return

        async with self.db_pool.acquire() as conn:
            await self._insert_repositories_conn(conn, org_id, app_id, repositories)

    async def remove_repositories(self, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        repo_ids = [self._coerce_repo(repo)["repo_id"] for repo in repositories or []]
        if not repo_ids:
            return

        if self.db_session:
            await self.db_session.execute(
                text(
                    """
                    DELETE FROM app_installation_repos
                    WHERE org_id = :org_id
                      AND app_id = :app_id
                      AND repo_id = ANY(:repo_ids)
                    """
                ),
                {"org_id": org_id, "app_id": app_id, "repo_ids": repo_ids},
            )
            await self.db_session.flush()
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM app_installation_repos
                WHERE org_id = $1
                  AND app_id = $2
                  AND repo_id = ANY($3::int[])
                """,
                org_id,
                app_id,
                repo_ids,
            )

    async def remove_installation(self, org_id: str, app_id: int) -> None:
        if self.db_session:
            await self.db_session.execute(
                text(
                    """
                    DELETE FROM app_installation_repos
                    WHERE org_id = :org_id AND app_id = :app_id
                    """
                ),
                {"org_id": org_id, "app_id": app_id},
            )
            await self.db_session.execute(
                text(
                    """
                    DELETE FROM app_installations
                    WHERE org_id = :org_id AND app_id = :app_id
                    """
                ),
                {"org_id": org_id, "app_id": app_id},
            )
            await self.db_session.flush()
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM app_installation_repos
                WHERE org_id = $1 AND app_id = $2
                """,
                org_id,
                app_id,
            )
            await conn.execute(
                """
                DELETE FROM app_installations
                WHERE org_id = $1 AND app_id = $2
                """,
                org_id,
                app_id,
            )

    async def _store_installation_session(
        self,
        *,
        org_id: str,
        app_id: int,
        installation_id: int,
        repository_selection: str,
        user_id: Optional[str],
    ) -> None:
        await self.db_session.execute(
            text(
                """
                INSERT INTO app_installations (
                    org_id,
                    app_id,
                    installation_id,
                    repository_selection,
                    user_id,
                    created_at,
                    updated_at
                ) VALUES (:org_id, :app_id, :installation_id, :repository_selection, :user_id, NOW(), NOW())
                ON CONFLICT (org_id, app_id) DO UPDATE SET
                    installation_id = EXCLUDED.installation_id,
                    repository_selection = EXCLUDED.repository_selection,
                    user_id = COALESCE(EXCLUDED.user_id, app_installations.user_id),
                    updated_at = NOW()
                """
            ),
            {
                "org_id": org_id,
                "app_id": app_id,
                "installation_id": installation_id,
                "repository_selection": repository_selection or "all",
                "user_id": user_id,
            },
        )

    async def _replace_repositories_session(self, *, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        await self.db_session.execute(
            text(
                """
                DELETE FROM app_installation_repos
                WHERE org_id = :org_id AND app_id = :app_id
                """
            ),
            {"org_id": org_id, "app_id": app_id},
        )
        await self._insert_repositories_session(org_id, app_id, repositories)

    async def _insert_repositories_session(self, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        for repo in repositories:
            repo_data = self._coerce_repo(repo)
            await self.db_session.execute(
                text(
                    """
                    INSERT INTO app_installation_repos (
                        org_id,
                        app_id,
                        repo_id,
                        repo_name,
                        repo_full_name,
                        created_at
                    ) VALUES (:org_id, :app_id, :repo_id, :repo_name, :repo_full_name, NOW())
                    ON CONFLICT (org_id, app_id, repo_id) DO UPDATE SET
                        repo_name = EXCLUDED.repo_name,
                        repo_full_name = EXCLUDED.repo_full_name,
                        created_at = NOW()
                    """
                ),
                {
                    "org_id": org_id,
                    "app_id": app_id,
                    "repo_id": repo_data["repo_id"],
                    "repo_name": repo_data["repo_name"],
                    "repo_full_name": repo_data["repo_full_name"],
                },
            )

    async def _store_installation_conn(self, conn, *, org_id: str, app_id: int, installation_id: int, repository_selection: str, user_id: Optional[str]) -> None:
        await conn.execute(
            """
            INSERT INTO app_installations (
                org_id,
                app_id,
                installation_id,
                repository_selection,
                user_id,
                created_at,
                updated_at
            ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            ON CONFLICT (org_id, app_id) DO UPDATE SET
                installation_id = EXCLUDED.installation_id,
                repository_selection = EXCLUDED.repository_selection,
                user_id = COALESCE(EXCLUDED.user_id, app_installations.user_id),
                updated_at = NOW()
            """,
            org_id,
            app_id,
            installation_id,
            repository_selection or "all",
            user_id,
        )

    async def _replace_repositories_conn(self, conn, *, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        await conn.execute(
            """
            DELETE FROM app_installation_repos
            WHERE org_id = $1 AND app_id = $2
            """,
            org_id,
            app_id,
        )
        await self._insert_repositories_conn(conn, org_id, app_id, repositories)

    async def _insert_repositories_conn(self, conn, org_id: str, app_id: int, repositories: Iterable[dict]) -> None:
        for repo in repositories:
            repo_data = self._coerce_repo(repo)
            await conn.execute(
                """
                INSERT INTO app_installation_repos (
                    org_id,
                    app_id,
                    repo_id,
                    repo_name,
                    repo_full_name,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (org_id, app_id, repo_id) DO UPDATE SET
                    repo_name = EXCLUDED.repo_name,
                    repo_full_name = EXCLUDED.repo_full_name,
                    created_at = NOW()
                """,
                org_id,
                app_id,
                repo_data["repo_id"],
                repo_data["repo_name"],
                repo_data["repo_full_name"],
            )

    async def get_app_installation_id(
        self,
        org_id: str,
        app_id: int,
    ) -> Optional[int]:
        """
        Get installation ID for an app in an org (like old codebase)
        
        Args:
            org_id: Organization ID
            app_id: GitHub App ID
            
        Returns:
            Installation ID or None
        """
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT installation_id
                        FROM app_installations
                        WHERE org_id = $1 AND app_id = $2
                        """,
                        org_id,
                        app_id,
                    )
                    return row["installation_id"] if row else None
            except Exception as e:
                print(f"❌ Error getting app installation ID: {e}")
                return None
        
        if self.db_session:
            try:
                result = await self.db_session.execute(
                    text(
                        """
                        SELECT installation_id
                        FROM app_installations
                        WHERE org_id = :org_id AND app_id = :app_id
                        """
                    ),
                    {"org_id": org_id, "app_id": app_id},
                )
                row = result.first()
                return row[0] if row else None
            except Exception as e:
                print(f"❌ Error getting app installation ID: {e}")
                return None
        
        return None

    @staticmethod
    def _coerce_repo(repo: dict) -> dict:
        repo_id = repo.get("id")
        if repo_id is None:
            raise ValueError("Repository payload missing 'id'")
        repo_name = repo.get("name") or repo.get("full_name", "")
        repo_full_name = repo.get("full_name") or repo_name
        return {
            "repo_id": repo_id,
            "repo_name": repo_name,
            "repo_full_name": repo_full_name,
        }
