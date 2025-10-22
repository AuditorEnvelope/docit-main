"""
Lekhak AI - Main API Server
Handles GitHub webhooks and stores events in commit bus for processing
"""

import os
import hmac
import hashlib
import json
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Import services
from commit_bus import CommitBusService
from subscription_service import SubscriptionService
from overlay_service import OverlayService
from smart_processor import handle_push_event as legacy_handle_push
from quality_checker import DocumentationQualityChecker, DocumentationQuality

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

# Feature flags
HAS_COMMIT_BUS = True  # Always enable commit bus
HAS_SUBSCRIPTIONS = True  # Always enable subscriptions
HAS_OVERLAYS = True  # Always enable overlays

# Initialize services
commit_bus = None
subscription_service = None
overlay_service = None
quality_checker = None

@app.on_event("startup")
async def startup():
    """Initialize all services on startup"""
    global commit_bus, subscription_service, overlay_service, quality_checker
    
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
            from commit_bus import CommitEvent
            from datetime import datetime
            
            # Extract commit info from payload
            repo = payload.get('repository', {})
            commits = payload.get('commits', [])
            
            if commits:
                commit = commits[-1]  # Use last commit
                
                # Create CommitEvent object
                # Parse timestamp and convert to naive datetime for database
                timestamp_str = commit.get('timestamp', datetime.now().isoformat())
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Convert to naive datetime (remove timezone info)
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.replace(tzinfo=None)
                
                event = CommitEvent(
                    repo_id=repo.get('full_name', 'unknown'),
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
                    metadata={'payload': payload}
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
