# 🎯 MULTI-ORG ARCHITECTURE - DETAILED CLARIFICATION

---

## **QUESTION 1: Why do we need separate PUSTAK token?**

### **The Confusion**
You're right to be confused! Let me clarify:

```
PUSTAK Token (from .env) = PUSTAK's personal access token
GitHub App = Installed in each org
```

These are **TWO DIFFERENT THINGS**.

### **GitHub App (What you're thinking of)**

```
GitHub App "Lekhak AI" installed in:
├─ Company A's org (beta-org-for-pustak)
│  └─ installation_id = 12345
│  └─ Can read/write to Company A's repos
│
├─ Company B's org (another-org)
│  └─ installation_id = 67890
│  └─ Can read/write to Company B's repos
│
└─ PUSTAK's org (AuditorEnvelope)
   └─ installation_id = 11111
   └─ Can read/write to PUSTAK's repos
```

**Each installation is separate and scoped to that org.**

### **Personal Tokens (What we're storing)**

```
PUSTAK's token (from .env):
├─ Can access ALL repos PUSTAK has access to
├─ Can access AuditorEnvelope org
├─ CANNOT access Company A's private repos (unless PUSTAK is member)
├─ CANNOT access Company B's private repos (unless PUSTAK is member)
└─ ❌ NOT SCALABLE for multi-org

Company A User's token:
├─ Can access ALL repos Company A user has access to
├─ Can access Company A's private repos ✅
├─ CANNOT access Company B's repos
└─ ✅ SCALABLE for multi-org

Company B User's token:
├─ Can access ALL repos Company B user has access to
├─ Can access Company B's private repos ✅
├─ CANNOT access Company A's repos
└─ ✅ SCALABLE for multi-org
```

### **Why We Need Separate Tokens**

**Scenario: Company A pushes code**

```
❌ CURRENT (using PUSTAK's token):
Company A push
  ↓
Webhook stores event
  ↓
Event Consumer gets: os.getenv("GITHUB_TOKEN")  # PUSTAK's token
  ↓
Tries to clone: Company A's private repo
  ↓
❌ FAILS - PUSTAK doesn't have access!

✅ AFTER FIX (using Company A's token):
Company A push
  ↓
Webhook stores event with: user_id=CompanyA_user, token_id=CompanyA_token
  ↓
Event Consumer gets: user_github_tokens[CompanyA_token]  # Company A's token
  ↓
Clones: Company A's private repo ✅
  ↓
✅ SUCCESS - Company A's token has access!
```

### **Answer to Your Question**

> "pustak token to ek hi app ka hai na... its basically the token of the app installed in org repos"

**No, there's a difference:**

| Aspect | GitHub App | Personal Token |
|--------|-----------|-----------------|
| **What it is** | OAuth app installed in org | User's access token |
| **Scope** | One org only | All user's orgs |
| **Created by** | GitHub admin | User |
| **Used for** | API calls, webhooks | Git operations, API calls |
| **Permissions** | Org-specific | User-specific |
| **Scalability** | ✅ Works for multi-org | ❌ Only works if user is member |

**We need personal tokens because:**
1. GitHub App tokens are temporary (1 hour)
2. Personal tokens are persistent
3. Personal tokens can be used for git clone/push
4. Each user's token has their permissions

---

## **QUESTION 2: Server downtime + commits on different org repos**

### **Current Situation**

```
PUSTAK's Server is running:
├─ Company A pushes to their repo
│  └─ Webhook received ✅
│  └─ Event stored in DB ✅
│  └─ Event Consumer processes ✅
│  └─ Docs generated ✅
│
└─ Company B pushes to their repo
   └─ Webhook received ✅
   └─ Event stored in DB ✅
   └─ Event Consumer processes ✅
   └─ Docs generated ✅

PUSTAK's Server GOES DOWN:
├─ Company A pushes to their repo
│  └─ Webhook sent to PUSTAK's server
│  └─ ❌ SERVER DOWN - webhook fails
│  └─ GitHub retries webhook (24 hours)
│  └─ If server still down: ❌ COMMIT LOST
│
└─ Company B pushes to their repo
   └─ Webhook sent to PUSTAK's server
   └─ ❌ SERVER DOWN - webhook fails
   └─ GitHub retries webhook (24 hours)
   └─ If server still down: ❌ COMMIT LOST
```

### **What Happens with Commit Bus?**

```
PUSTAK's Server GOES DOWN (with Commit Bus):
├─ Company A pushes to their repo
│  └─ Webhook sent to PUSTAK's server
│  └─ ❌ SERVER DOWN - webhook fails
│  └─ GitHub retries webhook (24 hours)
│  └─ Server comes back up
│  └─ GitHub retries webhook ✅
│  └─ Webhook received ✅
│  └─ Event stored in DB ✅
│  └─ Event Consumer processes ✅
│  └─ ✅ COMMIT RECOVERED
│
└─ Company B pushes to their repo
   └─ Webhook sent to PUSTAK's server
   └─ ❌ SERVER DOWN - webhook fails
   └─ GitHub retries webhook (24 hours)
   └─ Server comes back up
   └─ GitHub retries webhook ✅
   └─ Webhook received ✅
   └─ Event stored in DB ✅
   └─ Event Consumer processes ✅
   └─ ✅ COMMIT RECOVERED
```

### **But There's a Gap!**

```
What if server is down for > 24 hours?

PUSTAK's Server DOWN for 48 hours:
├─ Company A pushes at hour 0
│  └─ Webhook sent
│  └─ ❌ SERVER DOWN
│  └─ GitHub retries for 24 hours
│  └─ At hour 24: GitHub stops retrying
│  └─ At hour 48: Server comes back up
│  └─ ❌ WEBHOOK NEVER ARRIVES (already stopped retrying)
│  └─ ❌ COMMIT LOST (not in DB, not in queue)
│
└─ Company B pushes at hour 0
   └─ Same problem...
```

### **Solution: Missed Commit Detection**

```
When server comes back up:

check_missed_commits():
├─ For each org (Company A, Company B, etc.)
│  ├─ Get that org's GitHub token
│  ├─ Query GitHub API: "Give me commits after last_processed_sha"
│  ├─ GitHub returns: [commit1, commit2, commit3, ...]
│  ├─ Store in DB: commit_events table
│  └─ Event Consumer processes them ✅
│
└─ ✅ ALL MISSED COMMITS RECOVERED!
```

### **Answer to Your Question**

> "Currently if the server goes down and commit happens on different org repos apart from lekhak so it will not work.. you are saying ????"

**YES, exactly!**

```
Current system (BROKEN for multi-org):
├─ Server down for 48 hours
├─ Company A pushes (at hour 0)
├─ Company B pushes (at hour 0)
├─ Server comes back up (at hour 48)
├─ check_missed_commits() runs
├─ But it only checks: os.getenv("GITHUB_ORG") = "AuditorEnvelope"
├─ It only checks: "AuditorEnvelope/lekhak_ai" repo
├─ ❌ Doesn't check Company A's repos
├─ ❌ Doesn't check Company B's repos
└─ ❌ COMMITS LOST!

After fix (WORKING for multi-org):
├─ Server down for 48 hours
├─ Company A pushes (at hour 0)
├─ Company B pushes (at hour 0)
├─ Server comes back up (at hour 48)
├─ check_missed_commits_all_orgs() runs
├─ Loops through ALL orgs in database
├─ For Company A: gets Company A's token, checks Company A's repos
├─ For Company B: gets Company B's token, checks Company B's repos
├─ ✅ Finds all missed commits
└─ ✅ COMMITS RECOVERED!
```

---

## **QUESTION 3: Current Flow vs New Flow**

### **CURRENT FLOW (SINGLE-ORG MODE)**

```
┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK PHASE (Immediate)                                   │
└─────────────────────────────────────────────────────────────┘

GitHub Push Event
    ↓
POST /webhook (main.py:460)
    ↓
webhook_multi_org() (webhook_multi_org.py)
    ├─ Try to find org from signature
    ├─ ❌ Not found (no org_webhooks table)
    └─ Fall back to env var: GITHUB_WEBHOOK_SECRET ✅
    ↓
Verify signature ✅
    ↓
process_commit_event() (main.py:126)
    ├─ Extract webhook context
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

┌─────────────────────────────────────────────────────────────┐
│ RESULT: ONLY WORKS FOR PUSTAK'S REPOS                       │
└─────────────────────────────────────────────────────────────┘
```

---

### **NEW FLOW (MULTI-ORG MODE) - AFTER FIX**

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
        Generate webhook_secret = "whsec_yyy..."
        ↓
        Store in org_webhooks:
        ├─ user_id: "company-a-user-uuid"
        ├─ org_id: "beta-org-for-pustak"
        ├─ webhook_secret: "whsec_yyy..."
        ├─ github_token_id: "token-uuid-123"
        ↓
        Store in user_github_tokens:
        ├─ token_id: "token-uuid-123"
        ├─ user_id: "company-a-user-uuid"
        ├─ org_id: "beta-org-for-pustak"
        ├─ github_token: "ghp_xxxxx..." (encrypted in production)
        ↓
        Return: {
            "webhook_url": "https://yourdomain.com/webhook",
            "webhook_secret": "whsec_yyy...",
            "instructions": "Configure in GitHub org settings"
        }
    ↓
    Company A Admin:
    ├─ Goes to GitHub org settings
    ├─ Adds webhook: https://yourdomain.com/webhook
    ├─ Sets secret: whsec_yyy...
    └─ ✅ Webhook configured!

Same for Company B, Company C, etc.

┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK PHASE (Immediate, per push)                         │
└─────────────────────────────────────────────────────────────┘

Company A Push Event:
    ↓
POST /webhook
    ├─ Header: X-Hub-Signature-256: sha256=abc123...
    ↓
webhook_multi_org()
    ├─ signature = "sha256=abc123..."
    ├─ Try multi-org mode:
    │   ├─ get_org_webhook_context(db_pool, signature)
    │   ├─ Query: SELECT * FROM org_webhooks WHERE webhook_secret = "abc123"
    │   ├─ Found! ✅
    │   ├─ webhook_context = {
    │   │   "user_id": "company-a-user-uuid",
    │   │   "org_id": "beta-org-for-pustak",
    │   │   "webhook_secret": "whsec_yyy...",
    │   │   "github_token_id": "token-uuid-123"
    │   │ }
    │   └─ webhook_secret = "whsec_yyy..."
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

Company B Push Event:
    ├─ Same flow, but:
    ├─ webhook_context = {
    │   "user_id": "company-b-user-uuid",
    │   "org_id": "another-org",
    │   "webhook_secret": "whsec_zzz...",
    │   "github_token_id": "token-uuid-456"
    │ }
    └─ Event stored with Company B's context ✅

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
    ├─ Company B event:
    │   ├─ event_id, repo_id, commit_sha, etc.
    │   ├─ user_id: "company-b-user-uuid" ✅
    │   ├─ org_id: "another-org" ✅
    │   ├─ github_token_id: "token-uuid-456" ✅
    │   ↓
    │   EventConsumer.process_event()
    │       ├─ user_id = "company-b-user-uuid"
    │       ├─ token_id = "token-uuid-456"
    │       ├─ github_token = await self.get_github_token(
    │       │   "company-b-user-uuid",
    │       │   "token-uuid-456"
    │       │ )
    │       ├─ github_token = "ghp_yyyyy..." ✅ (Company B's token)
    │       ↓
    │       handle_push_event(payload, "ghp_yyyyy...")
    │           ├─ Clone repo: "another-org/Their-Project"
    │           ├─ Using: Company B's token ✅
    │           ├─ Generate docs
    │           ├─ Push to: "another-org/Their-Project"
    │           └─ Using: Company B's token ✅
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

┌─────────────────────────────────────────────────────────────┐
│ RESULT: WORKS FOR ALL ORGS!                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## **COMPARISON TABLE**

| Phase | Current (Single-Org) | New (Multi-Org) |
|-------|----------------------|-----------------|
| **Webhook Registration** | ❌ None | ✅ Per org |
| **Webhook Verification** | Uses env var | Uses org's webhook_secret |
| **Event Storage** | No org context | ✅ Stores user_id, org_id, token_id |
| **Token Lookup** | Hardcoded env var | ✅ Per-org from DB |
| **Doc Generation** | PUSTAK's token only | ✅ Each org's token |
| **Missed Commits** | Checks 1 repo | ✅ Checks 100,000 repos |
| **Scalability** | ❌ Broken | ✅ Enterprise-ready |
| **Multi-org Support** | ❌ No | ✅ Yes |

---

## **KEY DIFFERENCES EXPLAINED**

### **1. Webhook Registration (NEW)**

**Before:** No registration needed (hardcoded)
```python
# main.py
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
```

**After:** Each org registers
```python
# POST /webhook/register
# Company A: webhook_secret = "whsec_aaa..."
# Company B: webhook_secret = "whsec_bbb..."
# Company C: webhook_secret = "whsec_ccc..."
```

### **2. Event Storage (ENHANCED)**

**Before:** No org context
```python
commit_events:
├─ repo_id: "AuditorEnvelope/lekhak_ai"
├─ user_id: NULL
├─ org_id: NULL
├─ github_token_id: NULL
```

**After:** Full org context
```python
commit_events:
├─ repo_id: "beta-org-for-pustak/College-ERP"
├─ user_id: "company-a-user-uuid"
├─ org_id: "beta-org-for-pustak"
├─ github_token_id: "token-uuid-123"
```

### **3. Token Lookup (CHANGED)**

**Before:** Hardcoded
```python
# event_consumer.py line 254
github_token = os.getenv("GITHUB_TOKEN")  # PUSTAK's token
```

**After:** Per-org from DB
```python
# event_consumer.py (new)
github_token = await self.get_github_token(user_id, token_id)
# Gets Company A's token, or Company B's token, etc.
```

### **4. Missed Commits Detection (EXPANDED)**

**Before:** Single repo
```python
# event_consumer.py line 267
missed = await sync.find_missed_commits(
    "AuditorEnvelope/lekhak_ai",  # ❌ HARDCODED
    last_processed_sha=last_sha
)
```

**After:** All repos
```python
# event_consumer.py (new)
for repo_record in repos:  # 100,000 repos
    org_id = repo_record["org_id"]
    repo_id = repo_record["repo_id"]
    token_id = repo_record["github_token_id"]
    
    github_token = await self.get_github_token(user_id, token_id)
    
    missed = await sync.find_missed_commits(
        repo_id,  # ✅ DYNAMIC
        last_processed_sha=last_sha
    )
```

---

## **SUMMARY**

### **Question 1: Why separate PUSTAK token?**
- **GitHub App** = Installed in each org, scoped to that org
- **Personal Token** = User's access token, has their permissions
- **We need personal tokens** because they're persistent and can be used for git operations
- **Each user's token** gives access to their org's repos

### **Question 2: Server downtime + different org repos?**
- **Current:** Only PUSTAK's repos are recovered (hardcoded)
- **After fix:** ALL orgs' repos are recovered (loop through all orgs)
- **Commit Bus** stores events durably, but needs to check ALL orgs on startup

### **Question 3: Current flow vs new flow?**
- **Current:** Webhook → Store (no context) → Process (PUSTAK's token) → Missed commits (1 repo)
- **New:** Register → Webhook → Store (with context) → Process (org's token) → Missed commits (100,000 repos)
- **Main change:** Add org context at every step, use org's token instead of PUSTAK's token
