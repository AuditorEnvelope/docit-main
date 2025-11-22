import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.docbook.publisher import DocbookPublisher
from app.services.documentation.comprehensive import ComprehensiveDocBuilder
from app.services.documentation.quality_integration import check_documentation_quality
from app.services.documentation.quality_checker import DocumentationQualityChecker
from app.services.github.app_installation_service import AppInstallationService
from app.services.github.change_analysis import smart_analyze_change
from app.utils.github_dual_app import GitHubDualAppHelper

class GitHubService:
    def __init__(self, db_pool=None, db_session: Optional[AsyncSession] = None):
        if db_pool is None and db_session is None:
            raise ValueError("GitHubService requires db_pool or db_session")

        self.db_pool = db_pool
        self.db_session = db_session
        self.dual_app = GitHubDualAppHelper()
        self.installation_service = (
            AppInstallationService(db_pool=db_pool, db_session=db_session)
            if (db_pool or db_session)
            else None
        )

    async def handle_push_event(self, payload: Dict[str, Any]) -> None:
        """Handle GitHub push event"""
        # Extract relevant information from payload
        repo = payload.get("repository", {})
        commits = payload.get("commits", [])
        ref = payload.get("ref", "")
        
        # Skip if no commits or not to the main branch
        if not commits or "main" not in ref and "master" not in ref:
            return

        # Process each commit
        for commit in commits:
            await self.process_commit(repo, commit, ref)

    async def process_commit(self, repo: Dict[str, Any], commit: Dict[str, Any], ref: str) -> None:
        """Process a single commit"""
        repo_name = repo.get("full_name")
        commit_sha = commit.get("id")
        
        if not repo_name or not commit_sha:
            return

        changed_files, removed_files = self._extract_commit_changes(commit)

        if not changed_files and not removed_files:
            print("ℹ️  No file changes detected in commit, skipping")
            return

        # Create temporary directory for the repository
        with tempfile.TemporaryDirectory(prefix="docai_") as tmp_dir:
            try:
                # Clone the repository
                await self.clone_repository(repo_name, tmp_dir, commit_sha)
                
                # Analyze change significance before generating docs
                analysis = await self._analyze_change_significance(
                    repo=repo,
                    commit=commit,
                    ref=ref,
                    repo_path=tmp_dir,
                    changed_files=changed_files,
                    removed_files=removed_files,
                )

                if not analysis.get("is_significant"):
                    print(
                        "ℹ️  Skipping documentation generation - change not significant:",
                        analysis.get("reason", "no reason provided"),
                    )
                    return

                # Generate documentation
                docs_dir, generation_meta = await self.generate_documentation(
                    repo_dict=repo,
                    repo_path=tmp_dir,
                    repo_full_name=repo_name,
                    commit_sha=commit_sha,
                    changed_files=changed_files,
                    change_analysis=analysis,
                )

                # Publish to docbook
                if docs_dir:
                    await self.publish_to_docbook(
                        repo,
                        docs_dir,
                        commit_sha,
                        generation_meta=generation_meta,
                    )
                    
            except Exception as e:
                print(f"Error processing commit: {e}")
                # Add proper error handling and logging

    async def clone_repository(self, repo_name: str, target_dir: str, commit_sha: str) -> None:
        """Clone a specific commit from a repository"""
        # Get installation token for the repository
        org = repo_name.split("/")[0]
        reader_app_id = (
            int(self.dual_app.reader_app_id)
            if getattr(self.dual_app, "reader_app_id", None)
            else None
        )
        installation_id = await self.get_installation_id(org, reader_app_id)
        token = await self.dual_app.get_reader_token(installation_id)

        # Clone the repository
        url = f"https://x-access-token:{token}@github.com/{repo_name}.git"
        subprocess.run(
            ["git", "clone", "--depth", "50", "--single-branch", url, target_dir],
            check=True,
        )
        
        # Checkout specific commit
        subprocess.run(["git", "checkout", commit_sha], cwd=target_dir, check=True)

    def get_changed_files(self, repo_path: str, commit_sha: str) -> list:
        """Deprecated: left for compatibility (now using payload diff)."""
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return [line for line in result.stdout.splitlines() if line]

    async def generate_documentation(
        self,
        *,
        repo_dict: Dict[str, Any],
        repo_path: str,
        repo_full_name: str,
        commit_sha: str,
        changed_files: list,
        change_analysis: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Path], Dict[str, Any]]:
        """Generate comprehensive documentation for the repository."""

        persona = repo_dict.get("doc_persona") or "internal"
        repo_path_obj = Path(repo_path)
        docs_dir = repo_path_obj / "docs"

        self._log_build_start(repo_full_name, persona)

        # Initial quality report (pre-generation)
        initial_quality = await check_documentation_quality(repo_path_obj)
        self._log_quality_report(initial_quality)

        # Generate documentation via the comprehensive builder
        analysis_payload = change_analysis or {}
        builder = ComprehensiveDocBuilder(repo_path_obj, persona)
        docs_output = await builder.build()

        # Run quality checker post-generation
        quality_checker = DocumentationQualityChecker()
        docs_payload = {key: value or "" for key, value in (docs_output or {}).items()}
        readme_path = repo_path_obj / "README.md"
        if readme_path.exists():
            docs_payload.setdefault("readme", readme_path.read_text())

        codebase_size = await self._calculate_codebase_stats(repo_path)
        quality_scores = await quality_checker.evaluate_documentation(
            repo_full_name,
            codebase_size,
            docs_payload,
        )

        metadata = {
            "initial_quality": initial_quality,
            "post_quality": {
                "overall": quality_scores.overall_score,
                "needs_regeneration": quality_scores.get_low_quality_docs(),
            },
            "analysis": analysis_payload,
        }

        self._log_build_complete(metadata)

        return docs_dir, metadata

    async def _analyze_change_significance(
        self,
        *,
        repo: Dict[str, Any],
        commit: Dict[str, Any],
        ref: str,
        repo_path: str,
        changed_files: list[str],
        removed_files: list[str],
    ) -> Dict[str, Any]:
        """Run legacy smart analyzer with heuristic fallback."""

        payload = {
            "repository": repo,
            "commits": [commit],
            "ref": ref,
            "after": commit.get("id"),
            "_org_id": repo.get("owner", {}).get("login"),
            "_db_pool": self.db_pool,
        }

        analysis = smart_analyze_change(
            payload,
            repo_path,
            changed_files,
            removed_files,
        )

        if not analysis:
            analysis = self._heuristic_analysis(commit, ref, changed_files, removed_files)

        significance_threshold = getattr(settings, "DOC_SIGNIFICANCE_THRESHOLD", 7)
        significance_score = analysis.get("significance", 0)
        is_significant = analysis.get("is_significant")
        if is_significant is None:
            is_significant = significance_score >= significance_threshold

        analysis.update(
            {
                "is_significant": is_significant,
                "changed_files": changed_files,
                "removed_files": removed_files,
                "ref": ref,
            }
        )

        return analysis

    @staticmethod
    def build_commit_event_data(
        payload: Dict[str, Any],
        *,
        webhook_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Convert a GitHub push payload into commit bus event data (like old codebase)."""

        repository = payload.get("repository") or {}
        repo_full_name = repository.get("full_name")
        commits = payload.get("commits") or []

        if not repo_full_name or not commits:
            return None

        commit = commits[-1]
        commit_sha = commit.get("id")
        if not commit_sha:
            return None

        timestamp = datetime.utcnow()
        timestamp_str = commit.get("timestamp")
        if isinstance(timestamp_str, str):
            try:
                parsed = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp = parsed.replace(tzinfo=None)
            except ValueError:
                pass

        files_changed = []
        for path in (commit.get("added") or []):
            files_changed.append({"path": path, "status": "added"})
        for path in (commit.get("modified") or []):
            files_changed.append({"path": path, "status": "modified"})
        for path in (commit.get("removed") or []):
            files_changed.append({"path": path, "status": "deleted"})

        branch_ref = payload.get("ref") or "refs/heads/main"
        branch = branch_ref.replace("refs/heads/", "")

        # Extract installation_id from payload (like old codebase)
        installation = payload.get("installation", {})
        installation_id = installation.get("id") if isinstance(installation, dict) else None

        metadata: Dict[str, Any] = {"payload": payload}
        if webhook_context:
            metadata["webhook_context"] = webhook_context

        return {
            "repo_id": repo_full_name,
            "commit_sha": commit_sha,
            "parent_sha": [payload.get("before")] if payload.get("before") else [],
            "author_name": (commit.get("author") or {}).get("name", "unknown"),
            "author_email": (commit.get("author") or {}).get("email", "unknown@example.com"),
            "timestamp": timestamp,
            "branch": branch,
            "files_changed": files_changed,
            "commit_message": commit.get("message", ""),
            "push_id": str(payload.get("push_id")) if payload.get("push_id") else None,
            "source": "github",
            "metadata": metadata,
            "user_id": (webhook_context or {}).get("user_id"),
            "org_id": (webhook_context or {}).get("org_id") or repo_full_name.split("/")[0],
            "github_token_id": (webhook_context or {}).get("github_token_id"),
            "installation_id": installation_id,
        }

    def _heuristic_analysis(
        self,
        commit: Dict[str, Any],
        ref: str,
        changed_files: list[str],
        removed_files: list[str],
    ) -> Dict[str, Any]:
        doc_extensions = {".md", ".rst", ".adoc", ".txt"}

        def is_doc_path(path: str) -> bool:
            lowered = path.lower()
            return lowered.startswith("docs/") or Path(lowered).suffix in doc_extensions

        code_changes = [path for path in changed_files if not is_doc_path(path)]
        docs_only = bool(changed_files) and not code_changes

        commit_message = (commit.get("message") or "").lower()
        keywords = {
            "feat": 3,
            "feature": 3,
            "fix": 2,
            "bug": 2,
            "refactor": 2,
            "breaking": 4,
            "security": 4,
            "chore": -1,
            "docs": 1,
        }

        structural_indicators = [
            any(part in path.lower() for part in ("auth", "payment", "database", "schema"))
            for path in code_changes
        ]

        score = min(10, len(code_changes) * 1.5)
        for word, weight in keywords.items():
            if word in commit_message:
                score += weight

        if removed_files:
            score += 1

        if any(structural_indicators):
            score += 2

        score = max(0, min(score, 10))

        reason = (
            "Docs-only change" if docs_only and not removed_files
            else "High impact keywords detected" if any(k in commit_message for k in keywords)
            else "Multiple code files changed" if len(code_changes) > 5
            else "Structural component updated" if any(structural_indicators)
            else "Removed files" if removed_files
            else "Below significance threshold"
        )

        return {
            "title": commit.get("id", "change")[:12],
            "type": "auto",
            "significance": score,
            "impact_scope": ["docs"] if docs_only else [],
            "reason": reason,
        }

    def _extract_commit_changes(self, commit: Dict[str, Any]) -> Tuple[list[str], list[str]]:
        """Collect added/modified/removed files from commit payload."""

        added = commit.get("added") or []
        modified = commit.get("modified") or []
        removed = commit.get("removed") or []

        changed = sorted({*added, *modified})
        return changed, list(removed)

    async def _calculate_codebase_stats(self, repo_path: str) -> Dict[str, int]:
        """Approximate codebase size by language for quality evaluation."""
        language_counts: Dict[str, int] = {}
        for path in Path(repo_path).rglob("*"):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            language = {
                ".py": "Python",
                ".js": "JavaScript",
                ".ts": "TypeScript",
                ".go": "Go",
                ".rb": "Ruby",
                ".java": "Java",
                ".rs": "Rust",
                ".php": "PHP",
                ".cs": "C#",
                ".cpp": "C++",
                ".c": "C",
            }.get(ext)

            if not language:
                continue

            try:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    line_count = sum(1 for _ in handle)
            except OSError:
                continue

            language_counts[language] = language_counts.get(language, 0) + line_count

        return language_counts

    def _log_build_start(self, repo_full_name: str, persona: str) -> None:
        print("=" * 80)
        print(f"📦 Starting comprehensive documentation build for {repo_full_name}")
        print(f"👤 Persona: {persona}")
        print("=" * 80)

    def _log_quality_report(self, quality: Dict[str, Any]) -> None:
        print(f"📋 Quality Report: {json.dumps(quality, indent=2)}")

    def _log_build_complete(self, metadata: Dict[str, Any]) -> None:
        print("✅ Comprehensive documentation build complete!")
        print(f"📊 Post-generation quality: {metadata['post_quality']}")

    async def publish_to_docbook(
        self,
        repo: Dict[str, Any],
        docs_dir: Path,
        commit_sha: str,
        *,
        generation_meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish documentation to docbook"""
        try:
            publisher = DocbookPublisher(self.db_pool, dual_app=self.dual_app)
            org_id = repo["owner"]["login"]

            # Get writer token
            writer_app_id = (
                int(self.dual_app.writer_app_id)
                if getattr(self.dual_app, "writer_app_id", None)
                else None
            )
            installation_id = await self.get_installation_id(org_id, writer_app_id)
            writer_token = await self.dual_app.get_writer_token(installation_id)
            
            # Publish to docbook
            result = await publisher.publish_to_docbook(
                user_id="system",  # or get from auth
                org_id=org_id,
                source_repo_name=repo["name"],
                docs_dir=docs_dir,
                writer_token=writer_token,
                commit_message=f"docs: Auto-generated documentation for {commit_sha[:7]}",
                commit_sha=commit_sha,
                installation_id=installation_id,
            )

            if generation_meta is not None:
                result["generation_meta"] = generation_meta
            return result.get("status") not in {"error"}
        except Exception as e:
            print(f"Error publishing to docbook: {e}")
            return False

    async def handle_installation_event(self, payload: Dict[str, Any]) -> None:
        """Handle GitHub App installation events"""
        action = payload.get("action")
        installation = payload.get("installation", {})
        repositories = payload.get("repositories", [])

        if action in ["created", "deleted"]:
            org_id = installation.get("account", {}).get("login")
            installation_id = installation.get("id")
            app_id = installation.get("app_id")
            repository_selection = installation.get("repository_selection", "all")

            if not org_id or installation_id is None or app_id is None:
                return

            if action == "created":
                await self.store_installation(installation)
                if self.installation_service:
                    await self.installation_service.store_installation(
                        org_id=org_id,
                        app_id=app_id,
                        installation_id=installation_id,
                        repository_selection=repository_selection,
                        repositories=repositories,
                    )
            else:
                await self.remove_installation(org_id, app_id)
                if self.installation_service:
                    await self.installation_service.remove_installation(org_id, app_id)

    async def handle_installation_repositories_event(self, payload: Dict[str, Any]) -> None:
        """Handle installation repositories added/removed events."""
        if not self.installation_service:
            return

        installation = payload.get("installation", {})
        org_id = installation.get("account", {}).get("login")
        app_id = installation.get("app_id")

        if not org_id or app_id is None:
            return

        added = payload.get("repositories_added", [])
        removed = payload.get("repositories_removed", [])

        if added:
            await self.installation_service.add_repositories(org_id, app_id, added)
        if removed:
            await self.installation_service.remove_repositories(org_id, app_id, removed)

    async def get_installation_id(self, org_id: str, app_id: Optional[int] = None) -> Optional[int]:
        """Get installation ID for an organization/app pair."""
        if self.db_session:
            params = {"org_id": org_id}
            query = """
                SELECT installation_id
                FROM github_installations
                WHERE org_id = :org_id
            """
            if app_id is not None:
                query += " AND app_id = :app_id"
                params["app_id"] = app_id

            query += " ORDER BY updated_at DESC NULLS LAST LIMIT 1"

            result = await self.db_session.execute(text(query), params)
            row = result.first()
            if row:
                return row[0]
            return None

        if not self.db_pool:
            return None

        async with self.db_pool.acquire() as conn:
            if app_id is not None:
                row = await conn.fetchrow(
                    """
                    SELECT installation_id
                    FROM github_installations
                    WHERE org_id = $1 AND app_id = $2
                    ORDER BY updated_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    org_id,
                    app_id,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT installation_id
                    FROM github_installations
                    WHERE org_id = $1
                    ORDER BY updated_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    org_id,
                )
            return row["installation_id"] if row else None

    async def store_installation(self, installation: Dict[str, Any]) -> None:
        """Store GitHub App installation details."""
        account = installation.get("account") or {}
        org_id = account.get("login")
        installation_id = installation.get("id")
        app_id = installation.get("app_id")

        if not org_id or installation_id is None or app_id is None:
            return

        account_type = (account.get("type") or installation.get("target_type") or "Organization")[:50]
        target_type = (installation.get("target_type") or account_type)[:50]
        account_id = account.get("id") or 0
        account_login = account.get("login") or org_id
        permissions = installation.get("permissions") or {}
        events = installation.get("events") or []
        suspended_by_info = installation.get("suspended_by")
        suspended_by = None
        if isinstance(suspended_by_info, dict):
            suspended_by = suspended_by_info.get("login") or suspended_by_info.get("id")
        elif isinstance(suspended_by_info, str):
            suspended_by = suspended_by_info
        suspended_at = installation.get("suspended_at")
        is_active = not bool(suspended_at or suspended_by)

        metadata_keys = {
            "id",
            "app_id",
            "account",
            "account_type",
            "target_type",
            "permissions",
            "events",
            "suspended_by",
            "suspended_at",
            "repositories",
            "repository_selection",
        }
        metadata = {
            key: value
            for key, value in installation.items()
            if key not in metadata_keys
        }

        params = {
            "org_id": org_id,
            "app_id": app_id,
            "installation_id": installation_id,
            "account_type": account_type,
            "account_id": account_id,
            "account_login": account_login,
            "target_type": target_type,
            "permissions": json.dumps(permissions),
            "events": json.dumps(events),
            "is_active": is_active,
            "suspended_at": suspended_at,
            "suspended_by": suspended_by,
            "metadata": json.dumps(metadata),
        }

        if self.db_session:
            await self.db_session.execute(
                text(
                    """
                    INSERT INTO github_installations (
                        org_id,
                        app_id,
                        installation_id,
                        account_type,
                        account_id,
                        account_login,
                        target_type,
                        permissions,
                        events,
                        is_active,
                        suspended_at,
                        suspended_by,
                        metadata,
                        created_at,
                        updated_at
                    ) VALUES (
                        :org_id,
                        :app_id,
                        :installation_id,
                        :account_type,
                        :account_id,
                        :account_login,
                        :target_type,
                        CAST(:permissions AS JSONB),
                        CAST(:events AS JSONB),
                        :is_active,
                        :suspended_at,
                        :suspended_by,
                        CAST(:metadata AS JSONB),
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (org_id, app_id) DO UPDATE SET
                        installation_id = EXCLUDED.installation_id,
                        account_type = EXCLUDED.account_type,
                        account_id = EXCLUDED.account_id,
                        account_login = EXCLUDED.account_login,
                        target_type = EXCLUDED.target_type,
                        permissions = EXCLUDED.permissions,
                        events = EXCLUDED.events,
                        is_active = EXCLUDED.is_active,
                        suspended_at = EXCLUDED.suspended_at,
                        suspended_by = EXCLUDED.suspended_by,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                params,
            )
            await self.db_session.flush()
            return

        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO github_installations (
                    org_id,
                    app_id,
                    installation_id,
                    account_type,
                    account_id,
                    account_login,
                    target_type,
                    permissions,
                    events,
                    is_active,
                    suspended_at,
                    suspended_by,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7,
                    $8::jsonb,
                    $9::jsonb,
                    $10,
                    $11,
                    $12,
                    $13::jsonb,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (org_id, app_id) DO UPDATE SET
                    installation_id = EXCLUDED.installation_id,
                    account_type = EXCLUDED.account_type,
                    account_id = EXCLUDED.account_id,
                    account_login = EXCLUDED.account_login,
                    target_type = EXCLUDED.target_type,
                    permissions = EXCLUDED.permissions,
                    events = EXCLUDED.events,
                    is_active = EXCLUDED.is_active,
                    suspended_at = EXCLUDED.suspended_at,
                    suspended_by = EXCLUDED.suspended_by,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                org_id,
                app_id,
                installation_id,
                account_type,
                account_id,
                account_login,
                target_type,
                json.dumps(permissions),
                json.dumps(events),
                is_active,
                suspended_at,
                suspended_by,
                json.dumps(metadata),
            )

    async def remove_installation(self, org_id: str, app_id: int) -> None:
        """Remove GitHub App installation"""
        if self.db_session:
            await self.db_session.execute(
                text(
                    """
                    UPDATE github_installations
                    SET is_active = FALSE,
                        deleted_at = NOW(),
                        updated_at = NOW()
                    WHERE org_id = :org_id AND app_id = :app_id
                    """
                ),
                {"org_id": org_id, "app_id": app_id},
            )
            await self.db_session.flush()
            return

        if not self.db_pool:
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE github_installations
                SET is_active = FALSE,
                    deleted_at = NOW(),
                    updated_at = NOW()
                WHERE org_id = $1 AND app_id = $2
                """,
                org_id,
                app_id,
            )
