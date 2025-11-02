"""
Doc-Maintainer Pusher - Push docs to centralized doc-maintainer repo
Instead of pushing to source repo, push to doc-maintainer with review workflow
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import asyncpg

from utilities.github_app_helper import get_github_app_helper

logger = logging.getLogger(__name__)

class DocMaintainerPusher:
    """Push documentation to doc-maintainer repo with review workflow"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.github_app = get_github_app_helper()
    
    async def push_docs_to_maintainer(
        self,
        user_id: str,
        org_id: str,
        repo_name: str,
        commit_sha: str,
        doc_persona: str,
        installation_id: int,
        docs_path: Path,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Push documentation to doc-maintainer repo instead of source repo
        Creates review branch and PR for approval workflow
        
        Args:
            user_id: User UUID
            org_id: Organization name
            repo_name: Source repository name
            commit_sha: Commit SHA that triggered generation
            doc_persona: Documentation persona (internal|developer)
            installation_id: GitHub App installation ID
            docs_path: Path to generated docs directory
            token: GitHub token for authentication
            
        Returns:
            Review details {review_id, pr_number, pr_url, ...} or None
        """
        try:
            logger.info(f"📚 Pushing docs to doc-maintainer for {org_id}/{repo_name}")
            
            # Step 1: Ensure doc-maintainer repo exists
            doc_maintainer = await self._ensure_doc_maintainer_repo(
                user_id,
                org_id,
                installation_id
            )
            
            if not doc_maintainer:
                logger.error(f"❌ Could not get doc-maintainer repo")
                return None
            
            # Step 2: Create review branch name
            review_branch = f"docai-review/{repo_name}/{commit_sha[:8]}"
            logger.info(f"🌿 Creating review branch: {review_branch}")
            
            # Step 3: Clone doc-maintainer repo
            tmpdir = tempfile.mkdtemp(prefix="docai_maintainer_")
            try:
                await self._clone_doc_maintainer(
                    doc_maintainer["full_name"],
                    token,
                    tmpdir
                )
                
                # Step 4: Create review branch
                await self._create_review_branch(tmpdir, review_branch)
                
                # Step 5: Copy docs to appropriate folder
                await self._copy_docs_to_folder(
                    tmpdir,
                    repo_name,
                    doc_persona,
                    docs_path
                )
                
                # Step 6: Commit changes
                await self._commit_docs(
                    tmpdir,
                    repo_name,
                    commit_sha,
                    doc_persona
                )
                
                # Step 7: Push review branch
                await self._push_review_branch(
                    tmpdir,
                    review_branch,
                    token
                )
                
                # Step 8: Create PR
                inst_token = await self.github_app.get_installation_token(installation_id)
                if not inst_token:
                    logger.error(f"❌ Could not get installation token")
                    return None
                
                pr_data = await self.github_app.create_pull_request(
                    org_id,
                    "doc-maintainer",
                    inst_token,
                    title=f"📚 Docs: {repo_name} - {doc_persona.capitalize()} ({commit_sha[:8]})",
                    body=self._generate_pr_description(repo_name, doc_persona, commit_sha),
                    head_branch=review_branch,
                    base_branch="staging"
                )
                
                if not pr_data:
                    logger.error(f"❌ Failed to create PR")
                    return None
                
                # Step 9: Store review in database
                review_id = await self._store_review_in_db(
                    user_id,
                    org_id,
                    repo_name,
                    commit_sha,
                    doc_persona,
                    pr_data,
                    review_branch
                )
                
                logger.info(f"✅ Created review PR #{pr_data['number']}")
                
                return {
                    'review_id': review_id,
                    'pr_number': pr_data['number'],
                    'pr_url': pr_data['url'],
                    'review_branch': review_branch,
                    'status': 'pending',
                    'doc_persona': doc_persona
                }
                
            finally:
                # Cleanup
                shutil.rmtree(tmpdir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"❌ Error pushing docs to maintainer: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _ensure_doc_maintainer_repo(
        self,
        user_id: str,
        org_id: str,
        installation_id: int
    ) -> Optional[Dict[str, Any]]:
        """Ensure doc-maintainer repo exists"""
        try:
            async with self.db_pool.acquire() as conn:
                # Check if already in database
                row = await conn.fetchrow("""
                    SELECT repo_full_name, repo_url
                    FROM doc_maintainer_repos
                    WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
                """, user_id, org_id)
                
                if row:
                    return {
                        'full_name': row['repo_full_name'],
                        'url': row['repo_url']
                    }
                
                # Create new doc-maintainer repo
                repo_data = await self.github_app.create_doc_maintainer_repo(
                    org_id,
                    installation_id
                )
                
                if repo_data:
                    # Store in database
                    await conn.execute("""
                        INSERT INTO doc_maintainer_repos 
                        (user_id, org_id, repo_name, repo_full_name, repo_url, is_active)
                        VALUES ($1, $2, $3, $4, $5, TRUE)
                        ON CONFLICT (user_id, org_id) DO UPDATE
                        SET is_active = TRUE, updated_at = NOW()
                    """,
                    user_id, org_id, "doc-maintainer", repo_data['full_name'],
                    repo_data['url']
                    )
                
                return repo_data
                
        except Exception as e:
            logger.error(f"❌ Error ensuring doc-maintainer repo: {e}")
            return None
    
    async def _clone_doc_maintainer(
        self,
        repo_full_name: str,
        token: str,
        target_dir: str
    ) -> bool:
        """Clone doc-maintainer repo"""
        try:
            url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
            subprocess.run(
                f"git clone {url} {target_dir}",
                shell=True,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Cloned doc-maintainer repo")
            return True
        except Exception as e:
            logger.error(f"❌ Error cloning doc-maintainer: {e}")
            return False
    
    async def _create_review_branch(
        self,
        repo_dir: str,
        branch_name: str
    ) -> bool:
        """Create review branch"""
        try:
            subprocess.run(
                f"cd {repo_dir} && git checkout -b {branch_name}",
                shell=True,
                check=True,
                capture_output=True
            )
            logger.info(f"✅ Created review branch: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating review branch: {e}")
            return False
    
    async def _copy_docs_to_folder(
        self,
        repo_dir: str,
        repo_name: str,
        doc_persona: str,
        docs_path: Path
    ) -> bool:
        """Copy docs to appropriate folder in doc-maintainer"""
        try:
            # Create folder structure: docs/{repo_name}/{persona}/
            target_dir = Path(repo_dir) / "docs" / repo_name / doc_persona
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all docs
            if docs_path.exists():
                for doc_file in docs_path.glob("**/*"):
                    if doc_file.is_file():
                        relative_path = doc_file.relative_to(docs_path)
                        target_file = target_dir / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(doc_file, target_file)
            
            logger.info(f"✅ Copied docs to {repo_name}/{doc_persona}")
            return True
        except Exception as e:
            logger.error(f"❌ Error copying docs: {e}")
            return False
    
    async def _commit_docs(
        self,
        repo_dir: str,
        repo_name: str,
        commit_sha: str,
        doc_persona: str
    ) -> bool:
        """Commit docs to review branch"""
        try:
            subprocess.run(
                f"cd {repo_dir} && git add -A",
                shell=True,
                check=True,
                capture_output=True
            )
            
            commit_msg = f"docs: {repo_name} - {doc_persona} ({commit_sha[:8]})"
            subprocess.run(
                f'cd {repo_dir} && git commit -m "{commit_msg}"',
                shell=True,
                check=True,
                capture_output=True
            )
            
            logger.info(f"✅ Committed docs")
            return True
        except Exception as e:
            logger.error(f"❌ Error committing docs: {e}")
            return False
    
    async def _push_review_branch(
        self,
        repo_dir: str,
        branch_name: str,
        token: str
    ) -> bool:
        """Push review branch"""
        try:
            subprocess.run(
                f"cd {repo_dir} && git push origin {branch_name}",
                shell=True,
                check=True,
                capture_output=True,
                env={**os.environ, "GIT_ASKPASS": "echo", "GIT_PASSWORD": token}
            )
            
            logger.info(f"✅ Pushed review branch")
            return True
        except Exception as e:
            logger.error(f"❌ Error pushing review branch: {e}")
            return False
    
    async def _store_review_in_db(
        self,
        user_id: str,
        org_id: str,
        repo_name: str,
        commit_sha: str,
        doc_persona: str,
        pr_data: Dict[str, Any],
        review_branch: str
    ) -> Optional[str]:
        """Store review in database"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get repository ID
                repo_row = await conn.fetchrow("""
                    SELECT id FROM repositories
                    WHERE user_id = $1 AND org_id = $2 AND repo_name = $3
                """, user_id, org_id, repo_name)
                
                if not repo_row:
                    logger.warning(f"⚠️  Repository not found in DB: {repo_name}")
                    return None
                
                repo_id = repo_row['id']
                
                # Store review
                review_id = await conn.fetchval("""
                    INSERT INTO doc_generation_reviews
                    (repository_id, commit_sha, pr_number, pr_url, review_branch, 
                     doc_persona, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, 'pending', NOW())
                    RETURNING id
                """,
                repo_id, commit_sha, pr_data['number'], pr_data['url'],
                review_branch, doc_persona
                )
                
                logger.info(f"✅ Stored review in DB: {review_id}")
                return str(review_id)
        except Exception as e:
            logger.error(f"❌ Error storing review in DB: {e}")
            return None
    
    def _generate_pr_description(
        self,
        repo_name: str,
        doc_persona: str,
        commit_sha: str
    ) -> str:
        """Generate PR description"""
        persona_desc = {
            'internal': 'Internal documentation (detailed, for staff engineers)',
            'developer': 'Developer documentation (public-safe, for external partners)'
        }
        
        return f"""
## 📚 Documentation Review

**Repository:** `{repo_name}`
**Type:** {persona_desc.get(doc_persona, 'Unknown')}
**Commit:** `{commit_sha}`

### 📋 What's Included

- ✅ README.md / SUMMARY.md
- ✅ Architecture documentation
- ✅ Workflow documentation
- ✅ API documentation
- ✅ Change documentation

### 🔍 Review Checklist

- [ ] Documentation is accurate
- [ ] Code examples are correct
- [ ] No sensitive information exposed (for developer docs)
- [ ] Formatting is consistent
- [ ] Links are working

### 📝 Notes

Please review the generated documentation and approve if it looks good.
You can edit files directly in this PR if needed.

---

*Generated by Lekhak AI - Doc-Maintainer*
"""


# Singleton instance
_doc_maintainer_pusher = None

async def get_doc_maintainer_pusher(db_pool: asyncpg.Pool) -> DocMaintainerPusher:
    """Get or create doc-maintainer pusher instance"""
    global _doc_maintainer_pusher
    if _doc_maintainer_pusher is None:
        _doc_maintainer_pusher = DocMaintainerPusher(db_pool)
    return _doc_maintainer_pusher
