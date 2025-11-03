"""
Lekhak AI - Main API Server
Handles GitHub webhooks and stores events in commit bus for processing
"""

# Load environment variables FIRST before any imports that use them
from dotenv import load_dotenv
load_dotenv()

import os
import hmac
import hashlib
import json
import base64
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import aiohttp

# Import core services
from core.commit_bus import CommitBusService
from core.auth_service import AuthService, get_current_user, get_optional_user, User
from core.quality_checker import DocumentationQualityChecker, DocumentationQuality

# Import business services
from services.subscription_service import SubscriptionService
from services.overlay_service import OverlayService

# Import processors
from processors.smart_processor import handle_push_event as legacy_handle_push

# Import utilities
from utilities.github_dual_app_helper import get_github_dual_app_helper

# Import routes
from routes.github_app_installation import router as app_installation_router

# Import webhooks
from webhooks.webhook_multi_org import webhook_multi_org

# Initialize FastAPI
app = FastAPI(
    title="Lekhak AI",
    description="Production-grade AI-first documentation platform",
    version="1.0.0"
)

# CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
allow_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://192.168.1.2:3000",
    "http://192.168.1.2:8000",
]

# Add production frontend URL if configured
if FRONTEND_URL not in allow_origins:
    allow_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(app_installation_router)

# Configuration
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/lekhak_ai")

# Feature flags
HAS_COMMIT_BUS = True  # Always enable commit bus
HAS_SUBSCRIPTIONS = True  # Always enable subscriptions
HAS_OVERLAYS = True  # Always enable overlays

# Initialize services
commit_bus = None
subscription_service = None
overlay_service = None
quality_checker = None
auth_service = None

@app.on_event("startup")
async def startup():
    """Initialize all services on startup"""
    global commit_bus, subscription_service, overlay_service, quality_checker, auth_service
    
    print("🚀 Starting Lekhak AI...")
    
    # Initialize Quality Checker
    try:
        quality_checker = DocumentationQualityChecker()
        print("✅ Quality Checker initialized")
    except Exception as e:
        print(f"⚠️  Quality Checker failed: {e}")
        quality_checker = None
    
    
    # Initialize Commit Bus
    if HAS_COMMIT_BUS:
        try:
            commit_bus = CommitBusService(DATABASE_URL)
            await commit_bus.init_pool()
            print("✅ Commit Bus initialized")
        except Exception as e:
            print(f"⚠️  Commit Bus failed: {e}")
            commit_bus = None
    
    # Initialize Auth Service
    if commit_bus and commit_bus.pool:
        try:
            auth_service = AuthService(commit_bus.pool)
            print("✅ Auth Service initialized")
        except Exception as e:
            print(f"⚠️  Auth Service failed: {e}")
            auth_service = None
    
    # Initialize Subscription Service
    if HAS_SUBSCRIPTIONS:
        try:
            subscription_service = SubscriptionService(DATABASE_URL)
            await subscription_service.init_db()
            print("✅ Subscription Service initialized")
        except Exception as e:
            print(f"⚠️  Subscription Service failed: {e}")
            subscription_service = None
    
    # Initialize Overlay Service
    if HAS_OVERLAYS:
        try:
            overlay_service = OverlayService(DATABASE_URL)
            await overlay_service.init_db()
            print("✅ Overlay Service initialized")
        except Exception as e:
            print(f"⚠️  Overlay Service failed: {e}")
            overlay_service = None
    
    print("✅ Lekhak AI ready!")

def verify_signature(secret: str, payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    sha_name, sig = signature.split('=')
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)

async def process_commit_event(payload: dict):
    """Process commit event through commit bus or legacy processor"""
    
    # Extract webhook context if available (multi-org mode)
    webhook_context = payload.pop('_webhook_context', None)
    
    # Try commit bus first (durable, never loses commits)
    if commit_bus:
        try:
            from core.commit_bus import CommitEvent
            from datetime import datetime
            
            # Extract commit info from payload
            repo = payload.get('repository', {})
            commits = payload.get('commits', [])
            installation = payload.get('installation', {})
            installation_id = installation.get('id')
            
            # DEBUG: Log what we're receiving
            print(f"🔍 DEBUG: Webhook payload repo: {repo.get('full_name')}")
            print(f"🔍 DEBUG: Webhook context: {webhook_context}")
            print(f"🔍 DEBUG: Installation ID: {installation_id}")
            
            if commits:
                commit = commits[-1]  # Use last commit
                
                # Create CommitEvent object
                # Parse timestamp and convert to naive datetime for database
                timestamp_str = commit.get('timestamp', datetime.now().isoformat())
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Convert to naive datetime (remove timezone info)
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                
                # Extract repo info
                repo_full_name = repo.get('full_name', 'unknown')
                repo_org = repo_full_name.split('/')[0] if '/' in repo_full_name else 'unknown'
                
                # Try to get user_id from org_registrations if webhook_context doesn't have it
                user_id_for_event = None
                if webhook_context and webhook_context.get('user_id'):
                    user_id_for_event = webhook_context['user_id']
                elif commit_bus and commit_bus.pool:
                    # Check if org is registered
                    try:
                        async with commit_bus.pool.acquire() as conn:
                            reg = await conn.fetchrow(
                                "SELECT user_id FROM org_registrations WHERE org_id = $1 LIMIT 1",
                                repo_org
                            )
                            if reg:
                                user_id_for_event = str(reg['user_id'])
                    except Exception as e:
                        print(f"⚠️  Could not check org_registrations: {e}")
                
                event = CommitEvent(
                    repo_id=repo_full_name,
                    commit_sha=commit.get('id', payload.get('after', 'unknown')),
                    parent_sha=[payload.get('before', '')] if payload.get('before') else [],
                    author_name=commit.get('author', {}).get('name', 'unknown'),
                    author_email=commit.get('author', {}).get('email', 'unknown@example.com'),
                    timestamp=timestamp,
                    branch=payload.get('ref', 'refs/heads/main').replace('refs/heads/', ''),
                    files_changed=[
                        {
                            'path': f,
                            'status': 'modified' if f in commit.get('modified', []) else 
                                     'added' if f in commit.get('added', []) else 'deleted'
                        }
                        for f in (commit.get('added', []) + commit.get('modified', []) + commit.get('removed', []))
                    ],
                    commit_message=commit.get('message', ''),
                    push_id=payload.get('push_id'),
                    source='github',
                    metadata={'payload': payload},
                    user_id=user_id_for_event,
                    org_id=repo_org,
                    github_token_id=webhook_context.get('github_token_id') if webhook_context else None,
                    webhook_secret=webhook_context.get('webhook_secret') if webhook_context else None,
                    installation_id=installation_id
                )
                
                event_id = await commit_bus.store_event(event)
                print(f"✅ Event stored in commit bus: {event_id}")
                return {"status": "queued", "event_id": event_id}
        except Exception as e:
            print(f"⚠️  Commit bus failed, falling back to legacy: {e}")
            import traceback
            traceback.print_exc()
    
    # Fallback to legacy processor
    try:
        legacy_handle_push(payload)
        return {"status": "processed", "method": "legacy"}
    except Exception as e:
        print(f"❌ Legacy processor failed: {e}")
        raise

# ============================================
# API ROUTES
# ============================================

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.get("/auth/github")
async def start_github_oauth(redirect_uri: str, scope: str = None):
    """Start GitHub OAuth flow - Returns GitHub OAuth URL"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    oauth_url = auth_service.get_oauth_url(redirect_uri, scope=scope)
    return {"url": oauth_url}


@app.get("/auth/callback")
async def handle_github_callback(code: str, request: Request):
    """Handle GitHub OAuth callback - Exchanges code for tokens"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    result = await auth_service.handle_oauth_callback(
        code=code,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return result


async def get_auth_user(authorization: str = Header(None)):
    """Dependency to get current authenticated user"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    
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


@app.get("/auth/me")
async def get_current_user(user = Depends(get_auth_user)):
    """Get current authenticated user"""
    return {
        "id": user.id,
        "github_id": user.github_id,
        "email": user.email,
        "name": user.name,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "plan": user.plan,
    }


@app.get("/auth/repositories")
async def get_user_repositories(user = Depends(get_auth_user)):
    """Get user's GitHub repositories"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    repos = await auth_service.get_user_repositories(user.id)
    return {"repositories": repos}


@app.get("/auth/user-organizations")
async def get_user_organizations(user = Depends(get_auth_user)):
    """Get user's GitHub organizations"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    try:
        github_token = await auth_service.get_github_token(user.id)
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/user/orgs",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                }
            ) as response:
                if response.status == 200:
                    orgs = await response.json()
                    return {"organizations": orgs}
                else:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch organizations")
    except Exception as e:
        print(f"❌ Error fetching organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs/fetch-file")
async def fetch_file_from_github(repo: str, filePath: str, user = Depends(get_auth_user)):
    """Fetch a file from GitHub using user's token"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    try:
        # Get user's GitHub token from database
        github_token = await auth_service.get_github_token(user.id)
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        # Fetch file from GitHub
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{repo}/contents/{filePath}",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Pustak-AI"
                }
            ) as response:
                if response.status == 404:
                    raise HTTPException(status_code=404, detail="File not found")
                if response.status == 401 or response.status == 403:
                    raise HTTPException(status_code=403, detail="Access denied")
                if not response.ok:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch file")
                
                data = await response.json()
                
                # Decode base64 content
                if data.get("encoding") == "base64" and data.get("content"):
                    import base64
                    content = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
                    return {"content": content, "fileName": filePath}
                
                return {"content": data.get("content", ""), "fileName": filePath}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching file: {str(e)}")


# REMOVED: Old /docs/generate endpoint (legacy V3 code)
# Use /docs/generate-v4 instead (V4 with docbook publishing)

@app.post("/docs/generate-v4")
async def generate_documentation_v4(repo_name: str, user = Depends(get_auth_user)):
    """
    Generate documentation for a repository (V4 - NEW!)
    Publishes to docbook repo staging branch instead of source repo
    Uses user's OAuth token for transparent commits
    """
    if not auth_service or not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        import tempfile
        import shutil
        from pathlib import Path
        from processors.comprehensive_doc_generator import generate_comprehensive_documentation
        from processors.smart_processor import clone_repo_via_token
        
        # Get user's GitHub token
        github_token = await auth_service.get_github_token(user.id)
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        # Parse org and repo from full name
        if '/' not in repo_name:
            raise HTTPException(status_code=400, detail="Invalid repo name format. Use org/repo")
        
        org_id, source_repo = repo_name.split('/', 1)
        
        print(f"🚀 Generating docs for {repo_name} (V4)...")
        
        # Clone the repository
        tmpdir = tempfile.mkdtemp(prefix="docai_manual_")
        try:
            clone_repo_via_token(repo_name, github_token, tmpdir)
            print(f"✅ Cloned {repo_name}")
            
            # Generate comprehensive documentation
            analysis = {
                "title": f"Manual documentation generation for {source_repo}",
                "type": "manual",
                "significance": 5,
                "impact_scope": []
            }
            
            # Generate docs using comprehensive generator
            generate_comprehensive_documentation(
                tmpdir,
                analysis,
                [],  # No specific changed files for manual generation
                doc_persona="internal"
            )
            
            print(f"✅ Documentation generated for {repo_name}")
            
            # ⭐ NEW: Push to docbook repo (V4 mode)
            from services.docbook_publisher import DocbookPublisher
            from processors.smart_processor import push_to_docbook_v4
            
            print(f"📚 V4 Mode - Publishing to docbook repo (staging branch)")
            
            # Get Writer token for docbook publishing
            writer_token = github_token  # Use user's token for now
            dual_app = get_github_dual_app_helper()
            if dual_app.dual_app_mode:
                print(f"✅ Dual-app mode enabled, attempting to get Writer token")
                # Note: In manual trigger mode, we don't have installation_id
                # So we'll use the user's OAuth token instead
                # In webhook mode, installation_id will be available
            
            # Create synthetic payload for docbook publishing
            payload = {
                "repository": {
                    "full_name": repo_name,
                    "name": source_repo,
                    "url": f"https://github.com/{repo_name}"
                },
                "commits": [{
                    "id": "manual-trigger",
                    "message": "Manual doc generation via dashboard",
                    "author": {"name": user.email}
                }],
                # ⭐ NEW: Add required fields for docbook publishing
                "_user_id": str(user.id),
                "_org_id": org_id,
                "_db_pool": commit_bus.pool
            }
            
            # Push to docbook
            await push_to_docbook_v4(tmpdir, {"full_name": repo_name, "name": source_repo}, analysis, "manual-trigger", writer_token, payload)
            
            print(f"✅ Documentation published to docbook/staging")
            
            # Return success
            return {
                "status": "success",
                "message": f"Documentation generated and published to docbook/staging for {repo_name}",
                "repo": repo_name
            }
        finally:
            # Clean up temp directory
            shutil.rmtree(tmpdir, ignore_errors=True)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """GitHub webhook for automatic documentation generation on push"""
    from webhooks.webhook_handler import verify_github_signature, handle_push_webhook
    
    # Verify signature
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "")
    
    if event_type == "push":
        # Get the repository's GitHub token from database
        # For now, use the environment token as fallback
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            await handle_push_webhook(payload, github_token)
    
    return {"status": "received"}


# ============================================
# GENERAL ROUTES
# ============================================

@app.get("/")
async def root():
    """Health check and service status"""
    return {
        "service": "Lekhak AI",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "commit_bus": commit_bus is not None,
            "subscriptions": subscription_service is not None,
            "overlays": overlay_service is not None,
            "legacy_processor": True,
            "multi_language": True,
            "rag_system": True,
        }
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "commit_bus": "active" if commit_bus else "disabled",
            "subscriptions": "active" if subscription_service else "disabled",
            "overlays": "active" if overlay_service else "disabled",
        }
    }

@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    """GitHub webhook handler with multi-org support"""
    return await webhook_multi_org(
        request=request,
        background_tasks=background_tasks,
        x_hub_signature_256=x_hub_signature_256,
        x_github_event=x_github_event,
        db_pool=commit_bus.pool if commit_bus else None,
        process_commit_event_func=process_commit_event
    )

@app.get("/webhook/check-app-installation")
async def check_app_installation(
    org_id: str,
    user = Depends(get_current_user)
):
    """
    Check if GitHub App is installed in the organization
    
    Returns:
    - app_installed: bool - Whether the app is installed
    - connected: bool - Whether the org is already connected
    """
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    try:
        # Extract user_id from dict
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        # Get user's GitHub token from OAuth (not personal token)
        github_token = await auth_service.get_github_token(user_id)
        if not github_token:
            print(f"❌ No GitHub token found for user {user_id}")
            raise HTTPException(status_code=401, detail="No GitHub token found. Please log in again.")
        
        # Check if app is installed in this org using GitHub App JWT
        from webhooks.github_app import create_jwt
        
        try:
            jwt_token = create_jwt()
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # Get all app installations (using app JWT, not user token)
                async with session.get(
                    "https://api.github.com/app/installations",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # The endpoint returns an array directly, not an object
                        installations = data if isinstance(data, list) else data.get('installations', [])
                        print(f"🔍 Checking org: {org_id}")
                        print(f"📦 Found {len(installations)} installations:")
                        for inst in installations:
                            account_login = inst.get('account', {}).get('login')
                            print(f"   - {account_login}")
                        app_installed = any(
                            inst.get('account', {}).get('login') == org_id 
                            for inst in installations
                        )
                        print(f"✅ App installed for {org_id}: {app_installed}")
                    else:
                        print(f"❌ Failed to get installations: {resp.status}")
                        app_installed = False
        except Exception as e:
            print(f"❌ Error checking app installation: {e}")
            app_installed = False
        
        # Check if org is already connected
        connected = False
        if commit_bus and commit_bus.pool:
            async with commit_bus.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM org_registrations WHERE user_id = $1 AND org_id = $2)",
                    user_id, org_id
                )
                connected = result or False
        
        return {
            "app_installed": app_installed,
            "connected": connected,
            "org_id": org_id
        }
    except Exception as e:
        print(f"❌ Error checking app installation: {e}")
        return {
            "app_installed": False,
            "connected": False,
            "org_id": org_id
        }

class WebhookRegisterRequest(BaseModel):
    org_id: str

@app.post("/webhook/register")
async def register_webhook(
    request: WebhookRegisterRequest,
    user = Depends(get_current_user)
):
    """
    Register webhook for an organization (multi-org support)
    
    This endpoint:
    1. Stores the org_id + user_id mapping
    2. Creates doc-maintainer repo for the org
    3. Returns webhook URL for user to configure on GitHub
    4. Enables multi-org support via GitHub App
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Extract org_id from request
        org_id = request.org_id
        
        # Extract user_id from dict (get_current_user returns dict)
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        async with commit_bus.pool.acquire() as conn:
            # Store org registration (user can register multiple orgs)
            await conn.execute("""
                INSERT INTO org_registrations (user_id, org_id, registered_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id, org_id) DO UPDATE
                SET registered_at = NOW()
            """, user_id, org_id)
            
            # Also register in org_webhooks for real-time webhook processing
            # Get user's GitHub token
            user_token_record = await conn.fetchrow("""
                SELECT token_id FROM user_github_tokens 
                WHERE user_id = $1 
                LIMIT 1
            """, user_id)
            
            if user_token_record:
                await conn.execute("""
                    INSERT INTO org_webhooks (user_id, org_id, webhook_secret, github_token_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, org_id) DO UPDATE
                    SET updated_at = NOW()
                """, user_id, org_id, f'webhook_{org_id}', user_token_record['token_id'])
                print(f"✅ Registered org {org_id} for webhooks with user {user_id}")
        
        # STEP 2: User will manually create lekhak-docbook-org-{ORG_ID} repo
        # (No automatic repo creation - user has full control)
        print(f"✅ Org {org_id} registered! User will create lekhak-docbook-org-{org_id} manually.")
        
        webhook_url = os.getenv("WEBHOOK_URL", os.getenv("NGROK_URL", "http://localhost:8000")) + "/webhook"
        
        return {
            "status": "registered",
            "org_id": org_id,
            "webhook_url": webhook_url,
            "message": f"Organization '{org_id}' registered! Configure webhook on GitHub with this URL."
        }
    except Exception as e:
        print(f"❌ Error registering webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# DOCBOOK MANAGEMENT ENDPOINTS (NEW V4)
# ============================================
# These endpoints handle the new user-driven docbook workflow
# User creates lekhak-docbook-org-{ORG_ID} manually
# Then links it via these endpoints

class LinkDocbookRequest(BaseModel):
    org_id: str
    docbook_repo_name: str  # e.g., "lekhak-docbook-org-12345"

@app.post("/docbook/link-repo")
async def link_docbook_repo(
    request: LinkDocbookRequest,
    user = Depends(get_current_user)
):
    """
    Link a user-created lekhak-docbook repo to an organization
    
    This endpoint:
    1. Verifies the docbook repo exists
    2. Verifies user has access to it
    3. Stores the mapping in database
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        org_id = request.org_id
        docbook_repo_name = request.docbook_repo_name
        
        # Get user's GitHub token
        github_token = await auth_service.get_github_token(user_id)
        if not github_token:
            raise HTTPException(status_code=401, detail="No GitHub token found")
        
        # Verify docbook repo exists and user has access
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Check if repo exists
            async with session.get(
                f'https://api.github.com/repos/{org_id}/{docbook_repo_name}',
                headers=headers
            ) as resp:
                if resp.status == 404:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Repository {org_id}/{docbook_repo_name} not found"
                    )
                elif resp.status != 200:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have access to this repository"
                    )
                
                repo_data = await resp.json()
                docbook_full_name = repo_data['full_name']
                docbook_url = repo_data['html_url']
        
        # Store in database
        async with commit_bus.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO docbook_repos 
                (user_id, org_id, docbook_repo_name, docbook_full_name, docbook_url, is_active)
                VALUES ($1, $2, $3, $4, $5, TRUE)
                ON CONFLICT (user_id, org_id) DO UPDATE
                SET docbook_repo_name = $3, docbook_full_name = $4, docbook_url = $5, 
                    is_active = TRUE, updated_at = NOW()
            """,
            user_id, org_id, docbook_repo_name, docbook_full_name, docbook_url
            )
        
        print(f"✅ Linked docbook repo: {docbook_full_name}")
        
        return {
            "status": "linked",
            "org_id": org_id,
            "docbook_repo": docbook_full_name,
            "docbook_url": docbook_url,
            "message": f"Successfully linked {docbook_full_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error linking docbook repo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docbook/pending-reviews")
async def get_pending_reviews(
    org_id: str,
    user = Depends(get_current_user)
):
    """
    Get pending documentation reviews for an organization
    
    Returns:
    - reviews: List of pending reviews waiting for user approval
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        async with commit_bus.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT id, source_repo_name, docbook_full_name, status, commit_message, created_at
                FROM docbook_reviews
                WHERE user_id = $1 AND org_id = $2 AND status = 'pending_review'
                ORDER BY created_at DESC
            """, user_id, org_id)
        
        reviews = [
            {
                'id': r['id'],
                'source_repo_name': r['source_repo_name'],
                'docbook_full_name': r['docbook_full_name'],
                'status': r['status'],
                'commit_message': r['commit_message'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else None
            }
            for r in results
        ]
        
        return {
            "org_id": org_id,
            "reviews": reviews,
            "count": len(reviews)
        }
    except Exception as e:
        print(f"❌ Error fetching pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docbook/check-exists")
async def check_docbook_exists(
    org_id: str,
    user = Depends(get_current_user)
):
    """
    Check if a docbook repo is linked for an organization
    
    Returns:
    - exists: bool - Whether docbook is linked
    - docbook_repo: str - Full name of docbook repo (if exists)
    - docbook_url: str - URL of docbook repo (if exists)
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        async with commit_bus.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT docbook_repo_name, docbook_full_name, docbook_url, is_active
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
            """, user_id, org_id)
        
        if result:
            return {
                "exists": True,
                "org_id": org_id,
                "docbook_repo": result['docbook_full_name'],
                "docbook_url": result['docbook_url']
            }
        else:
            return {
                "exists": False,
                "org_id": org_id,
                "message": f"No docbook linked for {org_id}. Please create lekhak-docbook-org-{{ORG_ID}} and link it."
            }
    except Exception as e:
        print(f"❌ Error checking docbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PublishDocbookRequest(BaseModel):
    org_id: str
    repo_name: str  # Source repo name
    docs_content: Dict[str, Any]  # Generated docs to publish
    message: str = "docs: Update documentation"  # Commit message

@app.post("/docbook/publish")
async def publish_to_docbook(
    request: PublishDocbookRequest,
    user = Depends(get_current_user)
):
    """
    Publish documentation to the lekhak-docbook repo
    
    This endpoint:
    1. Gets the linked docbook repo
    2. Creates a commit in the staging branch
    3. Returns the commit details for user review
    
    User can then approve to merge staging → main
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        org_id = request.org_id
        repo_name = request.repo_name
        docs_content = request.docs_content
        commit_message = request.message
        
        # Get user's GitHub token
        github_token = await auth_service.get_github_token(user_id)
        if not github_token:
            raise HTTPException(status_code=401, detail="No GitHub token found")
        
        # Get docbook repo info
        async with commit_bus.pool.acquire() as conn:
            docbook = await conn.fetchrow("""
                SELECT docbook_full_name, docbook_url
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
            """, user_id, org_id)
        
        if not docbook:
            raise HTTPException(
                status_code=404,
                detail=f"No docbook linked for {org_id}"
            )
        
        docbook_full_name = docbook['docbook_full_name']
        
        # Create commit in staging branch
        # This is a simplified version - full implementation would handle multiple files
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Create commit with docs
            # Path: {repo_name}/internal/README.md, {repo_name}/developer/README.md, etc.
            commit_data = {
                "message": commit_message,
                "branch": "staging",
                "committer": {
                    "name": "Lekhak AI",
                    "email": "lekhak@ai.com"
                },
                "content": base64.b64encode(
                    json.dumps(docs_content, indent=2).encode()
                ).decode()
            }
            
            # For now, create a summary file
            async with session.put(
                f'https://api.github.com/repos/{docbook_full_name}/contents/{repo_name}/SUMMARY.md',
                headers=headers,
                json={
                    "message": commit_message,
                    "branch": "staging",
                    "content": base64.b64encode(
                        f"# {repo_name} Documentation\n\nGenerated by Lekhak AI".encode()
                    ).decode()
                }
            ) as resp:
                if resp.status not in [200, 201]:
                    error = await resp.text()
                    print(f"❌ Failed to publish: {resp.status} - {error}")
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to publish to docbook: {error}"
                    )
                
                commit_resp = await resp.json()
        
        print(f"✅ Published docs to {docbook_full_name}/staging")
        
        return {
            "status": "published_to_staging",
            "org_id": org_id,
            "repo_name": repo_name,
            "docbook_repo": docbook_full_name,
            "branch": "staging",
            "message": f"Documentation published to staging branch. Please review and approve to merge to main.",
            "review_url": f"{docbook['docbook_url']}/compare/main...staging"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error publishing to docbook: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

class MergeDocbookRequest(BaseModel):
    org_id: str
    repo_name: str  # Source repo name
    message: str = "docs: Approve and merge documentation"  # Merge commit message

@app.post("/docbook/approve-and-merge")
async def approve_and_merge_docbook(
    request: MergeDocbookRequest,
    user = Depends(get_current_user)
):
    """
    Approve and merge documentation from staging to main branch
    
    This endpoint:
    1. Gets the linked docbook repo
    2. Creates a pull request from staging → main
    3. Merges the PR (auto-merge)
    4. Returns confirmation
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        org_id = request.org_id
        repo_name = request.repo_name
        merge_message = request.message
        
        # Get user's GitHub token
        github_token = await auth_service.get_github_token(user_id)
        if not github_token:
            raise HTTPException(status_code=401, detail="No GitHub token found")
        
        # Get docbook repo info
        async with commit_bus.pool.acquire() as conn:
            docbook = await conn.fetchrow("""
                SELECT docbook_full_name, docbook_url
                FROM docbook_repos
                WHERE user_id = $1 AND org_id = $2 AND is_active = TRUE
            """, user_id, org_id)
        
        if not docbook:
            raise HTTPException(
                status_code=404,
                detail=f"No docbook linked for {org_id}"
            )
        
        docbook_full_name = docbook['docbook_full_name']
        
        # Merge staging → main using GitHub API
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Create merge commit
            merge_payload = {
                "base": "main",
                "head": "staging",
                "commit_message": merge_message
            }
            
            async with session.post(
                f'https://api.github.com/repos/{docbook_full_name}/merges',
                headers=headers,
                json=merge_payload
            ) as resp:
                if resp.status == 201:
                    merge_data = await resp.json()
                    print(f"✅ Merged staging → main in {docbook_full_name}")
                    return {
                        "status": "merged",
                        "org_id": org_id,
                        "repo_name": repo_name,
                        "docbook_repo": docbook_full_name,
                        "commit_sha": merge_data.get('sha'),
                        "message": "Documentation approved and merged to main branch!"
                    }
                elif resp.status == 204:
                    # No changes to merge
                    print(f"⚠️  No changes to merge in {docbook_full_name}")
                    return {
                        "status": "no_changes",
                        "org_id": org_id,
                        "message": "No changes to merge between staging and main"
                    }
                elif resp.status == 409:
                    # Conflict
                    error = await resp.text()
                    print(f"❌ Merge conflict in {docbook_full_name}")
                    raise HTTPException(
                        status_code=409,
                        detail=f"Merge conflict detected. Please resolve manually on GitHub."
                    )
                else:
                    error = await resp.text()
                    print(f"❌ Failed to merge: {resp.status} - {error}")
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to merge documentation: {error}"
                    )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error merging docbook: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/{repo_name}/docs")
async def get_repo_docs(repo_name: str):
    """Get repository documentation (legacy flat docs)"""
    # TODO: Integrate with hierarchical doc generator
    return {
        "summary": {"content": f"# {repo_name}\n\nDocumentation", "fileName": "README.md"},
        "readme": {"content": f"# {repo_name}", "fileName": "README.md"},
        "api": {"content": "# API Documentation", "fileName": "api.md"},
        "changelog": {"content": "# Changelog", "fileName": "CHANGELOG.md"},
        "changes": [],
    }

# ============================================
# HIERARCHICAL DOCUMENTATION ROUTES (NEW)
# ============================================
# These routes provide access to the hierarchical documentation tree
# Architecture: Repo → SDK → Module → Feature → Function → Class/Method
# Each level has AI-generated descriptions and maintains relationships

@app.get("/api/repos/{repo_name}/tree")
async def get_repo_tree(repo_name: str, commit_sha: str = None):
    """
    Get full hierarchical tree for a repository
    
    Returns the complete tree structure: Repo → SDK → Module → Feature → Function
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with commit_bus.pool.acquire() as conn:
            # Get latest commit if not specified
            if not commit_sha:
                # Try exact match first
                result = await conn.fetchrow("""
                    SELECT commit_sha FROM doc_nodes
                    WHERE repo_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, repo_name)
                
                # If not found, try partial match (e.g., "lekhak_ai" matches "AuditorEnvelope/lekhak_ai")
                if not result:
                    result = await conn.fetchrow("""
                        SELECT commit_sha FROM doc_nodes
                        WHERE repo_id LIKE $1
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, f"%{repo_name}")
                
                if result:
                    commit_sha = result['commit_sha']
                    # Also get the actual repo_id for subsequent queries
                    actual_repo = await conn.fetchval("""
                        SELECT repo_id FROM doc_nodes
                        WHERE commit_sha = $1
                        LIMIT 1
                    """, commit_sha)
                    repo_name = actual_repo
                else:
                    raise HTTPException(status_code=404, detail="No documentation found for this repository")
            
            # Get all nodes for this repo and commit
            nodes = await conn.fetch("""
                SELECT 
                    id, repo_id, type, title, slug, path,
                    parent_id, depth, position, commit_sha, version,
                    content, metadata, created_at
                FROM doc_nodes
                WHERE repo_id = $1 AND commit_sha = $2
                ORDER BY depth, position
            """, repo_name, commit_sha)
            
            if not nodes:
                raise HTTPException(status_code=404, detail="No documentation found")
            
            # Convert to dict and build tree structure
            nodes_dict = {str(node['id']): dict(node) for node in nodes}
            
            # Build tree
            root = None
            for node in nodes_dict.values():
                node['children'] = []
                if node['parent_id'] is None:
                    root = node
            
            for node in nodes_dict.values():
                if node['parent_id']:
                    parent = nodes_dict.get(str(node['parent_id']))
                    if parent:
                        parent['children'].append(node)
            
            return root if root else {}
            
    except Exception as e:
        print(f"Error fetching tree: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repos/{repo_name}/node/{node_id}")
async def get_node_details(repo_name: str, node_id: str):
    """Get details for a specific node (SDK/module/function)"""
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with commit_bus.pool.acquire() as conn:
            # Try to find the node by ID first (ID is unique)
            node = await conn.fetchrow("""
                SELECT 
                    id, repo_id, type, title, slug, path,
                    parent_id, depth, position, commit_sha, version,
                    content, metadata, created_at
                FROM doc_nodes
                WHERE id = $1
            """, node_id)
            
            # If found, verify it matches the repo (with partial match support)
            if node and not (node['repo_id'] == repo_name or repo_name in node['repo_id']):
                node = None
            
            if not node:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Get children
            children = await conn.fetch("""
                SELECT 
                    id, type, title, slug, path, position
                FROM doc_nodes
                WHERE parent_id = $1
                ORDER BY position
            """, node_id)
            
            result = dict(node)
            result['children'] = [dict(child) for child in children]
            
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def global_search(query: str):
    """Search across ALL documentation (global search)"""
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if not query or len(query) < 3:
        return []
    
    try:
        async with commit_bus.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    id, repo_id, type, title, slug, path,
                    content, created_at
                FROM doc_nodes
                WHERE 
                    title ILIKE $1 
                    OR content::text ILIKE $1
                    OR path ILIKE $1
                ORDER BY 
                    CASE 
                        WHEN title ILIKE $1 THEN 1
                        WHEN path ILIKE $1 THEN 2
                        ELSE 3
                    END,
                    created_at DESC
                LIMIT 50
            """, f"%{query}%")
            
            return [dict(r) for r in results]
            
    except Exception as e:
        print(f"Error in global search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repos/{repo_name}/search")
async def search_hierarchy(repo_name: str, query: str):
    """Search across hierarchical documentation for a specific repo"""
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if not query or len(query) < 3:
        return []
    
    try:
        async with commit_bus.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT 
                    id, repo_id, type, title, slug, path,
                    content, created_at
                FROM doc_nodes
                WHERE repo_id = $1
                AND (
                    title ILIKE $2 
                    OR content::text ILIKE $2
                    OR path ILIKE $2
                )
                ORDER BY 
                    CASE 
                        WHEN title ILIKE $2 THEN 1
                        WHEN path ILIKE $2 THEN 2
                        ELSE 3
                    END,
                    created_at DESC
                LIMIT 20
            """, repo_name, f"%{query}%")
            
            return [dict(r) for r in results]
            
    except Exception as e:
        print(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# COMMIT BUS ROUTES
# ============================================

@app.get("/events/stats")
async def get_event_stats():
    """Get commit bus statistics"""
    if not commit_bus:
        raise HTTPException(status_code=503, detail="Commit bus not available")
    
    stats = await commit_bus.get_stats()
    return stats

@app.post("/events/replay")
async def replay_events():
    """Replay unprocessed events"""
    if not commit_bus:
        raise HTTPException(status_code=503, detail="Commit bus not available")
    
    # TODO: Trigger event consumer
    return {"status": "replay_started"}

# ============================================
# SUBSCRIPTION ROUTES
# ============================================

@app.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    if not subscription_service:
        raise HTTPException(status_code=503, detail="Subscriptions not available")
    
    return await subscription_service.get_plans()

@app.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    """Get user subscription"""
    if not subscription_service:
        raise HTTPException(status_code=503, detail="Subscriptions not available")
    
    return await subscription_service.get_subscription(user_id)

@app.post("/subscription")
async def create_subscription(user_id: str, plan: str):
    """Create new subscription"""
    if not subscription_service:
        raise HTTPException(status_code=503, detail="Subscriptions not available")
    
    sub_id = await subscription_service.create_subscription(user_id, plan)
    return {"subscription_id": sub_id}

# ============================================
# OVERLAY ROUTES
# ============================================

@app.get("/doc/{node_id}")
async def get_doc_with_overlay(node_id: str):
    """Get documentation with overlays merged"""
    if not overlay_service:
        raise HTTPException(status_code=503, detail="Overlays not available")
    
    doc = await overlay_service.get_merged_doc(node_id)
    return doc

@app.post("/overlay")
async def create_overlay(
    node_id: str,
    content: dict,
    author_id: str,
    author_name: str,
    author_email: str,
    reason: str = None
):
    """Create or update overlay"""
    if not overlay_service:
        raise HTTPException(status_code=503, detail="Overlays not available")
    
    overlay_id = await overlay_service.create_overlay(
        node_id=node_id,
        content=content,
        author_id=author_id,
        author_name=author_name,
        author_email=author_email,
        reason=reason
    )
    return {"overlay_id": overlay_id}

# ============================================
# QUALITY CHECKING ROUTES
# ============================================

@app.post("/api/quality/check")
async def check_documentation_quality(
    repo_name: str,
    codebase_size: dict,
    docs: dict
):
    """
    Check documentation quality and get scores
    
    Args:
        repo_name: Repository name
        codebase_size: Dict of language -> line count
        docs: Dict of doc_type -> content
    
    Returns:
        Quality scores and feedback
    """
    if not quality_checker:
        raise HTTPException(status_code=503, detail="Quality checker not available")
    
    quality = await quality_checker.evaluate_documentation(
        repo_name=repo_name,
        codebase_size=codebase_size,
        docs=docs
    )
    
    return {
        "overall_score": quality.overall_score,
        "should_regenerate": quality.should_regenerate(),
        "low_quality_docs": quality.get_low_quality_docs(),
        "architecture": {
            "score": quality.architecture_score.score if quality.architecture_score else None,
            "feedback": quality.architecture_score.feedback if quality.architecture_score else None,
        } if quality.architecture_score else None,
        "workflow": {
            "score": quality.workflow_score.score if quality.workflow_score else None,
            "feedback": quality.workflow_score.feedback if quality.workflow_score else None,
        } if quality.workflow_score else None,
        "readme": {
            "score": quality.readme_score.score if quality.readme_score else None,
            "feedback": quality.readme_score.feedback if quality.readme_score else None,
        } if quality.readme_score else None,
        "api": {
            "score": quality.api_score.score if quality.api_score else None,
            "feedback": quality.api_score.feedback if quality.api_score else None,
        } if quality.api_score else None,
    }

@app.get("/api/quality/report/{repo_name}")
async def get_quality_report(repo_name: str):
    """Get detailed quality report for a repository"""
    if not quality_checker:
        raise HTTPException(status_code=503, detail="Quality checker not available")
    
    # TODO: Fetch docs from database or GitHub
    # For now, return placeholder
    return {
        "message": "Quality report generation - coming soon",
        "repo_name": repo_name
    }

# ============================================
# ADMIN ROUTES
# ============================================

@app.get("/admin/features")
async def list_features():
    """List all enabled features"""
    return {
        "core": [
            "GitHub webhook processing",
            "Multi-LLM support (Gemini, Groq, OpenAI)",
            "Smart documentation generation",
            "Pustak frontend integration",
            "AI Quality Validation (NEW)" if quality_checker else None,
        ],
        "advanced": [
            "Commit Bus (event store)" if commit_bus else None,
            "14+ language support" if True else None,
            "RAG system with embeddings" if True else None,
            "Admin overlays" if overlay_service else None,
            "Subscription management" if subscription_service else None,
            "Documentation Quality Checker" if quality_checker else None,
        ],
        "languages_supported": [
            "Python", "TypeScript", "JavaScript", "Go", "Rust", "Java",
            "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
            "Elixir", "Dart"
        ]
    }

@app.get("/admin/progress")
async def get_project_progress():
    """Get 5-week project progress tracking"""
    return {
        "project": "Lekhak AI - AI-Powered Documentation Platform",
        "timeline": "5 weeks",
        "current_week": 3,
        "weeks": [
            {
                "week": 1,
                "title": "Core Documentation System",
                "status": "completed",
                "progress": 100,
                "tasks": [
                    {"name": "GitHub webhook integration", "status": "done"},
                    {"name": "Multi-language code parsing", "status": "done"},
                    {"name": "Basic documentation generation", "status": "done"},
                    {"name": "Pustak frontend setup", "status": "done"},
                ]
            },
            {
                "week": 2,
                "title": "Advanced Features",
                "status": "completed",
                "progress": 100,
                "tasks": [
                    {"name": "Hierarchical documentation tree", "status": "done"},
                    {"name": "Version management (v1, v2, v3, v3.1, v3.2, v3.3)", "status": "done"},
                    {"name": "Commit bus with event storage", "status": "done"},
                    {"name": "Multi-LLM support (Gemini, Groq, OpenAI)", "status": "done"},
                ]
            },
            {
                "week": 3,
                "title": "Quality & Intelligence",
                "status": "in_progress",
                "progress": 60,
                "tasks": [
                    {"name": "AI quality validation system", "status": "done"},
                    {"name": "Auto-regeneration for low-quality docs", "status": "in_progress"},
                    {"name": "Quality scoring (0-10 scale)", "status": "done"},
                    {"name": "Feedback-driven improvements", "status": "pending"},
                ]
            },
            {
                "week": 4,
                "title": "Production Features",
                "status": "pending",
                "progress": 0,
                "tasks": [
                    {"name": "Subscription management", "status": "pending"},
                    {"name": "Admin overlays", "status": "pending"},
                    {"name": "RAG system with embeddings", "status": "pending"},
                    {"name": "Search functionality", "status": "pending"},
                ]
            },
            {
                "week": 5,
                "title": "Polish & Deployment",
                "status": "pending",
                "progress": 0,
                "tasks": [
                    {"name": "Performance optimization", "status": "pending"},
                    {"name": "Error handling & logging", "status": "pending"},
                    {"name": "Documentation & guides", "status": "pending"},
                    {"name": "Production deployment", "status": "pending"},
                ]
            }
        ],
        "overall_progress": 52,
        "quality_validation_enabled": quality_checker is not None
    }

# ============================================================================
# REPOSITORY SETTINGS ENDPOINTS
# ============================================================================

class UpdateDocPersonaRequest(BaseModel):
    doc_persona: str  # "internal" or "developer"

@app.post("/api/repositories/{repo_id}/doc-persona")
async def update_repo_doc_persona(
    repo_id: str,
    request: UpdateDocPersonaRequest,
    user = Depends(get_current_user)
):
    """
    Update doc_persona for a repository
    
    Args:
        repo_id: Repository ID (org/repo format)
        request: {doc_persona: "internal" or "developer"}
        user: Current authenticated user
        
    Returns:
        {status: "updated", repo_id: str, doc_persona: str}
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Validate doc_persona
    if request.doc_persona not in ["internal", "developer"]:
        raise HTTPException(
            status_code=400,
            detail="doc_persona must be 'internal' or 'developer'"
        )
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        async with commit_bus.pool.acquire() as conn:
            # Update doc_persona in repositories table
            result = await conn.execute("""
                UPDATE repositories
                SET doc_persona = $1, doc_persona_updated_at = NOW()
                WHERE repo_full_name = $2 AND user_id = $3
            """, request.doc_persona, repo_id, user_id)
            
            if result == "UPDATE 0":
                # Repository not found, try to create it
                await conn.execute("""
                    INSERT INTO repositories 
                    (user_id, org_id, repo_name, repo_full_name, doc_persona, doc_persona_updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (user_id, org_id, repo_full_name) DO UPDATE
                    SET doc_persona = $5, doc_persona_updated_at = NOW()
                """,
                user_id,
                repo_id.split('/')[0],  # org_id
                repo_id.split('/')[1],  # repo_name
                repo_id,  # repo_full_name
                request.doc_persona
                )
            
            print(f"✅ Updated doc_persona for {repo_id}: {request.doc_persona}")
        
        return {
            "status": "updated",
            "repo_id": repo_id,
            "doc_persona": request.doc_persona,
            "message": f"Documentation persona updated to '{request.doc_persona}'"
        }
        
    except Exception as e:
        print(f"❌ Error updating doc_persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repositories/{repo_id}/doc-persona")
async def get_repo_doc_persona(
    repo_id: str,
    user = Depends(get_current_user)
):
    """
    Get current doc_persona for a repository
    
    Returns:
        {repo_id: str, doc_persona: str}
    """
    if not commit_bus or not commit_bus.pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = user.get('id') if isinstance(user, dict) else user.id
        
        async with commit_bus.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT doc_persona FROM repositories
                WHERE repo_full_name = $1 AND user_id = $2
            """, repo_id, user_id)
            
            doc_persona = result['doc_persona'] if result else "internal"
            
            return {
                "repo_id": repo_id,
                "doc_persona": doc_persona
            }
            
    except Exception as e:
        print(f"❌ Error getting doc_persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 4: APP VERIFICATION & REPOSITORY LISTING ENDPOINTS
# ============================================================================

@app.get("/api/v1/org/{org_id}/verify-apps")
async def verify_apps(org_id: str, user = Depends(get_current_user)):
    """
    Verify both Reader and Writer apps are installed
    Returns installation status and access levels
    """
    try:
        dual_app = get_github_dual_app_helper()
        
        # Get user's GitHub token for verification
        github_token = await auth_service.get_github_token(user.id if hasattr(user, 'id') else user.get('id'))
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        # For now, return status based on environment configuration
        reader_installed = dual_app.dual_app_mode and bool(dual_app.reader_app_id)
        writer_installed = dual_app.dual_app_mode and bool(dual_app.writer_app_id)
        
        return {
            "reader_app": {
                "installed": reader_installed,
                "app_name": "Pustak Analyser AI",
                "app_id": dual_app.reader_app_id if reader_installed else None,
                "permissions": ["contents:read", "metadata:read"],
                "status": "ready" if reader_installed else "not_configured"
            },
            "writer_app": {
                "installed": writer_installed,
                "app_name": "Pustak Publisher AI",
                "app_id": dual_app.writer_app_id if writer_installed else None,
                "permissions": ["contents:read_write", "metadata:read"],
                "status": "ready" if writer_installed else "not_configured"
            },
            "dual_app_mode": dual_app.dual_app_mode,
            "fallback_mode": not dual_app.dual_app_mode
        }
    except Exception as e:
        logger.error(f"❌ Error verifying apps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/org/{org_id}/reader/repositories")
async def get_reader_repositories(org_id: str, user = Depends(get_current_user)):
    """
    Get list of repositories that Reader App can access
    Used to populate the "Select Repositories" dropdown in Step 4
    """
    try:
        # Get user's GitHub token
        user_id = user.id if hasattr(user, 'id') else user.get('id')
        github_token = await auth_service.get_github_token(user_id)
        
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        # Fetch repositories using user's token
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github+json',
            }
            
            url = f'https://api.github.com/user/repos'
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    repos = await response.json()
                    
                    # Filter and format repositories
                    formatted_repos = [
                        {
                            'id': repo['id'],
                            'name': repo['name'],
                            'full_name': repo['full_name'],
                            'url': repo['html_url'],
                            'private': repo['private'],
                            'description': repo['description'],
                            'language': repo['language']
                        }
                        for repo in repos
                    ]
                    
                    return {
                        "repositories": formatted_repos,
                        "count": len(formatted_repos),
                        "org_id": org_id
                    }
                else:
                    error = await response.text()
                    logger.error(f"❌ Failed to fetch repositories: {response.status} - {error}")
                    raise HTTPException(status_code=response.status, detail="Failed to fetch repositories")
    except Exception as e:
        logger.error(f"❌ Error fetching reader repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/org/{org_id}/setup-docbook")
async def setup_docbook(org_id: str, docbook_repo: str, user = Depends(get_current_user)):
    """
    User has created docbook repo, verify it exists and link it
    """
    try:
        user_id = user.id if hasattr(user, 'id') else user.get('id')
        
        # Get user's GitHub token
        github_token = await auth_service.get_github_token(user_id)
        if not github_token:
            raise HTTPException(status_code=401, detail="GitHub token not found")
        
        # Verify docbook repo exists
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github+json',
            }
            
            url = f'https://api.github.com/repos/{docbook_repo}'
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    repo_data = await response.json()
                    
                    # Store docbook repo in database
                    if commit_bus and commit_bus.pool:
                        async with commit_bus.pool.acquire() as conn:
                            await conn.execute("""
                                INSERT INTO docbook_repos (org_id, repo_name, repo_full_name, user_id, created_at)
                                VALUES ($1, $2, $3, $4, NOW())
                                ON CONFLICT (org_id) DO UPDATE SET repo_full_name = $3
                            """, org_id, repo_data['name'], docbook_repo, user_id)
                    
                    return {
                        "status": "success",
                        "message": f"Docbook repository {docbook_repo} linked",
                        "docbook_repo": docbook_repo,
                        "repo_data": {
                            "name": repo_data['name'],
                            "full_name": repo_data['full_name'],
                            "url": repo_data['html_url'],
                            "private": repo_data['private']
                        }
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Repository {docbook_repo} not found")
    except Exception as e:
        logger.error(f"❌ Error setting up docbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
