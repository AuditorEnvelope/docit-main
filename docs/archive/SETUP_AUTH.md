# 🔐 Authentication Setup Guide

**Complete guide to setting up GitHub OAuth authentication for Pustak**

---

## 📋 Prerequisites

- GitHub account
- PostgreSQL database running
- Python backend running
- Next.js frontend running

---

## 🚀 Step 1: Create GitHub OAuth App

### 1.1 Go to GitHub Settings
1. Navigate to https://github.com/settings/developers
2. Click **"OAuth Apps"** → **"New OAuth App"**

### 1.2 Configure OAuth App

**Application name:** `Pustak (Development)`

**Homepage URL:** `http://localhost:3000`

**Authorization callback URL:** `http://localhost:3000/auth/callback`

**Description:** `AI-powered documentation platform`

### 1.3 Get Credentials
After creating the app:
1. Copy the **Client ID**
2. Click **"Generate a new client secret"**
3. Copy the **Client Secret** (you won't see it again!)

---

## 🔧 Step 2: Configure Environment Variables

### 2.1 Backend (.env)

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=Iv1.your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here

# JWT Secret (generate with: openssl rand -base64 32)
JWT_SECRET=your_random_32_char_secret_here

# Database
DATABASE_URL=postgresql://localhost/lekhak_ai
```

### 2.2 Frontend (pustak/.env.local)

```bash
# Backend API
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# GitHub OAuth (same as backend)
NEXT_PUBLIC_GITHUB_CLIENT_ID=Iv1.your_client_id_here
```

---

## 🗄️ Step 3: Run Database Migrations

```bash
# Connect to your PostgreSQL database
psql -U postgres -d lekhak_ai

# Run the migration
\i migrations/001_auth_and_billing.sql

# Verify tables were created
\dt

# You should see:
# - users
# - subscriptions
# - github_installations
# - user_repositories
# - api_usage
# - payment_events
# - sessions
# - audit_logs
```

---

## 🧪 Step 4: Test Authentication Flow

### 4.1 Start Backend
```bash
cd /Users/harshsrivastava/Desktop/doc_ai
python src/main.py
```

You should see:
```
✅ Auth Service initialized
```

### 4.2 Test OAuth URL Generation
```bash
curl "http://localhost:8000/auth/github?redirect_uri=http://localhost:3000/auth/callback"
```

Expected response:
```json
{
  "url": "https://github.com/login/oauth/authorize?client_id=..."
}
```

### 4.3 Test Complete Flow (Manual)

1. **Get OAuth URL:**
   ```bash
   curl "http://localhost:8000/auth/github?redirect_uri=http://localhost:3000/auth/callback"
   ```

2. **Visit the URL** in your browser and authorize the app

3. **GitHub redirects** to: `http://localhost:3000/auth/callback?code=XXXXX`

4. **Exchange code for token:**
   ```bash
   curl "http://localhost:8000/auth/callback?code=XXXXX"
   ```

5. **Expected response:**
   ```json
   {
     "user": {
       "id": "uuid-here",
       "github_id": 12345,
       "email": "you@example.com",
       "name": "Your Name",
       "username": "yourusername",
       "plan": "free"
     },
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
     "expires_in": 86400
   }
   ```

6. **Test authenticated endpoint:**
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        http://localhost:8000/auth/me
   ```

---

## 🎨 Step 5: Frontend Integration (Next Steps)

We'll create:
- `/pustak/src/app/login/page.tsx` - Login page
- `/pustak/src/app/auth/callback/page.tsx` - OAuth callback handler
- `/pustak/src/contexts/AuthContext.tsx` - Auth state management
- `/pustak/src/lib/auth.ts` - Auth utilities

---

## 🔒 Security Best Practices

### ✅ DO:
- Use HTTPS in production
- Store JWT in httpOnly cookies (not localStorage)
- Rotate JWT secrets regularly
- Set short token expiration (24h)
- Use refresh tokens for long sessions
- Log all authentication events
- Rate limit auth endpoints

### ❌ DON'T:
- Commit secrets to git
- Use default JWT_SECRET in production
- Store tokens in localStorage (XSS vulnerable)
- Share OAuth credentials
- Disable CSRF protection

---

## 🐛 Troubleshooting

### "Auth service not available"
- Check DATABASE_URL is correct
- Ensure PostgreSQL is running
- Verify migrations ran successfully

### "Failed to exchange code for token"
- Check GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
- Verify OAuth app callback URL matches exactly
- Code expires after 10 minutes - get a new one

### "Token expired"
- Tokens expire after 24 hours
- Use refresh token to get new access token
- Re-authenticate if refresh token expired (30 days)

### Database connection errors
```bash
# Test connection
psql -U postgres -d lekhak_ai -c "SELECT 1"

# Check if tables exist
psql -U postgres -d lekhak_ai -c "\dt"
```

---

## 📊 Database Schema Overview

```
users
├── id (UUID, PK)
├── github_id (BIGINT, unique)
├── email, name, username
├── plan (free/pro/team/enterprise)
├── stripe_customer_id
└── timestamps

sessions
├── id (UUID, PK)
├── user_id (FK → users)
├── token (JWT access token)
├── refresh_token
├── expires_at
└── ip_address, user_agent

audit_logs
├── id (UUID, PK)
├── user_id (FK → users)
├── action (user.login, user.created, etc.)
├── ip_address
└── metadata (JSONB)
```

---

## 🎯 Next Steps

1. ✅ **Backend auth complete!**
2. 🚧 **Frontend auth UI** (next)
3. 🚧 **Protected routes**
4. 🚧 **Stripe integration**
5. 🚧 **GitHub App installation**

---

## 📚 API Reference

### `GET /auth/github`
Start OAuth flow
- **Query:** `redirect_uri` (required)
- **Returns:** `{ url: string }`

### `GET /auth/callback`
Handle OAuth callback
- **Query:** `code` (required)
- **Returns:** `{ user, access_token, refresh_token, expires_in }`

### `GET /auth/me`
Get current user
- **Headers:** `Authorization: Bearer <token>`
- **Returns:** User object

---

**🎉 Authentication backend is production-ready!**
