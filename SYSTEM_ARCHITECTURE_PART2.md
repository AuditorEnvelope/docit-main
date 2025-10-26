# 🏗️ LEKHAK AI - SYSTEM ARCHITECTURE DEEP DIVE (PART 2)

> **File-by-File Architecture, Webhook Flow, Event Processing**

---

## 📁 FILE-BY-FILE ARCHITECTURE

### **1. `src/main.py` - FastAPI Server & Routes**

**Purpose:** Entry point, HTTP routes, middleware, service initialization  
**Size:** ~1100 lines

**Responsibilities:**
1. Initialize all services on startup
2. Handle HTTP routes
3. Webhook endpoint
4. Auth endpoints
5. Documentation endpoints

**Key Routes:**
```python
POST /webhook                    # GitHub webhook receiver
GET  /auth/github                # OAuth redirect to GitHub
GET  /auth/callback              # OAuth callback handler
GET  /auth/me                    # Get current user info
GET  /auth/repositories          # Get user's repos
GET  /auth/user-organizations    # Get user's orgs
POST /webhook/register           # Register org for webhooks
GET  /webhook/check-app-installation  # Check if app installed
GET  /docs/generate              # Generate docs for repo
GET  /docs/fetch-file            # Fetch doc file from GitHub
```

**Startup Flow:**
```python
@app.on_event("startup")
async def startup():
    # 1. Initialize Quality Checker
    quality_checker = DocumentationQualityChecker()
    
    # 2. Initialize Commit Bus (event queue)
    commit_bus = CommitBusService(DATABASE_URL)
    await commit_bus.init_pool()
    
    # 3. Initialize Auth Service
    auth_service = AuthService(DATABASE_URL)
    await auth_service.init_pool()
    
    # 4. Initialize Subscription Service
    subscription_service = SubscriptionService(DATABASE_URL)
    
    # 5. Initialize Overlay Service
    overlay_service = OverlayService(DATABASE_URL)
```

**Webhook Endpoint:**
```python
@app.post("/webhook")
async def handle_webhook(request: Request):
    # 1. Get raw body for signature verification
    body = await request.body()
    
    # 2. Verify GitHub webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    verify_webhook_signature(body, signature)
    
    # 3. Parse payload
    payload = json.loads(body)
    
    # 4. Call webhook handler
    result = await webhook_multi_org(payload, commit_bus)
    
    # 5. Return 200 OK immediately (async processing)
    return {"status": "queued"}
```

---

### **2. `src/webhooks/webhook_multi_org.py` - Multi-Org Webhook Handler**

**Purpose:** Extract org context from webhook, attach user info  
**Size:** ~150 lines

**Key Function:** `get_org_context_from_repo(repo_full_name, commit_bus)`

**Logic:**
```python
async def get_org_context_from_repo(repo_full_name, commit_bus):
    """
    Extract org from "org/repo" and find user who owns it
    
    Flow:
    1. Extract org from "org/repo" → "org"
    2. Check org_webhooks table → find user & token
    3. If not found, check org_registrations → find user
    4. If not found, check commit_events → find user with history
    5. Return: {user_id, org_id, github_token_id}
    """
    
    org_id = repo_full_name.split('/')[0]
    
    # Try org_webhooks first (pre-registered)
    org_record = await conn.fetchrow(
        "SELECT user_id, github_token_id FROM org_webhooks WHERE org_id = $1",
        org_id
    )
    if org_record:
        return dict(org_record)
    
    # Try org_registrations (newly registered)
    reg_record = await conn.fetchrow(
        "SELECT user_id FROM org_registrations WHERE org_id = $1",
        org_id
    )
    if reg_record:
        # Get their token
        token = await conn.fetchrow(
            "SELECT token_id FROM user_github_tokens WHERE user_id = $1",
            reg_record['user_id']
        )
        return {
            'user_id': reg_record['user_id'],
            'org_id': org_id,
            'github_token_id': token['token_id']
        }
    
    # Try commit_events (orgs with history)
    user_record = await conn.fetchrow(
        """SELECT ce.user_id FROM commit_events ce
           WHERE ce.org_id = $1 AND ce.user_id IS NOT NULL
           ORDER BY ce.created_at DESC LIMIT 1""",
        org_id
    )
    if user_record:
        return {'user_id': user_record['user_id'], 'org_id': org_id}
    
    # Not found - fallback to ENV token
    return None
```

**Why This Matters:**
- Enables multi-org support
- Finds correct GitHub token for each org
- Attaches user context to event BEFORE processing
- Fallback to ENV token if org not registered

---

### **3. `src/core/commit_bus.py` - Event Queue Service**

**Purpose:** Store and retrieve events from database  
**Size:** ~200 lines

**Key Methods:**
```python
class CommitBusService:
    async def init_pool()
        # Initialize database connection pool
    
    async def store_event(event: CommitEvent) → event_id
        # INSERT event into commit_events table
        # Returns: event_id (UUID)
    
    async def get_pending_events(limit=10) → List[CommitEvent]
        # SELECT * FROM commit_events WHERE processed=false LIMIT 10
        # Returns: List of unprocessed events
    
    async def mark_event_processed(event_id, success=True)
        # UPDATE commit_events SET processed=true WHERE id=$1
        # If success=false: increment retry_count
    
    async def get_event_by_id(event_id) → CommitEvent
        # SELECT * FROM commit_events WHERE id=$1
```

**Data Flow:**
```
CommitEvent object (in memory)
    ↓
commit_bus.store_event(event)
    ↓
INSERT INTO commit_events (...)
    ↓
Event Consumer polls this table
    ↓
Processes event
    ↓
commit_bus.mark_event_processed(event_id)
    ↓
UPDATE processed=true
```

---

### **4. `src/core/event_consumer.py` - Async Event Processor**

**Purpose:** Poll events and process them  
**Size:** ~400 lines

**Key Responsibilities:**
1. Startup: Check all organizations for missed commits
2. Poll: Get pending events from commit_events table
3. Process: Clone repo, analyze code, generate docs
4. Update: Mark event as processed

**Startup Flow:**
```python
async def check_missed_commits():
    """
    Called on startup to recover from downtime
    """
    # 1. Get all organizations with activity
    orgs = await get_all_organizations()
    
    # 2. For each org:
    for org_id in orgs:
        # Get user's GitHub token
        token = await get_github_token_for_org(org_id)
        
        # Get all repos in org
        repos = await github_api.get_org_repos(org_id, token)
        
        # For each repo:
        for repo in repos:
            # Get last processed SHA
            last_sha = await get_last_processed_sha(org_id, repo)
            
            # Fetch recent commits from GitHub
            commits = await github_api.get_commits_since(repo, last_sha, token)
            
            # Store as events
            for commit in commits:
                await commit_bus.store_event(CommitEvent(...))
```

**Processing Loop:**
```python
async def process_events():
    """
    Main loop: poll and process events
    """
    while True:
        # 1. Get pending events
        events = await commit_bus.get_pending_events(limit=10)
        
        if not events:
            await asyncio.sleep(5)  # Poll every 5 seconds
            continue
        
        # 2. Process in parallel (max 3 concurrent)
        tasks = [process_event(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)

async def process_event(event: CommitEvent):
    """
    Process a single event
    """
    try:
        # 1. Get user's GitHub token
        token = await get_github_token(event.user_id)
        
        # 2. Clone repository
        repo_path = await clone_repo(event.repo_id, token)
        
        # 3. Call smart processor
        result = await smart_processor.process_event(
            repo_path, event, token
        )
        
        # 4. Mark as processed
        await commit_bus.mark_event_processed(event.id, success=True)
        
        # 5. Update repo_sync_state
        await update_repo_sync_state(
            event.org_id, event.repo_id, event.commit_sha
        )
        
    except Exception as e:
        # Mark as failed, increment retry_count
        await commit_bus.mark_event_processed(event.id, success=False)
        print(f"❌ Error processing event: {e}")
```

---

### **5. `src/core/auth_service.py` - Authentication Service**

**Purpose:** Handle GitHub OAuth and JWT tokens  
**Size:** ~800 lines

**Key Methods:**
```python
class AuthService:
    async def handle_oauth_callback(code) → {user, tokens}
        # Exchange code for GitHub token
        # Fetch user data from GitHub
        # Create/update user in database
        # Generate JWT tokens
        # Return to frontend
    
    async def create_or_update_user(github_user, token)
        # Create or update user in users table
        # Store token in user_github_tokens
        # Return User object
    
    async def generate_tokens(user) → (access_token, refresh_token)
        # Generate JWT tokens
        # Create session
        # Return tokens
    
    async def verify_token(token) → payload
        # Verify JWT signature
        # Return payload
    
    async def validate_session(token) → session
        # Check if session exists and is valid
        # Return session or None
```

**OAuth Flow:**
```
1. User clicks "Login with GitHub"
   └─> Frontend: GET /auth/github
   └─> Backend: Redirect to GitHub OAuth URL

2. GitHub OAuth
   └─> User authorizes app
   └─> GitHub redirects to /auth/callback?code=XXX

3. Exchange Code
   └─> Backend: POST to GitHub API
   └─> GitHub: Return access_token

4. Fetch User Data
   └─> Backend: GET /user from GitHub API
   └─> GitHub: Return user data (username, email, avatar, etc.)

5. Store in Database
   └─> INSERT INTO users (...)
   └─> INSERT INTO user_github_tokens (...)

6. Generate JWT Tokens
   └─> Create access_token (expires in 24 hours)
   └─> Create refresh_token (expires in 30 days)
   └─> INSERT INTO sessions (...)

7. Return to Frontend
   └─> Frontend: Redirect to /dashboard
   └─> Store tokens in localStorage
```

---

### **6. `src/processors/smart_processor.py` - Documentation Generator**

**Purpose:** Analyze code and generate documentation  
**Size:** ~600 lines

**Key Steps:**
```python
async def process_event(repo_path, event, token):
    """
    Main documentation generation flow
    """
    
    # 1. Parse code files
    files = parse_codebase(repo_path)
    
    # 2. Generate architecture doc
    arch_doc = await generate_with_llm(
        "Generate architecture documentation",
        files,
        model="gemini"
    )
    
    # 3. Generate workflow doc
    workflow_doc = await generate_with_llm(
        "Generate workflow documentation",
        files,
        model="groq"
    )
    
    # 4. Generate API doc
    api_doc = await generate_with_llm(
        "Generate API documentation",
        files,
        model="deepseek"
    )
    
    # 5. Commit docs to GitHub
    await commit_docs_to_github(
        repo_path, arch_doc, workflow_doc, api_doc, token
    )
    
    # 6. Store in database
    await store_doc_version(
        repo_id=event.repo_id,
        commit_sha=event.commit_sha,
        architecture_doc=arch_doc,
        workflow_doc=workflow_doc,
        api_doc=api_doc
    )
```

**LLM Fallback Strategy:**
```
Try Gemini
  ├─ Success? → Return
  └─ Fail? → Try Groq

Try Groq
  ├─ Success? → Return
  └─ Fail? → Try DeepSeek

Try DeepSeek
  ├─ Success? → Return
  └─ Fail? → Log error, skip this doc
```

---

## 🔄 WEBHOOK FLOW - DETAILED

### **When GitHub Sends a Webhook**

```
┌─────────────────────────────────────────────────────────────┐
│ GITHUB SENDS WEBHOOK                                        │
│ POST /webhook                                               │
│ Headers:                                                    │
│   X-Hub-Signature-256: sha256=...                           │
│   X-GitHub-Event: push                                      │
│ Body: {                                                     │
│   "repository": {"full_name": "jai-mahakal-poc/mahakal"},   │
│   "commits": [...],                                         │
│   "pusher": {...}                                           │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ MAIN.PY: handle_webhook()                                   │
│ 1. Get raw body for signature verification                  │
│ 2. Verify X-Hub-Signature-256 using GITHUB_WEBHOOK_SECRET   │
│ 3. Parse JSON payload                                       │
│ 4. Call webhook_multi_org(payload, commit_bus)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK_MULTI_ORG.PY: webhook_multi_org()                   │
│ 1. Extract repo: "jai-mahakal-poc/mahakal"                  │
│ 2. Extract org: "jai-mahakal-poc"                           │
│ 3. Call get_org_context_from_repo("jai-mahakal-poc")        │
│    ├─ Check org_webhooks table                              │
│    ├─ Check org_registrations table                         │
│    └─ Check commit_events table                             │
│ 4. Find user: harshpersonalai                               │
│ 5. Find token: gho_XXX...                                   │
│ 6. Return context: {user_id, org_id, token_id}              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CREATE COMMITEVENT OBJECT                                   │
│ CommitEvent(                                                │
│   repo_id="jai-mahakal-poc/mahakal",                         │
│   commit_sha="8a242762",                                    │
│   author_name="Harsh",                                      │
│   files_changed=[...],                                      │
│   user_id="1fc33792-486d-46e6-87df-579e90381ce0",           │
│   org_id="jai-mahakal-poc",                                 │
│   github_token_id="token_id_xxx"                            │
│ )                                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COMMIT_BUS.PY: store_event()                                │
│ INSERT INTO commit_events (...)                             │
│ Returns: event_id (UUID)                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ RETURN 200 OK TO GITHUB                                     │
│ (Processing happens asynchronously)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 EVENT PROCESSING FLOW - DETAILED

### **When Event Consumer Processes an Event**

```
┌─────────────────────────────────────────────────────────────┐
│ EVENT CONSUMER: process_events()                            │
│ Poll every 5 seconds                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COMMIT_BUS: get_pending_events()                            │
│ SELECT * FROM commit_events                                 │
│ WHERE processed=false                                       │
│ LIMIT 10                                                    │
│ Returns: List of unprocessed events                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FOR EACH EVENT: process_event()                             │
│ (Max 3 concurrent)                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GET USER'S GITHUB TOKEN                                     │
│ SELECT github_token FROM user_github_tokens                 │
│ WHERE user_id = event.user_id                               │
│ Returns: gho_XXX...                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CLONE REPOSITORY                                            │
│ git clone https://x-access-token:TOKEN@github.com/...       │
│ Returns: /tmp/docai_smart_xxxxx/                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ SMART_PROCESSOR: process_event()                            │
│ 1. Parse code files                                         │
│ 2. Generate architecture doc (LLM)                          │
│ 3. Generate workflow doc (LLM)                              │
│ 4. Generate API doc (LLM)                                   │
│ 5. Commit docs to GitHub                                    │
│ 6. Store in doc_versions table                              │
│ Returns: {success: true, docs: {...}}                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ MARK EVENT AS PROCESSED                                     │
│ UPDATE commit_events                                        │
│ SET processed=true                                          │
│ WHERE id=event.id                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ UPDATE REPO SYNC STATE                                      │
│ UPDATE repo_sync_state                                      │
│ SET last_processed_sha=event.commit_sha                     │
│ WHERE org_id=event.org_id AND repo_id=event.repo_id         │
│ (Used for next startup to find missed commits)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌍 ENVIRONMENT VARIABLES USED

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=Ov23lif8Bs...
GITHUB_CLIENT_SECRET=xxx...
GITHUB_WEBHOOK_SECRET=xxx...

# Database
DATABASE_URL=postgresql://localhost/lekhak_ai

# LLM Providers
GEMINI_API_KEY=xxx...
GROQ_API_KEY=xxx...
DEEPSEEK_API_KEY=xxx...

# Frontend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Stripe (future)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

---

**Continue to PART 3 for:** Optimization recommendations, table cleanup plan, and production readiness checklist.
