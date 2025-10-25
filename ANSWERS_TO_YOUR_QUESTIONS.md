# ✅ ANSWERS TO YOUR 3 QUESTIONS

---

## **QUESTION 1: Why do we need separate PUSTAK token?**

### **Your Understanding (Partially Correct)**
> "pustak token to ek hi app ka hai na... its basically the token of the app installed in org repos"

### **The Reality (More Nuanced)**

There are **TWO DIFFERENT THINGS**:

#### **1. GitHub App (What you're thinking of)**

```
Lekhak AI App (GitHub App)
├─ Installed in: beta-org-for-pustak
│  └─ installation_id = 12345
│  └─ Permissions: Read/write to beta-org-for-pustak's repos
│  └─ Token: Temporary (1 hour), generated per installation
│
├─ Installed in: another-org
│  └─ installation_id = 67890
│  └─ Permissions: Read/write to another-org's repos
│  └─ Token: Temporary (1 hour), generated per installation
│
└─ Installed in: AuditorEnvelope
   └─ installation_id = 11111
   └─ Permissions: Read/write to AuditorEnvelope's repos
   └─ Token: Temporary (1 hour), generated per installation
```

**Each installation is SEPARATE and SCOPED to that org.**

#### **2. Personal Tokens (What we're storing)**

```
PUSTAK's Personal Token (from .env):
├─ Belongs to: PUSTAK user
├─ Can access: All repos PUSTAK has access to
├─ Can access: AuditorEnvelope org ✅
├─ Cannot access: beta-org-for-pustak (unless PUSTAK is member) ❌
├─ Cannot access: another-org (unless PUSTAK is member) ❌
├─ Persistent: Yes (doesn't expire)
└─ ❌ NOT SCALABLE for multi-org

Company A User's Personal Token:
├─ Belongs to: Company A user
├─ Can access: All repos Company A user has access to
├─ Can access: beta-org-for-pustak's private repos ✅
├─ Cannot access: another-org ❌
├─ Persistent: Yes (doesn't expire)
└─ ✅ SCALABLE for multi-org

Company B User's Personal Token:
├─ Belongs to: Company B user
├─ Can access: All repos Company B user has access to
├─ Can access: another-org's private repos ✅
├─ Cannot access: beta-org-for-pustak ❌
├─ Persistent: Yes (doesn't expire)
└─ ✅ SCALABLE for multi-org
```

### **Why We Need Separate Tokens**

**Scenario: Company A pushes code to their private repo**

```
❌ CURRENT (using PUSTAK's token):
Company A push
  ↓
Webhook received ✅
  ↓
Event stored in DB ✅
  ↓
Event Consumer gets: os.getenv("GITHUB_TOKEN")
  ↓
github_token = PUSTAK's token
  ↓
Tries to clone: https://x-access-token:PUSTAK_token@github.com/beta-org-for-pustak/College-ERP.git
  ↓
❌ FAILS - PUSTAK doesn't have access to Company A's private repo!
  ❌ 403 Forbidden

✅ AFTER FIX (using Company A's token):
Company A push
  ↓
Webhook received ✅
  ↓
Event stored with: user_id=CompanyA_user, token_id=CompanyA_token ✅
  ↓
Event Consumer gets: await self.get_github_token(CompanyA_user, CompanyA_token)
  ↓
github_token = Company A's token ✅
  ↓
Clones: https://x-access-token:CompanyA_token@github.com/beta-org-for-pustak/College-ERP.git
  ↓
✅ SUCCESS - Company A's token has access!
  ✅ 200 OK
```

### **Comparison Table**

| Aspect | GitHub App Token | Personal Token |
|--------|-----------------|-----------------|
| **What it is** | OAuth app token | User's access token |
| **Scope** | One org only | All user's orgs |
| **Created by** | GitHub admin | User |
| **Duration** | 1 hour (temporary) | Persistent |
| **Used for** | API calls, webhooks | Git operations, API calls |
| **Permissions** | Org-specific | User-specific |
| **Scalability** | ✅ Works for multi-org | ✅ Works for multi-org |
| **Why we use it** | For webhook setup | For git clone/push |

### **Answer**

We need separate tokens because:
1. **GitHub App tokens are temporary** (1 hour) - not suitable for persistent operations
2. **Personal tokens are persistent** - suitable for git clone/push
3. **Each user's token has their permissions** - Company A's token can only access Company A's repos
4. **This is the only way to scale** - Without separate tokens, only PUSTAK's repos work

---

## **QUESTION 2: Server downtime + commits on different org repos?**

### **Your Question**
> "Currently if the server goes down and commit happens on different org repos apart from lekhak so it will not work.. you are saying ????"

### **YES, EXACTLY! Here's why:**

#### **Current System (BROKEN for multi-org)**

```
SCENARIO: Server down for 48 hours

Hour 0:
├─ Company A pushes to: beta-org-for-pustak/College-ERP
│  └─ Webhook sent to PUSTAK's server
│  └─ ❌ SERVER DOWN - webhook fails
│  └─ GitHub retries webhook (24 hours)
│
└─ Company B pushes to: another-org/Their-Project
   └─ Webhook sent to PUSTAK's server
   └─ ❌ SERVER DOWN - webhook fails
   └─ GitHub retries webhook (24 hours)

Hour 24:
├─ GitHub stops retrying Company A's webhook
└─ GitHub stops retrying Company B's webhook

Hour 48: PUSTAK's server comes back up
├─ EventConsumer.check_missed_commits() runs
├─ Queries GitHub for: "AuditorEnvelope/lekhak_ai" (hardcoded!)
├─ ❌ Doesn't check Company A's repos
├─ ❌ Doesn't check Company B's repos
└─ ❌ COMMITS LOST!

Why? Because check_missed_commits() is hardcoded:
```python
# event_consumer.py line 267
missed = await sync.find_missed_commits(
    "AuditorEnvelope/lekhak_ai",  # ❌ HARDCODED!
    last_processed_sha=last_sha
)
```

It only checks PUSTAK's repo, not other orgs!
```

#### **After Fix (WORKS for multi-org)**

```
SCENARIO: Server down for 48 hours (WITH FIX)

Hour 48: PUSTAK's server comes back up
├─ EventConsumer.check_missed_commits_all_orgs() runs
│
├─ For Company A:
│  ├─ Gets Company A's token from DB
│  ├─ Queries GitHub: "beta-org-for-pustak/College-ERP"
│  ├─ GitHub returns: [commit1, commit2, commit3]
│  └─ ✅ Stores in DB with Company A's context
│
├─ For Company B:
│  ├─ Gets Company B's token from DB
│  ├─ Queries GitHub: "another-org/Their-Project"
│  ├─ GitHub returns: [commit1, commit2]
│  └─ ✅ Stores in DB with Company B's context
│
├─ For Company C, D, E, ... (1000 orgs):
│  └─ ✅ Same process for each org
│
└─ ✅ ALL MISSED COMMITS RECOVERED!

New code:
```python
# event_consumer.py (new)
async def check_missed_commits_all_orgs(self):
    # Get all unique (org_id, repo_id) pairs
    repos = await conn.fetch("""
        SELECT DISTINCT org_id, repo_id, github_token_id, user_id
        FROM commit_events
        WHERE org_id IS NOT NULL
    """)
    
    # For each repo:
    for repo_record in repos:
        org_id = repo_record["org_id"]
        repo_id = repo_record["repo_id"]
        token_id = repo_record["github_token_id"]
        user_id = repo_record["user_id"]
        
        # Get THIS org's token
        github_token = await self.get_github_token(user_id, token_id)
        
        # Query GitHub for THIS org's repo
        missed = await sync.find_missed_commits(
            repo_id,  # ✅ DYNAMIC!
            last_processed_sha=last_sha
        )
```

It checks ALL orgs' repos!
```

### **Key Insight**

The **Commit Bus** (PostgreSQL) stores events durably, so they're not lost. But if the server is down for > 24 hours:
- GitHub stops retrying webhooks
- Webhooks never arrive
- Events never get stored in Commit Bus
- **Missed Commit Detection** is the only way to recover them

**Current system:** Only detects missed commits for PUSTAK's repo ❌
**After fix:** Detects missed commits for ALL 1000 orgs' repos ✅

---

## **QUESTION 3: Current flow vs new flow?**

### **CURRENT FLOW (Single-Org Mode)**

```
┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK PHASE (Immediate)                                   │
└─────────────────────────────────────────────────────────────┘

GitHub Push Event (from ANY org, but only PUSTAK's works)
    ↓
POST /webhook (main.py:460)
    ↓
webhook_multi_org() (webhook_multi_org.py)
    ├─ Try to find org from signature
    ├─ Query: SELECT * FROM org_webhooks WHERE webhook_secret = ?
    ├─ ❌ NOT FOUND (no org_webhooks table yet)
    └─ Fall back to env var: GITHUB_WEBHOOK_SECRET ✅
    ↓
Verify signature with env var secret ✅
    ↓
process_commit_event() (main.py:126)
    ├─ Extract webhook context from payload
    ├─ ❌ No context (not multi-org)
    └─ payload._webhook_context = None
    ↓
CommitBusService.store_event()
    ├─ repo_id: "AuditorEnvelope/lekhak_ai"
    ├─ user_id: NULL ❌
    ├─ org_id: NULL ❌
    ├─ github_token_id: NULL ❌
    └─ Store in DB ✅
    ↓
Return 200 OK immediately ✅

┌─────────────────────────────────────────────────────────────┐
│ EVENT CONSUMER PHASE (Background, every 5 seconds)          │
└─────────────────────────────────────────────────────────────┘

EventConsumer.run() (event_consumer.py)
    ↓
Poll DB: SELECT * FROM commit_events WHERE processed = FALSE
    ↓
For each event:
    ├─ event_id, repo_id, commit_sha, etc.
    ├─ user_id: NULL ❌
    ├─ org_id: NULL ❌
    ├─ github_token_id: NULL ❌
    ↓
    EventConsumer.process_event()
        ├─ user_id = event.get("user_id")  # NULL
        ├─ token_id = event.get("github_token_id")  # NULL
        ├─ if user_id and token_id:  # FALSE ❌
        │   └─ github_token = await self.get_github_token(...)
        ├─ else:  # TRUE ✅
        │   └─ github_token = os.getenv("GITHUB_TOKEN")  # PUSTAK's token
        ↓
        convert_to_webhook_payload(event)
        ↓
        handle_push_event(payload, github_token)
            ├─ Clone repo: "AuditorEnvelope/lekhak_ai"
            ├─ Using: PUSTAK's token ✅ (works for PUSTAK's repos)
            ├─ Generate docs
            ├─ Push to: "AuditorEnvelope/lekhak_ai"
            └─ Using: PUSTAK's token ✅
        ↓
        Mark as processed ✅

┌─────────────────────────────────────────────────────────────┐
│ MISSED COMMITS PHASE (On startup)                           │
└─────────────────────────────────────────────────────────────┘

EventConsumer.check_missed_commits()
    ├─ Get unprocessed events from DB
    ├─ github_token = os.getenv("GITHUB_TOKEN")  # PUSTAK's token
    ├─ github_org = os.getenv("GITHUB_ORG", "AuditorEnvelope")
    ├─ enable_github_sync = os.getenv("ENABLE_GITHUB_SYNC")
    ↓
    if github_token and enable_github_sync:
        ├─ sync = GitHubSync(PUSTAK's token)
        ├─ last_sha = await self.get_last_processed_sha()
        ├─ missed = await sync.find_missed_commits(
        │   "AuditorEnvelope/lekhak_ai",  # ❌ HARDCODED!
        │   last_processed_sha=last_sha
        │ )
        ├─ For each missed commit:
        │   └─ Store in DB
        └─ ✅ Recovered missed commits for PUSTAK's repo only
    ↓
    ❌ DOESN'T CHECK OTHER ORGS!
    ❌ Company A's missed commits: LOST
    ❌ Company B's missed commits: LOST

RESULT: ❌ ONLY WORKS FOR PUSTAK'S REPOS
```

### **NEW FLOW (Multi-Org Mode)**

```
┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK REGISTRATION PHASE (One-time per org)               │
└─────────────────────────────────────────────────────────────┘

Company A Admin:
    ├─ Logs into Lekhak AI
    ├─ Clicks: "Connect GitHub Org"
    ├─ Selects: "beta-org-for-pustak"
    ├─ Authorizes: Lekhak AI app
    ↓
    POST /webhook/register
        ├─ user_id = "company-a-user-uuid"
        ├─ org_id = "beta-org-for-pustak"
        ├─ github_token = "ghp_xxxxx..." (Company A's token)
        ↓
        Generate webhook_secret = "whsec_aaa..."
        ↓
        Store in org_webhooks:
        ├─ user_id: "company-a-user-uuid"
        ├─ org_id: "beta-org-for-pustak"
        ├─ webhook_secret: "whsec_aaa..."
        ├─ github_token_id: "token-uuid-123"
        ↓
        Store in user_github_tokens:
        ├─ token_id: "token-uuid-123"
        ├─ user_id: "company-a-user-uuid"
        ├─ org_id: "beta-org-for-pustak"
        ├─ github_token: "ghp_xxxxx..." (encrypted)
        ↓
        Return: {
            "webhook_url": "https://yourdomain.com/webhook",
            "webhook_secret": "whsec_aaa...",
            "instructions": "Configure in GitHub org settings"
        }
    ↓
    Company A Admin:
    ├─ Goes to GitHub org settings
    ├─ Adds webhook: https://yourdomain.com/webhook
    ├─ Sets secret: whsec_aaa...
    └─ ✅ Webhook configured!

Same for Company B, Company C, etc.

┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK PHASE (Immediate, per push)                         │
└─────────────────────────────────────────────────────────────┘

Company A Push Event:
    ↓
POST /webhook
    ├─ Header: X-Hub-Signature-256: sha256=whsec_aaa...
    ↓
webhook_multi_org()
    ├─ signature = "sha256=whsec_aaa..."
    ├─ Try multi-org mode:
    │   ├─ get_org_webhook_context(db_pool, signature)
    │   ├─ Query: SELECT * FROM org_webhooks WHERE webhook_secret = "whsec_aaa"
    │   ├─ Found! ✅
    │   ├─ webhook_context = {
    │   │   "user_id": "company-a-user-uuid",
    │   │   "org_id": "beta-org-for-pustak",
    │   │   "webhook_secret": "whsec_aaa...",
    │   │   "github_token_id": "token-uuid-123"
    │   │ }
    │   └─ webhook_secret = "whsec_aaa..."
    ├─ Verify signature with webhook_secret ✅
    ├─ Add context to payload:
    │   └─ payload._webhook_context = webhook_context
    ↓
process_commit_event(payload)
    ├─ Extract context from payload._webhook_context
    ├─ user_id = "company-a-user-uuid"
    ├─ org_id = "beta-org-for-pustak"
    ├─ github_token_id = "token-uuid-123"
    ↓
CommitBusService.store_event()
    ├─ repo_id: "beta-org-for-pustak/College-ERP"
    ├─ user_id: "company-a-user-uuid" ✅
    ├─ org_id: "beta-org-for-pustak" ✅
    ├─ github_token_id: "token-uuid-123" ✅
    └─ Store in DB ✅
    ↓
Return 200 OK immediately ✅

┌─────────────────────────────────────────────────────────────┐
│ EVENT CONSUMER PHASE (Background, every 5 seconds)          │
└─────────────────────────────────────────────────────────────┘

EventConsumer.run()
    ↓
Poll DB: SELECT * FROM commit_events WHERE processed = FALSE
    ↓
For each event:
    ├─ Company A event:
    │   ├─ event_id, repo_id, commit_sha, etc.
    │   ├─ user_id: "company-a-user-uuid" ✅
    │   ├─ org_id: "beta-org-for-pustak" ✅
    │   ├─ github_token_id: "token-uuid-123" ✅
    │   ↓
    │   EventConsumer.process_event()
    │       ├─ user_id = "company-a-user-uuid"
    │       ├─ token_id = "token-uuid-123"
    │       ├─ if user_id and token_id:  # TRUE ✅
    │       │   ├─ github_token = await self.get_github_token(
    │       │   │   "company-a-user-uuid",
    │       │   │   "token-uuid-123"
    │       │   │ )
    │       │   ├─ Query: SELECT github_token FROM user_github_tokens
    │       │   │   WHERE user_id = "company-a-user-uuid"
    │       │   │   AND token_id = "token-uuid-123"
    │       │   ├─ github_token = "ghp_xxxxx..." ✅ (Company A's token)
    │       │   └─ print("✅ Got token for org beta-org-for-pustak")
    │       ↓
    │       convert_to_webhook_payload(event)
    │       ↓
    │       handle_push_event(payload, "ghp_xxxxx...")
    │           ├─ Clone repo: "beta-org-for-pustak/College-ERP"
    │           ├─ Using: Company A's token ✅
    │           ├─ Generate docs
    │           ├─ Push to: "beta-org-for-pustak/College-ERP"
    │           └─ Using: Company A's token ✅
    │       ↓
    │       Mark as processed ✅
    │
    └─ ✅ BOTH COMPANIES' COMMITS PROCESSED!

┌─────────────────────────────────────────────────────────────┐
│ MISSED COMMITS PHASE (On startup)                           │
└─────────────────────────────────────────────────────────────┘

EventConsumer.check_missed_commits_all_orgs()
    ↓
Get all unique (org_id, repo_id) pairs from DB:
    ├─ ("beta-org-for-pustak", "beta-org-for-pustak/College-ERP")
    ├─ ("another-org", "another-org/Their-Project")
    ├─ ("third-org", "third-org/Repo1")
    ├─ ... (1000 orgs × 100 repos = 100,000 repos)
    ↓
For each repo:
    ├─ Company A repo:
    │   ├─ org_id = "beta-org-for-pustak"
    │   ├─ repo_id = "beta-org-for-pustak/College-ERP"
    │   ├─ token_id = "token-uuid-123"
    │   ├─ user_id = "company-a-user-uuid"
    │   ↓
    │   ├─ Get Company A's token:
    │   │   └─ github_token = "ghp_xxxxx..."
    │   ↓
    │   ├─ Get last processed commit:
    │   │   └─ last_sha = "abc123def456..."
    │   ↓
    │   ├─ Query GitHub:
    │   │   └─ GET /repos/beta-org-for-pustak/College-ERP/commits?since=abc123def456
    │   │   └─ Using: Company A's token ✅
    │   ↓
    │   ├─ GitHub returns: [commit1, commit2, commit3]
    │   ↓
    │   ├─ Store in DB:
    │   │   ├─ user_id: "company-a-user-uuid"
    │   │   ├─ org_id: "beta-org-for-pustak"
    │   │   ├─ github_token_id: "token-uuid-123"
    │   │   └─ ✅ Stored with context
    │   ↓
    │   └─ print("✅ Recovered 3 missed commits for beta-org-for-pustak/College-ERP")
    │
    ├─ Company B repo:
    │   ├─ org_id = "another-org"
    │   ├─ repo_id = "another-org/Their-Project"
    │   ├─ token_id = "token-uuid-456"
    │   ├─ user_id = "company-b-user-uuid"
    │   ↓
    │   ├─ Get Company B's token:
    │   │   └─ github_token = "ghp_yyyyy..."
    │   ↓
    │   ├─ Query GitHub:
    │   │   └─ GET /repos/another-org/Their-Project/commits?since=xyz789...
    │   │   └─ Using: Company B's token ✅
    │   ↓
    │   ├─ GitHub returns: [commit1, commit2]
    │   ↓
    │   ├─ Store in DB with context ✅
    │   ↓
    │   └─ print("✅ Recovered 2 missed commits for another-org/Their-Project")
    │
    └─ ... (repeat for all 100,000 repos)
    ↓
    print("✅ Total recovered: 500,000 missed commits across all orgs!")

RESULT: ✅ WORKS FOR ALL ORGS!
```

### **Side-by-Side Comparison**

| Step | Current (Single-Org) | New (Multi-Org) |
|------|----------------------|-----------------|
| **1. Registration** | ❌ None | ✅ Per org |
| **2. Webhook Verification** | env var (hardcoded) | org's webhook_secret (from DB) |
| **3. Event Storage** | No org context | ✅ user_id, org_id, token_id |
| **4. Token Lookup** | Hardcoded env var | ✅ Per-org from DB |
| **5. Doc Generation** | PUSTAK's token only | ✅ Each org's token |
| **6. Missed Commits** | 1 repo (hardcoded) | ✅ 100,000 repos (all orgs) |
| **7. Multi-org Support** | ❌ No | ✅ Yes |

---

## **SUMMARY**

| Question | Answer |
|----------|--------|
| **Q1: Why separate PUSTAK token?** | GitHub App tokens are temporary (1 hour). Personal tokens are persistent and can be used for git operations. Each user's token has their permissions. This is the only way to scale to multi-org. |
| **Q2: Server downtime + different org repos?** | YES, currently broken. Only PUSTAK's repos are recovered (hardcoded). After fix: ALL 1000 orgs' repos are recovered (loop through all orgs, get each token, query GitHub). |
| **Q3: Current flow vs new flow?** | Current: Webhook → Store (no context) → Process (PUSTAK's token) → Missed commits (1 repo). New: Register → Webhook → Store (with context) → Process (org's token) → Missed commits (100,000 repos). |

---

## **NEXT STEPS**

Ready to implement? I can start with:

1. **Phase 1: Database schema** (create tables)
2. **Phase 2: Webhook registration** (add endpoint)
3. **Phase 3-6: Integration** (connect all pieces)
4. **Phase 7: Testing** (verify everything works)

Which phase should we start with?
