# 🏗️ LEKHAK AI - SYSTEM ARCHITECTURE DEEP DIVE (PART 1)

> **Last Updated:** Oct 27, 2025  
> **Scope:** Complete end-to-end flow, database schema, architectural decisions

---

## 📋 QUICK SUMMARY

**Lekhak AI** is an AI-powered documentation generator that:
- Monitors GitHub repos for code changes via webhooks
- Automatically generates docs when commits are pushed
- Supports **multi-organization** architecture
- Stores docs with versioning and quality scores
- Integrates with subscription/billing system

---

## 🎯 SYSTEM ARCHITECTURE

```
GitHub (External)
    ↓ (webhooks + OAuth)
FastAPI Server (main.py)
    ├─ Webhook Handler (webhook_multi_org.py)
    ├─ Auth Service (auth_service.py)
    └─ Docs Generator (smart_processor.py)
        ↓
    Commit Bus (commit_bus.py)
        ↓
    PostgreSQL Database (21 tables)
        ↓
    Event Consumer (event_consumer.py) [async worker]
        ↓
    Smart Processor (doc generation)
        ↓
    GitHub (push docs back)
```

---

## 🗄️ DATABASE SCHEMA - COMPLETE BREAKDOWN

### **CRITICAL TABLES (Must Keep)**

#### **1. `users` - User Profile**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    github_id INTEGER UNIQUE,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    avatar_url TEXT,
    github_access_token TEXT,  -- ⚠️ SECURITY: Plaintext token
    plan VARCHAR(50) DEFAULT 'free',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Core user data  
**Status:** ✅ CRITICAL  
**Data Flow:**
- Created during OAuth callback
- Updated on each login
- Referenced by: sessions, org_registrations, audit_logs

**Issue:** `github_access_token` stored in plaintext → should use `user_github_tokens` table instead

---

#### **2. `user_github_tokens` - GitHub Token Storage**
```sql
CREATE TABLE user_github_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    github_token TEXT,  -- ⚠️ Should be encrypted
    token_id UUID UNIQUE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Store GitHub tokens separately  
**Status:** ✅ CRITICAL - Multi-org support depends on this  
**Data Flow:**
- Created during OAuth callback
- Used by: event_consumer, smart_processor, webhook_multi_org
- `token_id` used to link org → token

**Why Important:**
- Multiple tokens per user (one per org)
- Event consumer queries this to get correct token
- Enables multi-org support

---

#### **3. `org_registrations` - Org-User Mapping**
```sql
CREATE TABLE org_registrations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    org_id VARCHAR(255),
    registered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

**Purpose:** Map which user owns which organization  
**Status:** ✅ CRITICAL - Multi-org support  
**Data Flow:**
- Created when user clicks "Register Webhook" in UI
- Queried by webhook handler to find user for new orgs
- Used by event_consumer to fetch org-specific tokens

**Example:**
```
User: harshpersonalai
├─ Org: AuditorEnvelope
├─ Org: Testing-Org-For-Pustak
├─ Org: beta-org-for-pustak
└─ Org: jai-mahakal-poc
```

---

#### **4. `org_webhooks` - Webhook Configuration**
```sql
CREATE TABLE org_webhooks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    org_id VARCHAR(255),
    webhook_secret VARCHAR(255),
    github_token_id UUID REFERENCES user_github_tokens(token_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);
```

**Purpose:** Store webhook config and token mapping  
**Status:** ✅ CRITICAL - Real-time webhook processing  
**Data Flow:**
- Created by webhook register endpoint
- Queried by webhook handler to get correct token
- Links: org → user → token

---

#### **5. `commit_events` - Core Event Queue**
```sql
CREATE TABLE commit_events (
    id UUID PRIMARY KEY,
    repo_id VARCHAR(255),
    commit_sha VARCHAR(255),
    parent_sha TEXT[],
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    timestamp TIMESTAMP,
    branch VARCHAR(255),
    files_changed JSONB,
    commit_message TEXT,
    push_id INTEGER,
    source VARCHAR(50),
    metadata JSONB,
    user_id UUID REFERENCES users(id),
    org_id VARCHAR(255),
    github_token_id UUID,
    webhook_secret VARCHAR(255),
    installation_id INTEGER,
    processed BOOLEAN DEFAULT false,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Queue of all GitHub push events  
**Status:** ✅ CRITICAL - Core of the system  
**Data Flow:**
```
Webhook arrives
    ↓
CommitEvent object created
    ↓
commit_bus.store_event()
    ↓
INSERT INTO commit_events
    ↓
Event Consumer polls this table
    ↓
Processes event
    ↓
UPDATE processed=true
```

**Key Columns:**
- `user_id`: Which user owns this org
- `org_id`: Which organization
- `processed`: Is it done?
- `retry_count`: How many times failed?
- `files_changed`: What changed (JSONB)

---

#### **6. `repo_sync_state` - Last Processed Commit**
```sql
CREATE TABLE repo_sync_state (
    id UUID PRIMARY KEY,
    org_id VARCHAR(255),
    repo_id VARCHAR(255),
    last_processed_sha VARCHAR(255),
    last_processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, repo_id)
);
```

**Purpose:** Track last processed commit per repo  
**Status:** ✅ IMPORTANT - Optimization  
**Data Flow:**
- Updated after each successful event processing
- Used by event_consumer to find missed commits
- Speeds up startup (don't re-check all commits)

**Example:**
```
AuditorEnvelope/hivemind-poc → last_sha: 521fe77a
jai-mahakal-poc/mahakal → last_sha: 8a242762
```

---

#### **7. `doc_versions` - Documentation Snapshots**
```sql
CREATE TABLE doc_versions (
    id UUID PRIMARY KEY,
    repo_id VARCHAR(255),
    commit_sha VARCHAR(255),
    version_number INTEGER,
    architecture_doc TEXT,
    workflow_doc TEXT,
    api_doc TEXT,
    summary_doc TEXT,
    quality_score DECIMAL(3,2),
    generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Store generated documentation  
**Status:** ✅ IMPORTANT - Core output  
**Data Flow:**
- Created by smart_processor after doc generation
- Queried by frontend to display docs
- Versioned (multiple versions per repo)

---

#### **8. `sessions` - User Sessions**
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Track active user sessions  
**Status:** ✅ IMPORTANT - Authentication  
**Data Flow:**
- Created after OAuth callback
- Validated on each API request
- Used for JWT token validation

---

### **MEDIUM PRIORITY TABLES (Keep for Now)**

#### **9. `github_installations` - GitHub App Installations**
```sql
CREATE TABLE github_installations (
    id UUID PRIMARY KEY,
    installation_id INTEGER UNIQUE,
    org_id VARCHAR(255),
    app_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Track GitHub App installations  
**Status:** ⚠️ MEDIUM - Used for validation  
**Current Usage:** Checked to verify app is installed  
**Recommendation:** Could be optimized (currently just stores metadata)

---

#### **10. `audit_logs` - Activity Tracking**
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(255),
    ip_address VARCHAR(45),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Track user actions for security/compliance  
**Status:** ⚠️ LOW PRIORITY - Audit trail only  
**Current Usage:** Minimal (only login events logged)  
**Recommendation:** Keep for compliance, but not critical

---

#### **11. `doc_overlays` - Documentation Annotations**
```sql
CREATE TABLE doc_overlays (
    id UUID PRIMARY KEY,
    doc_version_id UUID REFERENCES doc_versions(id),
    overlay_type VARCHAR(50),
    content JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Store overlay annotations on docs  
**Status:** ⚠️ MEDIUM - Feature in development  
**Current Usage:** Used by overlay_service  
**Recommendation:** Keep, but optimize JSONB storage

---

#### **12. `changelogs` - Change Documentation**
```sql
CREATE TABLE changelogs (
    id UUID PRIMARY KEY,
    repo_id VARCHAR(255),
    commit_sha VARCHAR(255),
    change_summary TEXT,
    change_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Store auto-generated changelogs  
**Status:** ⚠️ MEDIUM - Feature in development  
**Current Usage:** Minimal  
**Recommendation:** Keep for future use

---

#### **13. `subscriptions` - User Subscriptions**
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    plan_id VARCHAR(50),
    status VARCHAR(50),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:** Track user subscription status  
**Status:** ⚠️ MEDIUM - Billing feature  
**Current Usage:** Minimal (all users on 'free' plan)  
**Recommendation:** Keep for future monetization

---

### **REMOVE THESE TABLES (Not Used)**

| Table | Reason |
|-------|--------|
| `event_processing_log` | Debug only, not actively used |
| `doc_nodes` | Hierarchical structure not used |
| `overlay_history` | Change history not needed |
| `embeddings_metadata` | Vector search not implemented |
| `repositories` | Use GitHub API instead |
| `user_repositories` | Use GitHub API instead |
| `payment_events` | Not implemented |
| `api_usage` | Rate limiting not implemented |

---

## 🔄 COMPLETE DATA FLOW - STEP BY STEP

### **SCENARIO: New Organization Onboarding**

```
STEP 1: User Logs In
├─ Frontend: Click "Login with GitHub"
├─ Backend: GET /auth/github
├─ Action: Redirect to GitHub OAuth
└─ Database: No changes

STEP 2: GitHub OAuth Callback
├─ Frontend: /auth/callback?code=XXX
├─ Backend: GET /auth/callback
├─ Action:
│  ├─ Exchange code for GitHub token
│  ├─ Fetch user from GitHub API
│  ├─ Create user in users table
│  ├─ Store token in user_github_tokens
│  ├─ Generate JWT tokens
│  └─ Create session in sessions table
└─ Database:
   ├─ INSERT users
   ├─ INSERT user_github_tokens
   └─ INSERT sessions

STEP 3: User Selects Organization
├─ Frontend: GET /auth/user-organizations
├─ Backend: Fetch from GitHub API
└─ Database: No changes

STEP 4: User Registers Organization
├─ Frontend: POST /webhook/register {org_id}
├─ Backend: POST /webhook/register
├─ Action:
│  ├─ Get current user from JWT
│  ├─ Store org-user mapping
│  └─ Store webhook config with token
└─ Database:
   ├─ INSERT org_registrations
   └─ INSERT org_webhooks

STEP 5: User Installs GitHub App
├─ Frontend: Redirects to GitHub App page
├─ User: Authorizes app on organization
├─ GitHub: Sends webhook to POST /webhook
├─ Backend: Receives installation webhook
└─ Database:
   └─ INSERT github_installations
```

---

## 📊 TABLE USAGE MATRIX

| Table | Used | Critical | Action |
|-------|------|----------|--------|
| users | ✅ | ✅ | KEEP |
| user_github_tokens | ✅ | ✅ | KEEP |
| sessions | ✅ | ✅ | KEEP |
| org_registrations | ✅ | ✅ | KEEP |
| org_webhooks | ✅ | ✅ | KEEP |
| commit_events | ✅ | ✅ | KEEP |
| repo_sync_state | ✅ | ✅ | KEEP |
| doc_versions | ✅ | ✅ | KEEP |
| github_installations | ✅ | ⚠️ | OPTIMIZE |
| audit_logs | ⚠️ | ❌ | KEEP (compliance) |
| doc_overlays | ⚠️ | ❌ | KEEP (dev feature) |
| changelogs | ⚠️ | ❌ | KEEP (future) |
| subscriptions | ⚠️ | ❌ | KEEP (future) |
| event_processing_log | ❌ | ❌ | REMOVE |
| doc_nodes | ❌ | ❌ | REMOVE |
| overlay_history | ❌ | ❌ | REMOVE |
| embeddings_metadata | ❌ | ❌ | REMOVE |
| repositories | ❌ | ❌ | REMOVE |
| user_repositories | ❌ | ❌ | REMOVE |
| payment_events | ❌ | ❌ | REMOVE |
| api_usage | ❌ | ❌ | REMOVE |

---

**Continue to PART 2 for:** File-by-file architecture, webhook flow, event consumer details, and optimization recommendations.
