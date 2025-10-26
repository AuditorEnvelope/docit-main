# 🚀 Lekhak AI - Complete Workflow Guide (PART 1)
## From Organization Signup to Documentation Generation

This document explains **exactly what happens** when an organization comes to Lekhak AI, step-by-step, in simple language.

---

## 📋 Quick Overview

When an organization comes to Lekhak AI, here's what happens at a high level:

```
Organization Visits Portal
    ↓
User Logs In with GitHub
    ↓
User Selects Organization
    ↓
Organization Gets Registered
    ↓
Webhook Gets Configured on GitHub
    ↓
Code Changes Happen on GitHub
    ↓
GitHub Sends Webhook to Lekhak AI
    ↓
Event Gets Stored in Database
    ↓
Background Worker Processes Event
    ↓
Documentation Gets Generated
    ↓
Documentation Gets Pushed Back to GitHub
```

---

## PHASE 1: AUTHENTICATION & SETUP

### **Step 1: User Visits Portal and Clicks "Login with GitHub"**

**What Happens:**
- User comes to your Lekhak AI portal
- User clicks "Login with GitHub" button
- Browser redirects to GitHub's OAuth login page

**API Called:**
```
GET /auth/github?redirect_uri=http://localhost:3000/callback&scope=repo,admin:repo_hook,read:org
```

**Function in Code:**
- `start_github_oauth()` in `src/main.py` (line 246)

**What Gets Stored:**
- ❌ **Nothing yet** - this is just redirecting to GitHub

**Tables Involved:**
- ❌ No tables yet

**Why This Step:**
- We need to get permission from GitHub to access the user's repositories and organizations
- The `scope` parameter tells GitHub what permissions we need:
  - `repo` = Access to repositories
  - `admin:repo_hook` = Permission to create webhooks
  - `read:org` = Permission to read organization info

---

### **Step 2: GitHub Redirects Back with Authorization Code**

**What Happens:**
- User logs in on GitHub
- GitHub redirects back to your portal with an authorization code
- Your backend exchanges this code for an access token

**API Called:**
```
GET /auth/callback?code=abc123def456
```

**Function in Code:**
- `handle_github_callback()` in `src/main.py` (line 256)
- This calls `auth_service.handle_oauth_callback()`

**What Gets Stored:**
- ✅ **User record** - User's GitHub info (name, email, avatar, etc.)
- ✅ **GitHub token** - The token that lets us access GitHub on behalf of the user
- ✅ **Session** - A session token for the user to stay logged in

**Tables Involved:**

| Table | What's Stored | Why |
|-------|---------------|-----|
| `users` | User ID, GitHub ID, email, name, avatar, plan | Identifies who the user is |
| `user_github_tokens` | Token ID, user ID, GitHub access token, token type | Stores the token we use to access GitHub APIs |
| `sessions` | Session ID, user ID, JWT token, created_at, expires_at | Keeps user logged in without re-authenticating |

**Why This Step:**
- We need to store the user's GitHub token so we can:
  - Access their repositories
  - Create webhooks on their behalf
  - Push documentation back to GitHub
- The session token lets the user stay logged in

**Token Explanation:**
- **GitHub Access Token**: This is like a password that lets us act as the user on GitHub. It's stored securely in the database.
- **JWT Session Token**: This is what the frontend uses to prove the user is logged in. It's sent with every API request.

---

### **Step 3: User Selects Organization to Connect**

**What Happens:**
- User is now logged in
- User sees a list of their GitHub organizations
- User clicks on an organization they want to connect (e.g., "jai-mahakal-poc")

**API Called:**
```
GET /auth/user-organizations
```

**Function in Code:**
- `get_user_organizations()` in `src/main.py` (line 327)

**What Gets Stored:**
- ❌ **Nothing yet** - we're just fetching the list

**Tables Involved:**
- ❌ No tables involved yet

**Why This Step:**
- We fetch the list from GitHub to show the user which organizations they can connect
- This uses the GitHub token we stored in Step 2

---

### **Step 4: User Registers Organization with Lekhak AI**

**What Happens:**
- User clicks "Register" on an organization
- Lekhak AI stores the mapping: "This organization belongs to this user"
- Lekhak AI also stores the webhook information for this organization

**API Called:**
```
POST /webhook/register
{
  "org_id": "jai-mahakal-poc"
}
```

**Function in Code:**
- `register_webhook()` in `src/main.py` (line 596)

**What Gets Stored:**
- ✅ **Organization Registration** - Maps user to organization
- ✅ **Organization Webhook** - Stores webhook secret and token for this org

**Tables Involved:**

| Table | What's Stored | Why |
|-------|---------------|-----|
| `org_registrations` | user_id, org_id, registered_at | Records that this user owns this organization |
| `org_webhooks` | user_id, org_id, webhook_secret, github_token_id | Stores webhook info for this org so we can process events |

**Why This Step:**
- We need to know which user owns which organization
- We need to store the webhook secret so we can verify that GitHub webhooks are legitimate
- We store the token_id so we know which token to use when processing events for this org

**Example Data Stored:**
```
org_registrations:
  user_id: 12345
  org_id: "jai-mahakal-poc"
  registered_at: 2024-10-27 10:30:00

org_webhooks:
  user_id: 12345
  org_id: "jai-mahakal-poc"
  webhook_secret: "webhook_jai-mahakal-poc"
  github_token_id: 789
```

---

## PHASE 2: WEBHOOK CONFIGURATION

### **Step 5: User Configures Webhook on GitHub**

**What Happens:**
- Lekhak AI returns a webhook URL: `https://your-domain.com/webhook`
- User goes to GitHub organization settings
- User adds this webhook URL to their repository or organization
- User sets the webhook to send "push" events

**API Called:**
- ❌ **No API call from Lekhak AI** - User does this manually on GitHub

**What Gets Stored:**
- ❌ **Nothing in our database** - GitHub stores this on their side

**Why This Step:**
- GitHub needs to know where to send notifications when code changes
- When someone pushes code, GitHub will send a POST request to our webhook URL

**GitHub Webhook Configuration:**
```
Payload URL: https://your-domain.com/webhook
Content type: application/json
Events: Push events
Secret: (GitHub generates a secret)
```

---

## PHASE 3: CODE CHANGE & WEBHOOK TRIGGER

### **Step 6: Developer Pushes Code to GitHub**

**What Happens:**
- A developer in the organization pushes code to GitHub
- GitHub detects the push event
- GitHub sends a webhook notification to Lekhak AI

**API Called:**
- ❌ **No API call from developer** - This is automatic

**What Gets Sent:**
- GitHub sends a POST request to `/webhook` endpoint with:
  - Repository name
  - Commit SHA
  - Changed files
  - Author info
  - Commit message
  - Signature (for verification)

**Example Webhook Payload:**
```json
{
  "repository": {
    "full_name": "jai-mahakal-poc/mahakal",
    "name": "mahakal"
  },
  "commits": [
    {
      "id": "abc123def456",
      "message": "Add new feature",
      "author": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "added": ["src/new_feature.py"],
      "modified": ["README.md"],
      "removed": []
    }
  ],
  "push_id": 12345,
  "ref": "refs/heads/main"
}
```

---

### **Step 7: Lekhak AI Receives Webhook**

**What Happens:**
- Lekhak AI receives the webhook POST request
- First, it verifies the signature to make sure it's really from GitHub
- Then it extracts the organization name from the repository
- Then it looks up which user owns this organization

**API Called:**
```
POST /webhook
Headers:
  X-Hub-Signature-256: sha256=xxxxx
  X-GitHub-Event: push
```

**Function in Code:**
- `webhook_multi_org()` in `src/webhooks/webhook_multi_org.py` (line 155)
- This is called from `@app.post("/webhook")` in `src/main.py`

**What Happens Step-by-Step:**

1. **Verify Signature** (Line 216 in webhook_multi_org.py):
   - GitHub sends a signature header
   - We verify it matches our webhook secret
   - This proves the webhook is really from GitHub

2. **Extract Organization** (Line 175-176 in main.py):
   - Repository name: `jai-mahakal-poc/mahakal`
   - Extract org: `jai-mahakal-poc`

3. **Look Up User** (Line 186-191 in main.py):
   - Query `org_registrations` table
   - Find which user owns `jai-mahakal-poc`
   - Get the user's GitHub token

**Tables Involved:**

| Table | What's Read | Why |
|-------|------------|-----|
| `org_registrations` | user_id for this org | To find which user owns this org |
| `user_github_tokens` | GitHub token for this user | To use when cloning and processing the repo |

**Why This Step:**
- We need to verify the webhook is legitimate (not a fake request)
- We need to find which user owns this organization
- We need to get the user's GitHub token so we can access the repository

---

### **Step 8: Lekhak AI Stores Event in Commit Bus**

**What Happens:**
- Lekhak AI creates a "CommitEvent" object with all the information
- This event is stored in the database
- The event is marked as "pending" (not processed yet)

**API Called:**
- ❌ **No external API** - Internal database operation

**Function in Code:**
- `process_commit_event()` in `src/main.py` (line 140)
- `commit_bus.store_event()` in `src/core/commit_bus.py`

**What Gets Stored:**

| Field | Value | Example |
|-------|-------|---------|
| event_id | Unique ID | `259f1845-cf2b-47a5-8e6e-13f45849233f` |
| repo_id | Repository name | `jai-mahakal-poc/mahakal` |
| commit_sha | Commit hash | `cfc41a13...` |
| author_name | Who made the commit | `John Doe` |
| author_email | Author's email | `john@example.com` |
| branch | Branch name | `main` |
| files_changed | List of files | `["src/new_feature.py", "README.md"]` |
| commit_message | Commit message | `Add new feature` |
| user_id | Which user owns this org | `12345` |
| org_id | Organization | `jai-mahakal-poc` |
| github_token_id | Which token to use | `789` |
| processed | Is it done? | `false` (pending) |
| created_at | When was it created | `2024-10-27 10:30:00` |

**Tables Involved:**

| Table | What's Stored | Why |
|-------|---------------|-----|
| `commit_events` | All the above fields | This is the "queue" of events waiting to be processed |

**Why This Step:**
- We store the event so we don't lose it if the server crashes
- We mark it as "pending" so a background worker can process it later
- We store the user_id and token_id so we know which token to use

**Example Data Stored:**
```
commit_events:
  id: 259f1845-cf2b-47a5-8e6e-13f45849233f
  repo_id: jai-mahakal-poc/mahakal
  commit_sha: cfc41a13...
  author_name: John Doe
  user_id: 12345
  org_id: jai-mahakal-poc
  github_token_id: 789
  processed: false
  created_at: 2024-10-27 10:30:00
```

---

**Continue to PART 2 for:** Background processing, documentation generation, and token explanations.
