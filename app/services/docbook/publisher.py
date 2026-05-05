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
            raise FileNotFoundError(
                f"Docs directory does not exist: {docs_dir}")

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
            docbook_full_name = f"{org_id}/docit-docbook-{org_id}"
            docbook_url = f"https://github.com/{docbook_full_name}"
            staging_branch = DEFAULT_STAGING_BRANCH
            main_branch = DEFAULT_MAIN_BRANCH
            print(
                f"ℹ️  Using default docbook repo naming: {docbook_full_name}")

        if not writer_token:
            token_source = "provided installation" if installation_id else "database"
            print(
                f"🔑 Writer token not provided. Resolving via {token_source}...")
            installation_id = installation_id or await self._get_installation_id(org_id)
            if not installation_id:
                # Don't raise - make it non-blocking, just log and return error status
                error_msg = f"No GitHub installation found for org {org_id}. Please install Writer App."
                print(f"⚠️  {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "docbook_repo": docbook_full_name,
                    "branch": staging_branch,
                }
            writer_token = await self._get_writer_token(installation_id)
            if not writer_token:
                # Don't raise - make it non-blocking
                error_msg = "Failed to resolve writer token. Installation may not exist or app credentials may be invalid."
                print(f"⚠️  {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "docbook_repo": docbook_full_name,
                    "branch": staging_branch,
                }
            print("✅ Obtained writer token from GitHub App")
        else:
            print("ℹ️  Using provided writer token")

        tmp_dir = Path(tempfile.mkdtemp(prefix="docai_docbook_"))
        print(f"📁 Working directory: {tmp_dir}")

        # Check if repository exists
        repo_exists = await self._check_repo_exists(org_id, f"docit-docbook-{org_id}", writer_token)
        if not repo_exists:
            print(
                f"❌ Error publishing to docbook: Repository {docbook_full_name} not found")
            print(
                "ℹ️ You may need to create this repository first or check the organization name")
            print(f"ℹ️ Expected repository name: {docbook_full_name}")
            return {
                "status": "error",
                "message": f"Repository {docbook_full_name} not found. Please create it first.",
                "docbook_repo": docbook_full_name,
                "branch": staging_branch,
            }

        try:
            try:
                self._clone_repo(docbook_full_name, writer_token, tmp_dir)
            except RuntimeError as e:
                error_msg = str(e)
                if "Repository not found" in error_msg:
                    print(
                        f"❌ Error publishing to docbook: Repository {docbook_full_name} not found")
                    print(
                        "ℹ️ You may need to create this repository first or check the organization name")
                    return {
                        "status": "error",
                        "message": f"Repository {docbook_full_name} not found. Please create it first.",
                        "docbook_repo": docbook_full_name,
                        "branch": staging_branch,
                    }
                else:
                    raise

            self._configure_git_identity(tmp_dir)
            self._checkout_staging(
                tmp_dir, staging_branch, main_branch, writer_token, docbook_full_name)
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
            self._push_changes(tmp_dir, docbook_full_name,
                               staging_branch, writer_token)

            metadata = {
                "source_repo": source_repo_name,
                "docbook_repo": docbook_full_name,
                "branch": staging_branch,
                "commit_sha": commit_sha,
            }

            if user_uuid:
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
                print("⚠️  Skipping review logging – missing user UUID")

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

        try:
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

                # Don't flush here - let the caller handle the transaction
                # await self.db_session.flush()
        except Exception as exc:
            # Log but don't fail - publication logging is non-critical
            print(f"⚠️  Failed to log publication (non-critical): {exc}")

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
        """
        Get writer app installation ID for an org (like old codebase)
        Uses AppInstallationService to query app_installations table
        """
        from app.services.github.app_installation_service import AppInstallationService

        writer_app_id = self._writer_app_id()
        if not writer_app_id:
            return None

        try:
            writer_app_id_int = int(writer_app_id)
        except (TypeError, ValueError):
            return None

        # Use AppInstallationService like old codebase does
        # This is the correct way - matches old codebase behavior
        if self.db_pool:
            try:
                service = AppInstallationService(db_pool=self.db_pool)
                installation_id = await service.get_app_installation_id(org_id, writer_app_id_int)
                if installation_id:
                    print(
                        f"✅ Resolved writer installation ID {installation_id} for org {org_id} (app {writer_app_id_int})")
                    return installation_id
            except Exception as e:
                print(f"⚠️  Error using AppInstallationService: {e}")

        if self.db_session:
            try:
                service = AppInstallationService(db_session=self.db_session)
                installation_id = await service.get_app_installation_id(org_id, writer_app_id_int)
                if installation_id:
                    print(
                        f"✅ Resolved writer installation ID {installation_id} for org {org_id} (app {writer_app_id_int})")
                    return installation_id
            except Exception as e:
                print(f"⚠️  Error using AppInstallationService: {e}")

        # Fallback: try legacy github_installations table
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
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
            except Exception as e:
                print(f"⚠️  Error looking up legacy installation: {e}")

        print(
            f"⚠️  No installation found for org {org_id}, app {writer_app_id_int}")
        return None

    async def _get_writer_token(self, installation_id: int) -> Optional[str]:
        helper = self._get_dual_app_helper()
        token = await helper.get_writer_token(installation_id)
        return token

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
        """
        Checkout staging branch (like old codebase)
        Handles empty repos by creating initial commit on main, then staging from main
        """
        # Fetch all branches (like old codebase)
        try:
            self._run_git(["git", "fetch", "origin"], cwd=repo_dir)
        except RuntimeError:
            # If fetch fails, repo might be empty
            pass

        # Check if repo is empty (like old codebase)
        try:
            branches = self._run_git(
                ["git", "branch", "-r"], cwd=repo_dir, capture_output=True).strip()
            is_empty = not branches or "origin/" not in branches
        except RuntimeError:
            is_empty = True

        if is_empty:
            # Repo is empty - create initial commit on main, then staging (like old codebase)
            print(f"📝 Repo is empty, creating initial commit...")
            clone_url, _ = self._tokenized_urls(repo_full_name, writer_token)
            self._initialize_empty_repo(
                repo_dir=repo_dir,
                main_branch=main_branch,
                staging_branch=staging_branch,
                writer_token=writer_token,
                repo_full_name=repo_full_name,
                clone_url=clone_url,
            )
            print(f"✅ Created staging branch")
            return

        # Repo has content - try to checkout staging (like old codebase)
        try:
            self._run_git(["git", "checkout", staging_branch], cwd=repo_dir)
            print(f"✅ Checked out existing staging branch")
            return
        except RuntimeError:
            # Staging doesn't exist - create it from main (like old codebase)
            try:
                # Try to checkout main first
                self._run_git(["git", "checkout", main_branch], cwd=repo_dir)
            except RuntimeError:
                # Try master as fallback
                try:
                    self._run_git(["git", "checkout", "master"], cwd=repo_dir)
                    main_branch = "master"
                except RuntimeError:
                    # Try to checkout from remote
                    try:
                        self._run_git(
                            ["git", "checkout", "-b", main_branch, f"origin/{main_branch}"], cwd=repo_dir)
                    except RuntimeError:
                        # Last resort - try master from remote
                        self._run_git(
                            ["git", "checkout", "-b", "master", "origin/master"], cwd=repo_dir)
                        main_branch = "master"

            # Now create staging from main (like old codebase)
            self._run_git(["git", "checkout", "-b",
                          staging_branch], cwd=repo_dir)
            print(f"✅ Created staging branch from {main_branch}")

    def _determine_base_ref(
        self,
        repo_dir: Path,
        preferred_main: str,
    ) -> Optional[str]:
        candidates = [preferred_main, "main", "master"]
        for candidate in candidates:
            if self._remote_branch_exists(repo_dir, candidate):
                return f"origin/{candidate}"

        # Try default remote HEAD
        try:
            head_ref = self._run_git(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=repo_dir,
                capture_output=True,
            ).strip()
            if head_ref:
                return head_ref
        except RuntimeError:
            pass

        return None

    def _remote_branch_exists(self, repo_dir: Path, branch: str) -> bool:
        try:
            output = self._run_git(
                ["git", "ls-remote", "--heads", "origin", branch],
                cwd=repo_dir,
                capture_output=True,
            )
            return bool(output.strip())
        except RuntimeError:
            return False

    def _initialize_empty_repo(
        self,
        *,
        repo_dir: Path,
        main_branch: str,
        staging_branch: str,
        writer_token: str,
        repo_full_name: str,
        clone_url: str,
    ) -> None:
        print(
            f"ℹ️  Repository {repo_full_name} has no default branch. Initializing {main_branch}."
        )

        self._run_git(["git", "checkout", "--orphan",
                      main_branch], cwd=repo_dir)

        placeholder = repo_dir / "README.md"
        if not placeholder.exists():
            placeholder.write_text(
                f"# {repo_full_name}\n\nInitial commit for docbook repository."
            )

        self._run_git(["git", "add", "README.md"], cwd=repo_dir)
        self._run_git(
            ["git", "commit", "-m", "chore: initialize docbook main branch"],
            cwd=repo_dir,
        )

        self._run_git(
            ["git", "push", clone_url, f"HEAD:{main_branch}"],
            cwd=repo_dir,
            mask_tokens=[writer_token],
        )

        # Create staging from freshly created main
        self._run_git(
            ["git", "checkout", "-B", staging_branch, main_branch],
            cwd=repo_dir,
        )

    def _sync_docs(self, repo_dir: Path, source_repo_name: str, docs_dir: Path) -> None:
        # Create target repo directory if it doesn't exist
        target_dir = repo_dir / source_repo_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create docs directory inside target repo directory
        target_docs_dir = target_dir / "docs"
        target_docs_dir.mkdir(parents=True, exist_ok=True)

        # Check if we're dealing with legacy structure (no internal/dev folders)
        is_legacy = not any((docs_dir / persona).exists()
                            for persona in ["internal", "dev"])

        if is_legacy:
            # Legacy mode: Copy everything to internal folder
            internal_target_dir = target_docs_dir / "internal"
            internal_target_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from docs_dir to internal_target_dir
            for item in docs_dir.glob("**/*"):
                if item.is_file():
                    rel_path = item.relative_to(docs_dir)
                    dest_path = internal_target_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)

            # Create minimal dev folder with README
            dev_target_dir = target_docs_dir / "dev"
            dev_target_dir.mkdir(parents=True, exist_ok=True)
            with open(dev_target_dir / "README.md", "w") as f:
                f.write(
                    f"# {source_repo_name}\n\nPublic documentation is not available for this repository.")
        else:
            # New structure: Find which persona folder has been modified
            # We'll determine this by looking for a SUMMARY.md file
            modified_personas = []
            for persona in ["internal", "dev"]:
                source_persona_dir = docs_dir / persona
                if source_persona_dir.exists() and (source_persona_dir / "SUMMARY.md").exists():
                    modified_personas.append(persona)

            print(
                f"📝 Modified personas: {', '.join(modified_personas) or 'none'}")

            # Only copy the modified persona folders
            for persona in modified_personas:
                source_persona_dir = docs_dir / persona
                print(f"📋 Copying {persona} documentation")
                target_persona_dir = target_docs_dir / persona

                # Remove existing content in this persona folder
                if target_persona_dir.exists():
                    shutil.rmtree(target_persona_dir)

                # Copy the updated persona folder
                shutil.copytree(source_persona_dir, target_persona_dir)

            # Ensure both persona folders exist in the target
            for persona in ["internal", "dev"]:
                target_persona_dir = target_docs_dir / persona
                if not target_persona_dir.exists():
                    target_persona_dir.mkdir(exist_ok=True)
                    with open(target_persona_dir / "README.md", "w") as f:
                        f.write(
                            f"# {source_repo_name} {persona.capitalize()} Documentation\n\nThis persona documentation is not available yet.")

        # Add all changes
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
        push_url, masked_url = self._tokenized_urls(
            repo_full_name, writer_token)
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
        """Record pending review in database (like old codebase - no review_metadata column)"""
        # Always use asyncpg pool (like old codebase) to avoid schema mismatches
        # The SQLAlchemy model has review_metadata but database doesn't have this column
        if self.db_session:
            try:
                await self.db_session.execute(
                    text(
                        """
                        INSERT INTO docbook_reviews (
                            user_id, org_id, source_repo_name, docbook_full_name,
                            status, commit_message
                        ) VALUES (:user_id, :org_id, :source_repo_name, :docbook_full_name,
                                  'pending_review', :commit_message)
                        ON CONFLICT (user_id, org_id, source_repo_name) DO UPDATE
                        SET status = 'pending_review',
                            commit_message = :commit_message,
                            updated_at = NOW()
                        """
                    ),
                    {
                        "user_id": str(user_uuid),
                        "org_id": org_id,
                        "source_repo_name": source_repo_name,
                        "docbook_full_name": docbook_full_name,
                        "commit_message": commit_message,
                    },
                )
                await self.db_session.flush()
                return
            except Exception as exc:
                print(
                    f"⚠️  Failed to record pending review via SQLAlchemy: {exc}")
                # Fall back to asyncpg pool if available

        if not self.db_pool:
            return

        # Use asyncpg pool directly (like old codebase) - no review_metadata column
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO docbook_reviews (
                    user_id, org_id, source_repo_name, docbook_full_name,
                    status, commit_message, created_at
                ) VALUES ($1, $2, $3, $4, 'pending_review', $5, NOW())
                ON CONFLICT (user_id, org_id, source_repo_name) DO UPDATE
                SET status = 'pending_review', commit_message = $5, updated_at = NOW()
                """,
                user_uuid,
                org_id,
                source_repo_name,
                docbook_full_name,
                commit_message,
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
        slug = "pustak-publisher-ai-test"
        bot_name = f"{slug}[bot]"
        bot_email = f"{app_id}+{slug}[bot]@users.noreply.github.com"
        return bot_name, bot_email

    def _tokenized_urls(self, repo_full_name: str, token: str) -> Tuple[str, str]:
        url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        masked = f"https://x-access-token:***MASKED***@github.com/{repo_full_name}.git"
        return url, masked

    def _clone_repo(self, repo_full_name: str, token: str, target_dir: Path) -> None:
        clone_url, masked_url = self._tokenized_urls(repo_full_name, token)
        print(f"📚 Cloning docbook repository: {masked_url}")
        try:
            self._run_git(["git", "clone", clone_url, str(target_dir)])
        except RuntimeError as e:
            error_msg = str(e)
            if "Repository not found" in error_msg:
                print(f"❌ Repository not found: {repo_full_name}")
                print("👉 Please check that:")
                print("   1. The repository exists on GitHub")
                print("   2. The GitHub token has access to the repository")
                print("   3. The repository name is spelled correctly")
                print("   4. The organization name is correct")
            raise

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
            print(
                f"❌ Command failed: {cmd_str}\nstdout: {stdout}\nstderr: {stderr}")
            raise RuntimeError(
                stderr or stdout or f"Command failed: {cmd_str}")

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

    async def _check_repo_exists(self, org_id: str, repo_name: str, token: str) -> bool:
        """Check if a repository exists on GitHub."""
        try:
            import httpx
            url = f"https://api.github.com/repos/{org_id}/{repo_name}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Error checking if repository exists: {e}")
            return False
