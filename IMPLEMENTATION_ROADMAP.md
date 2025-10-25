# 🛣️ MULTI-ORG IMPLEMENTATION ROADMAP

## **OVERVIEW**

This document outlines the exact steps to implement multi-org support in the Lekhak AI system.

**Current State:** Single-org (PUSTAK only)
**Target State:** Multi-org (1000+ organizations)
**Estimated Time:** 9-12 hours
**Complexity:** Medium (straightforward changes, good test coverage needed)

---

## **PHASE 1: DATABASE SCHEMA (1 hour)**

### **1.1 Create org_webhooks table**

```sql
CREATE TABLE org_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    org_id VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255) UNIQUE NOT NULL,
    github_token_id UUID NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id),
    FOREIGN KEY (github_token_id) REFERENCES user_github_tokens(token_id)
);

CREATE INDEX idx_org_webhooks_secret ON org_webhooks(webhook_secret);
CREATE INDEX idx_org_webhooks_user_org ON org_webhooks(user_id, org_id);
```

### **1.2 Create user_github_tokens table**

```sql
CREATE TABLE user_github_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    org_id VARCHAR(255),
    github_token TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX idx_user_tokens_user ON user_github_tokens(user_id);
CREATE INDEX idx_user_tokens_user_token ON user_github_tokens(user_id, token_id);
```

### **1.3 Alter commit_events table**

```sql
ALTER TABLE commit_events
ADD COLUMN user_id UUID,
ADD COLUMN org_id VARCHAR(255),
ADD COLUMN github_token_id UUID;

CREATE INDEX idx_commit_events_org ON commit_events(org_id);
CREATE INDEX idx_commit_events_user_org ON commit_events(user_id, org_id);
```

---

## **PHASE 2: WEBHOOK REGISTRATION ENDPOINT (2 hours)**

### **2.1 Add endpoint to main.py**

```python
# main.py - Add this endpoint

from pydantic import BaseModel
import secrets
from uuid import uuid4

class WebhookRegisterRequest(BaseModel):
    org_id: str
    github_token: str

@app.post("/webhook/register")
async def register_webhook(
    request: WebhookRegisterRequest,
    user = Depends(get_current_user)
):
    """
    Register webhook for an organization
    
    Flow:
    1. Verify user is authenticated
    2. Generate unique webhook_secret
    3. Store org context in database
    4. Return webhook URL + secret
    """
    
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth service not available")
    
    try:
        # Extract user_id
        user_id = user.get('id') if isinstance(user, dict) else user.id
        org_id = request.org_id
        github_token = request.github_token
        
        print(f"📝 Registering webhook for org: {org_id}")
        
        # Step 1: Generate unique webhook_secret
        webhook_secret = secrets.token_urlsafe(32)
        
        # Step 2: Store token in user_github_tokens
        async with commit_bus.pool.acquire() as conn:
            token_id = await conn.fetchval("""
                INSERT INTO user_github_tokens (user_id, org_id, github_token, is_active)
                VALUES ($1, $2, $3, TRUE)
                RETURNING token_id
            """, user_id, org_id, github_token)
            
            # Step 3: Store webhook registration
            await conn.execute("""
                INSERT INTO org_webhooks (user_id, org_id, webhook_secret, github_token_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, org_id) DO UPDATE
                SET webhook_secret = $3, github_token_id = $4, updated_at = NOW()
            """, user_id, org_id, webhook_secret, token_id)
        
        print(f"✅ Webhook registered for org: {org_id}")
        
        # Step 4: Return webhook URL
        return {
            "status": "success",
            "webhook_url": "https://yourdomain.com/webhook",
            "webhook_secret": webhook_secret,
            "instructions": "Configure this in GitHub org settings > Webhooks",
            "events": ["push"],
            "content_type": "json"
        }
        
    except Exception as e:
        print(f"❌ Error registering webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## **PHASE 3: MULTI-ORG WEBHOOK HANDLER (1 hour)**

### **3.1 Update webhook_multi_org.py**

The file already exists and is being used. Just verify it's correct:

```python
# webhook_multi_org.py - Already exists, verify it has:

async def get_org_webhook_context(db_pool, signature: str):
    """Look up org webhook context from database"""
    if not signature or '=' not in signature:
        return None
    
    try:
        secret_from_sig = signature.split('=')[1]
        
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

async def webhook_multi_org(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = None,
    x_github_event: str = None,
    db_pool = None,
    process_commit_event_func = None
):
    """GitHub webhook handler with multi-org support"""
    
    body = await request.body()
    payload = json.loads(body)
    
    # Try multi-org mode
    webhook_context = None
    webhook_secret = None
    
    if db_pool and x_hub_signature_256:
        webhook_context = await get_org_webhook_context(db_pool, x_hub_signature_256)
        
        if webhook_context:
            webhook_secret = webhook_context['webhook_secret']
            print(f"✅ Multi-org mode: Found webhook for org {webhook_context['org_id']}")
    
    # Fall back to single-org mode
    if not webhook_secret:
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        if webhook_secret:
            print(f"⚠️  Single-org mode: Using GITHUB_WEBHOOK_SECRET from env")
    
    # Verify signature
    if not webhook_secret:
        print(f"❌ No webhook secret found")
        raise HTTPException(status_code=403, detail="No webhook secret configured")
    
    if not verify_signature(webhook_secret, body, x_hub_signature_256):
        print(f"❌ Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    print(f"✅ Webhook signature verified")
    
    # Handle push events
    if x_github_event == "push":
        if webhook_context:
            payload['_webhook_context'] = {
                'user_id': str(webhook_context['user_id']),
                'org_id': webhook_context['org_id'],
                'github_token_id': str(webhook_context['github_token_id']),
                'webhook_secret': webhook_context['webhook_secret']
            }
            print(f"📝 Added webhook context: org_id={webhook_context['org_id']}")
        
        background_tasks.add_task(process_commit_event_func, payload)
        return {"status": "accepted"}
    
    return {"status": "ignored", "event": x_github_event}
```

---

## **PHASE 4: EVENT CONSUMER INTEGRATION (2 hours)**

### **4.1 Add get_github_token() method to EventConsumer**

```python
# event_consumer.py - Add this method to EventConsumer class

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

### **4.2 Replace process_event() method in EventConsumer**

```python
# event_consumer.py - Replace the existing process_event() method

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
            handle_push_event,
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
```

---

## **PHASE 5: SMART PROCESSOR UPDATE (1 hour)**

### **5.1 Update handle_push_event() signature**

```python
# smart_processor.py - Update the function signature

def handle_push_event(payload, github_token=None):
    """Enhanced push event handler with smart analysis
    
    Args:
        payload: GitHub webhook payload
        github_token: GitHub token to use (org-specific or env var)
    """
    
    # Use provided token or fall back to env var
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    
    repo = payload.get("repository", {})
    repo_full = repo.get("full_name")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")
    
    # ... rest of the function uses github_token for clone and push
```

---

## **PHASE 6: MISSED COMMITS DETECTION (2 hours)**

### **6.1 Add check_missed_commits_all_orgs() method to EventConsumer**

```python
# event_consumer.py - Add this method to EventConsumer class

async def check_missed_commits_all_orgs(self):
    """
    Check for missed commits across ALL registered orgs
    
    On startup: Query GitHub for recent commits in each org's repos
    and compare with our database to find any commits that were missed
    during downtime.
    """
    
    try:
        print("\n🔍 Checking for missed commits across all orgs...")
        
        # Step 1: Get all unique (org_id, repo_id) pairs
        async with self.pool.acquire() as conn:
            repos = await conn.fetch("""
                SELECT DISTINCT org_id, repo_id, github_token_id, user_id
                FROM commit_events
                WHERE org_id IS NOT NULL
                ORDER BY org_id, repo_id
            """)
        
        print(f"📊 Found {len(repos)} unique repos across orgs")
        
        total_missed = 0
        
        # Step 2: For each org, get its token and check for missed commits
        for repo_record in repos:
            org_id = repo_record["org_id"]
            repo_id = repo_record["repo_id"]
            token_id = repo_record["github_token_id"]
            user_id = repo_record["user_id"]
            
            try:
                # Get THIS org's GitHub token
                github_token = await self.get_github_token(user_id, token_id)
                
                if not github_token:
                    print(f"⚠️  No token for org {org_id}, skipping")
                    continue
                
                # Step 3: Check missed commits for THIS repo
                last_sha = await self.get_last_processed_sha_for_repo(repo_id)
                
                if not last_sha:
                    print(f"⏭️  No previous commits for {repo_id}, skipping")
                    continue
                
                # Query GitHub for commits after last_sha
                github_commits = await self.get_commits_after_sha(
                    repo_id, last_sha, github_token
                )
                
                if github_commits:
                    print(f"🔍 {org_id}/{repo_id}: Found {len(github_commits)} missed commits")
                    
                    # Store missed commits
                    for commit in github_commits:
                        event = CommitEvent(
                            repo_id=repo_id,
                            commit_sha=commit["sha"],
                            parent_sha=commit.get("parents", []),
                            author_name=commit.get("author", {}).get("name", ""),
                            author_email=commit.get("author", {}).get("email", ""),
                            timestamp=commit.get("timestamp", datetime.now()),
                            branch="main",  # TODO: Get actual branch
                            files_changed=[],  # TODO: Get file changes
                            commit_message=commit.get("message", ""),
                            user_id=user_id,
                            org_id=org_id,
                            github_token_id=token_id,
                        )
                        await self.bus.store_event(event)
                    
                    total_missed += len(github_commits)
                    
            except Exception as e:
                print(f"⚠️  Error checking {org_id}/{repo_id}: {e}")
                continue
        
        print(f"✅ Recovered {total_missed} missed commits across all orgs")
        
    except Exception as e:
        print(f"⚠️  Error checking missed commits: {e}")

async def get_last_processed_sha_for_repo(self, repo_id: str) -> Optional[str]:
    """Get the last processed commit SHA for a specific repo"""
    try:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT commit_sha FROM commit_events
                WHERE repo_id = $1 AND processed = TRUE
                ORDER BY timestamp DESC
                LIMIT 1
            """, repo_id)
            return result
    except Exception as e:
        print(f"⚠️  Error getting last processed SHA: {e}")
        return None

async def get_commits_after_sha(self, repo_id: str, last_sha: str, github_token: str):
    """Query GitHub for commits after a specific SHA"""
    try:
        sync = GitHubSync(github_token)
        commits = await sync.find_missed_commits(repo_id, last_processed_sha=last_sha)
        return commits
    except Exception as e:
        print(f"⚠️  Error getting commits from GitHub: {e}")
        return []
```

### **6.2 Update check_missed_commits() to call new method**

```python
# event_consumer.py - Update the existing check_missed_commits() method

async def check_missed_commits(self):
    """
    Check for missed commits on startup
    
    This now checks ALL orgs, not just the single hardcoded org.
    """
    try:
        print("\n🔍 Checking for missed commits...")
        
        # Get unprocessed events from database
        stats = await self.bus.get_event_stats()
        
        if stats["pending"] > 0:
            print(f"📊 Found {stats['pending']} unprocessed events in database")
            print(f"   These will be processed automatically")
        
        # Check GitHub for missed commits across ALL orgs
        await self.check_missed_commits_all_orgs()
        
        if stats["pending"] == 0:
            print(f"\n✅ No missed commits found")
            print(f"   Last processed: {stats['processed']} events")
        
    except Exception as e:
        print(f"⚠️  Error checking missed commits: {e}")
```

---

## **PHASE 7: TESTING (2 hours)**

### **7.1 Test Webhook Registration**

```bash
# Test registering webhook for Company A
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "beta-org-for-pustak",
    "github_token": "ghp_xxxxx..."
  }'

# Expected response:
# {
#   "status": "success",
#   "webhook_url": "https://yourdomain.com/webhook",
#   "webhook_secret": "whsec_aaa...",
#   "instructions": "Configure this in GitHub org settings > Webhooks"
# }
```

### **7.2 Test Webhook Reception**

```bash
# Simulate GitHub webhook from Company A
curl -X POST http://localhost:8000/webhook \
  -H "X-Hub-Signature-256: sha256=whsec_aaa..." \
  -H "X-GitHub-Event: push" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": {
      "full_name": "beta-org-for-pustak/College-ERP"
    },
    "commits": [...]
  }'

# Expected: Event stored in DB with org context
```

### **7.3 Test Event Processing**

```bash
# Check if event was processed
SELECT * FROM commit_events 
WHERE org_id = 'beta-org-for-pustak' 
AND processed = TRUE;

# Expected: Event marked as processed with correct token used
```

### **7.4 Test Missed Commits Detection**

```bash
# Simulate server downtime by manually deleting processed flag
UPDATE commit_events SET processed = FALSE 
WHERE org_id = 'beta-org-for-pustak';

# Restart event consumer
python src/event_consumer.py

# Expected: Missed commits detected and recovered
```

---

## **PHASE 8: CLEANUP (1 hour)**

### **8.1 Delete unused files**

```bash
# Delete old webhook handler (replaced by webhook_multi_org.py)
rm src/webhook_handler.py

# Delete reference code (integrated into event_consumer.py)
rm src/event_consumer_multi_org.py

# Delete empty folders
rmdir src/integrations src/processors src/services
```

### **8.2 Update documentation**

```bash
# Update README with multi-org setup instructions
# Update SETUP_WEBHOOKS.md with new registration flow
# Update architecture docs
```

---

## **ROLLBACK PLAN**

If something goes wrong:

```sql
-- Rollback database changes
DROP TABLE org_webhooks;
DROP TABLE user_github_tokens;
ALTER TABLE commit_events DROP COLUMN user_id, org_id, github_token_id;

-- Revert code changes
git revert <commit-hash>
```

---

## **VERIFICATION CHECKLIST**

- [ ] Database tables created successfully
- [ ] Webhook registration endpoint works
- [ ] Multi-org webhook handler verifies signatures correctly
- [ ] Events stored with org context
- [ ] Event consumer retrieves correct token per org
- [ ] Smart processor uses org's token for clone/push
- [ ] Missed commits detected for all orgs
- [ ] Tests pass for Company A
- [ ] Tests pass for Company B
- [ ] Tests pass for 10+ orgs
- [ ] Documentation updated
- [ ] Old files deleted
- [ ] No breaking changes to existing single-org setup

---

## **SUCCESS CRITERIA**

✅ **Multi-org support is complete when:**

1. Company A can register their org and webhook
2. Company A's push events are processed with Company A's token
3. Company B can register their org and webhook
4. Company B's push events are processed with Company B's token
5. Server downtime recovery works for both orgs
6. Docs are generated and pushed to correct repos
7. System scales to 1000+ orgs without performance degradation
8. All tests pass
9. No breaking changes to existing functionality

---

## **ESTIMATED TIMELINE**

| Phase | Task | Time |
|-------|------|------|
| 1 | Database schema | 1h |
| 2 | Webhook registration | 2h |
| 3 | Multi-org webhook handler | 1h |
| 4 | Event consumer integration | 2h |
| 5 | Smart processor update | 1h |
| 6 | Missed commits detection | 2h |
| 7 | Testing | 2h |
| 8 | Cleanup & docs | 1h |
| **Total** | | **12h** |

---

## **NEXT STEPS**

1. Review this roadmap
2. Approve database schema changes
3. Start Phase 1: Database
4. Proceed sequentially through phases
5. Test thoroughly at each phase
6. Deploy to staging first
7. Monitor for issues
8. Deploy to production
