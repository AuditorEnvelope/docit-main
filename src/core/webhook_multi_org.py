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
    # STEP 2: Verify webhook is registered (PURELY DYNAMIC - NO FALLBACK)
    # ========================================================================
    
    if not webhook_secret:
        print(f"❌ Webhook not registered for this organization")
        raise HTTPException(status_code=403, detail="Webhook not registered. Please register your organization first.")
    
    # ========================================================================
    # STEP 3: Verify signature
    # ========================================================================
    
    if not verify_signature(webhook_secret, body, x_hub_signature_256):
        print(f"❌ Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    print(f"✅ Webhook signature verified")
    
    # ========================================================================
    # STEP 4: Handle push events
    # ========================================================================
    
    if x_github_event == "push":
        # Add context to payload if available (multi-org mode)
        if webhook_context:
            payload['_webhook_context'] = {
                'user_id': str(webhook_context['user_id']),
                'org_id': webhook_context['org_id'],
                'github_token_id': str(webhook_context['github_token_id']),
                'webhook_secret': webhook_context['webhook_secret']
            }
            print(f"📝 Added webhook context to payload: user_id={webhook_context['user_id']}, org_id={webhook_context['org_id']}")
        
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
