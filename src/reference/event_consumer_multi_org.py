"""
Multi-Org Event Consumer
Processes events with per-org GitHub token support

INTEGRATION INSTRUCTIONS:
1. This file contains the NEW process_event() method
2. Replace the existing process_event() method in event_consumer.py with this code
3. Add the new get_github_token() method to the EventConsumer class
4. Keep all other code unchanged
"""

import asyncio
import os
from datetime import datetime
from typing import Optional


# ============================================================================
# NEW METHOD 1: Get GitHub Token for User/Org
# ============================================================================

async def get_github_token(self, user_id: str, token_id: str) -> Optional[str]:
    """
    Get decrypted GitHub token for user/org
    
    Args:
        user_id: UUID of user
        token_id: UUID of token record
    
    Returns:
        GitHub token string or None if not found
    
    NOTES:
    - In production, tokens should be encrypted in database
    - For now, we store them as-is (TODO: add encryption)
    - This method can be extended to decrypt tokens
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


# ============================================================================
# NEW METHOD 2: Updated process_event() with Multi-Org Support
# ============================================================================

async def process_event(self, event: dict) -> bool:
    """
    Process a single event with multi-org support
    
    FLOW:
    1. Extract event_id and context (user_id, org_id, token_id)
    2. Get GitHub token for this user/org
    3. Convert event to webhook format
    4. Process using smart_processor
    5. Mark as processed or failed
    
    Returns: True if successful, False if failed
    
    BACKWARD COMPATIBLE:
    - Old events (without user_id/org_id) still work
    - Falls back to env var GITHUB_TOKEN if no token_id
    - Existing logic unchanged
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
        
        # ====================================================================
        # STEP 1: Extract context (multi-org mode)
        # ====================================================================
        
        user_id = event.get("user_id")
        org_id = event.get("org_id")
        token_id = event.get("github_token_id")
        
        # ====================================================================
        # STEP 2: Get GitHub token
        # ====================================================================
        
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
        
        # ====================================================================
        # STEP 3: Convert to webhook format
        # ====================================================================
        
        payload = self.convert_to_webhook_payload(event)
        
        # ====================================================================
        # STEP 4: Process using smart_processor
        # ====================================================================
        
        print(f"🔄 Processing with smart_processor...")
        
        # This is synchronous, so we run it in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, 
            handle_push_event,  # This function needs to accept github_token
            payload,
            github_token  # Pass token to smart_processor
        )
        
        # ====================================================================
        # STEP 5: Mark as processed
        # ====================================================================
        
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


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================

"""
HOW TO INTEGRATE INTO event_consumer.py:

1. Add the new get_github_token() method to EventConsumer class:

   async def get_github_token(self, user_id: str, token_id: str) -> Optional[str]:
       \"\"\"Get decrypted GitHub token for user/org\"\"\"
       try:
           async with self.pool.acquire() as conn:
               result = await conn.fetchrow(\"\"\"
                   SELECT github_token FROM user_github_tokens
                   WHERE user_id = $1 AND token_id = $2 AND is_active = TRUE
               \"\"\", user_id, token_id)
               
               if result:
                   token = result['github_token']
                   # TODO: Decrypt token here if encrypted in database
                   return token
               
               return None
       except Exception as e:
           print(f\"⚠️  Error getting GitHub token: {e}\")
           return None

2. Replace the existing process_event() method in EventConsumer class with the new one

3. Update the handle_push_event() call to pass the github_token:
   
   OLD:
   handle_push_event(payload)
   
   NEW:
   handle_push_event(payload, github_token)

4. Update smart_processor.handle_push_event() to accept github_token parameter:
   
   OLD:
   def handle_push_event(payload):
   
   NEW:
   def handle_push_event(payload, github_token=None):
       if github_token:
           # Use provided token
       else:
           # Fall back to env var
           github_token = os.getenv("GITHUB_TOKEN")

BACKWARD COMPATIBILITY:
- Old events (without user_id/org_id/token_id) still work
- Falls back to env var GITHUB_TOKEN if no token_id
- Existing smart_processor logic unchanged
- No breaking changes

WHAT THIS DOES:
1. Extracts user_id, org_id, github_token_id from event
2. Looks up GitHub token in user_github_tokens table
3. Falls back to env var if not found
4. Passes token to smart_processor
5. smart_processor uses correct token for this org
6. Docs are generated and pushed with correct permissions
"""
