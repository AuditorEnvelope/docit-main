# 🚀 Lekhak AI - Complete Workflow Guide (PART 2)
## Background Processing & Documentation Generation

---

## PHASE 4: EVENT PROCESSING

### **Step 9: Background Worker Picks Up Event**

**What Happens:**
- A background worker (event consumer) runs continuously
- It queries the database for pending events
- It picks up the event we just stored
- It marks the event as "processing"

**Function in Code:**
- Event consumer loop (in `src/processors/event_consumer.py` or similar)
- Queries: `SELECT * FROM commit_events WHERE processed = false LIMIT 10`

**Tables Involved:**

| Table | What's Read | What's Updated | Why |
|-------|------------|-----------------|-----|
| `commit_events` | All pending events | Mark as processing | To find events to process |

**Why This Step:**
- We process events in the background so the webhook endpoint returns quickly
- We mark as "processing" so we don't process the same event twice

---

### **Step 10: Clone Repository**

**What Happens:**
- The background worker clones the repository from GitHub
- It uses the user's GitHub token to authenticate
- It clones into a temporary directory

**Function in Code:**
- `smart_processor.handle_push_event()` or similar

**Command Executed:**
```bash
git clone https://x-access-token:{GITHUB_TOKEN}@github.com/jai-mahakal-poc/mahakal.git /tmp/docai_smart_xxxxx
```

**Why This Step:**
- We need the actual code to analyze it
- We use the GitHub token so we can access private repositories
- We clone into a temporary directory so we don't interfere with other events

**Token Used:**
- **GitHub Token** (from `user_github_tokens` table)
- This is the user's personal access token that gives us permission to access their repos

---

### **Step 11: Analyze Changed Files**

**What Happens:**
- The worker looks at which files changed in this commit
- For each changed file, it reads the file content
- It analyzes the code to understand what changed

**Function in Code:**
- `smart_processor.analyze_changes()`

**What Happens:**
1. Read the changed files from the repository
2. Extract code structure (functions, classes, etc.)
3. Identify what's new or modified

**Example:**
```
Changed files:
  - src/new_feature.py (added)
  - README.md (modified)

Analysis:
  - src/new_feature.py contains a new class "FeatureProcessor"
  - README.md was updated with new instructions
```

---

### **Step 12: Generate Documentation with AI**

**What Happens:**
- For each changed file, send the code to an LLM (AI model)
- The LLM generates documentation for the code
- The documentation explains what the code does

**Function in Code:**
- `smart_processor.generate_documentation()`
- Uses LLM API (Gemini, Groq, or DeepSeek)

**Example Prompt Sent to LLM:**
```
Here's some Python code:

class FeatureProcessor:
    def __init__(self, config):
        self.config = config
    
    def process(self, data):
        return self.config.apply(data)

Generate clear, concise documentation for this code.
```

**Example Response from LLM:**
```
## FeatureProcessor

A processor class that applies configuration to data.

### Methods:
- `__init__(config)`: Initialize with configuration
- `process(data)`: Apply configuration to data and return result
```

**Why This Step:**
- We automatically generate documentation so developers don't have to write it manually
- The AI understands the code and explains it clearly

---

### **Step 13: Store Documentation in Database**

**What Happens:**
- The generated documentation is stored in the database
- It's linked to the commit SHA
- It's organized hierarchically (Repo → SDK → Module → Feature → Function)

**Function in Code:**
- `smart_processor.store_documentation()`

**What Gets Stored:**

| Table | What's Stored | Why |
|-------|---------------|-----|
| `doc_versions` | Documentation content, version number, commit SHA | Keeps history of all documentation versions |
| `doc_nodes` | Hierarchical documentation tree (repo, module, function, etc.) | Organizes documentation hierarchically |
| `repo_sync_state` | Last processed commit SHA, sync status | Tracks which commits have been processed |

**Example Data Stored:**
```
doc_versions:
  id: 1001
  repo_id: jai-mahakal-poc/mahakal
  version: 1
  commit_sha: cfc41a13...
  content: "## FeatureProcessor\n\nA processor class..."
  created_at: 2024-10-27 10:35:00

doc_nodes:
  id: 2001
  repo_id: jai-mahakal-poc/mahakal
  type: "class"
  title: "FeatureProcessor"
  path: "src/new_feature.py"
  content: "A processor class that applies configuration to data."
  commit_sha: cfc41a13...
  parent_id: 2000 (module node)

repo_sync_state:
  repo_id: jai-mahakal-poc/mahakal
  last_commit_sha: cfc41a13...
  last_sync_at: 2024-10-27 10:35:00
```

---

### **Step 14: Push Documentation Back to GitHub**

**What Happens:**
- Lekhak AI creates a documentation file (e.g., `DOCUMENTATION.md`)
- It commits this file to the repository
- It pushes the commit back to GitHub

**Function in Code:**
- `smart_processor.push_documentation_to_github()`

**Commands Executed:**
```bash
# Create/update documentation file
echo "## Documentation\n\n..." > DOCUMENTATION.md

# Commit the file
git add DOCUMENTATION.md
git commit -m "docs: Auto-generated documentation by Lekhak AI"

# Push back to GitHub
git push origin main
```

**Why This Step:**
- The documentation is now visible in the repository
- Developers can see the auto-generated docs alongside their code
- The docs stay in sync with the code

**Token Used:**
- **GitHub Token** (from `user_github_tokens` table)
- This gives us permission to push to the repository

---

### **Step 15: Mark Event as Processed**

**What Happens:**
- The event is marked as "processed" in the database
- The temporary directory is deleted
- The worker is ready to process the next event

**Function in Code:**
- `commit_bus.mark_event_processed()`

**Tables Involved:**

| Table | What's Updated | Why |
|-------|-----------------|-----|
| `commit_events` | Set processed = true, updated_at = now | Record that we're done with this event |

**Example Data Updated:**
```
commit_events:
  id: 259f1845-cf2b-47a5-8e6e-13f45849233f
  processed: true
  updated_at: 2024-10-27 10:35:00
```

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LEKHAK AI DATA FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: AUTHENTICATION
═══════════════════════════════════════════════════════════════════════════════

  User Portal
      │
      ├─→ Click "Login with GitHub"
      │       │
      │       └─→ GET /auth/github
      │           │
      │           └─→ Redirect to GitHub OAuth
      │
      ├─→ User logs in on GitHub
      │       │
      │       └─→ GitHub redirects with code
      │
      └─→ GET /auth/callback?code=xxx
          │
          ├─→ Exchange code for GitHub token
          │
          ├─→ Store in DATABASE:
          │   ├─ users (user info)
          │   ├─ user_github_tokens (GitHub token)
          │   └─ sessions (JWT token)
          │
          └─→ User is now logged in ✅


PHASE 2: ORGANIZATION SETUP
═══════════════════════════════════════════════════════════════════════════════

  User Portal
      │
      ├─→ GET /auth/user-organizations
      │   │
      │   └─→ Fetch from GitHub API using stored token
      │
      ├─→ User selects organization "jai-mahakal-poc"
      │
      └─→ POST /webhook/register
          │
          ├─→ Store in DATABASE:
          │   ├─ org_registrations (user → org mapping)
          │   └─ org_webhooks (webhook secret + token)
          │
          └─→ Return webhook URL to user ✅


PHASE 3: WEBHOOK CONFIGURATION
═══════════════════════════════════════════════════════════════════════════════

  User goes to GitHub
      │
      └─→ Configure webhook on organization
          │
          ├─→ Payload URL: https://your-domain.com/webhook
          ├─→ Events: Push events
          └─→ Secret: (GitHub generates)


PHASE 4: CODE PUSH & WEBHOOK TRIGGER
═══════════════════════════════════════════════════════════════════════════════

  Developer
      │
      └─→ git push to GitHub
          │
          └─→ GitHub detects push
              │
              └─→ POST /webhook (to Lekhak AI)
                  │
                  ├─→ Verify signature using webhook_secret
                  │
                  ├─→ Extract org from repo name
                  │   "jai-mahakal-poc/mahakal" → "jai-mahakal-poc"
                  │
                  ├─→ Look up user in org_registrations
                  │
                  ├─→ Get GitHub token from user_github_tokens
                  │
                  └─→ Create CommitEvent and store in DATABASE:
                      └─ commit_events (marked as pending)


PHASE 5: BACKGROUND PROCESSING
═══════════════════════════════════════════════════════════════════════════════

  Event Consumer (Background Worker)
      │
      ├─→ Query: SELECT * FROM commit_events WHERE processed = false
      │
      ├─→ Pick up event
      │
      ├─→ Clone repository using GitHub token
      │   git clone https://x-access-token:{TOKEN}@github.com/...
      │
      ├─→ Analyze changed files
      │
      ├─→ Send code to LLM for documentation
      │   (Gemini, Groq, or DeepSeek)
      │
      ├─→ Store documentation in DATABASE:
      │   ├─ doc_versions (documentation content)
      │   ├─ doc_nodes (hierarchical tree)
      │   └─ repo_sync_state (sync status)
      │
      ├─→ Push documentation back to GitHub
      │   git commit -m "docs: Auto-generated documentation"
      │   git push origin main
      │
      └─→ Mark event as processed in DATABASE:
          └─ commit_events (set processed = true)


RESULT
═══════════════════════════════════════════════════════════════════════════════

  ✅ Documentation is now in the GitHub repository
  ✅ Documentation is stored in Lekhak AI database
  ✅ Developers can see auto-generated docs
  ✅ Docs stay in sync with code
```

---

## Table Usage at Each Step

```
STEP 1: User Clicks "Login with GitHub"
├─ Tables Read: (none)
├─ Tables Written: (none)
└─ Purpose: Redirect to GitHub OAuth

STEP 2: GitHub Redirects Back with Code
├─ Tables Read: (none)
├─ Tables Written:
│  ├─ users (INSERT new user or UPDATE existing)
│  ├─ user_github_tokens (INSERT GitHub token)
│  └─ sessions (INSERT JWT session token)
└─ Purpose: Store user and authentication info

STEP 3: User Selects Organization
├─ Tables Read: (none - data comes from GitHub API)
├─ Tables Written: (none)
└─ Purpose: Fetch organization list from GitHub

STEP 4: User Registers Organization
├─ Tables Read:
│  └─ user_github_tokens (SELECT to get token_id)
├─ Tables Written:
│  ├─ org_registrations (INSERT user → org mapping)
│  └─ org_webhooks (INSERT webhook info)
└─ Purpose: Store organization registration

STEP 5: User Configures Webhook on GitHub
├─ Tables Read: (none)
├─ Tables Written: (none - GitHub stores this)
└─ Purpose: Manual configuration on GitHub

STEP 6: Developer Pushes Code
├─ Tables Read: (none)
├─ Tables Written: (none)
└─ Purpose: Code change on GitHub

STEP 7: GitHub Sends Webhook to Lekhak AI
├─ Tables Read:
│  ├─ org_registrations (SELECT user_id by org_id)
│  └─ user_github_tokens (SELECT token by user_id)
├─ Tables Written: (none yet)
└─ Purpose: Verify webhook and find user context

STEP 8: Store Event in Commit Bus
├─ Tables Read: (none)
├─ Tables Written:
│  └─ commit_events (INSERT new event, marked as pending)
└─ Purpose: Queue event for processing

STEP 9: Background Worker Picks Up Event
├─ Tables Read:
│  └─ commit_events (SELECT pending events)
├─ Tables Written:
│  └─ commit_events (UPDATE status to processing)
└─ Purpose: Find and lock event for processing

STEP 10: Clone Repository
├─ Tables Read:
│  └─ user_github_tokens (SELECT token by token_id)
├─ Tables Written: (none)
└─ Purpose: Get token to authenticate with GitHub

STEP 11: Analyze Changed Files
├─ Tables Read: (none)
├─ Tables Written: (none)
└─ Purpose: Parse code locally

STEP 12: Generate Documentation with AI
├─ Tables Read: (none)
├─ Tables Written: (none)
└─ Purpose: Call LLM API (external)

STEP 13: Store Documentation in Database
├─ Tables Read: (none)
├─ Tables Written:
│  ├─ doc_versions (INSERT documentation)
│  ├─ doc_nodes (INSERT hierarchical tree)
│  └─ repo_sync_state (INSERT/UPDATE sync status)
└─ Purpose: Store generated documentation

STEP 14: Push Documentation Back to GitHub
├─ Tables Read:
│  └─ user_github_tokens (SELECT token by token_id)
├─ Tables Written: (none)
└─ Purpose: Get token to push to GitHub

STEP 15: Mark Event as Processed
├─ Tables Read: (none)
├─ Tables Written:
│  └─ commit_events (UPDATE processed = true)
└─ Purpose: Mark event as complete
```

---

**Continue to PART 3 for:** Token explanations and visual flowchart.
