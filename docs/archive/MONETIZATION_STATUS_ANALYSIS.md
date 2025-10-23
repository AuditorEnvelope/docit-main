# 💰 MONETIZATION & AUTH STATUS - COMPLETE ANALYSIS

**Date:** October 22, 2025  
**Focus:** GitHub-only, Scalable SaaS Platform

---

## 🎯 EXECUTIVE SUMMARY

**What's Built:** 40% Complete  
**What's Missing:** 60% Critical Features  
**Time to Launch:** 2-3 weeks of focused work

---

## ✅ WHAT'S ALREADY BUILT (The Good News!)

### **1. Backend Services** ✅

#### **Subscription Service** (`src/subscription_service.py`)
```
✅ 371 lines of production code
✅ Plan definitions (Free, Team, Enterprise)
✅ Feature gates (check_feature, check_limit)
✅ Usage tracking (track_api_usage)
✅ Plan features defined:
   - Free: 1 repo, 100 queries/day
   - Team: 10 repos, 10k queries/day, overlays
   - Enterprise: Unlimited everything
```

**Status:** ✅ **COMPLETE** - Ready to use!

#### **Stripe Service** (`src/stripe_service.py`)
```
✅ 330 lines of code
✅ Checkout session creation
✅ Webhook handling (5 events)
✅ Subscription management
✅ Billing portal integration
```

**Status:** ✅ **CODE COMPLETE** - Needs Stripe keys to activate

#### **Main API** (`src/main.py`)
```
✅ FastAPI server
✅ Services initialized on startup
✅ Subscription service integrated
✅ Overlay service integrated
✅ Quality checker integrated
```

**Status:** ✅ **RUNNING** - Services ready

---

### **2. Frontend Pages** ✅

#### **Pricing Page** (`pustak/src/app/pricing/page.tsx`)
```
✅ Beautiful 4-tier pricing UI
✅ Feature comparison
✅ FAQ section
✅ CTA buttons
✅ Responsive design
```

**URL:** http://localhost:3000/pricing  
**Status:** ✅ **LIVE & WORKING**

#### **Checkout Page** (`pustak/src/app/checkout/page.tsx`)
```
✅ Loading screen
✅ Stripe redirect logic
✅ Error handling
✅ Success/cancel flows
```

**URL:** http://localhost:3000/checkout?plan=pro  
**Status:** ✅ **BUILT** - Needs backend connection

#### **Checkout API** (`pustak/src/app/api/create-checkout/route.ts`)
```
✅ Next.js API route
✅ Calls backend Stripe service
✅ Error handling
```

**Status:** ✅ **BUILT** - Needs Stripe service running

---

### **3. Database Schema** ⚠️

**File:** `schema.sql` (19,311 bytes)

**What's Defined:**
```sql
✅ doc_nodes table (hierarchical docs)
✅ commit_events table (webhook events)
✅ overlays table (admin overlays)
✅ quality_metrics table (doc quality)
```

**What's MISSING:**
```sql
❌ users table (NO AUTH!)
❌ subscriptions table (NO BILLING!)
❌ installations table (NO GITHUB APP TRACKING!)
❌ api_usage table (NO USAGE TRACKING!)
❌ user_repos table (NO REPO PERMISSIONS!)
```

**Status:** ⚠️ **INCOMPLETE** - Missing critical tables!

---

## ❌ WHAT'S MISSING (The Reality Check)

### **1. Authentication System** ❌ **NOT BUILT**

**Current State:**
```
❌ No user login
❌ No GitHub OAuth
❌ No session management
❌ No user database
❌ No JWT tokens
❌ No protected routes
```

**What You Need:**
```
Frontend:
- /login page
- /callback page (OAuth redirect)
- Auth context provider
- Protected route wrapper

Backend:
- /auth/github endpoint (start OAuth)
- /auth/callback endpoint (handle OAuth)
- JWT token generation
- Session management
- User creation/lookup
```

**Time to Build:** 3-4 days

---

### **2. User Management** ❌ **NOT BUILT**

**Current State:**
```
❌ No user table in database
❌ No user profiles
❌ No user dashboard
❌ Can't track who owns what
```

**What You Need:**
```sql
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    github_id BIGINT UNIQUE,
    email VARCHAR(255),
    name VARCHAR(255),
    avatar_url TEXT,
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Time to Build:** 1 day

---

### **3. GitHub App Integration** ❌ **PARTIALLY BUILT**

**Current State:**
```
✅ You have "Lekhak AI" app (private)
✅ Webhook handling exists
❌ Not public (only you can install)
❌ No installation tracking
❌ No multi-tenant support
❌ Hardcoded for your org
```

**What You Need:**
```
1. Make GitHub App public
2. Track installations per user
3. Handle multiple organizations
4. Store installation tokens
5. Route webhooks by installation_id
```

**Database:**
```sql
CREATE TABLE installations (
    id SERIAL PRIMARY KEY,
    installation_id BIGINT UNIQUE,
    user_id VARCHAR(255),
    org_name VARCHAR(255),
    access_token TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Time to Build:** 2-3 days

---

### **4. Subscription Flow** ❌ **NOT CONNECTED**

**Current State:**
```
✅ Pricing page exists
✅ Checkout page exists
✅ Stripe service coded
❌ Not connected to users
❌ No subscription database
❌ Can't track who paid
❌ Can't enforce limits
```

**What You Need:**
```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    plan VARCHAR(50),
    status VARCHAR(50),
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Flow:**
```
1. User logs in (GitHub OAuth)
2. User clicks "Upgrade to Pro"
3. Redirects to Stripe checkout
4. Stripe webhook fires
5. Backend creates subscription record
6. User gets Pro features
```

**Time to Build:** 2 days

---

### **5. Feature Enforcement** ❌ **NOT IMPLEMENTED**

**Current State:**
```
✅ Code exists (subscription_service.py)
❌ Not called anywhere
❌ No middleware checking
❌ No API protection
❌ Anyone can use everything
```

**What You Need:**
```python
# Add to every API endpoint:
@app.get("/api/repos/{repo_name}")
async def get_repo(repo_name: str, user_id: str = Depends(get_current_user)):
    # Check subscription
    subscription = await subscription_service.get_subscription(user_id)
    
    # Check repo limit
    repo_count = await db.count_user_repos(user_id)
    if not await subscription_service.check_limit(user_id, 'repos', repo_count):
        raise HTTPException(402, "Upgrade to add more repos")
    
    # Return data
    return repo_data
```

**Time to Build:** 1-2 days

---

### **6. User Dashboard** ❌ **NOT BUILT**

**Current State:**
```
❌ No dashboard page
❌ Can't see current plan
❌ Can't see usage stats
❌ Can't manage billing
❌ Can't add/remove repos
```

**What You Need:**
```
Pages:
- /dashboard - Overview
- /dashboard/repos - Manage repositories
- /dashboard/billing - Subscription & invoices
- /dashboard/usage - Usage statistics
- /dashboard/settings - Account settings
```

**Time to Build:** 3-4 days

---

## 📊 COMPLETE FEATURE MATRIX

| Feature | Status | Code Exists | Database | Frontend | Backend | Working |
|---------|--------|-------------|----------|----------|---------|---------|
| **Pricing Page** | ✅ | Yes | N/A | ✅ | N/A | ✅ |
| **Checkout Flow** | ⚠️ | Yes | ❌ | ✅ | ⚠️ | ❌ |
| **Stripe Integration** | ⚠️ | Yes | ❌ | ✅ | ✅ | ❌ |
| **User Auth** | ❌ | No | ❌ | ❌ | ❌ | ❌ |
| **GitHub OAuth** | ❌ | No | ❌ | ❌ | ❌ | ❌ |
| **User Database** | ❌ | No | ❌ | N/A | N/A | ❌ |
| **Subscriptions DB** | ❌ | No | ❌ | N/A | N/A | ❌ |
| **Feature Gates** | ⚠️ | Yes | ❌ | N/A | ✅ | ❌ |
| **Usage Tracking** | ⚠️ | Yes | ❌ | N/A | ✅ | ❌ |
| **User Dashboard** | ❌ | No | ❌ | ❌ | ❌ | ❌ |
| **GitHub App (Public)** | ❌ | Partial | ❌ | N/A | ⚠️ | ❌ |
| **Multi-tenant** | ❌ | No | ❌ | N/A | ❌ | ❌ |
| **Billing Portal** | ⚠️ | Yes | ❌ | ❌ | ✅ | ❌ |

**Legend:**
- ✅ Complete & Working
- ⚠️ Partially Built
- ❌ Not Built

---

## 🎯 CRITICAL PATH TO LAUNCH

### **Phase 1: Foundation (Week 1)** 🔴 CRITICAL

**Priority 1: Database Schema**
```sql
Day 1-2: Create missing tables
- users
- subscriptions  
- installations
- api_usage
- user_repos
```

**Priority 2: Authentication**
```
Day 3-4: Build GitHub OAuth
- Frontend: Login page, callback handler
- Backend: OAuth endpoints, JWT tokens
- Database: User creation/lookup
```

**Priority 3: User Management**
```
Day 5: Connect everything
- User sessions
- Protected routes
- User context in frontend
```

**Deliverable:** Users can log in with GitHub ✅

---

### **Phase 2: Monetization (Week 2)** 🟡 HIGH PRIORITY

**Priority 1: Subscription Database**
```
Day 1: Create subscriptions table
Day 2: Connect Stripe webhooks
Day 3: Test payment flow
```

**Priority 2: Feature Enforcement**
```
Day 4: Add middleware to APIs
Day 5: Test free vs paid limits
```

**Priority 3: User Dashboard**
```
Day 6-7: Build dashboard pages
- Current plan display
- Usage statistics
- Billing management
```

**Deliverable:** Users can pay and get features ✅

---

### **Phase 3: GitHub Integration (Week 3)** 🟢 MEDIUM PRIORITY

**Priority 1: Public GitHub App**
```
Day 1: Make "Lekhak AI" public
Day 2: Add installation tracking
Day 3: Multi-tenant webhook routing
```

**Priority 2: Repository Management**
```
Day 4-5: Build repo selection UI
- List user's repos
- Add/remove repos
- Enforce repo limits
```

**Priority 3: Polish**
```
Day 6-7: Testing & bug fixes
- End-to-end testing
- Error handling
- Edge cases
```

**Deliverable:** Fully functional SaaS platform ✅

---

## 📋 DETAILED ACTION PLAN

### **STEP 1: Database Schema (Day 1-2)**

**Create:** `migrations/001_auth_and_billing.sql`

```sql
-- Users table
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    avatar_url TEXT,
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- GitHub installations
CREATE TABLE installations (
    id SERIAL PRIMARY KEY,
    installation_id BIGINT UNIQUE NOT NULL,
    user_id VARCHAR(255) REFERENCES users(id),
    org_name VARCHAR(255),
    org_id BIGINT,
    access_token TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User repositories
CREATE TABLE user_repos (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    installation_id BIGINT REFERENCES installations(installation_id),
    repo_name VARCHAR(255) NOT NULL,
    repo_id BIGINT NOT NULL,
    webhook_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, repo_name)
);

-- API usage tracking
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(id),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_installations_user_id ON installations(user_id);
CREATE INDEX idx_user_repos_user_id ON user_repos(user_id);
CREATE INDEX idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX idx_api_usage_created_at ON api_usage(created_at);
```

**Run:**
```bash
psql $DATABASE_URL < migrations/001_auth_and_billing.sql
```

---

### **STEP 2: GitHub OAuth (Day 3-4)**

**Backend:** `src/auth_service.py` (NEW FILE)

```python
"""
Authentication Service - GitHub OAuth
"""
import os
import httpx
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

class AuthService:
    async def start_oauth(self, redirect_uri: str) -> str:
        """Generate GitHub OAuth URL"""
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user:email,read:org"
        )
    
    async def handle_callback(self, code: str, db_pool):
        """Exchange code for token, create/update user"""
        # Get access token from GitHub
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code
                },
                headers={"Accept": "application/json"}
            )
            data = response.json()
            access_token = data["access_token"]
        
        # Get user info from GitHub
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            github_user = response.json()
        
        # Create or update user in database
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                INSERT INTO users (id, github_id, email, name, avatar_url)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (github_id) DO UPDATE
                SET email = $3, name = $4, avatar_url = $5, updated_at = NOW()
                RETURNING *
            """, 
                f"user_{github_user['id']}",
                github_user['id'],
                github_user.get('email'),
                github_user.get('name'),
                github_user.get('avatar_url')
            )
        
        # Generate JWT token
        jwt_token = jwt.encode({
            'user_id': user['id'],
            'github_id': user['github_id'],
            'exp': datetime.utcnow() + timedelta(days=30)
        }, JWT_SECRET, algorithm='HS256')
        
        return {
            'user': dict(user),
            'token': jwt_token
        }
```

**Add to `main.py`:**

```python
from auth_service import AuthService

auth_service = AuthService()

@app.get("/auth/github")
async def start_github_oauth(redirect_uri: str):
    """Start GitHub OAuth flow"""
    url = await auth_service.start_oauth(redirect_uri)
    return {"url": url}

@app.get("/auth/callback")
async def handle_github_callback(code: str):
    """Handle GitHub OAuth callback"""
    result = await auth_service.handle_callback(code, commit_bus.pool)
    return result
```

**Frontend:** `pustak/src/app/login/page.tsx` (NEW FILE)

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();

  const handleGitHubLogin = async () => {
    const redirectUri = `${window.location.origin}/callback`;
    const response = await fetch(
      `/api/auth/github?redirect_uri=${encodeURIComponent(redirectUri)}`
    );
    const data = await response.json();
    window.location.href = data.url;
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <button
        onClick={handleGitHubLogin}
        className="px-6 py-3 bg-black text-white rounded-lg"
      >
        Login with GitHub
      </button>
    </div>
  );
}
```

**Frontend:** `pustak/src/app/callback/page.tsx` (NEW FILE)

```tsx
"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function CallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      handleCallback(code);
    }
  }, []);

  const handleCallback = async (code: string) => {
    const response = await fetch(`/api/auth/callback?code=${code}`);
    const data = await response.json();
    
    // Store token
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    
    // Redirect to dashboard
    router.push("/dashboard");
  };

  return <div>Logging in...</div>;
}
```

---

### **STEP 3: Connect Stripe (Day 5-6)**

**Update:** `src/stripe_service.py`

```python
# Add to existing file:

async def handle_checkout_completed(self, session: Dict):
    """Handle successful checkout"""
    user_id = session['metadata']['user_id']
    plan = session['metadata']['plan']
    subscription_id = session['subscription']
    
    async with self.pool.acquire() as conn:
        # Create subscription record
        await conn.execute("""
            INSERT INTO subscriptions (
                user_id, plan, status, stripe_subscription_id,
                current_period_start, current_period_end
            ) VALUES ($1, $2, 'active', $3, NOW(), NOW() + INTERVAL '1 month')
            ON CONFLICT (stripe_subscription_id) 
            DO UPDATE SET 
                plan = $2,
                status = 'active',
                updated_at = NOW()
        """, user_id, plan, subscription_id)
        
        # Update user's plan
        await conn.execute("""
            UPDATE users SET plan = $1 WHERE id = $2
        """, plan, user_id)
    
    print(f"✅ Subscription created for user {user_id}: {plan}")
```

---

### **STEP 4: Build Dashboard (Day 7-10)**

**Create:** `pustak/src/app/dashboard/page.tsx`

```tsx
export default async function DashboardPage() {
  // Get user from session
  const user = await getCurrentUser();
  const subscription = await getSubscription(user.id);
  const usage = await getUsage(user.id);
  
  return (
    <div>
      <h1>Dashboard</h1>
      
      {/* Current Plan */}
      <div>
        <h2>Current Plan: {subscription.plan}</h2>
        <p>Status: {subscription.status}</p>
      </div>
      
      {/* Usage Stats */}
      <div>
        <h2>Usage This Month</h2>
        <p>Repositories: {usage.repos} / {subscription.repos_limit}</p>
        <p>Searches: {usage.searches} / {subscription.searches_limit}</p>
      </div>
      
      {/* Upgrade CTA */}
      {subscription.plan === 'free' && (
        <button onClick={() => router.push('/pricing')}>
          Upgrade to Pro
        </button>
      )}
    </div>
  );
}
```

---

## 🚀 LAUNCH CHECKLIST

### **Before Launch:**

- [ ] Database schema created
- [ ] GitHub OAuth working
- [ ] Users can log in
- [ ] Stripe connected
- [ ] Payment flow tested
- [ ] Subscriptions stored
- [ ] Feature gates enforced
- [ ] Dashboard functional
- [ ] GitHub App public
- [ ] Multi-tenant working
- [ ] Error handling complete
- [ ] Security audit done

### **Launch Day:**

- [ ] Deploy to production
- [ ] Test end-to-end flow
- [ ] Monitor errors
- [ ] Customer support ready

---

## 💡 SUMMARY

**What You Have:**
- ✅ 40% of code written
- ✅ Pricing page beautiful
- ✅ Stripe service coded
- ✅ Subscription logic ready

**What You Need:**
- ❌ Authentication (3-4 days)
- ❌ Database tables (1-2 days)
- ❌ User dashboard (3-4 days)
- ❌ GitHub App public (2-3 days)
- ❌ Integration & testing (3-4 days)

**Total Time:** 2-3 weeks of focused work

**Next Step:** Start with database schema tomorrow!

---

**Ready to build?** 🚀
