# 📊 **COMPLETE DATA STORAGE FLOW - WHERE EVERYTHING GOES**

## **YOUR QUESTION ANSWERED**

```
❓ "No Redis, No DB? Then where? Local pe? Kaise? Repositories?"
```

**ANSWER: PostgreSQL Database!** ✅

---

## **COMPLETE FLOW: REGISTRATION → WEBHOOK → CLONING → STORAGE**

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: REGISTRATION                          │
└─────────────────────────────────────────────────────────────────┘

User clicks "Connect Organization"
    ↓
POST /webhook/register
    ├─ org_id: "beta-org-for-pustak"
    └─ user_id: "aca20dc6-..." (from JWT token)
    ↓
Backend receives request
    ↓
Stores in PostgreSQL DATABASE:
    ├─ Table: org_registrations
    ├─ Columns:
    │  ├─ user_id: "aca20dc6-..."
    │  ├─ org_id: "beta-org-for-pustak"
    │  └─ registered_at: NOW()
    ↓
Returns to user:
    ├─ webhook_url: "https://xxxxx.ngrok.io/webhook"
    └─ message: "Organization registered!"

✅ DATA STORED IN: PostgreSQL (org_registrations table)
```

---

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: WEBHOOK RECEIVED                      │
└─────────────────────────────────────────────────────────────────┘

User pushes code to GitHub
    ↓
GitHub sends webhook to: POST /webhook
    ├─ Headers: X-Hub-Signature-256, X-GitHub-Event
    └─ Body: repository, commits, ref, etc.
    ↓
Backend receives webhook
    ↓
webhook_multi_org() processes:
    ├─ Looks up org_webhooks table
    ├─ Finds: user_id, org_id, webhook_secret, github_token_id
    └─ Extracts webhook context
    ↓
Stores in PostgreSQL DATABASE:
    ├─ Table: commit_events
    ├─ Columns:
    │  ├─ event_id: "ba48c37f-..." (UUID)
    │  ├─ repo_id: "beta-org-for-pustak/College-ERP"
    │  ├─ commit_sha: "9dcdaa34..."
    │  ├─ user_id: "aca20dc6-..."
    │  ├─ org_id: "beta-org-for-pustak"
    │  ├─ github_token_id: "token-uuid-123"
    │  ├─ processed: FALSE
    │  └─ created_at: NOW()
    ↓
Returns 200 OK immediately

✅ DATA STORED IN: PostgreSQL (commit_events table)
```

---

```
┌─────────────────────────────────────────────────────────────────┐
│                 STEP 3: EVENT CONSUMER POLLING                   │
└─────────────────────────────────────────────────────────────────┘

Event Consumer starts (separate process)
    ↓
Every 5 seconds:
    ├─ Query PostgreSQL: SELECT * FROM commit_events WHERE processed = FALSE
    └─ Gets events from DATABASE
    ↓
For each event:
    ├─ Extract: user_id, org_id, github_token_id
    ├─ Query PostgreSQL: SELECT github_token FROM user_github_tokens WHERE ...
    └─ Gets token from DATABASE
    ↓
Creates TEMPORARY directory:
    ├─ tmpdir = tempfile.mkdtemp(prefix="docai_smart_")
    └─ Location: /tmp/docai_smart_abc123xyz/
    ↓
Clones repo to TEMPORARY directory:
    ├─ git clone https://x-access-token:TOKEN@github.com/org/repo.git /tmp/docai_smart_abc123xyz/
    └─ ✅ REPO NOW IN: /tmp/docai_smart_abc123xyz/
    ↓
Generates docs in TEMPORARY directory:
    ├─ Creates: /tmp/docai_smart_abc123xyz/docs/
    ├─ Creates: /tmp/docai_smart_abc123xyz/docs/SUMMARY.md
    ├─ Creates: /tmp/docai_smart_abc123xyz/docs/ARCHITECTURE.md
    └─ etc.
    ↓
Commits & pushes to GitHub:
    ├─ git add .
    ├─ git commit -m "docs: auto-generated"
    └─ git push (using same token)
    ↓
Deletes TEMPORARY directory:
    ├─ shutil.rmtree(tmpdir)
    └─ /tmp/docai_smart_abc123xyz/ DELETED
    ↓
Updates PostgreSQL DATABASE:
    ├─ Table: commit_events
    ├─ UPDATE processed = TRUE WHERE event_id = ...
    └─ Marks event as processed

✅ DATA STORED IN: PostgreSQL (commit_events table - processed flag)
✅ DOCS STORED IN: GitHub repo (/docs folder)
✅ TEMPORARY FILES: Deleted (no local storage)
```

---

## **DATABASE SCHEMA - WHERE EVERYTHING IS STORED**

### **Table 1: org_registrations**
```sql
CREATE TABLE org_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    org_id VARCHAR(255) NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

**Stores:** Which user registered which org

---

### **Table 2: org_webhooks**
```sql
CREATE TABLE org_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    org_id VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255) NOT NULL UNIQUE,
    github_token_id UUID NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

**Stores:** Webhook secrets for each org

---

### **Table 3: user_github_tokens**
```sql
CREATE TABLE user_github_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    github_token TEXT NOT NULL,
    org_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Stores:** GitHub tokens for each user/org

---

### **Table 4: commit_events**
```sql
CREATE TABLE commit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    branch VARCHAR(255),
    files_changed TEXT,
    user_id UUID,
    org_id VARCHAR(255),
    github_token_id UUID,
    processed BOOLEAN DEFAULT FALSE,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(repo_id, commit_sha)
);
```

**Stores:** All webhook events for processing

---

## **COMPLETE DATA FLOW DIAGRAM**

```
┌─────────────────────────────────────────────────────────────────┐
│                        GITHUB                                    │
│                   (Push Events)                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
                    POST /webhook
                            │
                            ↓
                ┌───────────────────────┐
                │  webhook_multi_org()  │
                └───────────────────────┘
                            │
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
        ↓                                       ↓
    Query DB                           Store in DB
    org_webhooks                    commit_events
        │                                       │
        ↓                                       ↓
    Find:                               Stores:
    - webhook_secret                    - repo_id
    - user_id                           - commit_sha
    - org_id                            - user_id
    - github_token_id                   - org_id
                                        - github_token_id
                                        - processed: FALSE
                                        - created_at
                                            │
                                            ↓
                        ┌───────────────────────────────┐
                        │   PostgreSQL Database         │
                        │   (All data stored here!)     │
                        └───────────────────────────────┘
                                            │
                                            ↓
                        ┌───────────────────────────────┐
                        │   Event Consumer (Polling)    │
                        │   Every 5 seconds             │
                        └───────────────────────────────┘
                                            │
                                            ↓
                        Query: SELECT * FROM commit_events
                        WHERE processed = FALSE
                                            │
                                            ↓
                        ┌───────────────────────────────┐
                        │   For each event:             │
                        │   1. Get token from DB        │
                        │   2. Create temp dir          │
                        │   3. Clone repo               │
                        │   4. Generate docs            │
                        │   5. Push to GitHub           │
                        │   6. Delete temp dir          │
                        │   7. Update DB (processed=T)  │
                        └───────────────────────────────┘
                                            │
                                            ↓
                        ┌───────────────────────────────┐
                        │   GitHub                      │
                        │   (Docs pushed here!)         │
                        └───────────────────────────────┘
```

---

## **ANSWER TO YOUR QUESTIONS**

### **Q1: No Redis, No DB?**
**A:** ✅ **YES, WE HAVE DATABASE!** PostgreSQL

```
DATABASE_URL = postgresql://localhost/lekhak_ai
```

---

### **Q2: Then where?**
**A:** Everything stored in **PostgreSQL Database**

```
Tables:
- org_registrations (which user registered which org)
- org_webhooks (webhook secrets)
- user_github_tokens (GitHub tokens)
- commit_events (events to process)
```

---

### **Q3: Local pe?**
**A:** YES! Local PostgreSQL database

```
Location: postgresql://localhost/lekhak_ai
```

---

### **Q4: Kaise?**
**A:** Using `commit_bus.pool` (async PostgreSQL connection pool)

```python
# In main.py (Line 80-81)
commit_bus = CommitBusService(DATABASE_URL)
await commit_bus.init_pool()
```

---

### **Q5: Repositories?**
**A:** Repos cloned to **TEMPORARY directory** only!

```
Location: /tmp/docai_smart_<random>/
Lifetime: Only during processing
Cleanup: Automatically deleted after use
```

---

### **Q6: When we register org, it says cloning. So where?**
**A:** Cloning happens in **TWO PLACES**:

#### **During Registration:**
```
NO CLONING happens during registration!
Only stores org_id + user_id in database
```

#### **During Event Processing:**
```
1. Webhook received
2. Event stored in database
3. Event Consumer polls database
4. Gets event from database
5. Clones to: /tmp/docai_smart_abc123xyz/
6. Generates docs
7. Pushes to GitHub
8. Deletes temp directory
```

---

## **COMPLETE STORAGE ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA STORAGE LAYERS                           │
└─────────────────────────────────────────────────────────────────┘

LAYER 1: PERSISTENT STORAGE (PostgreSQL Database)
├─ org_registrations table
├─ org_webhooks table
├─ user_github_tokens table
├─ commit_events table
└─ All data PERSISTED

LAYER 2: TEMPORARY STORAGE (Local /tmp)
├─ /tmp/docai_smart_abc123xyz/ (during processing)
├─ Cloned repo
├─ Generated docs
└─ DELETED after processing

LAYER 3: PERMANENT STORAGE (GitHub)
├─ /docs folder in repo
├─ SUMMARY.md
├─ ARCHITECTURE.md
└─ All docs PUSHED to GitHub

LAYER 4: NO STORAGE (Deleted)
├─ Temporary directories
├─ Cloned repos
└─ All cleaned up automatically
```

---

## **SUMMARY**

| Component | Storage | Lifetime | Location |
|-----------|---------|----------|----------|
| **Org Registration** | PostgreSQL | Permanent | Database |
| **Webhook Secrets** | PostgreSQL | Permanent | Database |
| **GitHub Tokens** | PostgreSQL | Permanent | Database |
| **Events** | PostgreSQL | Permanent | Database |
| **Cloned Repos** | Local /tmp | Temporary | /tmp/docai_smart_* |
| **Generated Docs** | GitHub | Permanent | GitHub repo |
| **Temp Files** | Local /tmp | Temporary | Deleted |

---

## **KEY POINTS**

✅ **Database:** PostgreSQL (persistent)
✅ **Temporary Files:** /tmp (deleted after use)
✅ **Final Docs:** GitHub (permanent)
✅ **No Redis:** Not needed (using database)
✅ **No Local Storage:** Everything cleaned up
✅ **Scalable:** All data in database

**Everything is tracked in PostgreSQL!** 🎯
