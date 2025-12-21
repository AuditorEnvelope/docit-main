"""
Authentication Service

Handles GitHub OAuth, JWT tokens, and user session management
"""

import httpx
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.user import User, Session, UserPlan
from app.db.session import get_db

security = HTTPBearer()

class AuthService:
    """
    Production-grade authentication service
    
    Features:
    - GitHub OAuth 2.0 flow
    - JWT token generation & validation
    - Session management
    - User creation/lookup
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.github_api_base = "https://api.github.com"
        
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise ValueError("GitHub OAuth credentials not configured!")
    
    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None, scope: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        if not scope:
            scope = "user:email read:org repo"
        
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange OAuth code for GitHub access token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={  # Changed from json to data for form-encoded
                        "client_id": settings.GITHUB_CLIENT_ID,
                        "client_secret": settings.GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                    timeout=10.0
                )
                
                # Log response status and content for debugging
                print(f"🔍 GitHub OAuth Status: {response.status_code}")
                print(f"🔍 GitHub OAuth Headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"❌ GitHub OAuth failed: {error_text}")
                    raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {error_text}")
                
                # Try to parse as JSON
                try:
                    data = response.json()
                except Exception as e:
                    # If JSON parsing fails, try URL-encoded format
                    print(f"⚠️ JSON parse failed, trying URL-encoded. Raw response: {response.text}")
                    from urllib.parse import parse_qs
                    parsed = parse_qs(response.text)
                    data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                
                # Debug: Log the response data
                print(f"🔍 GitHub OAuth Response: {data}")
                
                if "access_token" not in data:
                    # Check if it's an error response
                    if "error" in data:
                        error_msg = f"{data.get('error')}: {data.get('error_description', 'Unknown error')}"
                        print(f"❌ GitHub OAuth Error: {error_msg}")
                        raise HTTPException(status_code=400, detail=error_msg)
                    
                    print(f"❌ No access token in response. Full data: {data}")
                    raise HTTPException(status_code=400, detail="No access token in response")
                
                return data["access_token"]
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    
    async def get_github_user(self, access_token: str) -> Dict[str, Any]:
        """Get user data from GitHub"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.github_api_base}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user data")
            
            return response.json()
    
    async def get_or_create_user(
        self,
        github_user: Dict[str, Any],
        github_token: Optional[str] = None,
    ) -> User:
        """Get existing user or create new one"""
        github_id = github_user["id"]
        
        # Try to find existing user
        result = await self.db.execute(
            select(User).where(User.github_id == github_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update user info
            user.username = github_user["login"]
            user.name = github_user.get("name")
            user.email = github_user.get("email")
            user.avatar_url = github_user.get("avatar_url")
            user.last_login_at = datetime.utcnow()
            if github_token:
                user.github_access_token = github_token
            await self.db.commit()
            await self.db.refresh(user)
            return user
        
        # Create new user
        import uuid
        user = User(
            id=uuid.uuid4(),
            github_id=github_id,
            username=github_user["login"],
            name=github_user.get("name"),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
            github_access_token=github_token,
            plan=UserPlan.FREE,
            is_active=True,
            last_login_at=datetime.utcnow()
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    def create_jwt_token(self, user_id) -> str:
        """Create JWT access token"""
        # Convert UUID to string if needed
        user_id_str = str(user_id) if user_id else None
        exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id_str,
            "exp": exp,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    
    def create_refresh_token(self) -> str:
        """Create refresh token"""
        return secrets.token_urlsafe(32)
    
    async def create_session(self, user_id, token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Session:
        """Create new user session"""
        import uuid
        
        # Ensure user_id is UUID (not string)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        session = Session(
            id=uuid.uuid4(),
            user_id=user_id,
            token=token,
            refresh_token=self.create_refresh_token(),
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
            user_id_str = payload.get("sub")
            if not user_id_str:
                return None
            
            # Convert string to UUID for comparison
            import uuid
            user_id = uuid.UUID(user_id_str)
            
            result = await self.db.execute(
                select(User).where(User.id == user_id, User.is_active == True)
            )
            return result.scalar_one_or_none()
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# Dependency for getting authenticated user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    
    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    token = credentials.credentials
    auth_service = AuthService(db)
    user = await auth_service.verify_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Optional: Dependency for getting user from header (for API keys)
async def get_auth_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get user from Authorization header (optional)
    Returns None if no auth provided
    """
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    auth_service = AuthService(db)
    return await auth_service.verify_token(token)


__all__ = ["AuthService", "get_current_user", "get_auth_user"]
