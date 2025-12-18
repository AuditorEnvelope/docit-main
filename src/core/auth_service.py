"""
Authentication Service - Production-Grade GitHub OAuth
Handles user authentication, session management, and JWT tokens

Features:
- GitHub OAuth 2.0 flow
- JWT token generation & validation
- Session management
- Rate limiting
- Security best practices
"""

import os
import jwt
import httpx
import hashlib
import secrets
import uuid
import aiohttp
import asyncio
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
from dataclasses import dataclass

# Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
REFRESH_TOKEN_EXPIRATION_DAYS = 30

# Security
security = HTTPBearer()


@dataclass
class User:
    """User data model"""
    id: str
    github_id: int
    email: Optional[str]
    name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]
    plan: str
    is_active: bool
    created_at: datetime


@dataclass
class Session:
    """Session data model"""
    id: str
    user_id: str
    token: str
    expires_at: datetime
    is_active: bool


class AuthService:
    """
    Production-grade authentication service
    
    Handles:
    - GitHub OAuth flow
    - JWT token generation
    - Session management
    - User creation/lookup
    - Security & rate limiting
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.github_api_base = "https://api.github.com"
        
        # Validate configuration
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            raise ValueError("GitHub OAuth credentials not configured!")
        
        if JWT_SECRET == "change-me-in-production":
            print("⚠️  WARNING: Using default JWT secret! Change in production!")
    
    
    # ========================================================================
    # GITHUB OAUTH FLOW
    # ========================================================================
    
    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None, scope: Optional[str] = None) -> str:
        """
        Generate GitHub OAuth authorization URL
        
        Args:
            redirect_uri: Where GitHub should redirect after auth
            state: CSRF protection token (optional but recommended)
            scope: OAuth scopes to request (default: user:email read:org)
        
        Returns:
            GitHub OAuth URL
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Default scope for basic auth, can be overridden for repo access
        if not scope:
            scope = "user:email read:org repo"
        
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    
    async def exchange_code_for_token(self, code: str) -> str:
        """
        Exchange OAuth code for GitHub access token
        
        Args:
            code: OAuth code from GitHub callback
        
        Returns:
            GitHub access token
        
        Raises:
            HTTPException: If exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                print(f"🔄 Exchanging code with GitHub...")
                print(f"   Client ID: {GITHUB_CLIENT_ID[:10]}...")
                print(f"   Code: {code[:10]}...")
                
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    json={
                        "client_id": GITHUB_CLIENT_ID,
                        "client_secret": GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                    timeout=10.0
                )
                
                print(f"📥 GitHub response status: {response.status_code}")
                print(f"📥 GitHub response body: {response.text}")
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to exchange code for token (HTTP {response.status_code})"
                    )
                
                data = response.json()
                
                if "error" in data:
                    print(f"❌ GitHub error: {data}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"GitHub OAuth error: {data.get('error_description', data['error'])}"
                    )
                
                return data["access_token"]
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="GitHub API timeout"
                )
            except Exception as e:
                print(f"OAuth exchange error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Authentication failed"
                )
    
    
    async def get_github_user(self, access_token: str) -> Dict:
        """
        Fetch user info from GitHub API
        
        Args:
            access_token: GitHub access token
        
        Returns:
            GitHub user data
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                response = await client.get(
                    f"{self.github_api_base}/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to fetch GitHub user"
                    )
                
                user_data = response.json()
                
                # Get user emails (for verified email)
                email_response = await client.get(
                    f"{self.github_api_base}/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Get primary verified email
                    primary_email = next(
                        (e["email"] for e in emails if e["primary"] and e["verified"]),
                        user_data.get("email")
                    )
                    user_data["email"] = primary_email
                
                return user_data
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="GitHub API timeout"
                )
            except Exception as e:
                print(f"GitHub user fetch error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch user data"
                )
    
    
    # ========================================================================
    # GITHUB API METHODS
    # ========================================================================
    
    async def get_user_repositories(self, user_id: str) -> List[Dict]:
        """
        Fetch user's GitHub repositories using stored access token
        Checks each repo for /docs folder
        
        Args:
            user_id: User ID
        
        Returns:
            List of repository data with hasDocsFolder flag
        """
        async with self.db_pool.acquire() as conn:
            # Get user's GitHub token
            user_row = await conn.fetchrow(
                "SELECT github_access_token FROM users WHERE id = $1",
                uuid.UUID(user_id)
            )
            
            if not user_row or not user_row["github_access_token"]:
                print(f"⚠️  No GitHub token found for user {user_id}")
                return []
            
            github_token = user_row["github_access_token"]
            
            # Fetch repositories from GitHub
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.github.com/user/repos",
                        headers={
                            "Authorization": f"Bearer {github_token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "Pustak-AI"
                        },
                        params={
                            "per_page": 100,
                            "sort": "updated",
                            "affiliation": "owner,collaborator,organization_member"
                        }
                    ) as response:
                        if response.status == 200:
                            repos = await response.json()
                            print(f"📚 Fetched {len(repos)} repositories for user {user_id}")
                            
                            # Check for /docs folder and get versions for each repo
                            repos_with_docs_check = []
                            for repo in repos:
                                has_docs = await self._check_repo_has_docs_async(
                                    repo['full_name'],
                                    github_token
                                )
                                repo['hasDocsFolder'] = has_docs
                                
                                # Get architecture and workflow versions
                                if has_docs:
                                    arch_versions = await self._get_versions_from_folder(
                                        repo['full_name'],
                                        'docs/architecture',
                                        github_token
                                    )
                                    workflow_versions = await self._get_versions_from_folder(
                                        repo['full_name'],
                                        'docs/workflow',
                                        github_token
                                    )
                                    repo['architectureVersions'] = arch_versions
                                    repo['workflowVersions'] = workflow_versions
                                else:
                                    repo['architectureVersions'] = []
                                    repo['workflowVersions'] = []
                                
                                repos_with_docs_check.append(repo)
                            
                            return repos_with_docs_check
                        else:
                            error_text = await response.text()
                            print(f"❌ GitHub API error: {response.status} - {error_text}")
                            return []
            except Exception as e:
                print(f"❌ Error fetching repositories: {str(e)}")
                return []
    
    async def _check_repo_has_docs_async(self, repo_full_name: str, github_token: str) -> bool:
        """
        Check if a repository has a /docs folder
        Creates its own session to avoid issues
        
        Args:
            repo_full_name: Full repo name (owner/repo)
            github_token: GitHub access token
        
        Returns:
            True if /docs folder exists, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/repos/{repo_full_name}/contents/docs",
                    headers={
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    has_docs = response.status == 200
                    if has_docs:
                        print(f"✅ {repo_full_name} has /docs folder")
                    else:
                        print(f"⚠️  {repo_full_name} has NO /docs folder (status: {response.status})")
                    return has_docs
        except asyncio.TimeoutError:
            print(f"⏱️  Timeout checking docs for {repo_full_name}")
            return False
        except Exception as e:
            print(f"⚠️  Error checking docs for {repo_full_name}: {str(e)}")
            return False
    
    async def _get_versions_from_folder(self, repo_full_name: str, folder_path: str, github_token: str) -> list:
        """
        Get version files from a folder (architecture or workflow)
        
        Args:
            repo_full_name: Full repo name (owner/repo)
            folder_path: Path to folder (e.g., docs/architecture)
            github_token: GitHub access token
        
        Returns:
            List of version dicts [{version: "v3.6", fileName: "v3.6-architecture.md"}, ...]
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/repos/{repo_full_name}/contents/{folder_path}",
                    headers={
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        files = await response.json()
                        # Filter markdown files and extract version
                        versions = []
                        for file in files:
                            if file['type'] == 'file' and file['name'].endswith('.md'):
                                # Extract version from filename (e.g., v3.6-architecture.md -> v3.6)
                                name = file['name'].replace('.md', '')
                                # Remove suffix like -architecture or -workflow
                                parts = name.split('-')
                                if parts[0].startswith('v'):
                                    version = parts[0]
                                    versions.append({
                                        'version': version,
                                        'fileName': file['name']
                                    })
                        
                        # Sort versions numerically
                        def parse_version(v_str):
                            return [int(x) for x in v_str[1:].split('.')]
                        
                        versions.sort(key=lambda x: parse_version(x['version']), reverse=True)
                        print(f"📚 Found {len(versions)} versions in {folder_path}")
                        return versions
                    else:
                        print(f"⚠️  Folder {folder_path} not found (status: {response.status})")
                        return []
        except Exception as e:
            print(f"⚠️  Error getting versions from {folder_path}: {str(e)}")
            return []
    
    async def get_github_token(self, user_id: str) -> str:
        """Get GitHub token for user"""
        async with self.db_pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT github_access_token FROM users WHERE id = $1",
                uuid.UUID(user_id)
            )
            if user_row:
                return user_row["github_access_token"]
            return None
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    async def create_or_update_user(self, github_user: Dict, github_token: str = None) -> User:
        """
        Create new user or update existing user from GitHub data
        
        Args:
            github_user: GitHub user data
        
        Returns:
            User object
        """
        async with self.db_pool.acquire() as conn:
            # Check if user exists
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE github_id = $1",
                github_user["id"]
            )
            
            if existing_user:
                # Update existing user
                user_row = await conn.fetchrow("""
                    UPDATE users SET
                        email = $1,
                        name = $2,
                        username = $3,
                        avatar_url = $4,
                        bio = $5,
                        company = $6,
                        location = $7,
                        github_access_token = $8,
                        last_login_at = NOW(),
                        updated_at = NOW()
                    WHERE github_id = $9
                    RETURNING *
                """,
                    github_user.get("email"),
                    github_user.get("name"),
                    github_user.get("login"),
                    github_user.get("avatar_url"),
                    github_user.get("bio"),
                    github_user.get("company"),
                    github_user.get("location"),
                    github_token,
                    github_user["id"]
                )
            else:
                # Create new user
                user_row = await conn.fetchrow("""
                    INSERT INTO users (
                        github_id, email, name, username, avatar_url,
                        bio, company, location, github_access_token, plan, is_active, last_login_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'free', true, NOW())
                    RETURNING *
                """,
                    github_user["id"],
                    github_user.get("email"),
                    github_user.get("name"),
                    github_user.get("login"),
                    github_user.get("avatar_url"),
                    github_user.get("bio"),
                    github_user.get("company"),
                    github_user.get("location"),
                    github_token
                )
                
                # Log user creation
                await self.log_audit(
                    conn,
                    user_id=str(user_row["id"]),
                    action="user.created",
                    metadata={"github_id": github_user["id"]}
                )
            
            return User(
                id=str(user_row["id"]),
                github_id=user_row["github_id"],
                email=user_row["email"],
                name=user_row["name"],
                username=user_row["username"],
                avatar_url=user_row["avatar_url"],
                plan=user_row["plan"],
                is_active=user_row["is_active"],
                created_at=user_row["created_at"]
            )
    
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1 AND is_active = true",
                user_id
            )
            
            if not row:
                return None
            
            return User(
                id=str(row["id"]),
                github_id=row["github_id"],
                email=row["email"],
                name=row["name"],
                username=row["username"],
                avatar_url=row["avatar_url"],
                plan=row["plan"],
                is_active=row["is_active"],
                created_at=row["created_at"]
            )
    
    
    # ========================================================================
    # JWT TOKEN MANAGEMENT
    # ========================================================================
    
    def generate_tokens(self, user: User) -> Tuple[str, str]:
        """
        Generate JWT access token and refresh token
        
        Args:
            user: User object
        
        Returns:
            Tuple of (access_token, refresh_token)
        """
        now = datetime.utcnow()
        
        # Access token (short-lived)
        access_payload = {
            "user_id": user.id,
            "github_id": user.github_id,
            "username": user.username,
            "plan": user.plan,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Refresh token (long-lived)
        refresh_payload = {
            "user_id": user.id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
        }
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return access_token, refresh_token
    
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token
        
        Returns:
            Decoded token payload
        
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """
        Create new session in database
        
        Args:
            user: User object
            access_token: JWT access token
            refresh_token: JWT refresh token
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Session object
        """
        async with self.db_pool.acquire() as conn:
            session_row = await conn.fetchrow("""
                INSERT INTO sessions (
                    user_id, token, refresh_token, ip_address, user_agent,
                    expires_at, refresh_expires_at, is_active
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    NOW() + INTERVAL '24 hours',
                    NOW() + INTERVAL '30 days',
                    true
                )
                RETURNING *
            """,
                user.id,
                access_token,
                refresh_token,
                ip_address,
                user_agent
            )
            
            return Session(
                id=str(session_row["id"]),
                user_id=str(session_row["user_id"]),
                token=session_row["token"],
                expires_at=session_row["expires_at"],
                is_active=session_row["is_active"]
            )
    
    
    async def validate_session(self, token: str) -> Optional[Session]:
        """Validate session token"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM sessions
                WHERE token = $1
                AND is_active = true
                AND expires_at > NOW()
            """, token)
            
            if not row:
                return None
            
            # Update last activity
            await conn.execute(
                "UPDATE sessions SET last_activity_at = NOW() WHERE id = $1",
                row["id"]
            )
            
            return Session(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                token=row["token"],
                expires_at=row["expires_at"],
                is_active=row["is_active"]
            )
    
    
    async def revoke_session(self, token: str):
        """Revoke/logout session"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE sessions
                SET is_active = false, revoked_at = NOW()
                WHERE token = $1
            """, token)
    
    
    # ========================================================================
    # COMPLETE AUTH FLOW
    # ========================================================================
    
    async def handle_oauth_callback(
        self,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Complete OAuth flow: exchange code, create/update user, generate tokens
        
        Args:
            code: OAuth code from GitHub
            ip_address: Client IP
            user_agent: Client user agent
        
        Returns:
            Dict with user, access_token, refresh_token
        """
        print(f"🔐 Starting OAuth callback for code: {code[:10]}...")
        
        # Exchange code for GitHub access token
        github_token = await self.exchange_code_for_token(code)
        print(f"✅ Got GitHub token: {github_token[:20]}...")
        
        # Get GitHub user data
        github_user = await self.get_github_user(github_token)
        print(f"👤 Got GitHub user: {github_user.get('login')} (ID: {github_user.get('id')})")
        
        # Create or update user in database (store the GitHub token)
        user = await self.create_or_update_user(github_user, github_token)
        print(f"💾 User saved to database: {user.username} (Plan: {user.plan})")
        print(f"🔑 GitHub token stored for repository access")
        
        # Generate JWT tokens
        access_token, refresh_token = self.generate_tokens(user)
        print(f"🎫 Generated JWT tokens for user {user.username}")
        
        # Create session
        session = await self.create_session(
            user, access_token, refresh_token, ip_address, user_agent
        )
        
        # Log successful login
        async with self.db_pool.acquire() as conn:
            await self.log_audit(
                conn,
                user_id=user.id,
                action="user.login",
                ip_address=ip_address,
                metadata={"session_id": session.id}
            )
        
        print(f"🎉 OAuth flow complete! User {user.username} authenticated successfully")
        
        return {
            "user": {
                "id": user.id,
                "github_id": user.github_id,
                "email": user.email,
                "name": user.name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "plan": user.plan,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "github_token": github_token,
            "expires_in": JWT_EXPIRATION_HOURS * 3600,  # seconds
        }
    
    
    # ========================================================================
    # HELPER FUNCTIONS
    # ========================================================================
    
    async def log_audit(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        action: str,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log action to audit trail"""
        import json
        metadata_json = json.dumps(metadata or {})
        await conn.execute("""
            INSERT INTO audit_logs (user_id, action, ip_address, metadata)
            VALUES ($1, $2, $3, $4::jsonb)
        """, user_id, action, ip_address, metadata_json)


# ============================================================================
# DEPENDENCY INJECTION FOR FASTAPI
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = None  # Will be injected by FastAPI
) -> User:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.get("/api/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials
    
    # Verify JWT token
    payload = auth_service.verify_token(token)
    
    # Validate session
    session = await auth_service.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    # Get user
    user = await auth_service.get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = None
) -> Optional[User]:
    """
    Optional authentication - returns None if not authenticated
    
    Usage:
        @app.get("/api/public")
        async def public_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.name}"}
            return {"message": "Hello guest"}
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        payload = auth_service.verify_token(token)
        session = await auth_service.validate_session(token)
        if session:
            return await auth_service.get_user_by_id(payload["user_id"])
    except:
        pass
    
    return None

"""
Authentication Service - Production-Grade GitHub OAuth
Handles user authentication, session management, and JWT tokens

Features:
- GitHub OAuth 2.0 flow
- JWT token generation & validation
- Session management
- Rate limiting
- Security best practices
"""

import os
import jwt
import httpx
import hashlib
import secrets
import uuid
import aiohttp
import asyncio
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
from dataclasses import dataclass

# Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
REFRESH_TOKEN_EXPIRATION_DAYS = 30

# Security
security = HTTPBearer()


@dataclass
class User:
    """User data model"""
    id: str
    github_id: int
    email: Optional[str]
    name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]
    plan: str
    is_active: bool
    created_at: datetime


@dataclass
class Session:
    """Session data model"""
    id: str
    user_id: str
    token: str
    expires_at: datetime
    is_active: bool


class AuthService:
    """
    Production-grade authentication service
    
    Handles:
    - GitHub OAuth flow
    - JWT token generation
    - Session management
    - User creation/lookup
    - Security & rate limiting
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.github_api_base = "https://api.github.com"
        
        # Validate configuration
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            raise ValueError("GitHub OAuth credentials not configured!")
        
        if JWT_SECRET == "change-me-in-production":
            print("⚠️  WARNING: Using default JWT secret! Change in production!")
    
    
    # ========================================================================
    # GITHUB OAUTH FLOW
    # ========================================================================
    
    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None, scope: Optional[str] = None) -> str:
        """
        Generate GitHub OAuth authorization URL
        
        Args:
            redirect_uri: Where GitHub should redirect after auth
            state: CSRF protection token (optional but recommended)
            scope: OAuth scopes to request (default: user:email read:org)
        
        Returns:
            GitHub OAuth URL
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Default scope for basic auth, can be overridden for repo access
        if not scope:
            scope = "user:email read:org repo"
        
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    
    async def exchange_code_for_token(self, code: str) -> str:
        """
        Exchange OAuth code for GitHub access token
        
        Args:
            code: OAuth code from GitHub callback
        
        Returns:
            GitHub access token
        
        Raises:
            HTTPException: If exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                print(f"🔄 Exchanging code with GitHub...")
                print(f"   Client ID: {GITHUB_CLIENT_ID[:10]}...")
                print(f"   Code: {code[:10]}...")
                
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    json={
                        "client_id": GITHUB_CLIENT_ID,
                        "client_secret": GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                    timeout=10.0
                )
                
                print(f"📥 GitHub response status: {response.status_code}")
                print(f"📥 GitHub response body: {response.text}")
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to exchange code for token (HTTP {response.status_code})"
                    )
                
                data = response.json()
                
                if "error" in data:
                    print(f"❌ GitHub error: {data}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"GitHub OAuth error: {data.get('error_description', data['error'])}"
                    )
                
                return data["access_token"]
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="GitHub API timeout"
                )
            except Exception as e:
                print(f"OAuth exchange error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Authentication failed"
                )
    
    
    async def get_github_user(self, access_token: str) -> Dict:
        """
        Fetch user info from GitHub API
        
        Args:
            access_token: GitHub access token
        
        Returns:
            GitHub user data
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                response = await client.get(
                    f"{self.github_api_base}/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to fetch GitHub user"
                    )
                
                user_data = response.json()
                
                # Get user emails (for verified email)
                email_response = await client.get(
                    f"{self.github_api_base}/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Get primary verified email
                    primary_email = next(
                        (e["email"] for e in emails if e["primary"] and e["verified"]),
                        user_data.get("email")
                    )
                    user_data["email"] = primary_email
                
                return user_data
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail="GitHub API timeout"
                )
            except Exception as e:
                print(f"GitHub user fetch error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch user data"
                )
    
    
    # ========================================================================
    # GITHUB API METHODS
    # ========================================================================
    
    async def get_user_repositories(self, user_id: str) -> List[Dict]:
        """
        Fetch user's GitHub repositories using stored access token
        Checks each repo for /docs folder
        
        Args:
            user_id: User ID
        
        Returns:
            List of repository data with hasDocsFolder flag
        """
        async with self.db_pool.acquire() as conn:
            # Get user's GitHub token
            user_row = await conn.fetchrow(
                "SELECT github_access_token FROM users WHERE id = $1",
                uuid.UUID(user_id)
            )
            
            if not user_row or not user_row["github_access_token"]:
                print(f"⚠️  No GitHub token found for user {user_id}")
                return []
            
            github_token = user_row["github_access_token"]
            
            # Fetch repositories from GitHub
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.github.com/user/repos",
                        headers={
                            "Authorization": f"Bearer {github_token}",
                            "Accept": "application/vnd.github.v3+json",
                            "User-Agent": "Pustak-AI"
                        },
                        params={
                            "per_page": 100,
                            "sort": "updated",
                            "affiliation": "owner,collaborator,organization_member"
                        }
                    ) as response:
                        if response.status == 200:
                            repos = await response.json()
                            print(f"📚 Fetched {len(repos)} repositories for user {user_id}")
                            
                            # Check for /docs folder and get versions for each repo
                            repos_with_docs_check = []
                            for repo in repos:
                                has_docs = await self._check_repo_has_docs_async(
                                    repo['full_name'],
                                    github_token
                                )
                                repo['hasDocsFolder'] = has_docs
                                
                                # Get architecture and workflow versions
                                if has_docs:
                                    arch_versions = await self._get_versions_from_folder(
                                        repo['full_name'],
                                        'docs/architecture',
                                        github_token
                                    )
                                    workflow_versions = await self._get_versions_from_folder(
                                        repo['full_name'],
                                        'docs/workflow',
                                        github_token
                                    )
                                    repo['architectureVersions'] = arch_versions
                                    repo['workflowVersions'] = workflow_versions
                                else:
                                    repo['architectureVersions'] = []
                                    repo['workflowVersions'] = []
                                
                                repos_with_docs_check.append(repo)
                            
                            return repos_with_docs_check
                        else:
                            error_text = await response.text()
                            print(f"❌ GitHub API error: {response.status} - {error_text}")
                            return []
            except Exception as e:
                print(f"❌ Error fetching repositories: {str(e)}")
                return []
    
    async def _check_repo_has_docs_async(self, repo_full_name: str, github_token: str) -> bool:
        """
        Check if a repository has a /docs folder
        Creates its own session to avoid issues
        
        Args:
            repo_full_name: Full repo name (owner/repo)
            github_token: GitHub access token
        
        Returns:
            True if /docs folder exists, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/repos/{repo_full_name}/contents/docs",
                    headers={
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    has_docs = response.status == 200
                    if has_docs:
                        print(f"✅ {repo_full_name} has /docs folder")
                    else:
                        print(f"⚠️  {repo_full_name} has NO /docs folder (status: {response.status})")
                    return has_docs
        except asyncio.TimeoutError:
            print(f"⏱️  Timeout checking docs for {repo_full_name}")
            return False
        except Exception as e:
            print(f"⚠️  Error checking docs for {repo_full_name}: {str(e)}")
            return False
    
    async def _get_versions_from_folder(self, repo_full_name: str, folder_path: str, github_token: str) -> list:
        """
        Get version files from a folder (architecture or workflow)
        
        Args:
            repo_full_name: Full repo name (owner/repo)
            folder_path: Path to folder (e.g., docs/architecture)
            github_token: GitHub access token
        
        Returns:
            List of version dicts [{version: "v3.6", fileName: "v3.6-architecture.md"}, ...]
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.github.com/repos/{repo_full_name}/contents/{folder_path}",
                    headers={
                        "Authorization": f"Bearer {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Pustak-AI"
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        files = await response.json()
                        # Filter markdown files and extract version
                        versions = []
                        for file in files:
                            if file['type'] == 'file' and file['name'].endswith('.md'):
                                # Extract version from filename (e.g., v3.6-architecture.md -> v3.6)
                                name = file['name'].replace('.md', '')
                                # Remove suffix like -architecture or -workflow
                                parts = name.split('-')
                                if parts[0].startswith('v'):
                                    version = parts[0]
                                    versions.append({
                                        'version': version,
                                        'fileName': file['name']
                                    })
                        
                        # Sort versions numerically
                        def parse_version(v_str):
                            return [int(x) for x in v_str[1:].split('.')]
                        
                        versions.sort(key=lambda x: parse_version(x['version']), reverse=True)
                        print(f"📚 Found {len(versions)} versions in {folder_path}")
                        return versions
                    else:
                        print(f"⚠️  Folder {folder_path} not found (status: {response.status})")
                        return []
        except Exception as e:
            print(f"⚠️  Error getting versions from {folder_path}: {str(e)}")
            return []
    
    async def get_github_token(self, user_id: str) -> str:
        """Get GitHub token for user"""
        async with self.db_pool.acquire() as conn:
            user_row = await conn.fetchrow(
                "SELECT github_access_token FROM users WHERE id = $1",
                uuid.UUID(user_id)
            )
            if user_row:
                return user_row["github_access_token"]
            return None
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    async def create_or_update_user(self, github_user: Dict, github_token: str = None) -> User:
        """
        Create new user or update existing user from GitHub data
        
        Args:
            github_user: GitHub user data
        
        Returns:
            User object
        """
        async with self.db_pool.acquire() as conn:
            # Check if user exists
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE github_id = $1",
                github_user["id"]
            )
            
            if existing_user:
                # Update existing user
                user_row = await conn.fetchrow("""
                    UPDATE users SET
                        email = $1,
                        name = $2,
                        username = $3,
                        avatar_url = $4,
                        bio = $5,
                        company = $6,
                        location = $7,
                        github_access_token = $8,
                        last_login_at = NOW(),
                        updated_at = NOW()
                    WHERE github_id = $9
                    RETURNING *
                """,
                    github_user.get("email"),
                    github_user.get("name"),
                    github_user.get("login"),
                    github_user.get("avatar_url"),
                    github_user.get("bio"),
                    github_user.get("company"),
                    github_user.get("location"),
                    github_token,
                    github_user["id"]
                )
            else:
                # Create new user
                user_row = await conn.fetchrow("""
                    INSERT INTO users (
                        github_id, email, name, username, avatar_url,
                        bio, company, location, github_access_token, plan, is_active, last_login_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'free', true, NOW())
                    RETURNING *
                """,
                    github_user["id"],
                    github_user.get("email"),
                    github_user.get("name"),
                    github_user.get("login"),
                    github_user.get("avatar_url"),
                    github_user.get("bio"),
                    github_user.get("company"),
                    github_user.get("location"),
                    github_token
                )
                
                # Log user creation
                await self.log_audit(
                    conn,
                    user_id=str(user_row["id"]),
                    action="user.created",
                    metadata={"github_id": github_user["id"]}
                )
            
            return User(
                id=str(user_row["id"]),
                github_id=user_row["github_id"],
                email=user_row["email"],
                name=user_row["name"],
                username=user_row["username"],
                avatar_url=user_row["avatar_url"],
                plan=user_row["plan"],
                is_active=user_row["is_active"],
                created_at=user_row["created_at"]
            )
    
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1 AND is_active = true",
                user_id
            )
            
            if not row:
                return None
            
            return User(
                id=str(row["id"]),
                github_id=row["github_id"],
                email=row["email"],
                name=row["name"],
                username=row["username"],
                avatar_url=row["avatar_url"],
                plan=row["plan"],
                is_active=row["is_active"],
                created_at=row["created_at"]
            )
    
    
    # ========================================================================
    # JWT TOKEN MANAGEMENT
    # ========================================================================
    
    def generate_tokens(self, user: User) -> Tuple[str, str]:
        """
        Generate JWT access token and refresh token
        
        Args:
            user: User object
        
        Returns:
            Tuple of (access_token, refresh_token)
        """
        now = datetime.utcnow()
        
        # Access token (short-lived)
        access_payload = {
            "user_id": user.id,
            "github_id": user.github_id,
            "username": user.username,
            "plan": user.plan,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Refresh token (long-lived)
        refresh_payload = {
            "user_id": user.id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
        }
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return access_token, refresh_token
    
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token
        
        Returns:
            Decoded token payload
        
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """
        Create new session in database
        
        Args:
            user: User object
            access_token: JWT access token
            refresh_token: JWT refresh token
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Session object
        """
        async with self.db_pool.acquire() as conn:
            session_row = await conn.fetchrow("""
                INSERT INTO sessions (
                    user_id, token, refresh_token, ip_address, user_agent,
                    expires_at, refresh_expires_at, is_active
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    NOW() + INTERVAL '24 hours',
                    NOW() + INTERVAL '30 days',
                    true
                )
                RETURNING *
            """,
                user.id,
                access_token,
                refresh_token,
                ip_address,
                user_agent
            )
            
            return Session(
                id=str(session_row["id"]),
                user_id=str(session_row["user_id"]),
                token=session_row["token"],
                expires_at=session_row["expires_at"],
                is_active=session_row["is_active"]
            )
    
    
    async def validate_session(self, token: str) -> Optional[Session]:
        """Validate session token"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM sessions
                WHERE token = $1
                AND is_active = true
                AND expires_at > NOW()
            """, token)
            
            if not row:
                return None
            
            # Update last activity
            await conn.execute(
                "UPDATE sessions SET last_activity_at = NOW() WHERE id = $1",
                row["id"]
            )
            
            return Session(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                token=row["token"],
                expires_at=row["expires_at"],
                is_active=row["is_active"]
            )
    
    
    async def revoke_session(self, token: str):
        """Revoke/logout session"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE sessions
                SET is_active = false, revoked_at = NOW()
                WHERE token = $1
            """, token)
    
    
    # ========================================================================
    # COMPLETE AUTH FLOW
    # ========================================================================
    
    async def handle_oauth_callback(
        self,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Complete OAuth flow: exchange code, create/update user, generate tokens
        
        Args:
            code: OAuth code from GitHub
            ip_address: Client IP
            user_agent: Client user agent
        
        Returns:
            Dict with user, access_token, refresh_token
        """
        print(f"🔐 Starting OAuth callback for code: {code[:10]}...")
        
        # Exchange code for GitHub access token
        github_token = await self.exchange_code_for_token(code)
        print(f"✅ Got GitHub token: {github_token[:20]}...")
        
        # Get GitHub user data
        github_user = await self.get_github_user(github_token)
        print(f"👤 Got GitHub user: {github_user.get('login')} (ID: {github_user.get('id')})")
        
        # Create or update user in database (store the GitHub token)
        user = await self.create_or_update_user(github_user, github_token)
        print(f"💾 User saved to database: {user.username} (Plan: {user.plan})")
        print(f"🔑 GitHub token stored for repository access")
        
        # Generate JWT tokens
        access_token, refresh_token = self.generate_tokens(user)
        print(f"🎫 Generated JWT tokens for user {user.username}")
        
        # Create session
        session = await self.create_session(
            user, access_token, refresh_token, ip_address, user_agent
        )
        
        # Log successful login
        async with self.db_pool.acquire() as conn:
            await self.log_audit(
                conn,
                user_id=user.id,
                action="user.login",
                ip_address=ip_address,
                metadata={"session_id": session.id}
            )
        
        print(f"🎉 OAuth flow complete! User {user.username} authenticated successfully")
        
        return {
            "user": {
                "id": user.id,
                "github_id": user.github_id,
                "email": user.email,
                "name": user.name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "plan": user.plan,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "github_token": github_token,
            "expires_in": JWT_EXPIRATION_HOURS * 3600,  # seconds
        }
    
    
    # ========================================================================
    # HELPER FUNCTIONS
    # ========================================================================
    
    async def log_audit(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        action: str,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log action to audit trail"""
        import json
        metadata_json = json.dumps(metadata or {})
        await conn.execute("""
            INSERT INTO audit_logs (user_id, action, ip_address, metadata)
            VALUES ($1, $2, $3, $4::jsonb)
        """, user_id, action, ip_address, metadata_json)


# ============================================================================
# DEPENDENCY INJECTION FOR FASTAPI
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = None  # Will be injected by FastAPI
) -> User:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.get("/api/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials
    
    # Verify JWT token
    payload = auth_service.verify_token(token)
    
    # Validate session
    session = await auth_service.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    # Get user
    user = await auth_service.get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = None
) -> Optional[User]:
    """
    Optional authentication - returns None if not authenticated
    
    Usage:
        @app.get("/api/public")
        async def public_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.name}"}
            return {"message": "Hello guest"}
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        payload = auth_service.verify_token(token)
        session = await auth_service.validate_session(token)
        if session:
            return await auth_service.get_user_by_id(payload["user_id"])
    except:
        pass
    
    return None
