"""
GitHub App Installation Routes
Handles Reader and Writer app installation flows
"""

from fastapi import APIRouter, HTTPException
import os

router = APIRouter(prefix="/auth", tags=["github-app"])


@router.get("/install-reader-app")
async def install_reader_app(redirect_uri: str = None):
    """
    Redirect to GitHub App installation page for Reader App
    User will install the app and GitHub will redirect back with installation_id
    """
    try:
        reader_app_id = os.getenv("READER_APP_ID")
        if not reader_app_id:
            raise HTTPException(status_code=500, detail="Reader App not configured")
        
        # GitHub App installation URL
        # After user installs, GitHub redirects to: redirect_uri?installation_id=XXX&setup_action=install
        github_install_url = f"https://github.com/apps/pustak-analyser-ai-test/installations/new"
        
        return {
            "status": "redirect",
            "url": github_install_url,
            "app_name": "Pustak Analyser AI",
            "app_id": reader_app_id,
            "message": "Redirecting to GitHub App installation page"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/install-writer-app")
async def install_writer_app(redirect_uri: str = None):
    """
    Redirect to GitHub App installation page for Writer App
    User will install the app and GitHub will redirect back with installation_id
    """
    try:
        writer_app_id = os.getenv("WRITER_APP_ID")
        if not writer_app_id:
            raise HTTPException(status_code=500, detail="Writer App not configured")
        
        # GitHub App installation URL
        # After user installs, GitHub redirects to: redirect_uri?installation_id=XXX&setup_action=install
        github_install_url = f"https://github.com/apps/pustak-publisher-ai-test/installations/new"
        
        return {
            "status": "redirect",
            "url": github_install_url,
            "app_name": "Pustak Publisher AI",
            "app_id": writer_app_id,
            "message": "Redirecting to GitHub App installation page"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/app-installation-callback")
async def handle_app_installation_callback(
    installation_id: int = None,
    setup_action: str = None,
    state: str = None
):
    """
    Handle GitHub App installation callback
    GitHub redirects here after user installs the app
    """
    try:
        if not installation_id:
            raise HTTPException(status_code=400, detail="No installation_id provided")
        
        return {
            "status": "success",
            "installation_id": installation_id,
            "setup_action": setup_action,
            "message": "GitHub App installed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
