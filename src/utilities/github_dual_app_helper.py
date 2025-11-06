"""
GitHub Dual App Helper - FIXED VERSION
Key fixes:
1. JWT iat timing (subtract 60 seconds for clock skew)
2. Simplified private key loading (matching test_push_env.py)
3. Correct API headers (matching test_push_env.py)
"""

import os
import jwt
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GitHubDualAppHelper:
    """Manages both Reader and Writer GitHub Apps with fallback to single app"""
    
    def __init__(self):
        # Reader App Config
        self.reader_app_id = os.getenv("READER_APP_ID")
        self.reader_private_key = self._load_private_key_simple(
            env_key_var="READER_PRIVATE_KEY",
            path_env_var="READER_PRIVATE_KEY_PATH",
            default_filename="pustak-reader.private-key.pem",
        )
        
        # Writer App Config
        self.writer_app_id = os.getenv("WRITER_APP_ID")
        self.writer_private_key = self._load_private_key_simple(
            env_key_var="WRITER_PRIVATE_KEY",
            path_env_var="WRITER_PRIVATE_KEY_PATH",
            default_filename="pustak-publisher-ai.private-key.pem",
        )
        
        # Fallback to old single app (for backward compatibility)
        self.github_app_id = os.getenv("GITHUB_APP_ID")
        self.github_private_key = self._load_private_key_simple(
            env_key_var="GITHUB_PRIVATE_KEY",
            path_env_var="GITHUB_PRIVATE_KEY_PATH",
            default_filename="pustak-github-app.private-key.pem",
        )
        
        # Determine which mode we're in
        self.dual_app_mode = bool(self.reader_app_id and self.reader_private_key and 
                                   self.writer_app_id and self.writer_private_key)
        
        if self.dual_app_mode:
            logger.info(f"✅ Dual-app mode enabled")
            logger.info(f"   Reader App ID: {self.reader_app_id}")
            logger.info(f"   Writer App ID: {self.writer_app_id}")
        else:
            logger.info(f"⚠️  Dual-app mode disabled, using fallback single app")
            logger.info(f"   GitHub App ID: {self.github_app_id}")
    
    def _load_private_key_simple(
        self,
        env_key_var: str,
        path_env_var: str,
        default_filename: str,
    ) -> Optional[str]:
        """
        SIMPLIFIED private key loading (matching test_push_env.py)
        This is the key fix - keep it simple and don't corrupt the key!
        """
        # 1. Try environment variable first
        private_key = os.getenv(env_key_var)
        if private_key:
            # Simple handling - just replace escaped newlines
            private_key = private_key.replace('\\n', '\n')
            logger.info(f"✅ Loaded {env_key_var} from environment")
            return private_key
        
        # 2. Try explicit path via env
        explicit_path = os.getenv(path_env_var)
        if explicit_path and os.path.exists(explicit_path):
            try:
                with open(explicit_path, 'r') as f:
                    private_key = f.read()
                logger.info(f"✅ Loaded private key from {explicit_path}")
                return private_key
            except Exception as e:
                logger.error(f"❌ Failed to load from {explicit_path}: {e}")
        
        # 3. Try common fallback locations
        candidate_paths = [
            Path.cwd() / default_filename,
            Path.cwd() / "keys" / default_filename,
            Path.home() / default_filename,
            Path.home() / ".ssh" / default_filename,
        ]
        
        for candidate in candidate_paths:
            if candidate.exists():
                try:
                    private_key = candidate.read_text()
                    logger.info(f"✅ Loaded private key from {candidate}")
                    return private_key
                except Exception as e:
                    logger.error(f"❌ Failed to load from {candidate}: {e}")
        
        logger.warning(
            f"⚠️  Private key for {env_key_var} not found. Configure {env_key_var} or {path_env_var}."
        )
        return None
    
    def _generate_jwt(self, app_id: str, private_key: str) -> str:
        """
        Generate JWT for GitHub App - FIXED VERSION
        Key fix: Use time.time() - 60 for iat (clock skew handling)
        """
        if not app_id or not private_key:
            raise ValueError("Missing app credentials")
        
        print(f"\n🔐 === JWT GENERATION DEBUG ===")
        print(f"App ID: {app_id}")
        print(f"Private Key starts with: {private_key[:50] if private_key else 'NONE'}...")
        print(f"Private Key length: {len(private_key) if private_key else 0}")
        print(f"Private Key has BEGIN: {'-----BEGIN' in private_key}")
        print(f"Private Key has END: {'-----END' in private_key}")
        
        # FIX: Match test_push_env.py exactly
        payload = {
            'iat': int(time.time()) - 60,  # 60 seconds in the past (clock skew)
            'exp': int(time.time()) + 600,  # 10 minutes in the future
            'iss': app_id
        }
        
        try:
            token = jwt.encode(payload, private_key, algorithm='RS256')
            result = token if isinstance(token, str) else token.decode('utf-8')
            print(f"✅ JWT generated successfully (length: {len(result)})")
            print(f"   iat: {payload['iat']} (60s ago)")
            print(f"   exp: {payload['exp']} (10m from now)")
            return result
        except Exception as e:
            print(f"❌ JWT generation failed: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"❌ JWT generation failed: {e}")
            raise
    
    async def get_reader_token(self, installation_id: int) -> Optional[str]:
        """
        Get installation token for Reader App
        Falls back to single app if dual-app not configured
        """
        try:
            if self.dual_app_mode:
                app_id = self.reader_app_id
                private_key = self.reader_private_key
                app_name = "Reader"
            else:
                app_id = self.github_app_id
                private_key = self.github_private_key
                app_name = "GitHub (fallback)"
            
            jwt_token = self._generate_jwt(app_id, private_key)
            
            async with aiohttp.ClientSession() as session:
                # FIX: Match test_push_env.py headers exactly
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28',  # Added!
                    'User-Agent': 'pustak-docai-app'
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                print(f"🔧 POST {url}")
                print(f"🔧 Headers: {headers}")
                
                async with session.post(url, headers=headers) as response:
                    response_text = await response.text()
                    print(f"🔧 Response status: {response.status}")
                    print(f"🔧 Response: {response_text[:200]}...")
                    
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got {app_name} token for installation {installation_id}")
                        return data['token']
                    else:
                        logger.error(f"❌ Failed to get {app_name} token: {response.status} - {response_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting reader token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_writer_token(self, installation_id: int) -> Optional[str]:
        """
        Get installation token for Writer App
        Falls back to single app if dual-app not configured
        """
        try:
            if self.dual_app_mode:
                app_id = self.writer_app_id
                private_key = self.writer_private_key
                app_name = "Writer"
            else:
                app_id = self.github_app_id
                private_key = self.github_private_key
                app_name = "GitHub (fallback)"
            
            jwt_token = self._generate_jwt(app_id, private_key)
            
            async with aiohttp.ClientSession() as session:
                # FIX: Match test_push_env.py headers exactly
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28',  # Added!
                    'User-Agent': 'pustak-docai-app'
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                print(f"🔧 POST {url}")
                print(f"🔧 Headers: {headers}")
                
                async with session.post(url, headers=headers) as response:
                    response_text = await response.text()
                    print(f"🔧 Response status: {response.status}")
                    print(f"🔧 Response: {response_text[:200]}...")
                    
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got {app_name} token for installation {installation_id}")
                        return data['token']
                    else:
                        logger.error(f"❌ Failed to get {app_name} token: {response.status} - {response_text}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting writer token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def verify_repo_access(self, repo_full_name: str, token: str, access_type: str = "read") -> bool:
        """
        Verify app has access to a repository
        
        Args:
            repo_full_name: Full repo name (owner/repo)
            token: GitHub token
            access_type: "read" or "write"
        
        Returns:
            True if app has access
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github+json',
                }
                
                url = f'https://api.github.com/repos/{repo_full_name}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        
                        if access_type == "write":
                            # Check if we have push permission
                            has_access = repo_data.get('permissions', {}).get('push', False)
                        else:
                            # Read access is implied if we can access the repo
                            has_access = True
                        
                        logger.info(f"✅ Verified {access_type} access to {repo_full_name}")
                        return has_access
                    else:
                        logger.warning(f"⚠️  Cannot access {repo_full_name}: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error verifying repo access: {e}")
            return False


# Singleton instance
_dual_app_helper = None


def get_github_dual_app_helper() -> GitHubDualAppHelper:
    """Get or create dual app helper instance"""
    global _dual_app_helper
    if _dual_app_helper is None:
        _dual_app_helper = GitHubDualAppHelper()
    return _dual_app_helper