# Migration Analysis: src/ → app/

## CRITICAL ISSUES FOUND ❌

### 1. MISSING ROUTES (32+ routes not migrated)

#### ✅ Migrated Routes (11 total):
- POST `/login/access-token` - Auth endpoint
- GET `/health` - Health check
- GET `/metrics` - Metrics
- GET `/documentation` - List docs
- POST `/documentation` - Create doc
- GET `/documentation/{doc_id}` - Get doc
- POST `/documentation/{doc_id}/publish` - Publish doc
- GET `/events` - List events
- POST `/events` - Create event
- GET `/events/{event_id}` - Get event
- POST `/events/{event_id}/retry` - Retry event
- POST `/webhooks/github` - GitHub webhook

#### ❌ MISSING ROUTES (32+ routes):

**Authentication & User Management:**
- GET `/auth/github` - Start GitHub OAuth
- GET `/auth/callback` - GitHub OAuth callback
- GET `/auth/me` - Get current user
- GET `/auth/repositories` - User's repos
- GET `/auth/user-organizations` - User's orgs
- GET `/api/v1/user/organizations` - User orgs (v1)

**Documentation Generation:**
- POST `/docs/generate-v4` - Generate docs (V4 with docbook)
- GET `/docs/fetch-file` - Fetch file from GitHub
- GET `/repos/{repo_name}/docs` - Get repo docs

**Hierarchical Documentation:**
- GET `/api/repos/{repo_name}/tree` - Get hierarchical tree
- GET `/api/repos/{repo_name}/node/{node_id}` - Get node details
- GET `/api/search` - Global search
- GET `/api/repos/{repo_name}/search` - Repo search

**Webhook & GitHub App:**
- POST `/webhook` - Main webhook handler (multi-org)
- POST `/webhook/github` - Legacy webhook
- GET `/webhook/check-app-installation` - Check app installed
- POST `/webhook/register` - Register webhook for org

**Docbook Management (Critical for Production):**
- POST `/docbook/link-repo` - Link docbook repo to org
- GET `/docbook/pending-reviews` - Get pending reviews
- GET `/docbook/check-github-repo` - Check if repo exists on GitHub
- GET `/docbook/check-exists` - Check if docbook linked in DB
- GET `/api/v1/docbook/{org_id}/structure` - Get docbook folder structure
- POST `/docbook/publish` - Publish to docbook staging
- POST `/docbook/approve-and-merge` - Merge staging to main

**Subscription Management:**
- GET `/plans` - Get subscription plans
- GET `/subscription/{user_id}` - Get user subscription
- POST `/subscription` - Create subscription

**Overlay System:**
- GET `/doc/{node_id}` - Get doc with overlays
- POST `/overlay` - Create/update overlay

**Quality Checking:**
- POST `/api/quality/check` - Check documentation quality
- GET `/api/quality/report/{repo_name}` - Get quality report

**Admin & Settings:**
- GET `/admin/features` - List enabled features
- GET `/admin/progress` - Get project progress (5-week tracking)
- POST `/api/repositories/{repo_id}/doc-persona` - Update doc persona
- GET `/api/repositories/{repo_id}/doc-persona` - Get doc persona

**Phase 4 - App Verification:**
- GET `/api/v1/org/{org_id}/verify-apps` - Verify Reader+Writer apps
- GET `/api/v1/org/{org_id}/verify-writer-app-access` - Verify Writer app access to repo
- GET `/api/v1/org/{org_id}/reader/repositories` - Get repos Reader app can access
- POST `/api/v1/org/{org_id}/setup-docbook` - Setup docbook repo

### 2. MISSING SERVICES

**From src/ directory:**
- `services/auth_service.py` - GitHub OAuth & user authentication ❌
- `services/commit_bus.py` - Event storage & idempotent commit handling ❌
- `services/docbook_publisher.py` - Docbook publishing logic ❌
- `services/smart_processor.py` - Smart documentation processor ❌
- `services/subscription_service.py` - Subscription management ❌
- `services/overlay_service.py` - Documentation overlay system ❌
- `services/quality_checker.py` - Doc quality checking ❌
- `utilities/github_dual_app.py` - Reader/Writer app token management ❌
- `processors/event_consumer.py` - Event processing pipeline ❌
- `integrations/postgres_adapter.py` - Database operations ❌

**Partially migrated in app/:**
- ✅ `services/event/service.py` - Basic event service (incomplete)
- ✅ `services/event/processor.py` - Event processor (incomplete)
- ✅ `services/llm/service.py` - LLM service (basic)
- ⚠️ `services/github/service.py` - GitHub service (stub only)
- ⚠️ `services/docbook/publisher.py` - Docbook publisher (stub only)

### 3. MISSING DATABASE MODELS

**From src/references/schema.sql:**
- `users` table - User authentication & profiles ❌
- `repositories` table - Repository metadata with doc_persona ❌
- `commit_events` table - Idempotent commit tracking ❌
- `docbook_repos` table - Docbook repo per organization ❌
- `subscriptions` table - User subscription management ❌
- `overlays` table - Documentation overlays ❌
- `quality_scores` table - Documentation quality tracking ❌

**Currently in app/models/:**
- ✅ `events` - Event tracking
- ✅ `event_processing_logs` - Event processing history
- ✅ `github_installations` - GitHub app installations
- ✅ `documentation_publications` - Doc publications

### 4. MISSING MIDDLEWARE & ERROR HANDLING

**From src/:**
- Proper GitHub signature verification ❌
- Subscription tier enforcement (free=1 repo, pro=unlimited) ❌
- Multi-org safety checks (org_id + user_id validation) ❌
- Idempotent commit handling (ON CONFLICT logic) ❌
- Background event processing ❌

**In app/:**
- ✅ Rate limiting middleware
- ✅ CORS middleware
- ✅ Security headers
- ⚠️ Logging middleware (basic)

### 5. MISSING UTILITIES

- `utilities/github_dual_app.py` - CRITICAL: Reader/Writer app token management ❌
- Dual GitHub App setup (Reader App ID: 2072879, Writer App ID: 2229202) ❌
- Proper OAuth flow handling ❌
- Token refresh logic ❌

### 6. CONFIGURATION GAPS

**Missing in app/core/config.py:**
- GitHub Reader App ID & Private Key ❌
- GitHub Writer App ID & Private Key ❌
- GitHub OAuth Client ID & Secret ❌
- Dual app configuration ❌
- Subscription tier limits ❌
- Quality checker settings ❌

## PRODUCTION READINESS ASSESSMENT

### Current State: 🔴 NOT PRODUCTION READY

**Completion Status: ~25%**
- ✅ Basic FastAPI structure
- ✅ Database models (partial)
- ✅ Some API endpoints (11/42)
- ❌ Critical business logic missing
- ❌ GitHub integration incomplete
- ❌ Docbook workflow missing
- ❌ Authentication flow missing
- ❌ Subscription management missing

### What's Working:
- Basic FastAPI server starts
- Database models defined (partial)
- Event tracking (basic)
- Health check endpoint

### What's NOT Working:
- **GitHub OAuth** - No authentication flow
- **Docbook Publishing** - Core feature completely missing
- **Multi-org Support** - Webhook handling incomplete
- **Subscription Management** - Not implemented
- **Documentation Generation** - Missing LLM integration
- **Quality Checking** - Not implemented
- **Hierarchical Docs** - Not implemented
- **Overlay System** - Not implemented

## RECOMMENDATION

### Option 1: Complete Full Migration (Recommended) ⭐
**Time Estimate: 2-3 days**
- Migrate all 32+ missing routes
- Implement all missing services
- Add all database models
- Complete GitHub integration
- Add subscription management
- Implement docbook workflow
- Add quality checking
- Full testing

### Option 2: Use src/ as Production (Quick Fix)
**Time Estimate: 1-2 hours**
- Clean up src/main.py structure
- Add proper configuration management
- Keep using src/ for production
- Deprecate incomplete app/ migration

### Option 3: Hybrid Approach
**Time Estimate: 1 day**
- Move critical routes from src to app
- Focus on core workflows only
- Deprecate advanced features temporarily
- Gradual migration plan

## CRITICAL MISSING FEATURES FOR PRODUCTION

1. **GitHub OAuth Authentication** - Users can't log in
2. **Docbook Publishing Workflow** - Core feature missing
3. **Multi-Org Webhook Handling** - Can't process GitHub events
4. **Subscription Management** - Can't enforce limits
5. **Documentation Generation** - Can't generate docs
6. **Reader/Writer App Management** - Critical for GitHub integration

## NEXT STEPS

Choose one of the options above and I'll implement it completely.
