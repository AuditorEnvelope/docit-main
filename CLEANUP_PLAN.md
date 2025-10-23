# 🧹 PROJECT CLEANUP EXECUTION PLAN

## Phase 1: Backend Reorganization

### Step 1.1: Create Folder Structure
```bash
mkdir -p src/services
mkdir -p src/integrations
mkdir -p src/processors
```

### Step 1.2: Move Files to Services
```bash
# Core services
mv src/auth_service.py src/services/
mv src/commit_bus.py src/services/
mv src/event_consumer.py src/services/
mv src/quality_checker.py src/services/
mv src/subscription_service.py src/services/
mv src/overlay_service.py src/services/
```

### Step 1.3: Move Files to Integrations
```bash
# GitHub integrations
mv src/github_app.py src/integrations/
mv src/webhook_multi_org.py src/integrations/
mv src/webhook_registration.py src/integrations/
```

### Step 1.4: Move Files to Processors
```bash
# Processing logic
mv src/smart_processor.py src/processors/
```

### Step 1.5: Delete Dead Code Files
```bash
# Delete unused files
rm src/agent_service.py
rm src/canonical_model.py
rm src/comprehensive_doc_generator.py
rm src/doc_generation_endpoint.py
rm src/event_consumer_multi_org.py
rm src/github_sync.py
rm src/hierarchical_doc_generator.py
rm src/indexer_service.py
rm src/lekhak_ai_integration.py
rm src/llm_provider_v2.py
rm src/pustak_integration.py
rm src/quality_integration.py
rm src/stripe_service.py
rm src/universal_code_parser.py
rm src/webhook_handler.py
```

### Step 1.6: Update main.py Imports
```python
# OLD
from auth_service import AuthService, get_current_user, get_optional_user, User
from commit_bus import CommitBusService
from subscription_service import SubscriptionService
from overlay_service import OverlayService
from smart_processor import handle_push_event as legacy_handle_push
from quality_checker import DocumentationQualityChecker, DocumentationQuality
from webhook_multi_org import webhook_multi_org

# NEW
from services.auth_service import AuthService, get_current_user, get_optional_user, User
from services.commit_bus import CommitBusService
from services.subscription_service import SubscriptionService
from services.overlay_service import OverlayService
from processors.smart_processor import handle_push_event as legacy_handle_push
from services.quality_checker import DocumentationQualityChecker, DocumentationQuality
from integrations.webhook_multi_org import webhook_multi_org
from integrations.github_app import create_jwt
```

### Step 1.7: Create __init__.py Files
```bash
touch src/__init__.py
touch src/services/__init__.py
touch src/integrations/__init__.py
touch src/processors/__init__.py
```

---

## Phase 2: Frontend Reorganization

### Step 2.1: Create Component Folders
```bash
mkdir -p pustak/src/components/auth
mkdir -p pustak/src/components/dashboard
mkdir -p pustak/src/components/docs
mkdir -p pustak/src/components/common
```

### Step 2.2: Organize Components
```bash
# Auth components
mv pustak/src/app/auth/callback/page.tsx pustak/src/components/auth/

# Dashboard components (create new ones)
# Move ConnectOrganizationModal to dashboard folder

# Doc components
# Move MarkdownRenderer, Breadcrumbs to docs folder

# Common components
mv pustak/src/components/Layout.tsx pustak/src/components/common/
mv pustak/src/components/EnhancedSidebar.tsx pustak/src/components/common/
```

### Step 2.3: Delete Unused Components
```bash
rm pustak/src/components/DocStatusBadge.tsx
rm pustak/src/components/GenerateDocsButton.tsx
rm pustak/src/components/GlobalSearch.tsx
rm pustak/src/components/NodeContent.tsx
rm pustak/src/components/TreeSidebar.tsx
```

### Step 2.4: Delete Unused Pages
```bash
rm -rf pustak/src/app/search
rm -rf pustak/src/app/pricing
rm -rf pustak/src/app/checkout
```

### Step 2.5: Delete Unused API Routes
```bash
rm pustak/src/app/api/search/route.ts
rm pustak/src/app/api/sync/route.ts
rm pustak/src/app/api/webhook/route.ts
```

### Step 2.6: Create lib/api.ts
```typescript
// Consolidate API calls
export const API = {
  repositories: (token: string) => fetch('/api/repositories', {
    headers: { Authorization: `Bearer ${token}` }
  }),
  
  fetchDoc: (repo: string, docType: string, token: string) => 
    fetch(`/api/fetch-doc?repo=${repo}&docType=${docType}`, {
      headers: { Authorization: `Bearer ${token}` }
    }),
  
  generateDocs: (repo: string, token: string) =>
    fetch('/api/generate-docs', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ repo })
    })
};
```

---

## Phase 3: Root Directory Cleanup

### Step 3.1: Create New Folders
```bash
mkdir -p scripts
mkdir -p docker
mkdir -p docs/archive
mkdir -p docs/api
mkdir -p docs/setup
mkdir -p docs/architecture
```

### Step 3.2: Move Utility Scripts
```bash
mv cleanup_events.py scripts/
mv cleanup_old_events.py scripts/
mv migrate_add_installation_id.py scripts/
```

### Step 3.3: Move Docker Files
```bash
mv Dockerfile.commit_bus docker/
mv Dockerfile.consumer docker/
```

### Step 3.4: Archive Old Documentation
```bash
# Move to docs/archive/
mv 21-10-2025-PRODUCT_ANALYSIS.md docs/archive/
mv AUTHENTICATION_COMPLETE.md docs/archive/
mv AUTH_IMPLEMENTATION_STATUS.md docs/archive/
mv CURRENT_STATUS_ANALYSIS.md docs/archive/
mv FINAL_IMPLEMENTATION_CHECKLIST.md docs/archive/
mv IMPLEMENTATION_COMPLETE.md docs/archive/
mv IMPLEMENTATION_SUMMARY.md docs/archive/
mv WEEK1_DAY1_COMPLETE.md docs/archive/
# ... and 10+ more
```

### Step 3.5: Keep Essential Docs in Root
```
README.md                    # Main project overview
.env.example                 # Environment template
docker-compose.yml           # Docker setup
requirements.txt             # Python dependencies
PROJECT_AUDIT.md             # This audit
CLEANUP_PLAN.md              # Cleanup steps
```

---

## Phase 4: Documentation Updates

### Step 4.1: Create ARCHITECTURE.md
```markdown
# Architecture Overview

## Backend Structure
- `src/services/` - Core business logic
- `src/integrations/` - External integrations (GitHub, etc)
- `src/processors/` - Document processing
- `src/main.py` - FastAPI server

## Frontend Structure
- `pustak/src/app/` - Next.js pages
- `pustak/src/components/` - React components
- `pustak/src/lib/` - Utilities and helpers
- `pustak/src/contexts/` - React contexts
```

### Step 4.2: Create API.md
```markdown
# API Reference

## Endpoints
- GET /auth/repositories
- GET /auth/user-organizations
- POST /webhook/register
- GET /webhook/check-app-installation
- POST /webhook
```

### Step 4.3: Create SETUP.md
```markdown
# Setup Guide

## Backend
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables: `cp .env.example .env`
3. Run migrations: `psql -U postgres -d lekhak_ai < migrations/*.sql`
4. Start server: `python src/main.py`

## Frontend
1. Install dependencies: `cd pustak && npm install`
2. Set environment variables: `cp .env.example .env.local`
3. Start dev server: `npm run dev`
```

### Step 4.4: Update README.md
```markdown
# Lekhak AI - Documentation Platform

## Quick Start
- [Setup Guide](docs/setup/SETUP.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [API Reference](docs/api/API.md)

## Project Structure
See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for detailed structure

## Development
- Backend: `python src/main.py`
- Frontend: `cd pustak && npm run dev`
```

---

## Phase 5: Verification Checklist

### Backend Verification
- [ ] All imports in `main.py` work
- [ ] Backend starts without errors: `python src/main.py`
- [ ] All services initialize correctly
- [ ] Database migrations run successfully
- [ ] API endpoints respond correctly

### Frontend Verification
- [ ] Frontend builds without errors: `npm run build`
- [ ] Dev server starts: `npm run dev`
- [ ] All pages load correctly
- [ ] No import errors in console
- [ ] All API calls work

### General Verification
- [ ] Git status shows only intended changes
- [ ] No broken imports anywhere
- [ ] Project structure matches proposed layout
- [ ] Documentation is up to date
- [ ] .gitignore is correct

---

## 🚀 Execution Order

1. **Backup** - `git commit -m "backup before cleanup"`
2. **Phase 1** - Backend reorganization (30 min)
3. **Phase 2** - Frontend reorganization (20 min)
4. **Phase 3** - Root cleanup (15 min)
5. **Phase 4** - Documentation (20 min)
6. **Phase 5** - Verification (30 min)
7. **Commit** - `git commit -m "project cleanup and reorganization"`

**Total Time:** ~2 hours

---

## ⚠️ Rollback Plan

If anything breaks:
```bash
git reset --hard HEAD~1
```

This will undo all changes and restore the previous state.

---

## 📝 Notes

- Keep `.gitignore` updated with new folder structure
- Update CI/CD pipelines if they reference old paths
- Notify team members of new structure
- Update any external documentation
- Consider creating a CONTRIBUTING.md guide

---

**Status:** Ready to execute  
**Last Updated:** October 23, 2025
