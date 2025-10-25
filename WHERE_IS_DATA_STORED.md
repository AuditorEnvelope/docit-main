# 🎯 **WHERE IS DATA STORED? - SIMPLE ANSWER**

## **THE ANSWER IN ONE SENTENCE**

```
PostgreSQL Database + GitHub Repos + Temporary /tmp folder
```

---

## **STEP-BY-STEP BREAKDOWN**

### **STEP 1: User Registers Organization**

```
User clicks: "Connect Organization"
    ↓
Enters: "beta-org-for-pustak"
    ↓
Backend stores in: PostgreSQL Database
    ├─ Table: org_registrations
    ├─ Stores: user_id, org_id, registered_at
    └─ Location: postgresql://localhost/lekhak_ai
    ↓
✅ DATA STORED IN: PostgreSQL
```

**Query to see it:**
```bash
psql -U postgres -d lekhak_ai -c "SELECT * FROM org_registrations;"
```

---

### **STEP 2: User Pushes Code to GitHub**

```
User pushes code
    ↓
GitHub sends webhook
    ↓
Backend receives webhook
    ↓
Backend stores in: PostgreSQL Database
    ├─ Table: commit_events
    ├─ Stores: repo_id, commit_sha, user_id, org_id, processed=FALSE
    └─ Location: postgresql://localhost/lekhak_ai
    ↓
✅ DATA STORED IN: PostgreSQL
```

**Query to see it:**
```bash
psql -U postgres -d lekhak_ai -c "SELECT * FROM commit_events WHERE processed = FALSE;"
```

---

### **STEP 3: Event Consumer Processes Event**

```
Event Consumer polls database every 5 seconds
    ↓
Finds unprocessed events in: PostgreSQL Database
    ↓
For each event:
    1. Gets GitHub token from: PostgreSQL Database
    2. Creates temporary folder: /tmp/docai_smart_abc123xyz/
    3. Clones repo to: /tmp/docai_smart_abc123xyz/
    4. Generates docs in: /tmp/docai_smart_abc123xyz/docs/
    5. Pushes docs to: GitHub repo
    6. Deletes: /tmp/docai_smart_abc123xyz/ (cleanup!)
    7. Updates: PostgreSQL Database (processed=TRUE)
    ↓
✅ FINAL DOCS STORED IN: GitHub repo
✅ EVENT STATUS STORED IN: PostgreSQL
✅ TEMP FILES: DELETED (no trace left)
```

**Query to see processed events:**
```bash
psql -U postgres -d lekhak_ai -c "SELECT * FROM commit_events WHERE processed = TRUE;"
```

---

## **WHERE IS EACH THING STORED?**

### **1. Organization Registration**
```
WHERE: PostgreSQL Database
TABLE: org_registrations
COLUMNS: user_id, org_id, registered_at
QUERY: SELECT * FROM org_registrations;
```

### **2. Webhook Secrets**
```
WHERE: PostgreSQL Database
TABLE: org_webhooks
COLUMNS: user_id, org_id, webhook_secret, github_token_id
QUERY: SELECT * FROM org_webhooks;
```

### **3. GitHub Tokens**
```
WHERE: PostgreSQL Database
TABLE: user_github_tokens
COLUMNS: user_id, github_token, org_id, is_active
QUERY: SELECT * FROM user_github_tokens;
```

### **4. Events to Process**
```
WHERE: PostgreSQL Database
TABLE: commit_events
COLUMNS: repo_id, commit_sha, user_id, org_id, processed, retry_count
QUERY: SELECT * FROM commit_events;
```

### **5. Cloned Repositories**
```
WHERE: Local /tmp directory
PATH: /tmp/docai_smart_<random_id>/
LIFETIME: Only during processing
CLEANUP: Automatically deleted after use
```

### **6. Generated Documentation**
```
WHERE: GitHub Repository
PATH: /docs folder in each repo
FILES: SUMMARY.md, ARCHITECTURE.md, CHANGELOG.md, etc.
LIFETIME: Permanent (in GitHub)
```

---

## **VISUAL STORAGE MAP**

```
┌──────────────────────────────────────────────────────────┐
│                   YOUR SYSTEM                            │
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│           PostgreSQL Database (PERSISTENT)              │
│  postgresql://localhost/lekhak_ai                       │
├─────────────────────────────────────────────────────────┤
│ Tables:                                                 │
│ ├─ org_registrations (org registrations)               │
│ ├─ org_webhooks (webhook secrets)                      │
│ ├─ user_github_tokens (GitHub tokens)                 │
│ └─ commit_events (events to process)                  │
│                                                         │
│ ✅ PERMANENT STORAGE                                    │
│ ✅ SURVIVES SERVER RESTART                             │
│ ✅ SURVIVES POWER LOSS                                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│      Local /tmp Directory (TEMPORARY)                   │
│  /tmp/docai_smart_abc123xyz/                           │
├─────────────────────────────────────────────────────────┤
│ Contents (during processing only):                      │
│ ├─ Cloned repository                                   │
│ ├─ Generated documentation                             │
│ └─ Temporary files                                     │
│                                                         │
│ ❌ TEMPORARY STORAGE                                    │
│ ❌ DELETED AFTER PROCESSING                            │
│ ❌ NOT PERSISTED                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│        GitHub Repository (PERMANENT)                    │
│  https://github.com/org/repo                           │
├─────────────────────────────────────────────────────────┤
│ Contents:                                               │
│ ├─ /docs folder                                        │
│ ├─ SUMMARY.md                                          │
│ ├─ ARCHITECTURE.md                                     │
│ ├─ CHANGELOG.md                                        │
│ └─ Other generated docs                                │
│                                                         │
│ ✅ PERMANENT STORAGE                                    │
│ ✅ SURVIVES EVERYTHING                                 │
│ ✅ VISIBLE TO USERS                                    │
└─────────────────────────────────────────────────────────┘
```

---

## **ANSWERING YOUR SPECIFIC QUESTIONS**

### **Q: No Redis?**
```
✅ CORRECT - No Redis needed
   We use PostgreSQL for everything
```

### **Q: No DB?**
```
❌ WRONG - We HAVE database!
   PostgreSQL at: postgresql://localhost/lekhak_ai
```

### **Q: Then where?**
```
✅ PostgreSQL Database!
   All data stored there
```

### **Q: Local pe?**
```
✅ YES - Local PostgreSQL
   Running on your machine
```

### **Q: Kaise?**
```
✅ Using Python asyncio + asyncpg
   Code: commit_bus.pool (async connection pool)
```

### **Q: Repositories?**
```
✅ Cloned to: /tmp/docai_smart_<random>/
   Only during processing
   Automatically deleted after
```

### **Q: When we register org, it says cloning. So where?**
```
❌ NO CLONING during registration!
   Only stores org_id in database

✅ CLONING happens during event processing:
   1. Event received from GitHub
   2. Event stored in database
   3. Event Consumer polls database
   4. Clones to: /tmp/docai_smart_abc123xyz/
   5. Generates docs
   6. Pushes to GitHub
   7. Deletes temp folder
```

---

## **COMPLETE LIFECYCLE**

```
┌─────────────────────────────────────────────────────────┐
│                    LIFECYCLE                            │
└─────────────────────────────────────────────────────────┘

1. USER REGISTERS ORG
   └─ Stored in: PostgreSQL (org_registrations table)

2. USER PUSHES CODE TO GITHUB
   └─ Webhook sent to: /webhook endpoint

3. WEBHOOK RECEIVED
   └─ Event stored in: PostgreSQL (commit_events table)

4. EVENT CONSUMER POLLS
   └─ Reads from: PostgreSQL (commit_events table)

5. EVENT CONSUMER PROCESSES
   ├─ Gets token from: PostgreSQL (user_github_tokens table)
   ├─ Creates temp dir: /tmp/docai_smart_abc123xyz/
   ├─ Clones repo to: /tmp/docai_smart_abc123xyz/
   ├─ Generates docs in: /tmp/docai_smart_abc123xyz/docs/
   ├─ Pushes to: GitHub repo
   ├─ Deletes: /tmp/docai_smart_abc123xyz/
   └─ Updates: PostgreSQL (processed=TRUE)

6. FINAL STATE
   ├─ Event status in: PostgreSQL (processed=TRUE)
   ├─ Docs in: GitHub repo (/docs folder)
   └─ Temp files: DELETED (no trace)
```

---

## **DATABASE LOCATION**

```bash
# Your PostgreSQL database is at:
postgresql://localhost/lekhak_ai

# Connect to it:
psql -U postgres -d lekhak_ai

# See all tables:
\dt

# See all data:
SELECT * FROM org_registrations;
SELECT * FROM org_webhooks;
SELECT * FROM user_github_tokens;
SELECT * FROM commit_events;
```

---

## **SUMMARY TABLE**

| What | Where | Permanent? | Lifetime |
|------|-------|-----------|----------|
| Org Registration | PostgreSQL | ✅ YES | Forever |
| Webhook Secrets | PostgreSQL | ✅ YES | Forever |
| GitHub Tokens | PostgreSQL | ✅ YES | Forever |
| Events | PostgreSQL | ✅ YES | Forever |
| Cloned Repos | /tmp | ❌ NO | During processing |
| Generated Docs | GitHub | ✅ YES | Forever |
| Temp Files | /tmp | ❌ NO | Deleted |

---

## **KEY TAKEAWAYS**

✅ **Database:** PostgreSQL (persistent, local)
✅ **Temporary Files:** /tmp (deleted after use)
✅ **Final Docs:** GitHub (permanent)
✅ **No Redis:** Not needed
✅ **No Cloud:** Everything local
✅ **Scalable:** All data in database

**Everything is tracked and stored in PostgreSQL!** 🎯
