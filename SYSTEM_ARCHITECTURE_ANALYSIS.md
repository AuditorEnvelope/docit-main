# 🏗️ **COMPLETE SYSTEM ARCHITECTURE ANALYSIS**

## **WHAT ARE WE BUILDING?**

A **Multi-Organization Documentation Generation System** that:
1. Accepts webhooks from multiple GitHub organizations
2. Routes each webhook to the correct organization's GitHub token
3. Generates documentation for each organization independently
4. Handles server downtime by recovering missed commits
5. Scales to 1000+ organizations

---

## **CURRENT ARCHITECTURE (BROKEN)**

```
GitHub Push Event (Any Org)
    ↓
/webhook endpoint
    ↓
webhook_multi_org() function
    ├─ Try: Look up org_webhooks table (multi-org mode) ✅
    └─ Fall back: Use GITHUB_WEBHOOK_SECRET env var ⚠️ PROBLEM!
    ↓
Verify signature
    ↓
process_commit_event()
    ├─ Extract webhook_context (user_id, org_id, token_id) ✅
    └─ Store in commit_events table ✅
    ↓
Event Consumer polls database
    ↓
process_event()
    ├─ Extract: user_id, org_id, token_id ✅
    ├─ Get token from database ✅
    └─ Fall back: Use GITHUB_TOKEN env var ⚠️ PROBLEM!
    ↓
handle_push_event(payload, github_token)
    ├─ Clone repo ✅
    ├─ Generate docs ✅
    └─ Push to GitHub ✅
    ↓
check_missed_commits_all_orgs()
    ├─ Query all orgs from database ✅
    ├─ Get each org's token ✅
    └─ Recover missed commits ✅
```

---

## **THE PROBLEM: FALLBACKS TO HARDCODED ORG**

### **Problem 1: Webhook Secret Fallback (Line 112 in webhook_multi_org.py)**
```python
# CURRENT (WRONG):
if not webhook_secret:
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if webhook_secret:
        print(f"⚠️  Single-org mode: Using GITHUB_WEBHOOK_SECRET from env")
```

**Issue:** If org webhook not found in database, falls back to env var
**Result:** All orgs use same webhook secret (defeats multi-org purpose!)

### **Problem 2: GitHub Token Fallback (Line 194-195 in event_consumer.py)**
```python
# CURRENT (WRONG):
if not github_token:
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print(f"⚠️  Using GITHUB_TOKEN from env (single-org mode)")
```

**Issue:** If org token not found in database, falls back to env var
**Result:** All orgs use PUSTAK's token (can't access other orgs' repos!)

### **Problem 3: Missed Commits Fallback (Line 281 in event_consumer.py)**
```python
# CURRENT (WRONG):
if not repos:
    print("⚠️  No multi-org repos found in database")
    print("   Falling back to single-org mode...")
    await self.check_missed_commits_single_org()
```

**Issue:** If no multi-org data, falls back to checking only PUSTAK's repo
**Result:** Only PUSTAK's org is checked for missed commits!

---

## **WHAT SHOULD HAPPEN: PURELY DYNAMIC**

### **Correct Flow:**

```
GitHub Push Event (Any Org)
    ↓
/webhook endpoint
    ↓
webhook_multi_org() function
    ├─ MUST find org in org_webhooks table
    ├─ If NOT found → REJECT (403 Forbidden)
    └─ If found → Continue with that org's context
    ↓
Verify signature with org-specific secret
    ↓
process_commit_event()
    ├─ MUST have webhook_context (user_id, org_id, token_id)
    └─ Store in commit_events table
    ↓
Event Consumer polls database
    ↓
process_event()
    ├─ MUST have user_id, org_id, token_id in event
    ├─ MUST get token from database
    ├─ If NOT found → FAIL (don't fall back!)
    └─ Continue with that org's token
    ↓
handle_push_event(payload, github_token)
    ├─ Clone repo with org's token
    ├─ Generate docs
    └─ Push to GitHub
    ↓
check_missed_commits_all_orgs()
    ├─ Query ALL orgs from database
    ├─ For EACH org:
    │  ├─ Get that org's token
    │  ├─ Query GitHub for that org
    │  └─ Recover missed commits
    └─ NO fallback to single-org mode!
```

---

## **KEY DIFFERENCES**

| Aspect | Current (Broken) | Should Be (Dynamic) |
|--------|------------------|-------------------|
| **Webhook Secret** | Try DB, fall back to env | MUST be in DB |
| **GitHub Token** | Try DB, fall back to env | MUST be in DB |
| **Missed Commits** | Try multi-org, fall back to single | MUST check ALL orgs |
| **Hardcoded Org** | PUSTAK's org in fallback | NO hardcoded org |
| **Scalability** | Limited (1 org + fallback) | Unlimited (all orgs) |

---

## **WHERE ARE THE FALLBACKS?**

### **File 1: webhook_multi_org.py (Line 111-114)**
```python
# REMOVE THIS:
if not webhook_secret:
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if webhook_secret:
        print(f"⚠️  Single-org mode: Using GITHUB_WEBHOOK_SECRET from env")

# REPLACE WITH:
if not webhook_secret:
    print(f"❌ No webhook secret found for this org")
    raise HTTPException(status_code=403, detail="Webhook not registered for this organization")
```

### **File 2: event_consumer.py (Line 193-201)**
```python
# REMOVE THIS:
if not github_token:
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print(f"⚠️  Using GITHUB_TOKEN from env (single-org mode)")
    else:
        print(f"❌ No GitHub token available (multi-org or env)")
        raise Exception(f"No GitHub token for user {user_id}")

# REPLACE WITH:
if not github_token:
    print(f"❌ No GitHub token found for user {user_id} org {org_id}")
    raise Exception(f"No GitHub token for user {user_id} org {org_id}")
```

### **File 3: event_consumer.py (Line 278-282)**
```python
# REMOVE THIS:
if not repos:
    print("⚠️  No multi-org repos found in database")
    print("   Falling back to single-org mode...")
    await self.check_missed_commits_single_org()
    return

# REPLACE WITH:
if not repos:
    print("⚠️  No events found in database yet")
    print("   Waiting for first webhook...")
    return
```

---

## **COMPLETE DYNAMIC FLOW**

### **1. Webhook Registration (User Action)**
```
User: "I want to register my org"
    ↓
POST /webhook/register
    ├─ org_id: "my-company-org"
    └─ user_id: "aca20dc6-..." (from JWT)
    ↓
Backend:
    ├─ Generate webhook_secret
    ├─ Store in org_webhooks table:
    │  ├─ user_id
    │  ├─ org_id
    │  ├─ webhook_secret (UNIQUE)
    │  └─ github_token_id
    └─ Return webhook_url
    ↓
User configures webhook on GitHub
```

### **2. Webhook Received (GitHub Action)**
```
GitHub: "Push event from my-company-org/repo"
    ↓
POST /webhook
    ├─ Header: X-Hub-Signature-256: sha256=<signature>
    └─ Body: {repository, commits, ...}
    ↓
webhook_multi_org():
    ├─ Extract signature
    ├─ Query org_webhooks table:
    │  └─ WHERE webhook_secret = <extracted_secret>
    ├─ If NOT found → REJECT (403)
    ├─ If found → Get user_id, org_id, token_id
    └─ Verify signature with org-specific secret
    ↓
process_commit_event():
    ├─ Add webhook_context to payload:
    │  ├─ user_id
    │  ├─ org_id
    │  └─ github_token_id
    └─ Store in commit_events table
```

### **3. Event Processing (Event Consumer)**
```
Event Consumer polls database every 5 seconds
    ↓
SELECT * FROM commit_events WHERE processed = FALSE
    ↓
For each event:
    ├─ Extract: user_id, org_id, github_token_id
    ├─ Query user_github_tokens table:
    │  └─ WHERE user_id = ? AND token_id = ?
    ├─ If NOT found → FAIL (don't fall back!)
    ├─ If found → Get github_token
    └─ Call handle_push_event(payload, github_token)
    ↓
handle_push_event():
    ├─ Clone repo with github_token
    ├─ Generate docs
    ├─ Push to GitHub
    └─ Return success
    ↓
Mark event as processed
```

### **4. Missed Commits Detection (Startup)**
```
Event Consumer starts
    ↓
check_missed_commits_all_orgs():
    ├─ Query: SELECT DISTINCT org_id, repo_id, user_id, github_token_id
    │         FROM commit_events
    │         WHERE org_id IS NOT NULL
    ├─ If NO rows → Log "No orgs registered yet"
    ├─ For EACH org:
    │  ├─ Get that org's token from database
    │  ├─ If NOT found → Skip this org
    │  ├─ Query GitHub for missed commits
    │  └─ Store missed commits with org context
    └─ Process all missed commits
```

---

## **SUMMARY: WHAT NEEDS TO CHANGE**

### **Remove All Fallbacks:**
1. ❌ Remove `os.getenv("GITHUB_WEBHOOK_SECRET")` fallback
2. ❌ Remove `os.getenv("GITHUB_TOKEN")` fallback
3. ❌ Remove `check_missed_commits_single_org()` fallback

### **Make Everything Dynamic:**
1. ✅ Webhook secret MUST come from org_webhooks table
2. ✅ GitHub token MUST come from user_github_tokens table
3. ✅ Missed commits MUST check ALL orgs in database

### **Result:**
- ✅ Purely dynamic (no hardcoded org)
- ✅ Scales to unlimited orgs
- ✅ Each org uses its own token
- ✅ Each org has its own webhook secret
- ✅ No fallback to PUSTAK's org

---

## **FILES TO MODIFY**

1. **webhook_multi_org.py** (Line 111-114)
   - Remove webhook secret fallback
   - Reject if org not found

2. **event_consumer.py** (Line 193-201)
   - Remove GitHub token fallback
   - Fail if token not found

3. **event_consumer.py** (Line 278-282)
   - Remove single-org fallback
   - Just log "waiting for first webhook"

---

## **TESTING STRATEGY**

After changes:
1. Register org 1 with token 1
2. Register org 2 with token 2
3. Push to org 1 → Should use token 1
4. Push to org 2 → Should use token 2
5. Push to unregistered org → Should REJECT (403)
6. Stop consumer, push to both orgs
7. Start consumer → Should recover ALL missed commits

---

## **NEXT STEP**

Once you confirm this analysis is correct, I'll:
1. Remove all fallbacks
2. Make everything purely dynamic
3. Help you test with multiple orgs
