"""
Docbook Publisher Service - V4 Architecture
Handles publishing generated docs to docbook repo (staging branch)
Uses user's OAuth token for transparent, user-authored commits
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import asyncpg
from typing import Optional, Dict, Any

class DocbookPublisher:
    """Publishes documentation to docbook repo using user's OAuth token"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_docbook_repo(self, user_id: str, org_id: str) -> Optional[Dict[str, str]]:
        """Get linked docbook repo for organization"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT docbook_full_name, docbook_url
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
            """, user_id, org_id)
            
            if result:
                return {
                    'full_name': result['docbook_full_name'],
                    'url': result['docbook_url']
                }
        return None
    
    async def publish_to_docbook(
        self,
        user_id: str,
        org_id: str,
        source_repo_name: str,
        docs_dir: Path,
        user_token: str,
        commit_message: str = "docs: Auto-generated documentation"
    ) -> Dict[str, Any]:
        """
        Publish generated docs to docbook repo staging branch
        
        Args:
            user_id: User ID
            org_id: Organization ID
            source_repo_name: Source repo name (e.g., alpha-testing)
            docs_dir: Path to docs directory
            user_token: User's GitHub OAuth token
            commit_message: Commit message
            
        Returns:
            Dict with status and details
        """
        
        # Get docbook repo info
        docbook = await self.get_docbook_repo(user_id, org_id)
        if not docbook:
            print(f"❌ No docbook repo linked for {org_id}")
            return {
                "status": "error",
                "message": f"No docbook repo linked for {org_id}"
            }
        
        docbook_full_name = docbook['full_name']
        tmpdir = tempfile.mkdtemp(prefix="docai_docbook_")
        
        try:
            print(f"📚 Publishing to docbook: {docbook_full_name}")
            
            # Clone docbook repo
            url = f"https://x-access-token:{user_token}@github.com/{docbook_full_name}.git"
            self._run_cmd(f"git clone {url} {tmpdir}")
            print(f"✅ Cloned docbook repo")
            
            # Configure git first
            self._run_cmd(
                "git config user.email 'docai@bots.local' && git config user.name 'docai-bot'",
                cwd=tmpdir
            )
            
            # Check if repo is empty
            try:
                self._run_cmd("git fetch origin", cwd=tmpdir)
                branches = self._run_cmd("git branch -r", cwd=tmpdir, capture_output=True).strip()
                is_empty = not branches or "origin/" not in branches
            except:
                is_empty = True
            
            if is_empty:
                print(f"📝 Repo is empty, creating initial commit...")
                # Create initial README
                readme_path = Path(tmpdir) / "README.md"
                readme_path.write_text(f"# {docbook_full_name}\n\nDocumentation repository for {docbook_full_name}\n")
                
                # Add and commit
                self._run_cmd("git add README.md", cwd=tmpdir)
                self._run_cmd("git commit -m 'Initial commit'", cwd=tmpdir)
                
                # Push to main
                self._run_cmd(
                    f"git push https://x-access-token:{user_token}@github.com/{docbook_full_name}.git HEAD:main",
                    cwd=tmpdir
                )
                print(f"✅ Created initial commit and pushed to main")
                
                # Now create staging from main
                self._run_cmd("git checkout -b staging", cwd=tmpdir)
                print(f"✅ Created staging branch")
            else:
                # Repo has content, try to checkout staging
                try:
                    self._run_cmd("git checkout staging", cwd=tmpdir)
                    print(f"✅ Checked out existing staging branch")
                except:
                    # Create staging branch from main
                    self._run_cmd("git checkout main", cwd=tmpdir)
                    self._run_cmd("git checkout -b staging", cwd=tmpdir)
                    print(f"✅ Created staging branch from main")
            
            # Create source repo folder structure
            repo_folder = Path(tmpdir) / source_repo_name
            repo_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy docs to repo folder
            if docs_dir.exists():
                for item in docs_dir.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, repo_folder / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, repo_folder / item.name)
                print(f"✅ Copied docs to {source_repo_name}/ folder")
            
            # Add changes
            self._run_cmd(f"git add {source_repo_name}/", cwd=tmpdir)
            
            # Check if there are changes
            status = self._run_cmd("git status --porcelain", cwd=tmpdir, capture_output=True).strip()
            
            if not status:
                print(f"ℹ️  No changes to commit")
                return {
                    "status": "no_changes",
                    "message": "No changes to commit",
                    "docbook_repo": docbook_full_name,
                    "branch": "staging"
                }
            
            # Commit
            full_commit_msg = f"{commit_message} ({source_repo_name})"
            self._run_cmd(f"git commit -m '{full_commit_msg}'", cwd=tmpdir)
            print(f"✅ Committed changes")
            
            # Push to staging
            self._run_cmd(
                f"git push https://x-access-token:{user_token}@github.com/{docbook_full_name}.git HEAD:staging",
                cwd=tmpdir
            )
            print(f"✅ Pushed to staging branch")
            
            # Store in database as pending review
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO docbook_reviews (
                        user_id, org_id, source_repo_name, docbook_full_name,
                        status, commit_message, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (user_id, org_id, source_repo_name) DO UPDATE
                    SET status = 'pending_review', commit_message = $6, created_at = NOW()
                """,
                user_id, org_id, source_repo_name, docbook_full_name, 'pending_review', full_commit_msg
                )
            
            print(f"✅ Stored in database as pending review")
            
            return {
                "status": "published_to_staging",
                "message": f"Documentation published to {docbook_full_name}/staging",
                "docbook_repo": docbook_full_name,
                "source_repo": source_repo_name,
                "branch": "staging",
                "review_url": f"{docbook['url']}/compare/main...staging",
                "commit_message": full_commit_msg
            }
            
        except Exception as e:
            print(f"❌ Error publishing to docbook: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "docbook_repo": docbook_full_name
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def _run_cmd(self, cmd: str, cwd: str = None, capture_output: bool = False) -> str:
        """Run shell command"""
        print(f"RUN: {cmd}")
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, capture_output=True, text=True)
                return result.stdout
            else:
                subprocess.run(cmd, shell=True, check=True, cwd=cwd)
                return ""
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            raise
