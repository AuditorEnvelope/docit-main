from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import DocumentationPublication, GitHubInstallation
from app.models.docbook import DocbookRepo, DocbookReview, DocbookStatus
from app.utils.github_dual_app import GitHubDualAppHelper

DEFAULT_STAGING_BRANCH = "staging"
DEFAULT_MAIN_BRANCH = "main"


class DocbookPublisher:
    """Publish documentation to the org's docbook staging branch."""

    def __init__(
        self,
        db_pool=None,
        *,
        dual_app: Optional[GitHubDualAppHelper] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> None:
        self.db_pool = db_pool
        self._dual_app = dual_app
        self.db_session = db_session

    async def publish_to_docbook(
        self,
        *,
        user_id: str | UUID,
        org_id: str,
        source_repo_name: str,
        docs_dir: Path,
        writer_token: Optional[str] = None,
        commit_message: str = "docs: Auto-generated documentation",
        commit_sha: Optional[str] = None,
        installation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Publish documentation artefacts to the staging branch."""

        if not docs_dir.exists():
            raise FileNotFoundError(f"Docs directory does not exist: {docs_dir}")

        user_uuid, user_label = self._normalize_user_id(user_id)

        print(f"\n{'=' * 80}")
        print(f"📦 Starting docbook publish for {source_repo_name}")
        print(f"👤 User: {user_label}, Org: {org_id}")
        print(f"📂 Docs dir: {docs_dir}")
        print(f"{'=' * 80}\n")

        docbook_repo = await self._get_docbook_repo(user_uuid, org_id)
        if docbook_repo:
            docbook_full_name = docbook_repo["full_name"]
            docbook_url = docbook_repo["url"]
            staging_branch = docbook_repo["staging_branch"]
            main_branch = docbook_repo["main_branch"]
            print(f"✅ Found linked docbook repo: {docbook_full_name}")
        else:
            docbook_full_name = f"{org_id}/pustak-docbook-{org_id}"
            docbook_url = f"https://github.com/{docbook_full_name}"
            staging_branch = DEFAULT_STAGING_BRANCH
            main_branch = DEFAULT_MAIN_BRANCH
            print(f"ℹ️  Using default docbook repo naming: {docbook_full_name}")

        if not writer_token:
            token_source = "provided installation" if installation_id else "database"
            print(f"🔑 Writer token not provided. Resolving via {token_source}...")
            installation_id = installation_id or await self._get_installation_id(org_id)
            if not installation_id:
                raise RuntimeError(f"No GitHub installation found for org {org_id}")
            writer_token = await self._get_writer_token(installation_id)
            if not writer_token:
                raise RuntimeError("Failed to resolve writer token")
            print("✅ Obtained writer token from GitHub App")
        else:
            print("ℹ️  Using provided writer token")

        tmp_dir = Path(tempfile.mkdtemp(prefix="docai_docbook_"))
        print(f"📁 Working directory: {tmp_dir}")

        try:
            self._clone_repo(docbook_full_name, writer_token, tmp_dir)
            self._configure_git_identity(tmp_dir)
            self._checkout_staging(tmp_dir, staging_branch, main_branch, writer_token, docbook_full_name)
            self._sync_docs(tmp_dir, source_repo_name, docs_dir)

            if not self._has_changes(tmp_dir):
                print("ℹ️  No changes detected – skipping push")
                return {
                    "status": "no_changes",
                    "message": "No documentation updates detected",
                    "docbook_repo": docbook_full_name,
                    "branch": staging_branch,
                }

            full_commit_msg = f"{commit_message} ({source_repo_name})"
            self._commit_changes(tmp_dir, full_commit_msg)
            self._push_changes(tmp_dir, docbook_full_name, staging_branch, writer_token)

            metadata = {
                "source_repo": source_repo_name,
                "docbook_repo": docbook_full_name,
                "branch": staging_branch,
                "commit_sha": commit_sha,
            }

            if self.db_pool and user_uuid:
                await self._record_pending_review(
                    user_uuid,
                    org_id,
                    source_repo_name,
                    docbook_full_name,
                    full_commit_msg,
                    metadata,
                )

                if commit_sha:
                    await self.log_publication(
                        user_id=str(user_uuid),
                        org_id=org_id,
                        repo_name=source_repo_name,
                        commit_sha=commit_sha,
                        status="pending_review",
                    )
            else:
                print("⚠️  Skipping review logging – missing db_pool or user UUID")

            review_url = f"{docbook_url}/compare/{main_branch}...{staging_branch}"
            print(f"✅ Published to {docbook_full_name}/{staging_branch}")
            print(f"🔗 Review diff: {review_url}")

            return {
                "status": "published_to_staging",
                "message": f"Documentation staged in {docbook_full_name}",
                "docbook_repo": docbook_full_name,
                "source_repo": source_repo_name,
                "branch": staging_branch,
                "review_url": review_url,
                "commit_message": full_commit_msg,
            }

        except Exception as exc:  # noqa: BLE001 - surface full error upstream
            print(f"❌ Error publishing to docbook: {exc}")
            return {
                "status": "error",
                "message": str(exc),
                "docbook_repo": docbook_full_name,
                "branch": staging_branch,
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def log_publication(
        self,
        *,
        user_id: str,
        org_id: str,
        repo_name: str,
        commit_sha: str,
        status: str,
    ) -> None:
        if self.db_session:
            await self._log_publication_session(
                user_id=user_id,
                org_id=org_id,
                repo_name=repo_name,
                commit_sha=commit_sha,
                status=status,
            )
            return

        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM documentation_publications
                    WHERE org_id = $1 AND repo_name = $2 AND commit_sha = $3
                    """,
                    org_id,
                    repo_name,
                    commit_sha,
                )

                if existing:
                    await conn.execute(
                        """
                        UPDATE documentation_publications
                        SET status = $1,
                            updated_at = NOW()
                        WHERE id = $2
                        """,
                        status,
                        existing["id"],
                    )
                else:
                    await conn.execute(
                        """
                        INSERT INTO documentation_publications (
                            user_id, org_id, repo_name, commit_sha, status, published_at
                        ) VALUES ($1, $2, $3, $4, $5, NOW())
                        """,
                        user_id,
                        org_id,
                        repo_name,
                        commit_sha,
                        status,
                    )
        except Exception as exc:  # noqa: BLE001 - log and continue
            print(f"❌ Failed to log publication: {exc}")

    async def _log_publication_session(
        self,
        *,
        user_id: str,
        org_id: str,
        repo_name: str,
        commit_sha: str,
        status: str,
    ) -> None:
        if not self.db_session:
            return

        result = await self.db_session.execute(
            select(DocumentationPublication).where(
                DocumentationPublication.org_id == org_id,
                DocumentationPublication.repo_name == repo_name,
                DocumentationPublication.commit_sha == commit_sha,
            )
        )
        publication = result.scalar_one_or_none()

        if publication:
            publication.status = status
            publication.updated_at = datetime.utcnow()
        else:
            publication = DocumentationPublication(
                user_id=user_id,
                org_id=org_id,
                repo_name=repo_name,
                commit_sha=commit_sha,
                status=status,
                published_at=datetime.utcnow(),
            )
            self.db_session.add(publication)

        await self.db_session.flush()

    async def _get_docbook_repo(self, user_uuid: Optional[UUID], org_id: str) -> Optional[Dict[str, Any]]:
        if not user_uuid:
            return None

        if self.db_session:
            result = await self.db_session.execute(
                select(DocbookRepo).where(
                    DocbookRepo.user_id == user_uuid,
                    DocbookRepo.org_id == org_id,
                    DocbookRepo.is_active.is_(True),
                )
            )
            repo = result.scalar_one_or_none()
            if not repo:
                return None
            return {
                "full_name": repo.docbook_full_name,
                "url": repo.docbook_url,
                "staging_branch": repo.staging_branch or DEFAULT_STAGING_BRANCH,
                "main_branch": repo.main_branch or DEFAULT_MAIN_BRANCH,
                "auto_merge": repo.auto_merge,
            }

        if not self.db_pool:
            return None

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT docbook_full_name,
                       docbook_url,
                       staging_branch,
                       main_branch,
                       auto_merge
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
                """,
                user_uuid,
                org_id,
            )

        if not row:
            return None

        return {
            "full_name": row["docbook_full_name"],
            "url": row["docbook_url"],
            "staging_branch": row["staging_branch"] or DEFAULT_STAGING_BRANCH,
            "main_branch": row["main_branch"] or DEFAULT_MAIN_BRANCH,
            "auto_merge": row["auto_merge"],
        }

    async def _get_installation_id(self, org_id: str) -> Optional[int]:
        writer_app_id = self._writer_app_id()

        def _as_int(value: Optional[str | int]) -> Optional[int]:
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                return None

        writer_app_id_int = _as_int(writer_app_id)

        if self.db_session:
            if writer_app_id_int is not None:
                session_result = await self.db_session.execute(
                    text(
                        """
                        SELECT installation_id
                        FROM app_installations
                        WHERE org_id = :org_id AND app_id = :app_id
                        """
                    ),
                    {"org_id": org_id, "app_id": writer_app_id_int},
                )
                row = session_result.first()
                if row:
                    return row[0]

            if writer_app_id_int is not None:
                result = await self.db_session.execute(
                    select(GitHubInstallation.installation_id).where(
                        GitHubInstallation.org_id == org_id,
                        GitHubInstallation.app_id == writer_app_id_int,
                    )
                )
                installation_id = result.scalar_one_or_none()
                if installation_id:
                    return installation_id

            result = await self.db_session.execute(
                select(GitHubInstallation.installation_id)
                .where(GitHubInstallation.org_id == org_id)
                .order_by(GitHubInstallation.updated_at.desc())
            )
            installation_id = result.scalar_one_or_none()
            if installation_id:
                return installation_id

        if not self.db_pool:
            return None

        async with self.db_pool.acquire() as conn:
            if writer_app_id_int is not None:
                app_installation_row = await conn.fetchrow(
                    """
                    SELECT installation_id
                    FROM app_installations
                    WHERE org_id = $1 AND app_id = $2
                    """,
                    org_id,
                    writer_app_id_int,
                )
                if app_installation_row:
                    return app_installation_row["installation_id"]

            if writer_app_id_int is not None:
                row = await conn.fetchrow(
                    """
                    SELECT installation_id
                    FROM github_installations
                    WHERE org_id = $1 AND app_id = $2
                    """,
                    org_id,
                    writer_app_id_int,
                )
                if row:
                    return row["installation_id"]

            row = await conn.fetchrow(
                """
                SELECT installation_id
                FROM github_installations
                WHERE org_id = $1
                ORDER BY updated_at DESC NULLS LAST
                """,
                org_id,
            )

        return row["installation_id"] if row else None

    async def _get_writer_token(self, installation_id: int) -> Optional[str]:
        helper = self._get_dual_app_helper()
        token = await helper.get_writer_token(installation_id)
        if token:
            preview = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "<short>"
            print(f"🔐 Writer token acquired ({preview})")
        return token

    def _clone_repo(self, repo_full_name: str, writer_token: str, destination: Path) -> None:
        clone_url, masked_url = self._tokenized_urls(repo_full_name, writer_token)
        print(f"📚 Cloning docbook repository: {masked_url}")
        self._run_git([
            "git",
            "clone",
            "--depth",
            "1",
            clone_url,
            str(destination),
        ], mask_tokens=[writer_token])

    def _configure_git_identity(self, repo_dir: Path) -> None:
        name, email = self._writer_identity()
        self._run_git(["git", "config", "user.name", name], cwd=repo_dir)
        self._run_git(["git", "config", "user.email", email], cwd=repo_dir)

    def _checkout_staging(
        self,
        repo_dir: Path,
        staging_branch: str,
        main_branch: str,
        writer_token: str,
        repo_full_name: str,
    ) -> None:
        clone_url, _ = self._tokenized_urls(repo_full_name, writer_token)
        self._run_git(["git", "fetch", "origin"], cwd=repo_dir)

        branches = self._run_git(
            ["git", "branch", "-r"],
            cwd=repo_dir,
            capture_output=True,
        )
        remote_branch = f"origin/{staging_branch}"
        if remote_branch in branches:
            self._run_git(["git", "checkout", staging_branch], cwd=repo_dir)
            self._run_git(["git", "reset", "--hard", remote_branch], cwd=repo_dir)
            return

        print(f"ℹ️  Staging branch missing. Creating {staging_branch} from {main_branch}")
        main_remote = f"origin/{main_branch}"
        if main_remote not in branches:
            raise RuntimeError(
                f"Main branch {main_branch} not found in repo {repo_full_name}."
            )
        self._run_git(["git", "checkout", "-b", staging_branch, main_remote], cwd=repo_dir)
        self._run_git([
            "git",
            "push",
            clone_url,
            f"HEAD:{staging_branch}",
        ], cwd=repo_dir, mask_tokens=[writer_token])

    def _sync_docs(self, repo_dir: Path, source_repo_name: str, docs_dir: Path) -> None:
        target_dir = repo_dir / source_repo_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(docs_dir, target_dir)
        self._run_git(["git", "add", f"{source_repo_name}/"], cwd=repo_dir)

    def _has_changes(self, repo_dir: Path) -> bool:
        status = self._run_git(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
        )
        return bool(status.strip())

    def _commit_changes(self, repo_dir: Path, commit_message: str) -> None:
        self._run_git(["git", "commit", "-m", commit_message], cwd=repo_dir)

    def _push_changes(
        self,
        repo_dir: Path,
        repo_full_name: str,
        staging_branch: str,
        writer_token: str,
    ) -> None:
        push_url, masked_url = self._tokenized_urls(repo_full_name, writer_token)
        print(f"🚀 Pushing updates to {masked_url} ({staging_branch})")
        self._run_git(
            ["git", "push", push_url, f"HEAD:{staging_branch}"],
            cwd=repo_dir,
            mask_tokens=[writer_token],
        )

    async def _record_pending_review(
        self,
        user_uuid: UUID,
        org_id: str,
        source_repo_name: str,
        docbook_full_name: str,
        commit_message: str,
        metadata: Dict[str, Any],
    ) -> None:
        if self.db_session:
            result = await self.db_session.execute(
                select(DocbookReview).where(
                    DocbookReview.user_id == user_uuid,
                    DocbookReview.org_id == org_id,
                    DocbookReview.source_repo_name == source_repo_name,
                )
            )
            review = result.scalar_one_or_none()

            if review:
                review.status = DocbookStatus.PENDING_REVIEW
                review.commit_message = commit_message
                review.review_metadata = metadata
                review.updated_at = datetime.utcnow()
            else:
                review = DocbookReview(
                    user_id=user_uuid,
                    org_id=org_id,
                    source_repo_name=source_repo_name,
                    docbook_full_name=docbook_full_name,
                    status=DocbookStatus.PENDING_REVIEW,
                    commit_message=commit_message,
                    review_metadata=metadata,
                )
                self.db_session.add(review)

            await self.db_session.flush()
            return

        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT id FROM docbook_reviews
                WHERE user_id = $1 AND org_id = $2 AND source_repo_name = $3
                """,
                user_uuid,
                org_id,
                source_repo_name,
            )

            if existing:
                await conn.execute(
                    """
                    UPDATE docbook_reviews
                    SET status = 'pending_review',
                        commit_message = $1,
                        review_metadata = $2,
                        updated_at = NOW()
                    WHERE id = $3
                    """,
                    commit_message,
                    json.dumps(metadata, default=str),
                    existing["id"],
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO docbook_reviews (
                        user_id,
                        org_id,
                        source_repo_name,
                        docbook_full_name,
                        status,
                        commit_message,
                        review_metadata,
                        created_at
                    ) VALUES ($1, $2, $3, $4, 'pending_review', $5, $6, NOW())
                    """,
                    user_uuid,
                    org_id,
                    source_repo_name,
                    docbook_full_name,
                    commit_message,
                    json.dumps(metadata, default=str),
                )

    def _normalize_user_id(self, user_id: str | UUID) -> Tuple[Optional[UUID], str]:
        if isinstance(user_id, UUID):
            return user_id, str(user_id)

        if not user_id:
            return None, "<unknown>"

        try:
            user_uuid = UUID(str(user_id))
            return user_uuid, str(user_uuid)
        except (ValueError, TypeError):
            fallback_uuid = uuid4()
            return None, f"{user_id} (anon {fallback_uuid})"

    def _writer_app_id(self) -> Optional[int]:
        helper = self._get_dual_app_helper()
        app_id = helper.writer_app_id or helper.github_app_id
        try:
            return int(app_id) if app_id else None
        except (TypeError, ValueError):
            return None

    def _writer_identity(self) -> Tuple[str, str]:
        helper = self._get_dual_app_helper()
        app_id = helper.writer_app_id or helper.github_app_id or "pustak-bot"
        slug = "pustak-publisher-ai"
        bot_name = f"{slug}[bot]"
        bot_email = f"{app_id}+{slug}[bot]@users.noreply.github.com"
        return bot_name, bot_email

    def _tokenized_urls(self, repo_full_name: str, token: str) -> Tuple[str, str]:
        url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        masked = f"https://x-access-token:***MASKED***@github.com/{repo_full_name}.git"
        return url, masked

    def _run_git(
        self,
        cmd: list[str],
        *,
        cwd: Optional[Path] = None,
        capture_output: bool = False,
        mask_tokens: Optional[list[str]] = None,
    ) -> str:
        mask_tokens = mask_tokens or []
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            stderr = self._mask(proc.stderr, mask_tokens)
            stdout = self._mask(proc.stdout, mask_tokens)
            cmd_str = " ".join(cmd)
            print(f"❌ Command failed: {cmd_str}\nstdout: {stdout}\nstderr: {stderr}")
            raise RuntimeError(stderr or stdout or f"Command failed: {cmd_str}")

        output = proc.stdout if capture_output else ""
        return self._mask(output, mask_tokens)

    def _mask(self, text: str, tokens: list[str]) -> str:
        masked = text
        for token in tokens:
            if token and len(token) > 4:
                masked = masked.replace(token, "***MASKED***")
        return masked

    def _get_dual_app_helper(self) -> GitHubDualAppHelper:
        if not self._dual_app:
            self._dual_app = GitHubDualAppHelper()
        return self._dual_app
