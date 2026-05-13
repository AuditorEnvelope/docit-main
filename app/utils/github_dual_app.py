"""
GitHub Dual App Helper - Manages authentication for both Reader and Writer GitHub Apps
"""
import os
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class GitHubDualAppHelper:
    """Manages authentication for both Reader and Writer GitHub Apps"""

    def __init__(self):
        # Reader App Config - Check both READER_APP_ID and GITHUB_READER_APP_ID
        self.reader_app_id = os.getenv(
            "READER_APP_ID") or os.getenv("GITHUB_READER_APP_ID")
        self.reader_private_key = self._load_private_key(
            env_key_var="READER_PRIVATE_KEY",
            path_env_var="READER_PRIVATE_KEY_PATH",
            default_filename="docit-reader.private-key.pem"
        )
        # Also check GITHUB_READER_PRIVATE_KEY if READER_PRIVATE_KEY not found
        if not self.reader_private_key:
            self.reader_private_key = self._load_private_key(
                env_key_var="GITHUB_READER_PRIVATE_KEY",
                path_env_var="GITHUB_READER_PRIVATE_KEY_PATH",
                default_filename="docit-reader.private-key.pem"
            )

        # Writer App Config - Check both WRITER_APP_ID and GITHUB_WRITER_APP_ID
        self.writer_app_id = os.getenv(
            "WRITER_APP_ID") or os.getenv("GITHUB_WRITER_APP_ID")
        self.writer_private_key = self._load_private_key(
            env_key_var="WRITER_PRIVATE_KEY",
            path_env_var="WRITER_PRIVATE_KEY_PATH",
            default_filename="docit-publisher.private-key.pem"
        )
        # Also check GITHUB_WRITER_PRIVATE_KEY if WRITER_PRIVATE_KEY not found
        if not self.writer_private_key:
            self.writer_private_key = self._load_private_key(
                env_key_var="GITHUB_WRITER_PRIVATE_KEY",
                path_env_var="GITHUB_WRITER_PRIVATE_KEY_PATH",
                default_filename="docit-publisher.private-key.pem"
            )

        # Fallback to old single app (for backward compatibility)
        self.github_app_id = os.getenv("GITHUB_APP_ID")
        self.github_private_key = self._load_private_key(
            env_key_var="GITHUB_PRIVATE_KEY",
            path_env_var="GITHUB_PRIVATE_KEY_PATH",
            default_filename="docit-github-app.private-key.pem"
        )

        # Determine which mode we're in
        self.dual_app_mode = bool(self.reader_app_id and self.reader_private_key and
                                  self.writer_app_id and self.writer_private_key)

        if not self.dual_app_mode and not (self.github_app_id and self.github_private_key):
            raise ValueError(
                "Either dual app configuration or single app configuration must be provided")

    def _load_private_key(
        self,
        env_key_var: str,
        path_env_var: str,
        default_filename: str
    ) -> Optional[str]:
        """Load private key from environment or file"""

        key = os.getenv(env_key_var)

        if key:
            # Remove wrapping quotes if present
            key = key.strip().strip('"').strip("'")

            # Convert escaped newlines into real newlines
            key = key.replace("\\n", "\n")

            return key

        key_path = os.getenv(path_env_var, default_filename)

        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                return f.read()

        return None

    def _create_jwt(self, app_id: str, private_key: str) -> str:
        """Create a JWT for GitHub App authentication

        GitHub requires:
        - iat (issued at): Can be up to 60 seconds in the past (clock skew tolerance)
        - exp (expiration): MUST be within 10 minutes from iat (not from 'now')
        """
        now = int(time.time())
        # Set iat 60 seconds in the past to handle clock skew
        iat = now - 60
        payload = {
            "iat": iat,
            # CRITICAL FIX: exp must be at most 10 minutes from iat (not from now)
            "exp": iat + (10 * 60),  # 10 minutes from iat, NOT from now
            "iss": app_id  # GitHub App ID
        }

        try:
            return jwt.encode(payload, private_key, algorithm="RS256")
        except Exception as e:
            print("JWT CREATION FAILED")
            print(repr(e))
            raise

    async def get_reader_token(self, installation_id: int) -> Optional[str]:
        """Get installation access token for reader app"""
        if self.dual_app_mode:
            return await self._get_installation_token(
                app_id=self.reader_app_id,
                private_key=self.reader_private_key,
                installation_id=installation_id,
                permissions={"contents": "read"},
            )
        return await self._get_installation_token(
            app_id=self.github_app_id,
            private_key=self.github_private_key,
            installation_id=installation_id,
            permissions={"contents": "read"},
        )

    async def get_writer_token(self, installation_id: int) -> Optional[str]:
        """Get installation access token for writer app"""
        if self.dual_app_mode:
            return await self._get_installation_token(
                app_id=self.writer_app_id,
                private_key=self.writer_private_key,
                installation_id=installation_id,
                permissions={"contents": "write"},
            )
        return await self._get_installation_token(
            app_id=self.github_app_id,
            private_key=self.github_private_key,
            installation_id=installation_id,
            permissions={"contents": "write"},
        )

    async def _get_installation_token(
        self,
        app_id: str,
        private_key: str,
        installation_id: int,
        permissions: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Get installation access token"""
        import aiohttp

        if not app_id or not private_key:
            return None

        jwt_token = self._create_jwt(app_id, private_key)
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            body: Dict[str, Any] = {}
            if permissions:
                body["permissions"] = permissions

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body or None) as response:
                    if response.status == 201:
                        data = await response.json()
                        return data.get("token")
                    else:
                        error = await response.text()
                        print(f"Failed to get installation token: {error}")
                        return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
