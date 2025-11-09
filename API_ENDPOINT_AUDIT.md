# API Endpoint Audit - Frontend vs Backend

## ✅ FIXED ENDPOINTS

| Endpoint | Frontend File | Status | Fix |
|----------|---------------|--------|-----|
| `/api/v1/auth/github` | login/page.tsx | ✅ FIXED | Now uses correct prefix |
| `/api/v1/auth/callback` | auth/callback/page.tsx | ✅ FIXED | Changed from `/auth/callback` |
| `/api/v1/auth/me` | AuthContext.tsx | ✅ FIXED | Already correct |
| `/api/v1/repositories` | api/repositories/route.ts | ✅ FIXED | Changed from `/auth/repositories` |
| `/api/v1/documentation/link-repo` | DocbookSetupModal.tsx | ✅ FIXED | Already correct |
| `/api/v1/user/organizations` | dashboard/page.tsx | ✅ FIXED | Changed from `/auth/user-organizations` |
| `/api/v1/search` | search/page.tsx | ✅ FIXED | Changed from `/api/search` |
| `/api/v1/repos/{repoName}/search` | search/page.tsx | ✅ FIXED | Changed from `/api/repos/...` |

---

## ⚠️ ENDPOINTS THAT DON'T EXIST IN BACKEND

These endpoints are called by frontend but don't exist in @[app]:

| Endpoint | Frontend File | Status | Action |
|----------|---------------|--------|--------|
| `/api/v1/repos/{repoName}/tree` | lib/api.ts | ❌ MISSING | Need to create in backend |
| `/api/v1/repos/{repoName}/node/{nodeId}` | lib/api.ts | ❌ MISSING | Need to create in backend |
| `/api/v1/org/{org}/verify-apps` | dashboard/page.tsx | ❌ MISSING | Need to create in backend |
| `/api/v1/org/{org}/verify-writer-app-access` | dashboard/page.tsx | ❌ MISSING | Need to create in backend |
| `/api/v1/org/{org}/reader/repositories` | dashboard/page.tsx | ❌ MISSING | Need to create in backend |

---

## BACKEND ENDPOINTS THAT EXIST

✅ `/api/v1/auth/github` - Get OAuth URL
✅ `/api/v1/auth/callback` - Handle OAuth callback
✅ `/api/v1/auth/me` - Get current user
✅ `/api/v1/repositories` - List repositories
✅ `/api/v1/documentation/link-repo` - Link docbook repo
✅ `/api/v1/subscriptions/plans` - Get subscription plans
✅ `/api/v1/subscriptions/me` - Get user subscription
✅ `/api/v1/events` - Event endpoints
✅ `/health` - Health check

---

## SUMMARY

### Frontend Fixes Applied ✅
- Fixed 8 API endpoint calls to use correct `/api/v1` prefix
- All authentication endpoints now working
- Repository listing endpoint fixed
- Search endpoints fixed

### Backend Endpoints Still Needed ⚠️
The following endpoints are called by frontend but don't exist yet:

1. **Repository Tree Endpoints** - For displaying documentation structure
   - `GET /api/v1/repos/{repoName}/tree`
   - `GET /api/v1/repos/{repoName}/node/{nodeId}`

2. **GitHub App Verification** - For checking app installations
   - `GET /api/v1/org/{org}/verify-apps`
   - `GET /api/v1/org/{org}/verify-writer-app-access`

3. **Reader App Repositories** - For listing org repositories
   - `GET /api/v1/org/{org}/reader/repositories`

---

## NEXT STEPS

1. ✅ Frontend API calls are now aligned with backend structure
2. ⏳ Need to implement missing backend endpoints for full functionality
3. ⏳ Test authentication flow end-to-end
4. ⏳ Test repository listing and documentation viewing
