"""
Docbook Publisher Service - V4 Architecture
Handles publishing generated docs to docbook repo (staging branch)
Uses GitHub App for authentication
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

import asyncpg
import uuid

from core.app_installation_service import AppInstallationService
from utilities.github_dual_app_helper import get_github_dual_app_helper

class DocbookPublisher:
    """Publishes documentation to docbook repo using user's OAuth token"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._app_install_service: Optional[AppInstallationService] = None
        self._dual_app_helper = None

    @property
    def app_install_service(self) -> AppInstallationService:
        if not self._app_install_service:
            self._app_install_service = AppInstallationService(self.db_pool)
        return self._app_install_service

    @property
    def dual_app_helper(self):
        if not self._dual_app_helper:
            self._dual_app_helper = get_github_dual_app_helper()
        return self._dual_app_helper

    async def get_docbook_installation_id(self, org_id: str) -> Optional[int]:
        """Get installation ID for writer app in the organization."""
        try:
            dual_app = self.dual_app_helper
            if not dual_app.writer_app_id:
                return None

            writer_app_id = int(dual_app.writer_app_id)
            return await self.app_install_service.get_app_installation_id(org_id, writer_app_id)
        except Exception as e:
            print(f"⚠️  Failed to get writer installation ID for {org_id}: {e}")
            return None
    
    async def get_docbook_repo(self, user_id: str | uuid.UUID, org_id: str) -> Optional[Dict[str, str]]:
        """Get linked docbook repo for organization"""
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT docbook_full_name, docbook_url
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
            """, user_uuid, org_id)
            
            if result:
                return {
                    'full_name': result['docbook_full_name'],
                    'url': result['docbook_url']
                }
        return None
    
    async def publish_to_docbook(
        self,
        user_id: str | uuid.UUID,
        org_id: str,
        source_repo_name: str,
        docs_dir: Path,
        writer_token: Optional[str] = None,
        installation_id: Optional[int] = None,
        commit_message: str = "docs: Auto-generated documentation"
    ) -> Dict[str, Any]:
        """
        Publish generated docs to docbook repo staging branch
        
        Args:
            user_id: User ID
            org_id: Organization ID
            source_repo_name: Source repo name (e.g., alpha-testing)
            docs_dir: Path to docs directory
            writer_token: Optional pre-obtained writer token
            installation_id: Optional GitHub App installation ID
            commit_message: Commit message
            
        Returns:
            Dict with status and details
        """
        print("\n" + "="*80)
        print(f"📦 Starting docbook publish for {source_repo_name}")
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        print(f"👤 User: {user_uuid}, Org: {org_id}")
        print(f"📂 Docs dir: {docs_dir}")
        print("="*80 + "\n")
        
        tmpdir = None
        try:
            # Get docbook repo info
            print("\n🔍 Looking up docbook repository...")
            docbook = await self.get_docbook_repo(user_uuid, org_id)
            
            # If no docbook found, create a default one following the pattern
            if not docbook:
                docbook_full_name = f"{org_id}/docit-docbook-{org_id}"
                docbook_url = f"https://github.com/{docbook_full_name}"
                print(f"ℹ️  No docbook repo linked, using default: {docbook_full_name}")
                docbook = {
                    'full_name': docbook_full_name,
                    'url': docbook_url
                }
                
                # Log the decision to use default docbook repo
                print(f"📌 Will use default docbook repo: {docbook_full_name}")
            else:
                docbook_full_name = docbook['full_name']
                print(f"✅ Found linked docbook repo: {docbook_full_name}")
            
            print(f"📚 Publishing to docbook repo: {docbook_full_name}")
            print(f"📝 Source repo: {source_repo_name}")
            print(f"📂 Docs directory: {docs_dir}")

            # Get writer token if not provided
            if not writer_token:
                print("\n🔑 No writer token provided, obtaining one...")
                print(f"   Installation ID: {installation_id or 'Not provided'}")
                
                writer_token = await self._get_writer_token(org_id, docbook_full_name, installation_id)
                
                if not writer_token:
                    raise RuntimeError("Failed to obtain writer token")
                    
                print("✅ Successfully obtained writer token")
                
                # Verify token has the right permissions
                print("🔐 Verifying token permissions...")
                try:
                    # This is a simple check to see if token is valid
                    # We'll try to get the repository info using the token
                    import requests
                    headers = {
                        "Authorization": f"token {writer_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                    repo_url = f"https://api.github.com/repos/{docbook_full_name}"
                    response = requests.get(repo_url, headers=headers)
                    
                    if response.status_code == 200:
                        print(f"✅ Token has access to {docbook_full_name}")
                        repo_data = response.json()
                        print(f"   Repo: {repo_data.get('full_name')}")
                        print(f"   Private: {repo_data.get('private')}")
                        print(f"   Permissions: {repo_data.get('permissions', {})}")
                    else:
                        print(f"⚠️  Token might not have access to {docbook_full_name}")
                        print(f"   Status code: {response.status_code}")
                        print(f"   Response: {response.text[:200]}...")
                except Exception as e:
                    print(f"⚠️  Error verifying token permissions: {e}")
            else:
                print("ℹ️  Using provided writer token (not verified)")
                
            # Create temp directory
            tmpdir = tempfile.mkdtemp(prefix="docai_docbook_")
            
            # Clone docbook repo with masked token in logs
            clone_url = f"https://x-access-token:{writer_token}@github.com/{docbook_full_name}.git"
            masked_url = f"https://x-access-token:***MASKED***@github.com/{docbook_full_name}.git"
            print(f"🔍 Cloning {masked_url}...")
            
            self._run_cmd(
                ["git", "clone", clone_url, tmpdir],
                mask_tokens=[writer_token]
            )
            print(f"✅ Cloned docbook repo")

            # Configure git identity with app bot defaults
            bot_name, bot_email = self._get_writer_identity()
            self._run_cmd(["git", "config", "user.email", bot_email], cwd=tmpdir)
            self._run_cmd(["git", "config", "user.name", bot_name], cwd=tmpdir)
            
            # Check if repo is empty
            try:
                self._run_cmd(["git", "fetch", "origin"], cwd=tmpdir)
                branches = self._run_cmd(["git", "branch", "-r"], cwd=tmpdir, capture_output=True).strip()
                is_empty = not branches or "origin/" not in branches
            except:
                is_empty = True
            
            if is_empty:
                print(f"📝 Repo is empty, creating initial commit...")
                # Create initial README
                readme_path = Path(tmpdir) / "README.md"
                readme_path.write_text(f"# {docbook_full_name}\n\nDocumentation repository for {docbook_full_name}\n")
                
                # Add and commit
                self._run_cmd(["git", "add", "README.md"], cwd=tmpdir)
                self._run_cmd(["git", "commit", "-m", "Initial commit"], cwd=tmpdir)
                
                # Push to main
                self._run_cmd([
                    "git",
                    "push",
                    f"https://x-access-token:{writer_token}@github.com/{docbook_full_name}.git",
                    "HEAD:main",
                ], cwd=tmpdir, mask_tokens=[writer_token])
                print(f"✅ Created initial commit and pushed to main")
                
                # Now create staging from main
                self._run_cmd(["git", "checkout", "-b", "staging"], cwd=tmpdir)
                print(f"✅ Created staging branch")
            else:
                # Repo has content, try to checkout staging
                try:
                    self._run_cmd(["git", "checkout", "staging"], cwd=tmpdir)
                    print(f"✅ Checked out existing staging branch")
                except:
                    # Create staging branch from main
                    self._run_cmd(["git", "checkout", "main"], cwd=tmpdir)
                    self._run_cmd(["git", "checkout", "-b", "staging"], cwd=tmpdir)
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
            self._run_cmd(["git", "add", f"{source_repo_name}/"], cwd=tmpdir)
            
            # Check if there are changes
            status = self._run_cmd(["git", "status", "--porcelain"], cwd=tmpdir, capture_output=True).strip()
            
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
            self._run_cmd(["git", "commit", "-m", full_commit_msg], cwd=tmpdir)
            print(f"✅ Committed changes")
            
            # Push to staging
            push_url = f"https://x-access-token:{writer_token}@github.com/{docbook_full_name}.git"
            masked_url = f"https://x-access-token:***MASKED***@github.com/{docbook_full_name}.git"
            print(f"🚀 Attempting to push to docbook repo: {masked_url}")
            print(f"📁 Working directory: {tmpdir}")
            
            try:
                # Verify the remote URL
                remote_url = self._run_cmd(
                    ["git", "remote", "get-url", "origin"], 
                    cwd=tmpdir, 
                    capture_output=True
                ).strip()
                print(f"🔗 Remote URL: {remote_url}")
                
                # Verify the branch
                branch = self._run_cmd(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                    cwd=tmpdir, 
                    capture_output=True
                ).strip()
                print(f"🌿 Current branch: {branch}")
                
                # Check what would be pushed
                print("📊 Git status before push:")
                self._run_cmd(["git", "status"], cwd=tmpdir)
                
                # Push to staging
                print(f"🚀 Pushing to {masked_url} (branch: staging)")
                self._run_cmd([
                    "git",
                    "push",
                    "--verbose",  # Add verbose output
                    push_url,
                    f"HEAD:staging",
                ], cwd=tmpdir, mask_tokens=[writer_token])
                print(f"✅ Successfully pushed to {docbook_full_name}/staging")
                
            except Exception as e:
                print(f"❌ Error during push: {str(e)}")
                print("📋 Last 10 git logs:")
                logs = self._run_cmd(
                    ["git", "log", "-n", "10", "--oneline"], 
                    cwd=tmpdir, 
                    capture_output=True
                )
                print(logs)
                raise
            
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
                "docbook_repo": docbook_full_name,
                "branch": "staging"
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def _load_private_key(self) -> str:
        """Load and validate the private key from environment"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Try to get private key from environment
        private_key = os.getenv("WRITER_PRIVATE_KEY")
        
        if not private_key:
            # Try to load from file if path is provided
            key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH")
            if key_path and os.path.exists(key_path):
                with open(key_path, 'r') as f:
                    private_key = f.read()
            else:
                raise ValueError("WRITER_PRIVATE_KEY not found in environment and no valid GITHUB_PRIVATE_KEY_PATH provided")
        
        # Clean up the key
        private_key = private_key.strip()
        
        # Ensure proper header and footer
        if not private_key.startswith('-----BEGIN RSA PRIVATE KEY-----'):
            private_key = '-----BEGIN RSA PRIVATE KEY-----\n' + private_key
        if not private_key.endswith('-----END RSA PRIVATE KEY-----'):
            private_key = private_key + '\n-----END RSA PRIVATE KEY-----'
            
        return private_key
        
    async def _get_writer_token(
        self,
        org_id: str,
        docbook_full_name: str,
        installation_id: Optional[int] = None,
    ) -> str:
        """Get writer token using direct JWT approach (matching test_push_env.py)"""
        print("🔑 Getting writer token using direct JWT approach...")
        
        # Get installation ID if not provided
        if not installation_id:
            installation_id = await self.get_docbook_installation_id(org_id)
            if not installation_id:
                raise RuntimeError("No installation ID found for writer app")
        
        try:
            import jwt
            import time
            import aiohttp
            
            # Load and validate private key
            private_key = self._load_private_key()
            
            # Debug: Print first 50 chars of key (don't log the whole key)
            print(f"🔑 Loaded private key. Starts with: {private_key[:50]}...")
            
            print("🔧 Generating JWT token...")
            print(f"🔐 Private key begins with: {private_key[:30]}...")
            
            # Generate JWT - exactly matching test_push_env.py
            payload = {
                'iat': int(time.time()) - 60,
                'exp': int(time.time()) + 600,  # 10 minutes
                'iss': "2229202"  # Hardcoded app ID
            }
            
            jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
            
            print(f"🔧 Requesting installation token for installation ID: {installation_id}")
            
            # Get installation token - exactly matching test script
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
            
            print(f"🔧 Making request to: {url}")
            print(f"🔧 Headers: {headers}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as resp:
                    response_text = await resp.text()
                    print(f"🔧 Response status: {resp.status}")
                    print(f"🔧 Response: {response_text}")
                    
                    if resp.status == 201:
                        data = await resp.json()
                        token = data["token"]
                        print("✅ Successfully obtained installation token")
                        if len(token) > 10:
                            token_preview = f"{token[:5]}...{token[-5:]}"
                            print(f"🔑 Token: {token_preview} (length: {len(token)})")
                        return token
                    else:
                        raise Exception(f"Failed to get installation token: {resp.status} - {response_text}")
            
        except Exception as e:
            print("❌ Error getting writer token:")
            import traceback
            traceback.print_exc()
            
            # Additional debug info
            print("\n🔍 Debug Info:")
            print(f"- Installation ID: {installation_id}")
            print(f"- App ID: 2229202 (hardcoded to match test script)")
            print(f"- Private key exists: {'Yes' if os.getenv('WRITER_PRIVATE_KEY') else 'No'}")
            print(f"- Current directory: {os.getcwd()}")
            
            # Try to find .env file
            env_path = os.path.join(os.getcwd(), '.env')
            print(f"- .env file exists: {os.path.exists(env_path)}")
            if os.path.exists(env_path):
                print(f"- .env file size: {os.path.getsize(env_path)} bytes")
            print(f"- Private Key Path: {os.getenv('GITHUB_PRIVATE_KEY_PATH', 'Not set')}")
            print(f"- Private Key in Env: {'Yes' if os.getenv('GITHUB_PRIVATE_KEY') else 'No'}")
            
            # Try to load private key directly for debugging
            try:
                key_paths = [
                    os.getenv('GITHUB_PRIVATE_KEY_PATH'),
                    'docit-publisher-ai.private-key.pem',
                    'keys/docit-publisher-ai.private-key.pem',
                    '.secrets/docit-publisher-ai.private-key.pem',
                    str(Path.home() / ".ssh/docit-publisher-ai.private-key.pem")
                ]
                
                print("\n🔍 Checking for private key files:")
                key_found = False
                for path in key_paths:
                    if path and os.path.exists(path):
                        print(f"✅ Found key at: {path}")
                        key_found = True
                        # Try to read the key to verify it's valid
                        try:
                            key_content = Path(path).read_text().strip()
                            print(f"   Key starts with: {key_content[:30]}...")
                            print(f"   Key length: {len(key_content)}")
                            print(f"   Has BEGIN/END: {'BEGIN' in key_content} / {'END' in key_content}")
                        except Exception as key_error:
                            print(f"   Error reading key: {key_error}")
                    else:
                        print(f"❌ Not found: {path}")
                
                if not key_found:
                    print("❌ No private key files found in any location")
                    
            except Exception as debug_error:
                print(f"Error during key file check: {debug_error}")
            
            raise RuntimeError(f"Failed to get writer token: {str(e)}")

    def _get_writer_identity(self) -> Tuple[str, str]:
        """Get writer app identity (name, email)"""
        # Default values
        app_id = "2229202"  # Default writer app ID
        app_slug = "docit-publisher-ai"
        
        # Try to get from dual app helper if available
        if hasattr(self, 'dual_app_helper') and self.dual_app_helper:
            app_id = self.dual_app_helper.writer_app_id or app_id
            
        bot_name = f"{app_slug}[bot]"
        bot_email = f"{app_id}+{app_slug}[bot]@users.noreply.github.com"
        print(f"🤖 Using writer identity: {bot_name} <{bot_email}>")
        return bot_name, bot_email

    def _run_cmd(self, cmd, cwd=None, capture_output=False, mask=False, mask_tokens=None):
        """Run a shell command with proper error handling and token masking"""
        if mask_tokens is None:
            mask_tokens = []
            
        def mask_sensitive(text, tokens):
            if not text or not tokens:
                return text
            for token in tokens:
                if token and len(token) > 8:  # Only mask tokens of reasonable length
                    text = text.replace(token, "***MASKED***")
            return text
            
        try:
            env = os.environ.copy()
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,  # Always capture to handle errors properly
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = mask_sensitive(result.stderr, mask_tokens)
                print(f"❌ Command failed: {' '.join(cmd)}")
                print(f"   Error: {error_msg}")
                raise RuntimeError(f"Command failed: {error_msg}")
                
            # Mask sensitive info in output if needed
            output = mask_sensitive(result.stdout, mask_tokens)
            return output if capture_output else None
            
        except Exception as e:
            error_msg = mask_sensitive(str(e), mask_tokens)
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"   Error: {error_msg}")
            raise RuntimeError(f"Command execution failed: {error_msg}")
