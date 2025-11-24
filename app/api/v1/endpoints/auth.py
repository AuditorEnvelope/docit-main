from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.config import settings
from app.db.session import get_db
from app.schemas.token import Token, AuthResponse
from app.services.auth import AuthService, get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/github")
async def start_github_oauth(
    redirect_uri: str = Query(..., description="Redirect URI after OAuth"),
    scope: Optional[str] = Query(None, description="OAuth scopes")
):
    """
    Start GitHub OAuth flow
    
    Returns GitHub OAuth URL for user to authorize
    """
    # Create temporary auth service (no DB needed for URL generation)
    auth_service = AuthService.__new__(AuthService)
    auth_service.github_api_base = "https://api.github.com"
    
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth not configured"
        )
    
    oauth_url = auth_service.get_oauth_url(redirect_uri, scope=scope)
    return {"url": oauth_url}


@router.get("/callback", response_model=AuthResponse)
async def handle_github_callback(
    code: str = Query(..., description="OAuth code from GitHub"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle GitHub OAuth callback
    
    Exchanges code for access token and creates user session
    """
    auth_service = AuthService(db)
    
    try:
        # Exchange code for GitHub token
        github_token = await auth_service.exchange_code_for_token(code)
        
        # Get GitHub user data
        github_user = await auth_service.get_github_user(github_token)
        
        # Get or create user (persist token)
        user = await auth_service.get_or_create_user(
            github_user,
            github_token=github_token,
        )
        
        # Create JWT token
        access_token = auth_service.create_jwt_token(user.id)
        
        # Create session
        ip_address = request.client.host if request else None
        user_agent = request.headers.get("user-agent") if request else None
        session = await auth_service.create_session(
            user.id,
            access_token,
            ip_address,
            user_agent
        )
        
        return {
            "access_token": access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),  # Convert UUID to string for JSON
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "plan": user.plan.value if hasattr(user.plan, 'value') else str(user.plan)
            }
        }
    
    except Exception as e:
        import traceback
        error_msg = f"Failed to authenticate: {str(e)}"
        print(f"❌ AUTH ERROR: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )


@router.get("/me")
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return {
        "id": str(user.id),  # Convert UUID to string for JSON
        "github_id": user.github_id,
        "username": user.username,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "plan": user.plan.value if hasattr(user.plan, 'value') else str(user.plan),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "is_onboarding_complete": bool(user.is_onboarding_complete),
        "onboarding_completed_at": user.onboarding_completed_at,
    }


@router.get("/install-reader-app")
async def install_reader_app() -> dict[str, str]:
    """Provide GitHub reader app installation redirect details."""
    reader_app_id = settings.GITHUB_READER_APP_ID or settings.GITHUB_APP_ID
    if not reader_app_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reader app is not configured"
        )

    return {
        "status": "redirect",
        "url": "https://github.com/apps/pustak-analyser-ai/installations/new",
        "app_name": "Pustak Analyser AI",
        "app_id": reader_app_id,
        "message": "Redirecting to GitHub App installation page"
    }


@router.get("/install-writer-app")
async def install_writer_app() -> dict[str, str]:
    """Provide GitHub writer app installation redirect details."""
    writer_app_id = settings.GITHUB_WRITER_APP_ID or settings.GITHUB_APP_ID
    if not writer_app_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Writer app is not configured"
        )

    return {
        "status": "redirect",
        "url": "https://github.com/apps/pustak-publisher-ai/installations/new",
        "app_name": "Pustak Publisher AI",
        "app_id": writer_app_id,
        "message": "Redirecting to GitHub App installation page"
    }


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    
    NOTE: This is a placeholder for password-based auth if needed.
    Primary auth method is GitHub OAuth via /auth/github
    
    """
    raise HTTPException(
        status_code=501,
        detail="Password-based authentication not implemented. Please use GitHub OAuth via /auth/github"
    )


@router.post("/onboarding-complete")
async def mark_onboarding_complete(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark the authenticated user's onboarding as complete."""

    if user.is_onboarding_complete:
        return {"status": "already_complete"}

    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(
            is_onboarding_complete=True,
            onboarding_completed_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        .execution_options(synchronize_session="fetch")
    )

    await db.execute(stmt)
    await db.commit()

    return {"status": "complete"}
