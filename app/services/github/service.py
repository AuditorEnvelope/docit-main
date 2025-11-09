from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import tempfile
import shutil
import subprocess

from app.core.config import settings
from app.services.docbook.publisher import DocbookPublisher
from app.services.github.app_installation_service import AppInstallationService
from app.utils.github_dual_app import GitHubDualAppHelper

class GitHubService:
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.dual_app = GitHubDualAppHelper()
        self.installation_service = (
            AppInstallationService(db_pool=db_pool) if db_pool else None
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

        # Create temporary directory for the repository
        with tempfile.TemporaryDirectory(prefix="docai_") as tmp_dir:
            try:
                # Clone the repository
                await self.clone_repository(repo_name, tmp_dir, commit_sha)
                
                # Get changed files
                changed_files = self.get_changed_files(tmp_dir, commit_sha)
                
                # Generate documentation
                docs_dir = await self.generate_documentation(tmp_dir, repo_name, commit_sha, changed_files)
                
                # Publish to docbook
                if docs_dir:
                    await self.publish_to_docbook(repo, docs_dir, commit_sha)
                    
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
        subprocess.run(["git", "clone", "--depth", "1", url, target_dir], check=True)
        
        # Checkout specific commit
        subprocess.run(["git", "checkout", commit_sha], cwd=target_dir, check=True)

    def get_changed_files(self, repo_path: str, commit_sha: str) -> list:
        """Get list of changed files in a commit"""
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout.splitlines()

    async def generate_documentation(self, repo_path: str, repo_name: str, commit_sha: str, changed_files: list) -> Optional[Path]:
        """Generate documentation for the repository"""
        # This is where you would integrate with your documentation generation logic
        # For now, we'll just create a simple markdown file
        docs_dir = Path(repo_path) / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # Create a simple README
        with open(docs_dir / "README.md", "w") as f:
            f.write(f"# {repo_name}\n\n")
            f.write(f"Documentation for commit `{commit_sha}`\n\n")
            f.write("## Changed Files\n\n")
            for file in changed_files:
                f.write(f"- {file}\n")
        
        return docs_dir

    async def publish_to_docbook(self, repo: Dict[str, Any], docs_dir: Path, commit_sha: str) -> bool:
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
                await self.store_installation(org_id, app_id, installation_id)
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

    async def store_installation(self, org_id: str, app_id: int, installation_id: int) -> None:
        """Store GitHub App installation details"""
        if not self.db_pool:
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO github_installations (org_id, app_id, installation_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (org_id, app_id) DO UPDATE
                SET installation_id = EXCLUDED.installation_id,
                    updated_at = NOW()
            """,
                org_id,
                app_id,
                installation_id,
            )

    async def remove_installation(self, org_id: str, app_id: int) -> None:
        """Remove GitHub App installation"""
        if not self.db_pool:
            return
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM github_installations WHERE org_id = $1 AND app_id = $2",
                org_id,
                app_id,
            )
