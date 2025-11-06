"""
Multi-Org Webhook Handler
Supports both single-org (legacy) and multi-org modes

INTEGRATION INSTRUCTIONS:
1. This file contains the NEW webhook endpoint
2. Replace the @app.post("/webhook") function in main.py with this code
3. Keep all other code in main.py unchanged
4. The new endpoint is backward compatible - old events still work
"""

import os
import json
import hmac
import hashlib
from fastapi import Request, HTTPException, BackgroundTasks
from datetime import datetime

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def verify_signature(secret: str, payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False
    sha_name, sig = signature.split('=')
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)


async def get_org_webhook_context(db_pool, signature: str):
    """
    Look up org webhook context from database
    
    Returns: {user_id, org_id, webhook_secret, github_token_id} or None
    """
    if not signature or '=' not in signature:
        return None
    
    try:
        # Extract secret from signature (format: "sha256=xxxxx")
        secret_from_sig = signature.split('=')[1]
        
        # Look up in org_webhooks table
        async with db_pool.acquire() as conn:
            webhook_record = await conn.fetchrow("""
                SELECT user_id, org_id, webhook_secret, github_token_id
                FROM org_webhooks
                WHERE webhook_secret = $1
            """, secret_from_sig)
            
            return webhook_record
    except Exception as e:
        print(f"⚠️  Error looking up org webhook: {e}")
        return None


async def get_org_context_from_repo(db_pool, repo_full_name: str):
    """
    Get org context from repository name when webhook is not registered
    This is the KEY for multi-org support without registered webhooks
    
    Args:
        db_pool: Database connection pool
        repo_full_name: Full repository name (e.g., "AuditorEnvelope/lekhak_ai")
    
    Returns: {user_id, org_id, github_token_id} or None
    """
    if not repo_full_name or '/' not in repo_full_name:
        return None
    
    org_id = repo_full_name.split('/')[0]
    
    try:
        async with db_pool.acquire() as conn:
            # First try to find in org_webhooks table
            org_record = await conn.fetchrow("""
                SELECT user_id, org_id, github_token_id
                FROM org_webhooks
                WHERE org_id = $1
                LIMIT 1
            """, org_id)
            
            if org_record:
                return dict(org_record)
            
            # If not found, check org_registrations (newly registered orgs)
            reg_record = await conn.fetchrow("""
                SELECT user_id, org_id FROM org_registrations
                WHERE org_id = $1
                LIMIT 1
            """, org_id)
            
            if reg_record:
                # Found in registrations, get their token
                token_record = await conn.fetchrow("""
                    SELECT token_id FROM user_github_tokens
                    WHERE user_id = $1
                    LIMIT 1
                """, reg_record['user_id'])
                
                if token_record:
                    return {
                        'user_id': reg_record['user_id'],
                        'org_id': org_id,
                        'github_token_id': token_record['token_id']
                    }
            
            # If not found, try to find any user with access to this org
            # Look for users who have successfully processed this org's repos before
            user_record = await conn.fetchrow("""
                SELECT ce.user_id, ce.org_id
                FROM commit_events ce
                WHERE ce.org_id = $1 
                  AND ce.user_id IS NOT NULL
                  AND ce.processed = true
                ORDER BY ce.created_at DESC
                LIMIT 1
            """, org_id)
            
            if user_record:
                # Found a user who has processed this org before
                # Auto-register this org for future use
                try:
                    await conn.execute("""
                        INSERT INTO org_webhooks (user_id, org_id, webhook_secret, github_token_id)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id, org_id) DO UPDATE
                        SET updated_at = NOW()
                    """, user_record['user_id'], org_id, 
                    'webhook_' + org_id,  # Simple webhook secret
                    None)  # Will use main token
                    
                    print(f"🎆 Auto-registered org {org_id} for user {user_record['user_id']}")
                except Exception as e:
                    print(f"⚠️  Could not auto-register org: {e}")
                
                return {
                    'user_id': user_record['user_id'],
                    'org_id': org_id,
                    'github_token_id': None  # Will use user's main token
                }
            
        return None
    except Exception as e:
        print(f"⚠️  Error getting org context: {e}")
        return None


# ============================================================================
# NEW WEBHOOK ENDPOINT - MULTI-ORG SUPPORT
# ============================================================================

async def webhook_multi_org(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = None,
    x_github_event: str = None,
    db_pool = None,  # Pass from main.py: commit_bus.pool
    process_commit_event_func = None  # Pass from main.py: process_commit_event
):
    """
    GitHub webhook handler with multi-org support
    
    FLOW:
    1. Try to find org-specific webhook (new multi-org mode)
    2. Fall back to env var webhook secret (old single-org mode)
    3. Verify signature with appropriate secret
    4. Extract user_id/org_id if available
    5. Store event with context
    
    Args:
        request: FastAPI request
        background_tasks: FastAPI background tasks
        x_hub_signature_256: GitHub webhook signature header
        x_github_event: GitHub event type header
        db_pool: Database connection pool (from commit_bus)
        process_commit_event_func: Function to process events
    """
    
    body = await request.body()
    payload = json.loads(body)
    
    # ========================================================================
    # STEP 1: Try multi-org mode (look up org webhook)
    # ========================================================================
    
    webhook_context = None
    webhook_secret = None
    
    if db_pool and x_hub_signature_256:
        webhook_context = await get_org_webhook_context(db_pool, x_hub_signature_256)
        
        if webhook_context:
            webhook_secret = webhook_context['webhook_secret']
            print(f"✅ Multi-org mode: Found webhook for org {webhook_context['org_id']}")
    
    # ========================================================================
    # STEP 2: Fall back to single-org mode (env var)
    # ========================================================================
    
    if not webhook_secret:
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        if webhook_secret:
            print(f"⚠️  Single-org mode: Using GITHUB_WEBHOOK_SECRET from env")
    
    # ========================================================================
    # STEP 3: Verify signature
    # ========================================================================
    
    if not webhook_secret:
        print(f"❌ No webhook secret found (multi-org or env)")
        raise HTTPException(status_code=403, detail="No webhook secret configured")
    
    if not verify_signature(webhook_secret, body, x_hub_signature_256):
        print(f"❌ Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    print(f"✅ Webhook signature verified")
    
    # ========================================================================
    # STEP 4: Handle installation events (store app repo access)
    # ========================================================================
    
    if x_github_event == "installation":
        try:
            action = payload.get("action")
            installation = payload.get("installation", {})
            repositories = payload.get("repositories", [])
            
            if action in ["created", "updated"] and db_pool:
                # Store app installation in database
                from core.app_installation_service import AppInstallationService
                
                app_install_service = AppInstallationService(db_pool)
                org_id = installation.get("account", {}).get("login")
                app_id = installation.get("app_id")
                installation_id = installation.get("id")
                repository_selection = installation.get("repository_selection", "all")
                
                if org_id and app_id:
                    success = await app_install_service.store_app_installation(
                        org_id=org_id,
                        app_id=app_id,
                        installation_id=installation_id,
                        repository_selection=repository_selection,
                        repositories=repositories,
                        user_id=None  # Will be filled by webhook context if available
                    )
                    
                    if success:
                        print(f"✅ Stored app installation: org={org_id}, app={app_id}, repos={len(repositories)}")
                    else:
                        print(f"⚠️  Failed to store app installation")
        except Exception as e:
            print(f"⚠️  Error handling installation event: {e}")
            import traceback
            traceback.print_exc()
        
        return {"status": "accepted", "event": "installation"}
    
    # ========================================================================
    # STEP 5: Handle push events
    # ========================================================================
    
    if x_github_event == "push":
        # Add context to payload if available (multi-org mode)
        if webhook_context:
            payload['_webhook_context'] = {
                'user_id': str(webhook_context['user_id']),
                'org_id': webhook_context['org_id'],
                'github_token_id': str(webhook_context['github_token_id']) if webhook_context.get('github_token_id') else None,
                'webhook_secret': webhook_context.get('webhook_secret')
            }
            print(f"📝 Added webhook context to payload: user_id={webhook_context['user_id']}, org_id={webhook_context['org_id']}")
        else:
            # CRITICAL: For unregistered webhooks, get org context from repo name
            # This enables multi-org support without pre-registering webhooks
            repo = payload.get('repository', {})
            repo_full_name = repo.get('full_name', '')
            
            if db_pool and repo_full_name:
                org_context = await get_org_context_from_repo(db_pool, repo_full_name)
                if org_context:
                    payload['_webhook_context'] = {
                        'user_id': str(org_context['user_id']),
                        'org_id': org_context['org_id'],
                        'github_token_id': str(org_context['github_token_id']) if org_context.get('github_token_id') else None,
                        'webhook_secret': None  # No registered webhook
                    }
                    print(f"🎯 Extracted org context from repo {repo_full_name}: user_id={org_context['user_id']}, org_id={org_context['org_id']}")
                else:
                    print(f"⚠️  No org context found for {repo_full_name}, will use ENV token (fallback)")
        
        # Process in background
        background_tasks.add_task(process_commit_event_func, payload)
        return {"status": "accepted"}
    
    return {"status": "ignored", "event": x_github_event}


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================
"""
HOW TO INTEGRATE INTO main.py:

1. Import this function at the top of main.py:
   from webhook_multi_org import webhook_multi_org

2. Replace the existing @app.post("/webhook") endpoint with:

   @app.post("/webhook")
   async def webhook(
       request: Request,
       background_tasks: BackgroundTasks,
       x_hub_signature_256: str = Header(None),
       x_github_event: str = Header(None)
   ):
       return await webhook_multi_org(
           request=request,
           background_tasks=background_tasks,
           x_hub_signature_256=x_hub_signature_256,
           x_github_event=x_github_event,
           db_pool=commit_bus.pool if commit_bus else None,
           process_commit_event_func=process_commit_event
       )

3. Update process_commit_event() in main.py to handle webhook context:

   async def process_commit_event(payload: dict):
       # Extract webhook context if available (multi-org mode)
       webhook_context = payload.pop('_webhook_context', None)
       
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
                   
                   # Parse timestamp
                   timestamp_str = commit.get('timestamp', datetime.now().isoformat())
                   timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                   if timestamp.tzinfo is not None:
                       timestamp = timestamp.replace(tzinfo=None)
                   
                   # Create CommitEvent with webhook context (if available)
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
                       metadata={'payload': payload},
                       # NEW: Add webhook context if available
                       user_id=webhook_context.get('user_id') if webhook_context else None,
                       org_id=webhook_context.get('org_id') if webhook_context else None,
                       github_token_id=webhook_context.get('github_token_id') if webhook_context else None,
                       webhook_secret=webhook_context.get('webhook_secret') if webhook_context else None
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

BACKWARD COMPATIBILITY:
- Old events (without webhook context) still work
- webhook_context is optional (defaults to None)
- Falls back to env var GITHUB_WEBHOOK_SECRET if no org webhook found
- Existing code continues to function unchanged
"""
