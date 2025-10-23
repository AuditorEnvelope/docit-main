# STEP 4: Event Consumer Integration Guide

## 📋 Overview

This guide shows how to integrate the new multi-org event consumer into `event_consumer.py` **without breaking existing functionality**.

## ✅ What's Ready

- ✅ New `get_github_token()` method created
- ✅ Updated `process_event()` method created
- ✅ Backward compatible with single-org mode
- ✅ Supports multi-org mode when tokens in database

## 🔧 Integration Steps

### Step 1: Add the new get_github_token() method

**File:** `src/event_consumer.py`

**Add this method to the EventConsumer class (around line 250):**

```python
async def get_github_token(self, user_id: str, token_id: str) -> Optional[str]:
    """
    Get decrypted GitHub token for user/org
    
    Args:
        user_id: UUID of user
        token_id: UUID of token record
    
    Returns:
        GitHub token string or None if not found
    """
    try:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT github_token FROM user_github_tokens
                WHERE user_id = $1 AND token_id = $2 AND is_active = TRUE
            """, user_id, token_id)
            
            if result:
                token = result['github_token']
                # TODO: Decrypt token here if encrypted in database
                return token
            
            return None
    except Exception as e:
        print(f"⚠️  Error getting GitHub token: {e}")
        return None
```

### Step 2: Replace the process_event() method

**File:** `src/event_consumer.py` (around line 122)

**BEFORE (Current):**
```python
async def process_event(self, event: dict) -> bool:
    """
    Process a single event
    
    Returns: True if successful, False if failed
    """
    event_id = str(event["event_id"])
    started_at = datetime.now()
    
    try:
        print(f"\n{'='*60}")
        print(f"📝 Processing event: {event_id}")
        print(f"   Repo: {event['repo_id']}")
        print(f"   Commit: {event['commit_sha'][:8]}")
        print(f"   Message: {event['commit_message'][:50]}...")
        print(f"{'='*60}")
        
        # Log start
        await self.log_processing(event_id, "started", started_at)
        
        # Convert to webhook format
        payload = self.convert_to_webhook_payload(event)
        
        # Process using existing smart_processor
        # This is synchronous, so we run it in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, 
            handle_push_event, 
            payload
        )
        
        # Mark as processed
        await self.bus.mark_processed(event_id, success=True)
        
        # Log completion
        await self.log_processing(event_id, "completed", started_at)
        
        print(f"✅ Event {event_id} processed successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error processing event {event_id}: {error_msg}")
        
        # Mark as failed (increments retry_count)
        await self.bus.mark_processed(event_id, success=False, error=error_msg)
        
        # Log failure
        await self.log_processing(event_id, "failed", started_at, error=error_msg)
        
        return False
```

**AFTER (New - Changes marked with ✅):**
```python
async def process_event(self, event: dict) -> bool:
    """
    Process a single event with multi-org support
    
    Returns: True if successful, False if failed
    """
    event_id = str(event["event_id"])
    started_at = datetime.now()
    
    try:
        print(f"\n{'='*60}")
        print(f"📝 Processing event: {event_id}")
        print(f"   Repo: {event['repo_id']}")
        print(f"   Commit: {event['commit_sha'][:8]}")
        print(f"   Message: {event['commit_message'][:50]}...")
        print(f"{'='*60}")
        
        # Log start
        await self.log_processing(event_id, "started", started_at)
        
        # ✅ NEW: Extract context (multi-org mode)
        user_id = event.get("user_id")
        org_id = event.get("org_id")
        token_id = event.get("github_token_id")
        
        # ✅ NEW: Get GitHub token
        github_token = None
        
        # Try multi-org mode first (get token for this user/org)
        if user_id and token_id:
            github_token = await self.get_github_token(user_id, token_id)
            
            if github_token:
                print(f"✅ Got GitHub token for user {user_id} org {org_id}")
            else:
                print(f"⚠️  No GitHub token found for user {user_id} org {org_id}")
        
        # Fall back to env var (single-org mode)
        if not github_token:
            github_token = os.getenv("GITHUB_TOKEN")
            
            if github_token:
                print(f"⚠️  Using GITHUB_TOKEN from env (single-org mode)")
            else:
                print(f"❌ No GitHub token available (multi-org or env)")
                raise Exception(f"No GitHub token for user {user_id}")
        
        # Convert to webhook format
        payload = self.convert_to_webhook_payload(event)
        
        # ✅ NEW: Process using existing smart_processor with token
        # This is synchronous, so we run it in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, 
            handle_push_event, 
            payload,
            github_token  # ✅ Pass token to smart_processor
        )
        
        # Mark as processed
        await self.bus.mark_processed(event_id, success=True)
        
        # Log completion
        await self.log_processing(event_id, "completed", started_at)
        
        print(f"✅ Event {event_id} processed successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error processing event {event_id}: {error_msg}")
        
        # Mark as failed (increments retry_count)
        await self.bus.mark_processed(event_id, success=False, error=error_msg)
        
        # Log failure
        await self.log_processing(event_id, "failed", started_at, error=error_msg)
        
        return False
```

### Step 3: Update smart_processor.handle_push_event()

**File:** `src/smart_processor.py` (around line 41)

**BEFORE (Current):**
```python
def handle_push_event(payload):
    """Enhanced push event handler with smart analysis"""
    repo = payload.get("repository", {})
    repo_full = repo.get("full_name")
    # ... rest of function uses os.getenv("GITHUB_TOKEN")
```

**AFTER (New):**
```python
def handle_push_event(payload, github_token=None):
    """Enhanced push event handler with smart analysis"""
    # ✅ NEW: Accept github_token parameter
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    
    repo = payload.get("repository", {})
    repo_full = repo.get("full_name")
    # ... rest of function uses github_token parameter
```

**Then update all uses of `os.getenv("GITHUB_TOKEN")` in smart_processor.py to use the `github_token` parameter instead.**

## ✅ Verification Checklist

After integration, verify:

- [ ] Event consumer starts without errors
- [ ] Old events (without user_id/org_id) still process
- [ ] New events with user_id/org_id use correct token
- [ ] Falls back to env var GITHUB_TOKEN if no token_id
- [ ] Doc generation still works
- [ ] No errors in logs
- [ ] Events marked as processed/failed correctly

## 🔄 Backward Compatibility

✅ **Fully backward compatible:**
- Old events have NULL user_id/org_id/token_id
- Falls back to env var GITHUB_TOKEN if no token_id
- Existing smart_processor logic unchanged
- No breaking changes

## 🚀 What Happens After This Step

After this step is integrated:

1. **Event Consumer polls** database every 5 seconds
2. **For each event:**
   - Extracts user_id, org_id, github_token_id
   - Looks up GitHub token in user_github_tokens table
   - Falls back to env var if not found
3. **Passes correct token** to smart_processor
4. **smart_processor uses** correct token for this org
5. **Docs are generated** and pushed with correct permissions
6. **Multi-org support works!** ✅

## ⚠️ Important Notes

- **Do NOT delete** the old process_event() code
- **Do NOT modify** smart_processor logic beyond accepting token parameter
- **Do NOT change** other event consumer methods
- **Just add** the new get_github_token() method
- **Just replace** the process_event() method
- **Just update** smart_processor to accept token parameter

## 📝 Files to Modify

1. `src/event_consumer.py` - Add method + replace process_event()
2. `src/smart_processor.py` - Accept token parameter + use it
3. That's it! Everything else stays the same.

## 🆘 If Something Breaks

1. Revert changes to `src/event_consumer.py`
2. Revert changes to `src/smart_processor.py`
3. All previous steps still work (migration, CommitEvent, webhook)
4. Old event consumer will work again
5. No data loss

---

**Ready to integrate? Follow the steps above and test!** ✅
