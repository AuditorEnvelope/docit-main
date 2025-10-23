# STEP 3: Webhook Endpoint Integration Guide

## 📋 Overview

This guide shows how to integrate the new multi-org webhook endpoint into `main.py` **without breaking existing functionality**.

## ✅ What's Ready

- ✅ New webhook handler created: `src/webhook_multi_org.py`
- ✅ Backward compatible with single-org mode
- ✅ Supports multi-org mode when org_webhooks table has data
- ✅ Falls back to env var if no org webhook found

## 🔧 Integration Steps

### Step 1: Import the new webhook handler

**File:** `src/main.py`

**Add at the top with other imports:**

```python
from webhook_multi_org import webhook_multi_org
```

### Step 2: Replace the webhook endpoint

**File:** `src/main.py` (around line 408)

**BEFORE (Current):**
```python
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
```

**AFTER (New):**
```python
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
```

### Step 3: Update process_commit_event() function

**File:** `src/main.py` (around line 124)

**BEFORE (Current):**
```python
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
```

**AFTER (New - Only changes are marked with ✅):**
```python
async def process_commit_event(payload: dict):
    """Process commit event through commit bus or legacy processor"""
    
    # ✅ NEW: Extract webhook context if available (multi-org mode)
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
                    metadata={'payload': payload},
                    # ✅ NEW: Add webhook context if available (multi-org mode)
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
```

## ✅ Verification Checklist

After integration, verify:

- [ ] Webhook endpoint still receives events
- [ ] Old events (without webhook context) still work
- [ ] New events include user_id, org_id, github_token_id
- [ ] Doc generation still works
- [ ] No errors in logs
- [ ] Event consumer can read new fields

## 🔄 Backward Compatibility

✅ **Fully backward compatible:**
- Old events have NULL user_id/org_id/github_token_id
- Event consumer handles both old and new events
- Falls back to env var WEBHOOK_SECRET if no org webhook found
- Existing code continues to work unchanged

## 🚀 What Happens Next

After this step is integrated:

1. **Old mode (single-org):** Uses WEBHOOK_SECRET from env
2. **New mode (multi-org):** Uses org-specific webhook_secret from database
3. **Events now include:** user_id, org_id, github_token_id
4. **Event consumer can:** Route to correct GitHub token per org

## ⚠️ Important Notes

- **Do NOT delete** the old webhook endpoint code
- **Do NOT modify** doc generation logic
- **Do NOT change** event consumer yet (that's Step 4)
- **Just replace** the webhook endpoint function
- **Just update** the process_commit_event function

## 📝 Files to Modify

1. `src/main.py` - Import + replace webhook endpoint + update process_commit_event
2. That's it! Everything else stays the same.

## 🆘 If Something Breaks

1. Revert the changes to `src/main.py`
2. The migration and CommitEvent changes are still there (safe)
3. Old webhook will work again
4. No data loss

---

**Ready to integrate? Follow the steps above and test!** ✅
