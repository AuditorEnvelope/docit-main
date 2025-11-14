# Pustak AI Backend (`app/`) Deep Dive

> Generated: 2025-11-12

This document explains the structure, responsibilities, and request handling flow for the FastAPI backend that lives under `app/`. It covers:

1. High-level architecture overview and primary entry points
2. Directory-by-directory responsibilities
3. Core services and database interactions
4. Exhaustive API endpoint catalogue with flow descriptions (46 endpoints)

---

## 1. Runtime Entry Points

### 1.1 `app/main.py`
- Creates the FastAPI application via `create_application()`
- Configures middleware (logging, rate limiting, security headers, CORS)
- Registers all API routers (`app/api/v1/api.py`) and legacy auth shortcuts
- Defines `lifespan` startup/shutdown to
  - Run DB migrations (`init_models`)
  - Launch background event processor (`run_event_processor`) that polls for queued events
- Exposes the ASGI app (`app`) for Uvicorn/Gunicorn

### 1.2 Background worker (`app/worker.py`)
- Standalone async worker mirroring legacy `event_consumer`
- Connects to PostgreSQL (asyncpg pool with `search_path=public`), polls `events` table, and delegates to `EventProcessor`
- Meant to be launched with `run-worker.sh`

### 1.3 Webhook entry point (`app/webhooks/github.py`)
- Defines `/api/v1/webhooks/github`
- Verifies GitHub signatures, normalizes payloads, persists events, and enqueues processing
- Shares processing pipeline with manual events API

---

## 2. Directory Overview

| Directory | Responsibility |
|-----------|----------------|
| `app/api` | FastAPI routers grouped by version (`v1`) and logical endpoint modules |
| `app/core` | Shared configuration (`config.py`), rate limiting middleware, security helpers |
| `app/db` | SQLAlchemy session setup (`session.py`), startup migrations (`init_db.py`) |
| `app/models` | SQLAlchemy ORM models (users, repositories, docbook artifacts, events, subscriptions, overlays) |
| `app/schemas` | Pydantic request/response models |
| `app/services` | Business logic split by domain (auth, documentation, events, docbook publisher, GitHub helpers, subscriptions) |
| `app/utils` | Supporting utilities (GitHub dual-app helper, logging helpers) |
| `app/webhooks` | Webhook routers (currently GitHub) |

Subdirectories of interest:
- `app/services/docbook`: Docbook repository management and publishing orchestration
- `app/services/event`: Event storage service and smart processor glue
- `app/services/documentation`: Manual generation pipeline, documentation CRUD
- `app/services/github`: GitHub API helpers (installs, tokens, cloning)

---

## 3. Core Components & Data Flow

### 3.1 Authentication & Sessions
- `app/services/auth.AuthService`
  - Exchanges GitHub OAuth codes, fetches user profile, stores tokens
  - Issues JWT access token, persists API sessions
  - Provides `get_current_user` dependency used by auth-required routes

### 3.2 Events Pipeline
1. Webhook/API writes event row via `EventService.create_event`
2. `EventProcessor.process` routes by `event_type`
   - `push`: clones repo, runs documentation generator, publishes to docbook staging (`DocbookPublisher`)
   - `github.installation`: persists installation metadata
3. Background runner updates status (`events.status`) and writes logs (`event_processing_log`)

### 3.3 Documentation Publishing
- `ManualDocGenerator` runs LLM+analysis for manual `/documentation/manual-generate`
- Results handed to `DocbookPublisher.publish_to_docbook`
  - Resolves docbook repo (or uses default naming)
  - Clones staging branch, applies docs, pushes, records review metadata

### 3.4 Subscription Enforcement
- `SubscriptionService` ensures plan-based repository limits
- Updates usage counters when repos created/deleted

### 3.5 Database Access
- Async SQLAlchemy sessions from `app/db/session.get_db`
- For performance-sensitive tasks (legacy compatibility) some services also accept asyncpg pools (e.g., event processor)

---

## 4. Detailed Endpoint Catalogue

Total endpoints registered under `/api/v1`: **46** (including legacy docs helpers, excluding `/health` duplicates and legacy `/auth/install-*`).

For each endpoint below:
- **Route**: HTTP method + path (relative to `/api/v1`)
- **Module**: File containing the route
- **Handler**: Function name
- **Dependencies/services**: Key collaborators
- **DB Interaction**: Tables touched
- **Flow Summary**

### 4.1 Authentication (`app/api/v1/endpoints/auth.py`)

1. `GET /auth/github`
   - Handler: `start_github_oauth`
   - Flow: Builds GitHub OAuth URL using `AuthService.get_oauth_url` (no DB).

2. `GET /auth/callback`
   - Handler: `handle_github_callback`
   - Dependencies: `get_db`
   - Services: `AuthService`
   - DB Tables: `users`, `user_sessions`
   - Flow: Exchange code → fetch profile → upsert user → create session + JWT → return tokens & user payload.

3. `GET /auth/me`
   - Handler: `get_current_user_info`
   - Dependencies: `get_current_user`
   - Flow: Returns authenticated user info (no write).

4. `GET /auth/install-reader-app`
   - Handler: `install_reader_app`
   - Flow: Provides GitHub App installation link.

5. `GET /auth/install-writer-app`
   - Handler: `install_writer_app`
   - Flow: Provides GitHub App installation link.

6. `POST /auth/login/access-token`
   - Handler: `login_access_token`
   - Flow: Placeholder; raises 501.

### 4.2 Repositories (`app/api/v1/endpoints/repositories.py`)

7. `GET /repositories`
   - Handler: `list_repositories`
   - Dependencies: `get_current_user`, `get_db`
   - DB: `repositories`
   - Flow: Query active repos, map to DTO; works around missing `org_id/user_id` columns.

8. `POST /repositories`
   - Handler: `create_repository`
   - Services: `SubscriptionService`
   - DB: `repositories`, plan usage tables
   - Flow: Enforce plan limits → ensure uniqueness → insert repository → increment subscription usage.

9. `GET /repositories/{repo_id}/doc-persona`
   - Handler: `get_repository_doc_persona`
   - DB: `repositories`
   - Flow: Lookup by full_name (`org/repo`) and return persona.

10. `POST /repositories/{repo_id}/doc-persona`
    - Handler: `update_repository_doc_persona`
    - Flow: Update persona + timestamp.

11. `DELETE /repositories/{repo_id}`
    - Handler: `delete_repository`
    - Flow: Soft-delete repository, decrement subscription usage.

### 4.3 Documentation (`app/api/v1/endpoints/documentation.py`)

12. `GET /documentation`
    - Handler: `list_documentation`
    - Services: `DocumentationService`
    - DB: `documentation_publications`

13. `GET /documentation/{doc_id}`
    - Handler: `get_documentation`
    - Flow: Fetch by UUID.

14. `POST /documentation`
    - Handler: `create_documentation`
    - Flow: Insert new publication record.

15. `POST /documentation/publish/{doc_id}`
    - Handler: `publish_documentation`
    - Flow: Service publishes to docbook staging/main, updates status.

16. `POST /documentation/manual-generate`
    - Handler: `manual_generate_documentation`
    - Dependencies: `get_current_user`, `get_db`
    - Services: `ManualDocGenerator`, `DocbookPublisher`, `GitHubDualAppHelper`
    - DB: `documentation_publications`, docbook review tables
    - Flow: Validate GitHub token → generate docs → publish to docbook staging → return review URL.

### 4.4 Docs (legacy helper) (`app/api/v1/endpoints/docs.py`)

17. `GET /docs/{org}/{repo}/structure`
18. `GET /docs/{org}/{repo}/content`
19. `POST /docs/{org}/{repo}/generate`
20. `GET /docs/{org}/{repo}/versions`
21. `GET /docs/{org}/{repo}/versions/{version}`
22. `POST /docs/{org}/{repo}/publish`
23. `POST /docs/{org}/{repo}/approve`
24. `POST /docs/{org}/{repo}/mirror`

- These endpoints mirror new documentation routes but are tailored for legacy UI flows. Most delegate to the same services (`ManualDocGenerator`, `DocbookPublisher`) and interact with `docbook_*` tables.

### 4.5 Events (`app/api/v1/endpoints/events.py`)

25. `POST /events`
    - Handler: `create_event`
    - Services: `EventService`, background `process_event_background`
    - DB: `events`
    - Flow: Persist event row, enqueue async processing.

26. `GET /events/{event_id}`
    - Handler: `get_event`
    - Flow: Return event and logs (`event_processing_log`).

27. `GET /events`
    - Handler: `list_events`
    - Flow: Filter/paginate events.

28. `POST /events/{event_id}/retry`
    - Handler: `retry_event`
    - Flow: Mark as RETRYING, enqueue processing.

### 4.6 Subscriptions (`app/api/v1/endpoints/subscriptions.py`)

29. `GET /subscriptions/plans`
    - Handler: `list_plans`
    - Flow: Returns plan catalog (static data).

30. `GET /subscriptions/current`
    - Handler: `get_current_subscription`
    - DB: `subscriptions`
    - Flow: Fetch current plan for authenticated user.

31. `POST /subscriptions/checkout`
    - Handler: `create_checkout_session`
    - Services: Stripe integration via `SubscriptionService`
    - Flow: Create Stripe checkout → store session metadata.

32. `POST /subscriptions/webhook`
    - Handler: `handle_stripe_webhook`
    - Flow: Process Stripe events, update subscription records.

### 4.7 Organizations (`app/api/v1/endpoints/organizations.py`)

33. `GET /organizations`
    - Handler: `list_organizations`
    - Flow: Use GitHub token to list orgs (no DB write).

34. `POST /organizations/{org_id}/webhook`
    - Handler: `register_org_webhook`
    - Services: Webhook registration service (GitHub App + DB)
    - DB: `org_webhooks`, `user_github_tokens`
    - Flow: Generate secret, register webhook via GitHub App, store metadata.

35. `GET /organizations/{org_id}/status`
    - Handler: `get_org_status`
    - Flow: Summarize webhook/docbook linkage state.

36. `POST /organizations/{org_id}/docbook`
    - Handler: `link_docbook_repo`
    - DB: `docbook_repos`
    - Flow: Bind docbook repo name/branch to org.

37. `GET /organizations/{org_id}/docbook`
    - Handler: `get_docbook_repo`
    - Flow: Retrieve docbook linkage metadata.

38. `POST /organizations/{org_id}/docbook/publish`
    - Handler: `publish_docbook`
    - Flow: Promote staging → main.

39. `POST /organizations/{org_id}/docbook/approve`
    - Handler: `approve_docbook`
    - Flow: Approve staging docs (finalize release).

40. `GET /organizations/{org_id}/pending-reviews`
    - Handler: `list_pending_reviews`
    - DB: `docbook_reviews`
    - Flow: List pending doc reviews for org.

### 4.8 Repos (Doc Viewer) (`app/api/v1/endpoints/repos.py`)

41. `GET /repos`
    - Handler: `list_repos`
    - Flow: Frontend-friendly repository list (wraps repository service).

42. `GET /repos/{repo_full_name}/docs/{doc_type}`
    - Handler: `get_repo_doc`
    - Flow: Fetch doc content with README/summary fallbacks (GitHub API + docbook).

43. `GET /repos/{repo_full_name}/docs/{doc_type}/{version}`
    - Handler: `get_repo_doc_version`
    - Flow: Fetch specific doc version from docbook.

44. `POST /repos/{repo_full_name}/generate`
    - Handler: `generate_repo_doc`
    - Flow: Trigger doc generation & publish similar to manual endpoint.

### 4.9 Docbook helper (`app/api/v1/endpoints/docbook.py`)

45. `POST /docbook/link-repo`
46. `GET /docbook/check-exists`
47. `POST /docbook/publish`
48. `POST /docbook/approve-and-merge`
49. `GET /docbook/pending-reviews`

- These supplement organization endpoints, focusing on docbook repo linkage, staging reviews, and approvals. They call `DocbookPublisher` and related services, touching `docbook_repos`, `docbook_reviews`.

### 4.10 Webhooks (`app/webhooks/github.py`)

50. `POST /webhooks/github`
    - Handler: `handle_github_webhook`
    - Flow: Verify signature → persist event via `EventService` → enqueue asynchronous processing.

### 4.11 Health (`app/api/v1/endpoints/health.py`)

51. `GET /health`
    - Handler: `health_status`
    - Flow: Returns service heartbeat metadata (no DB).

> Some endpoints are effectively aliases (e.g., organization vs docbook helpers) but are listed separately for clarity.

---

## 5. Supporting Services

| Service | Location | Responsibilities |
|---------|----------|------------------|
| `AuthService` | `app/services/auth.py` | OAuth exchange, user/session persistence, JWT issuance |
| `EventService` | `app/services/event/service.py` | CRUD for `events` and `event_processing_log` |
| `EventProcessor` | `app/services/event/processor.py` | Routes events (`push`, `github.installation`, etc.) to workflows |
| `DocbookPublisher` | `app/services/docbook/publisher.py` | Clone docbook repos, push staging/main, track reviews |
| `ManualDocGenerator` | `app/services/documentation/manual_generation.py` | On-demand doc generation using LLM + diff analysis |
| `SubscriptionService` | `app/services/subscription.py` | Plan enforcement, Stripe checkout/sync |
| `GitHubDualAppHelper` | `app/utils/github_dual_app.py` | Manages reader/writer GitHub App tokens |

---

## 6. Database Tables Touched (per major module)

- `users`, `user_sessions`: Authentication flows
- `repositories`: Repo onboarding & persona updates
- `documentation_publications`, `docbook_reviews`, `docbook_repos`: Documentation workflow
- `events`, `event_processing_log`: Event tracking & logs
- `github_installations`, `org_webhooks`, `user_github_tokens`: GitHub installation + webhook registration
- `subscriptions`, `subscription_usage`: Plan enforcement and billing

Schema definitions originate from `schema.sql` and incremental migrations in `migrations/`.

---

## 7. Suggested Reading Order

1. `app/main.py` – understand startup, routing, background tasks
2. `app/api/v1/api.py` – map endpoint modules
3. For each domain, read `models/*`, `schemas/*`, then corresponding `services/*`
4. Inspect `app/webhooks/github.py` & `app/services/event/processor.py` for webhook → event flow
5. Review `app/services/docbook/publisher.py` for docbook staging/publish logic

---

## 8. Next Steps / Observations

- Confirm duplication between `/documentation` and `/docs`; consider consolidation
- Track ORM ↔ schema mismatches (some models adapt to legacy columns)
- Ensure webhook registration consistently stores tokens/installation IDs for multi-org
- Expand automated tests to cover manual generation + docbook flows end-to-end

---

This document should serve as a comprehensive reference when onboarding or deep-diving into the backend implementation under `app/`.
