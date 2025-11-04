"""
GitHub Dual App Helper - Manage Reader and Writer apps
Handles separate token generation for read and write operations
Backward compatible with single app (lekhak-ai)
"""

import os
import jwt
import codecs
import aiohttp
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GitHubDualAppHelper:
    """Manages both Reader and Writer GitHub Apps with fallback to single app"""
    
    def __init__(self):
        # Reader App Config
        self.reader_app_id = os.getenv("READER_APP_ID")
        self.reader_private_key = self._decode_key(os.getenv("READER_PRIVATE_KEY"))
        
        # Writer App Config
        self.writer_app_id = os.getenv("WRITER_APP_ID")
        self.writer_private_key = self._decode_key(os.getenv("WRITER_PRIVATE_KEY"))
        
        # Fallback to old single app (for backward compatibility)
        self.github_app_id = os.getenv("GITHUB_APP_ID")
        self.github_private_key = self._decode_key(os.getenv("GITHUB_PRIVATE_KEY"))
        
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
    
    def _decode_key(self, key_raw: str) -> Optional[str]:
        """Decode private key from environment"""
        if not key_raw:
            return None
        
        # Remove quotes if present
        if key_raw.startswith('"') and key_raw.endswith('"'):
            key_raw = key_raw[1:-1]
        
        try:
            # Use codecs to properly decode escape sequences
            decoded = codecs.decode(key_raw, 'unicode_escape')
            return decoded
        except Exception as e:
            logger.error(f"❌ Failed to decode key: {e}")
            return None
    
    def _generate_jwt(self, app_id: str, private_key: str) -> str:
        """Generate JWT for GitHub App"""
        if not app_id or not private_key:
            raise ValueError("Missing app credentials")
        
        print(f"\n🔐 === JWT GENERATION DEBUG ===")
        print(f"App ID: {app_id}")
        print(f"Private Key starts with: {private_key[:50] if private_key else 'NONE'}...")
        print(f"Private Key length: {len(private_key) if private_key else 0}")
        print(f"Private Key has BEGIN: {'-----BEGIN' in private_key}")
        print(f"Private Key has END: {'-----END' in private_key}")
        
        now = datetime.utcnow()
        payload = {
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=10)).timestamp()),
            'iss': app_id
        }
        
        try:
            token = jwt.encode(payload, private_key, algorithm='RS256')
            result = token if isinstance(token, str) else token.decode('utf-8')
            print(f"✅ JWT generated successfully (length: {len(result)})")
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
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got {app_name} token for installation {installation_id}")
                        return data['token']
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to get {app_name} token: {response.status} - {error}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting reader token: {e}")
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
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got {app_name} token for installation {installation_id}")
                        return data['token']
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to get {app_name} token: {response.status} - {error}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error getting writer token: {e}")
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
