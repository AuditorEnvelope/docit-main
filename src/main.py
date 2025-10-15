"""
Lekhak AI - Production Main Application
Integrates all services: Webhooks, Commit Bus, Doc Generation, RAG, Overlays, Subscriptions
"""

import os
import hmac
import hashlib
import json
from fastapi import FastAPI, Header, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio

# Import existing services
from smart_processor import handle_push_event as legacy_handle_push

# Import new services (optional - graceful degradation)
try:
    from commit_bus import CommitBusService
    from event_consumer import EventConsumer
    HAS_COMMIT_BUS = True
except ImportError:
    HAS_COMMIT_BUS = False
    print("⚠️  Commit Bus not available (missing dependencies)")

try:
    from subscription_service import SubscriptionService
    HAS_SUBSCRIPTIONS = True
except ImportError:
    HAS_SUBSCRIPTIONS = False
    print("⚠️  Subscriptions not available (missing database)")

try:
    from overlay_service import OverlayService
    HAS_OVERLAYS = True
except ImportError:
    HAS_OVERLAYS = False
    print("⚠️  Overlays not available (missing database)")

load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Lekhak AI",
    description="Production-grade AI-first documentation platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/lekhak_ai")

# Initialize services
commit_bus = None
subscription_service = None
overlay_service = None

@app.on_event("startup")
async def startup():
    """Initialize all services on startup"""
    global commit_bus, subscription_service, overlay_service
    
    print("🚀 Starting Lekhak AI...")
    
    # Initialize Commit Bus
    if HAS_COMMIT_BUS:
        try:
            commit_bus = CommitBusService(DATABASE_URL)
            await commit_bus.init_db()
            print("✅ Commit Bus initialized")
        except Exception as e:
            print(f"⚠️  Commit Bus failed: {e}")
            commit_bus = None
    
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
    
    # Try commit bus first (durable, never loses commits)
    if commit_bus:
        try:
            event_id = await commit_bus.store_event(
                event_type="push",
                repo_id=payload.get('repository', {}).get('full_name', 'unknown'),
                payload=payload
            )
            print(f"✅ Event stored in commit bus: {event_id}")
            return {"status": "queued", "event_id": event_id}
        except Exception as e:
            print(f"⚠️  Commit bus failed, falling back to legacy: {e}")
    
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
    """GitHub webhook handler"""
    
    # Verify signature
    body = await request.body()
    if not verify_signature(WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    payload = json.loads(body)
    
    # Handle push events
    if x_github_event == "push":
        # Process in background
        background_tasks.add_task(process_commit_event, payload)
        return {"status": "accepted"}
    
    return {"status": "ignored", "event": x_github_event}

@app.get("/repos/{repo_name}/docs")
async def get_repo_docs(repo_name: str):
    """Get repository documentation"""
    # TODO: Integrate with hierarchical doc generator
    return {
        "summary": {"content": f"# {repo_name}\n\nDocumentation", "fileName": "README.md"},
        "readme": {"content": f"# {repo_name}", "fileName": "README.md"},
        "api": {"content": "# API Documentation", "fileName": "api.md"},
        "changelog": {"content": "# Changelog", "fileName": "CHANGELOG.md"},
        "changes": [],
    }

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
        ],
        "advanced": [
            "Commit Bus (event store)" if commit_bus else None,
            "14+ language support" if True else None,
            "RAG system with embeddings" if True else None,
            "Admin overlays" if overlay_service else None,
            "Subscription management" if subscription_service else None,
        ],
        "languages_supported": [
            "Python", "TypeScript", "JavaScript", "Go", "Rust", "Java",
            "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
            "Elixir", "Dart"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
