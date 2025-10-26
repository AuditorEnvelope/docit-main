# 🚀 Lekhak AI - Complete Workflow Guide (PART 3)
## Token Explanations & Visual Flowchart

---

## Token Explanation

### **Why Tokens Are Important**

Tokens are like passwords that give permission to do things. In Lekhak AI, we use different tokens for different purposes:

---

### **1. GitHub Access Token** 🔐

**What it is:**
- A token that lets Lekhak AI act as the user on GitHub
- It's like a password, but more secure and limited in scope

**Where it's stored:**
- `user_github_tokens` table
- Encrypted in the database

**What it's used for:**
- ✅ Cloning private repositories
- ✅ Pushing documentation back to GitHub
- ✅ Reading repository information
- ✅ Creating webhooks

**Why it's important:**
- Without this token, we can't access the user's repositories
- If this token leaks, someone could access all the user's repos
- We need to keep it secure

**Example:**
```bash
# Using the token to clone a repo
git clone https://x-access-token:{GITHUB_TOKEN}@github.com/jai-mahakal-poc/mahakal.git

# The token proves we have permission to access this repo
```

**Where it's used in code:**
- Line 217 in `src/main.py`: `github_token_id=webhook_context.get('github_token_id')`
- Used in Step 10 (Clone Repository)
- Used in Step 14 (Push Documentation Back)

---

### **2. Webhook Secret** 🔒

**What it is:**
- A secret that GitHub and Lekhak AI both know
- It's used to verify that webhooks are really from GitHub

**Where it's stored:**
- `org_webhooks` table
- `webhook_secret` column

**What it's used for:**
- ✅ Verifying webhook signatures
- ✅ Making sure the webhook is really from GitHub (not a fake request)

**Why it's important:**
- Without this, someone could send fake webhooks to our system
- This prevents attackers from triggering documentation generation
- It ensures only GitHub can trigger our webhook

**How it works:**
```
1. GitHub creates a signature using the webhook secret
   Signature = HMAC-SHA256(webhook_secret, payload)

2. GitHub sends the signature in the X-Hub-Signature-256 header

3. Lekhak AI receives the webhook
   - Calculates the signature using our stored webhook_secret
   - Compares it with the signature from GitHub
   - If they match, the webhook is legitimate ✅
   - If they don't match, reject the webhook ❌
```

**Where it's used in code:**
- Line 216 in `src/webhooks/webhook_multi_org.py`: `verify_signature(webhook_secret, body, x_hub_signature_256)`
- Used in Step 7 (Verify Signature)

**Example:**
```python
# Verification logic
def verify_signature(secret: str, payload_body: bytes, signature: str) -> bool:
    sha_name, sig = signature.split('=')
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)
```

---

### **3. JWT Session Token** 🎫

**What it is:**
- A token that proves the user is logged in
- It's sent with every API request from the frontend

**Where it's stored:**
- `sessions` table
- Browser's localStorage (frontend)

**What it's used for:**
- ✅ Authenticating API requests
- ✅ Keeping user logged in
- ✅ Identifying which user is making a request

**Why it's important:**
- Without this, anyone could make API requests as any user
- This ensures only the logged-in user can access their data
- It expires after a certain time for security

**Example:**
```
Frontend sends:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Backend verifies:
  - Token is valid
  - Token hasn't expired
  - User is active
  - Then processes the request
```

**Where it's used in code:**
- Line 282 in `src/main.py`: `token = authorization.split(" ")[1]`
- Line 285 in `src/main.py`: `payload = auth_service.verify_token(token)`
- Used in Step 2 (GitHub Redirects Back)

---

### **4. GitHub App Installation Token** 📱

**What it is:**
- A temporary token that GitHub generates for app installations
- It's used when the app is installed on an organization

**Where it's stored:**
- `github_installations` table
- `installation_id` column in `commit_events`

**What it's used for:**
- ✅ Accessing organization-level resources
- ✅ Creating webhooks at the organization level
- ✅ Accessing all repos in the organization

**Why it's important:**
- Provides organization-level access
- More secure than personal tokens
- Can be revoked at the organization level

**Where it's used in code:**
- Line 155 in `src/main.py`: `installation_id = installation.get('id')`
- Line 219 in `src/main.py`: `installation_id=installation_id`

---

### **Token Comparison Table**

| Token | Purpose | Stored In | Expires | Security Level | Used At Step |
|-------|---------|-----------|---------|-----------------|--------------|
| **GitHub Access Token** | Access GitHub APIs | `user_github_tokens` | User can revoke | 🔐🔐🔐 High | 10, 14 |
| **Webhook Secret** | Verify webhooks | `org_webhooks` | Never | 🔐🔐🔐 High | 7 |
| **JWT Session Token** | Authenticate user | `sessions` | 24 hours | 🔐🔐 Medium | 2, 4 |
| **Installation Token** | Organization access | `github_installations` | 1 hour | 🔐🔐🔐 High | 6 |

---

## Complete Visual Flowchart (Mermaid)

```mermaid
graph TD
    A["👤 User Visits Portal"] --> B["Click Login with GitHub"]
    B --> C["GET /auth/github"]
    C --> D["Redirect to GitHub OAuth"]
    D --> E["User Logs In on GitHub"]
    E --> F["GitHub Redirects with Code"]
    F --> G["GET /auth/callback?code=xxx"]
    G --> H["Exchange Code for Token"]
    H --> I["Store in Database:<br/>- users<br/>- user_github_tokens<br/>- sessions"]
    I --> J["✅ User Logged In"]
    
    J --> K["GET /auth/user-organizations"]
    K --> L["Fetch Orgs from GitHub API"]
    L --> M["Display Org List"]
    M --> N["User Selects Org:<br/>jai-mahakal-poc"]
    
    N --> O["POST /webhook/register"]
    O --> P["Store in Database:<br/>- org_registrations<br/>- org_webhooks"]
    P --> Q["Return Webhook URL"]
    Q --> R["User Configures Webhook<br/>on GitHub"]
    
    R --> S["Developer Pushes Code<br/>git push"]
    S --> T["GitHub Detects Push"]
    T --> U["POST /webhook<br/>to Lekhak AI"]
    
    U --> V["Verify Signature<br/>using webhook_secret"]
    V --> W{Signature Valid?}
    W -->|No| X["❌ Reject Webhook"]
    W -->|Yes| Y["Extract Org from Repo"]
    Y --> Z["Look Up User in<br/>org_registrations"]
    Z --> AA["Get GitHub Token from<br/>user_github_tokens"]
    
    AA --> AB["Create CommitEvent"]
    AB --> AC["Store in Database:<br/>commit_events<br/>marked as PENDING"]
    AC --> AD["✅ Return 200 OK"]
    
    AD --> AE["Background Worker<br/>Starts"]
    AE --> AF["Query: SELECT * FROM<br/>commit_events WHERE<br/>processed = false"]
    AF --> AG["Pick Up Event"]
    AG --> AH["Clone Repository<br/>using GitHub Token"]
    AH --> AI["Analyze Changed Files"]
    AI --> AJ["Send Code to LLM<br/>Gemini/Groq/DeepSeek"]
    AJ --> AK["Generate Documentation"]
    
    AK --> AL["Store in Database:<br/>- doc_versions<br/>- doc_nodes<br/>- repo_sync_state"]
    AL --> AM["Create DOCUMENTATION.md"]
    AM --> AN["git commit & push<br/>using GitHub Token"]
    AN --> AO["Documentation in<br/>GitHub Repository"]
    
    AO --> AP["Mark Event as Processed<br/>in commit_events"]
    AP --> AQ["✅ Complete!"]
    
    style A fill:#e1f5ff
    style J fill:#c8e6c9
    style Q fill:#c8e6c9
    style AD fill:#c8e6c9
    style AQ fill:#c8e6c9
    style X fill:#ffcdd2
    style V fill:#fff9c4
    style AH fill:#fff9c4
    style AN fill:#fff9c4
```

---

## Detailed Flowchart with Table Interactions

```mermaid
graph TD
    subgraph Phase1["PHASE 1: AUTHENTICATION"]
        A1["User Clicks Login"]
        A2["GET /auth/github"]
        A3["Redirect to GitHub"]
        A4["User Logs In"]
        A5["GitHub Redirects"]
        A6["GET /auth/callback"]
        A7["Exchange Code"]
        A8["INSERT INTO users"]
        A9["INSERT INTO user_github_tokens"]
        A10["INSERT INTO sessions"]
        
        A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7
        A7 --> A8 --> A9 --> A10
    end
    
    subgraph Phase2["PHASE 2: ORGANIZATION SETUP"]
        B1["GET /auth/user-organizations"]
        B2["Fetch from GitHub API"]
        B3["User Selects Org"]
        B4["POST /webhook/register"]
        B5["SELECT token_id FROM<br/>user_github_tokens"]
        B6["INSERT INTO org_registrations"]
        B7["INSERT INTO org_webhooks"]
        
        B1 --> B2 --> B3 --> B4 --> B5
        B5 --> B6 --> B7
    end
    
    subgraph Phase3["PHASE 3: WEBHOOK TRIGGER"]
        C1["Developer: git push"]
        C2["GitHub Detects Push"]
        C3["POST /webhook"]
        C4["Verify Signature"]
        C5["Extract Org"]
        C6["SELECT user_id FROM<br/>org_registrations"]
        C7["SELECT token FROM<br/>user_github_tokens"]
        C8["Create CommitEvent"]
        C9["INSERT INTO commit_events"]
        
        C1 --> C2 --> C3 --> C4 --> C5
        C5 --> C6 --> C7 --> C8 --> C9
    end
    
    subgraph Phase4["PHASE 4: BACKGROUND PROCESSING"]
        D1["Event Consumer"]
        D2["SELECT * FROM commit_events<br/>WHERE processed = false"]
        D3["Clone Repository"]
        D4["SELECT token FROM<br/>user_github_tokens"]
        D5["Analyze Code"]
        D6["Call LLM API"]
        D7["Generate Docs"]
        D8["INSERT INTO doc_versions"]
        D9["INSERT INTO doc_nodes"]
        D10["INSERT INTO repo_sync_state"]
        D11["Push to GitHub"]
        D12["UPDATE commit_events<br/>SET processed = true"]
        
        D1 --> D2 --> D3 --> D4 --> D5 --> D6
        D6 --> D7 --> D8 --> D9 --> D10 --> D11 --> D12
    end
    
    Phase1 --> Phase2 --> Phase3 --> Phase4
    
    style Phase1 fill:#e3f2fd
    style Phase2 fill:#f3e5f5
    style Phase3 fill:#fff3e0
    style Phase4 fill:#e8f5e9
```

---

## Database Tables Used at Each Phase

### **PHASE 1: AUTHENTICATION**

**Tables Written:**
- ✅ `users` - User profile information
- ✅ `user_github_tokens` - GitHub access token
- ✅ `sessions` - JWT session token

**Data Flow:**
```
GitHub OAuth
    ↓
Exchange Code for Token
    ↓
Store User Info → users table
    ↓
Store GitHub Token → user_github_tokens table
    ↓
Store Session → sessions table
```

---

### **PHASE 2: ORGANIZATION SETUP**

**Tables Read:**
- 📖 `user_github_tokens` - Get token_id

**Tables Written:**
- ✅ `org_registrations` - User → Org mapping
- ✅ `org_webhooks` - Webhook configuration

**Data Flow:**
```
User Selects Organization
    ↓
Fetch Token ID from user_github_tokens
    ↓
Store Mapping → org_registrations table
    ↓
Store Webhook Info → org_webhooks table
```

---

### **PHASE 3: WEBHOOK TRIGGER**

**Tables Read:**
- 📖 `org_registrations` - Find user for org
- 📖 `user_github_tokens` - Get GitHub token

**Tables Written:**
- ✅ `commit_events` - Queue event for processing

**Data Flow:**
```
GitHub Sends Webhook
    ↓
Verify Signature using webhook_secret
    ↓
Extract Org from Repo Name
    ↓
Look Up User in org_registrations
    ↓
Get Token from user_github_tokens
    ↓
Store Event → commit_events table (PENDING)
```

---

### **PHASE 4: BACKGROUND PROCESSING**

**Tables Read:**
- 📖 `commit_events` - Get pending events
- 📖 `user_github_tokens` - Get GitHub token for cloning

**Tables Written:**
- ✅ `doc_versions` - Store documentation
- ✅ `doc_nodes` - Store hierarchical tree
- ✅ `repo_sync_state` - Track sync status
- ✅ `commit_events` - Mark as processed

**Data Flow:**
```
Event Consumer Picks Up Event
    ↓
Clone Repository using GitHub Token
    ↓
Analyze Code
    ↓
Generate Documentation with LLM
    ↓
Store Docs → doc_versions, doc_nodes, repo_sync_state
    ↓
Push Documentation to GitHub
    ↓
Mark Event as Processed → commit_events
```

---

## Summary: What Table Gets Used When

| Step | Action | Tables Read | Tables Written | Token Used |
|------|--------|-------------|-----------------|-----------|
| 1 | User clicks login | - | - | - |
| 2 | GitHub callback | - | users, user_github_tokens, sessions | GitHub Token |
| 3 | Fetch organizations | - | - | GitHub Token |
| 4 | Register organization | user_github_tokens | org_registrations, org_webhooks | - |
| 5 | Configure webhook | - | - (GitHub) | - |
| 6 | Developer pushes code | - | - (GitHub) | - |
| 7 | Webhook received | org_registrations, user_github_tokens | - | Webhook Secret |
| 8 | Store event | - | commit_events | - |
| 9 | Worker picks up | commit_events | commit_events | - |
| 10 | Clone repo | user_github_tokens | - | GitHub Token |
| 11 | Analyze code | - | - | - |
| 12 | Generate docs | - | - | LLM API Key |
| 13 | Store docs | - | doc_versions, doc_nodes, repo_sync_state | - |
| 14 | Push to GitHub | user_github_tokens | - | GitHub Token |
| 15 | Mark processed | - | commit_events | - |

---

## Key Insights

### **Critical Tables (Always Used)**
- 🔴 `users` - Every authenticated user
- 🔴 `user_github_tokens` - Every operation with GitHub
- 🔴 `sessions` - Every logged-in user
- 🔴 `commit_events` - Every code change
- 🔴 `org_registrations` - Every organization connected
- 🔴 `org_webhooks` - Every webhook processed

### **Important Tables (Used in Processing)**
- 🟡 `doc_versions` - Stores documentation history
- 🟡 `doc_nodes` - Hierarchical documentation tree
- 🟡 `repo_sync_state` - Tracks sync status

### **Optional Tables (Not Critical)**
- 🟢 `audit_logs` - Compliance logging
- 🟢 `doc_overlays` - Developer customizations
- 🟢 `changelogs` - Future feature
- 🟢 `subscriptions` - Billing (future)

---

**All three parts complete! You now have a comprehensive guide to the entire Lekhak AI workflow.**
