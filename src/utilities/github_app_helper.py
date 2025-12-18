"""
GitHub App Helper - Manage doc-maintainer repository creation and configuration
Handles all GitHub App operations for doc-maintainer repos
"""

import os
import json
import aiohttp
import jwt
import time
import codecs
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GitHubAppHelper:
    """Helper class for GitHub App operations"""
    
    def __init__(self):
        self.app_id = os.getenv("GITHUB_APP_ID")
        private_key_raw = os.getenv("GITHUB_PRIVATE_KEY")
        
        # Handle escaped newlines from .env file using codecs
        # .env has: "-----BEGIN...\nMIIE...\n-----END..."
        # codecs.decode properly converts \n to actual newlines
        if private_key_raw:
            # Remove quotes if present
            if private_key_raw.startswith('"') and private_key_raw.endswith('"'):
                private_key_raw = private_key_raw[1:-1]
            # Use codecs to properly decode escape sequences
            try:
                self.private_key = codecs.decode(private_key_raw, 'unicode_escape')
                logger.info(f"✅ Private key decoded successfully")
                
                # DEBUG: Check if key was decoded correctly
                if '\\n' in self.private_key:
                    logger.error(f"❌ PROBLEM: Private key still has literal \\n (not decoded!)")
                    logger.error(f"First 100 chars: {self.private_key[:100]}")
                    logger.error(f"Last 100 chars: {self.private_key[-100:]}")
                else:
                    logger.info(f"✅ Private key properly decoded (no literal \\n)")
                    logger.info(f"Private key first 100 chars: {self.private_key[:100]}")
                    logger.info(f"Private key last 100 chars: {self.private_key[-100:]}")
                    logger.info(f"Private key length: {len(self.private_key)} chars")
                    logger.info(f"Private key newline count: {self.private_key.count(chr(10))}")
            except Exception as e:
                logger.error(f"❌ Failed to decode private key: {e}")
                self.private_key = None
        else:
            self.private_key = None
        
        self.app_name = os.getenv("GITHUB_APP_NAME", "lekhak-ai")
        
        if not self.app_id or not self.private_key:
            logger.warning(f"GitHub App credentials not configured: app_id={bool(self.app_id)}, private_key={bool(self.private_key)}")
    
    def _generate_jwt(self) -> str:
        """Generate JWT token for GitHub App authentication"""
        try:
            if not self.app_id or not self.private_key:
                logger.error(f"❌ Missing GitHub App credentials: app_id={bool(self.app_id)}, private_key={bool(self.private_key)}")
                return ""
            
            print(f"🔐 === JWT GENERATION DEBUG ===")
            print(f"🔐 App ID: {self.app_id}")
            print(f"🔐 Private key type: {type(self.private_key)}")
            print(f"🔐 Private key length: {len(self.private_key)} chars")
            print(f"🔐 Private key starts with: {repr(self.private_key[:50])}")
            print(f"🔐 Private key ends with: {repr(self.private_key[-50:])}")
            print(f"🔐 Newline count (actual): {self.private_key.count(chr(10))}")
            print(f"🔐 Backslash-n count (literal): {self.private_key.count(chr(92) + 'n')}")
            
            now = datetime.utcnow()
            payload = {
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(minutes=10)).timestamp()),
                'iss': self.app_id
            }
            
            print(f"🔐 JWT Payload: {payload}")
            print(f"🔐 Attempting to encode with RS256...")
            
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm='RS256'
            )
            
            result = token if isinstance(token, str) else token.decode('utf-8')
            print(f"✅ JWT Generated successfully")
            print(f"✅ JWT Token length: {len(result)} chars")
            print(f"✅ JWT Token header: {result.split('.')[0]}")
            print(f"✅ JWT Token payload: {result.split('.')[1]}")
            print(f"✅ JWT Token signature (first 50): {result.split('.')[2][:50]}...")
            print(f"🔐 === JWT GENERATION COMPLETE ===")
            return result
        except Exception as e:
            logger.error(f"❌ JWT Generation failed: {e}")
            import traceback
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            return ""
    
    async def get_app_installations(self) -> list:
        """
        Get list of GitHub App installations
        
        Returns:
            List of installation objects with account info
        """
        try:
            jwt_token = self._generate_jwt()
            
            if not jwt_token:
                logger.error(f"❌ JWT token generation returned empty string")
                return []
            
            print(f"🔐 === GITHUB API CALL DEBUG ===")
            print(f"🔐 JWT Token generated (length: {len(jwt_token)})")
            print(f"🔐 JWT Token header: {jwt_token.split('.')[0]}")
            print(f"🔐 JWT Token payload: {jwt_token.split('.')[1]}")
            print(f"🔐 JWT Token signature (first 50): {jwt_token.split('.')[2][:50]}...")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'
                }
                
                print(f"📡 === API REQUEST ===")
                print(f"📡 URL: https://api.github.com/app/installations")
                print(f"📡 Method: GET")
                print(f"📡 Headers: {headers}")
                url = 'https://api.github.com/app/installations'
                
                async with session.get(url, headers=headers) as response:
                    print(f"📡 === API RESPONSE ===")
                    print(f"📡 Status Code: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Got {len(data)} app installations")
                        print(f"✅ Installations: {[inst.get('account', {}).get('login') for inst in data]}")
                        return data
                    else:
                        error = await response.text()
                        print(f"❌ Failed to get installations: {response.status}")
                        print(f"❌ Error response: {error}")
                        print(f"📋 Request headers sent: {headers}")
                        print(f"📋 Response headers: {dict(response.headers)}")
                        print(f"🔐 === API CALL FAILED ===")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error getting app installations: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return []
    
    async def get_installation_token(self, installation_id: int) -> Optional[str]:
        """
        Get installation token for a specific GitHub App installation
        
        Args:
            installation_id: GitHub App installation ID for the org
            
        Returns:
            Installation token or None if failed
        """
        try:
            jwt_token = self._generate_jwt()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got installation token for installation {installation_id}")
                        return data['token']
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to get installation token: {response.status} - {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting installation token: {e}")
            return None
    
    
    async def _check_repo_exists(
        self,
        org_name: str,
        repo_name: str,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """Check if repository exists"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        return {
                            'name': repo_data['name'],
                            'full_name': repo_data['full_name'],
                            'url': repo_data['html_url'],
                            'clone_url': repo_data['clone_url'],
                            'default_branch': repo_data['default_branch'],
                            'private': repo_data['private']
                        }
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error checking repo existence: {e}")
            return None
    
    async def _create_branches(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        default_branch: str
    ) -> bool:
        """
        Create staging and main branches
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            token: GitHub token
            default_branch: Default branch name (usually 'main')
            
        Returns:
            True if successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                # Get default branch SHA
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/git/refs/heads/{default_branch}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"⚠️  Could not get default branch SHA")
                        return False
                    
                    ref_data = await response.json()
                    sha = ref_data['object']['sha']
                
                # Create staging branch
                staging_payload = {
                    'ref': 'refs/heads/staging',
                    'sha': sha
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/git/refs'
                
                async with session.post(url, json=staging_payload, headers=headers) as response:
                    if response.status == 201:
                        logger.info(f"✅ Created staging branch")
                    elif response.status == 422:
                        logger.info(f"ℹ️  Staging branch already exists")
                    else:
                        logger.warning(f"⚠️  Failed to create staging branch: {response.status}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creating branches: {e}")
            return False
    
    async def create_pull_request(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "staging"
    ) -> Optional[Dict[str, Any]]:
        """
        Create pull request in doc-maintainer repo
        
        Args:
            org_name: Organization name
            repo_name: Repository name (usually "doc-maintainer")
            token: GitHub token
            title: PR title
            body: PR description
            head_branch: Source branch (e.g., "docai-review/repo-a/commit-abc")
            base_branch: Target branch (default: "staging")
            
        Returns:
            PR details {number, url, ...} or None if failed
        """
        try:
            logger.info(f"📝 Creating PR in {org_name}/{repo_name}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                payload = {
                    'title': title,
                    'body': body,
                    'head': head_branch,
                    'base': base_branch
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/pulls'
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        pr_data = await response.json()
                        logger.info(f"✅ Created PR #{pr_data['number']}: {pr_data['html_url']}")
                        return {
                            'number': pr_data['number'],
                            'url': pr_data['html_url'],
                            'state': pr_data['state'],
                            'head_branch': pr_data['head']['ref'],
                            'base_branch': pr_data['base']['ref']
                        }
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to create PR: {response.status} - {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error creating PR: {e}")
            return None
    
    async def merge_pull_request(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        pr_number: int,
        merge_method: str = "squash"
    ) -> bool:
        """
        Merge pull request
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            token: GitHub token
            pr_number: PR number
            merge_method: Merge method (squash|merge|rebase)
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"🔀 Merging PR #{pr_number} in {org_name}/{repo_name}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                payload = {
                    'merge_method': merge_method,
                    'commit_title': f'Merge PR #{pr_number}',
                    'commit_message': f'Merge documentation review PR #{pr_number}'
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/pulls/{pr_number}/merge'
                
                async with session.put(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"✅ Merged PR #{pr_number}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to merge PR: {response.status} - {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error merging PR: {e}")
            return False
    
    


# Singleton instance
_github_app_helper = None

def get_github_app_helper() -> GitHubAppHelper:
    """Get or create GitHub App helper instance"""
    global _github_app_helper
    if _github_app_helper is None:
        _github_app_helper = GitHubAppHelper()
    return _github_app_helper

"""
GitHub App Helper - Manage doc-maintainer repository creation and configuration
Handles all GitHub App operations for doc-maintainer repos
"""

import os
import json
import aiohttp
import jwt
import time
import codecs
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GitHubAppHelper:
    """Helper class for GitHub App operations"""
    
    def __init__(self):
        self.app_id = os.getenv("GITHUB_APP_ID")
        private_key_raw = os.getenv("GITHUB_PRIVATE_KEY")
        
        # Handle escaped newlines from .env file using codecs
        # .env has: "-----BEGIN...\nMIIE...\n-----END..."
        # codecs.decode properly converts \n to actual newlines
        if private_key_raw:
            # Remove quotes if present
            if private_key_raw.startswith('"') and private_key_raw.endswith('"'):
                private_key_raw = private_key_raw[1:-1]
            # Use codecs to properly decode escape sequences
            try:
                self.private_key = codecs.decode(private_key_raw, 'unicode_escape')
                logger.info(f"✅ Private key decoded successfully")
                
                # DEBUG: Check if key was decoded correctly
                if '\\n' in self.private_key:
                    logger.error(f"❌ PROBLEM: Private key still has literal \\n (not decoded!)")
                    logger.error(f"First 100 chars: {self.private_key[:100]}")
                    logger.error(f"Last 100 chars: {self.private_key[-100:]}")
                else:
                    logger.info(f"✅ Private key properly decoded (no literal \\n)")
                    logger.info(f"Private key first 100 chars: {self.private_key[:100]}")
                    logger.info(f"Private key last 100 chars: {self.private_key[-100:]}")
                    logger.info(f"Private key length: {len(self.private_key)} chars")
                    logger.info(f"Private key newline count: {self.private_key.count(chr(10))}")
            except Exception as e:
                logger.error(f"❌ Failed to decode private key: {e}")
                self.private_key = None
        else:
            self.private_key = None
        
        self.app_name = os.getenv("GITHUB_APP_NAME", "lekhak-ai")
        
        if not self.app_id or not self.private_key:
            logger.warning(f"GitHub App credentials not configured: app_id={bool(self.app_id)}, private_key={bool(self.private_key)}")
    
    def _generate_jwt(self) -> str:
        """Generate JWT token for GitHub App authentication"""
        try:
            if not self.app_id or not self.private_key:
                logger.error(f"❌ Missing GitHub App credentials: app_id={bool(self.app_id)}, private_key={bool(self.private_key)}")
                return ""
            
            print(f"🔐 === JWT GENERATION DEBUG ===")
            print(f"🔐 App ID: {self.app_id}")
            print(f"🔐 Private key type: {type(self.private_key)}")
            print(f"🔐 Private key length: {len(self.private_key)} chars")
            print(f"🔐 Private key starts with: {repr(self.private_key[:50])}")
            print(f"🔐 Private key ends with: {repr(self.private_key[-50:])}")
            print(f"🔐 Newline count (actual): {self.private_key.count(chr(10))}")
            print(f"🔐 Backslash-n count (literal): {self.private_key.count(chr(92) + 'n')}")
            
            now = datetime.utcnow()
            payload = {
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(minutes=10)).timestamp()),
                'iss': self.app_id
            }
            
            print(f"🔐 JWT Payload: {payload}")
            print(f"🔐 Attempting to encode with RS256...")
            
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm='RS256'
            )
            
            result = token if isinstance(token, str) else token.decode('utf-8')
            print(f"✅ JWT Generated successfully")
            print(f"✅ JWT Token length: {len(result)} chars")
            print(f"✅ JWT Token header: {result.split('.')[0]}")
            print(f"✅ JWT Token payload: {result.split('.')[1]}")
            print(f"✅ JWT Token signature (first 50): {result.split('.')[2][:50]}...")
            print(f"🔐 === JWT GENERATION COMPLETE ===")
            return result
        except Exception as e:
            logger.error(f"❌ JWT Generation failed: {e}")
            import traceback
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            return ""
    
    async def get_app_installations(self) -> list:
        """
        Get list of GitHub App installations
        
        Returns:
            List of installation objects with account info
        """
        try:
            jwt_token = self._generate_jwt()
            
            if not jwt_token:
                logger.error(f"❌ JWT token generation returned empty string")
                return []
            
            print(f"🔐 === GITHUB API CALL DEBUG ===")
            print(f"🔐 JWT Token generated (length: {len(jwt_token)})")
            print(f"🔐 JWT Token header: {jwt_token.split('.')[0]}")
            print(f"🔐 JWT Token payload: {jwt_token.split('.')[1]}")
            print(f"🔐 JWT Token signature (first 50): {jwt_token.split('.')[2][:50]}...")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'
                }
                
                print(f"📡 === API REQUEST ===")
                print(f"📡 URL: https://api.github.com/app/installations")
                print(f"📡 Method: GET")
                print(f"📡 Headers: {headers}")
                url = 'https://api.github.com/app/installations'
                
                async with session.get(url, headers=headers) as response:
                    print(f"📡 === API RESPONSE ===")
                    print(f"📡 Status Code: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Got {len(data)} app installations")
                        print(f"✅ Installations: {[inst.get('account', {}).get('login') for inst in data]}")
                        return data
                    else:
                        error = await response.text()
                        print(f"❌ Failed to get installations: {response.status}")
                        print(f"❌ Error response: {error}")
                        print(f"📋 Request headers sent: {headers}")
                        print(f"📋 Response headers: {dict(response.headers)}")
                        print(f"🔐 === API CALL FAILED ===")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error getting app installations: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return []
    
    async def get_installation_token(self, installation_id: int) -> Optional[str]:
        """
        Get installation token for a specific GitHub App installation
        
        Args:
            installation_id: GitHub App installation ID for the org
            
        Returns:
            Installation token or None if failed
        """
        try:
            jwt_token = self._generate_jwt()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'
                }
                
                url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
                
                async with session.post(url, headers=headers) as response:
                    if response.status == 201:
                        data = await response.json()
                        logger.info(f"✅ Got installation token for installation {installation_id}")
                        return data['token']
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to get installation token: {response.status} - {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error getting installation token: {e}")
            return None
    
    
    async def _check_repo_exists(
        self,
        org_name: str,
        repo_name: str,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """Check if repository exists"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        return {
                            'name': repo_data['name'],
                            'full_name': repo_data['full_name'],
                            'url': repo_data['html_url'],
                            'clone_url': repo_data['clone_url'],
                            'default_branch': repo_data['default_branch'],
                            'private': repo_data['private']
                        }
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error checking repo existence: {e}")
            return None
    
    async def _create_branches(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        default_branch: str
    ) -> bool:
        """
        Create staging and main branches
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            token: GitHub token
            default_branch: Default branch name (usually 'main')
            
        Returns:
            True if successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                # Get default branch SHA
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/git/refs/heads/{default_branch}'
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"⚠️  Could not get default branch SHA")
                        return False
                    
                    ref_data = await response.json()
                    sha = ref_data['object']['sha']
                
                # Create staging branch
                staging_payload = {
                    'ref': 'refs/heads/staging',
                    'sha': sha
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/git/refs'
                
                async with session.post(url, json=staging_payload, headers=headers) as response:
                    if response.status == 201:
                        logger.info(f"✅ Created staging branch")
                    elif response.status == 422:
                        logger.info(f"ℹ️  Staging branch already exists")
                    else:
                        logger.warning(f"⚠️  Failed to create staging branch: {response.status}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creating branches: {e}")
            return False
    
    async def create_pull_request(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "staging"
    ) -> Optional[Dict[str, Any]]:
        """
        Create pull request in doc-maintainer repo
        
        Args:
            org_name: Organization name
            repo_name: Repository name (usually "doc-maintainer")
            token: GitHub token
            title: PR title
            body: PR description
            head_branch: Source branch (e.g., "docai-review/repo-a/commit-abc")
            base_branch: Target branch (default: "staging")
            
        Returns:
            PR details {number, url, ...} or None if failed
        """
        try:
            logger.info(f"📝 Creating PR in {org_name}/{repo_name}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                payload = {
                    'title': title,
                    'body': body,
                    'head': head_branch,
                    'base': base_branch
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/pulls'
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        pr_data = await response.json()
                        logger.info(f"✅ Created PR #{pr_data['number']}: {pr_data['html_url']}")
                        return {
                            'number': pr_data['number'],
                            'url': pr_data['html_url'],
                            'state': pr_data['state'],
                            'head_branch': pr_data['head']['ref'],
                            'base_branch': pr_data['base']['ref']
                        }
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to create PR: {response.status} - {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Error creating PR: {e}")
            return None
    
    async def merge_pull_request(
        self,
        org_name: str,
        repo_name: str,
        token: str,
        pr_number: int,
        merge_method: str = "squash"
    ) -> bool:
        """
        Merge pull request
        
        Args:
            org_name: Organization name
            repo_name: Repository name
            token: GitHub token
            pr_number: PR number
            merge_method: Merge method (squash|merge|rebase)
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"🔀 Merging PR #{pr_number} in {org_name}/{repo_name}")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                payload = {
                    'merge_method': merge_method,
                    'commit_title': f'Merge PR #{pr_number}',
                    'commit_message': f'Merge documentation review PR #{pr_number}'
                }
                
                url = f'https://api.github.com/repos/{org_name}/{repo_name}/pulls/{pr_number}/merge'
                
                async with session.put(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"✅ Merged PR #{pr_number}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to merge PR: {response.status} - {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error merging PR: {e}")
            return False
    
    


# Singleton instance
_github_app_helper = None

def get_github_app_helper() -> GitHubAppHelper:
    """Get or create GitHub App helper instance"""
    global _github_app_helper
    if _github_app_helper is None:
        _github_app_helper = GitHubAppHelper()
    return _github_app_helper
