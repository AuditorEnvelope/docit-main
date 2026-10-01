# DocIt AI — Database Schema & Data Model

**Document:** 02  
**Audience:** Technical reviewers, engineers  
**Related:** `01_TECHNICAL_ARCHITECTURE.md`

DocIt AI uses **PostgreSQL** with **SQLAlchemy 2.0** (async) + **Alembic** migrations. This document describes the logical data model and the key tables.

---

## 1. Entity Overview

```
 users ──< org_registrations
              │
              ├──< app_installations
              ├──< github_installations
              ├──< subscriptions ──< usage_events
              │
              └──< repositories ──< commit_events
                                        │
                                        ├──< pending_doc_reviews
                                        │
                                        └──< doc_tree_nodes ──< doc_versions

 doc_overlays ──< doc_overlay_history
```

---

## 2. Core Tables

### 2.1 `users`

The end-user identity (developer or admin).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `github_id` | BIGINT | GitHub user ID |
| `github_username` | TEXT unique | |
| `email` | TEXT | |
| `avatar_url` | TEXT | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |
| `is_admin` | BOOLEAN | Platform-level admin |

### 2.2 `org_registrations`

An organization that has connected DocIt AI via GitHub OAuth.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `github_org_id` | BIGINT | |
| `github_org_name` | TEXT | e.g. `acme` |
| `owner_user_id` | FK → users | Who connected it |
| `docbook_repo` | TEXT | `acme/docit-docbook-acme` |
| `doc_persona` | TEXT | `internal` / `dev` / both |
| `status` | TEXT | `active` / `suspended` |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### 2.3 `app_installations` / `github_installations`

Track GitHub App installations per org. Two rows per org in the dual-app model (one Reader, one Writer).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `org_id` | FK → org_registrations | |
| `app_role` | TEXT | `reader` / `writer` |
| `installation_id` | BIGINT | GitHub installation ID |
| `access_token` | TEXT | Encrypted at rest |
| `token_expires_at` | TIMESTAMPTZ | Installation tokens are short-lived |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### 2.4 `repositories`

A repo belonging to an org that DocIt AI documents.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `org_id` | FK → org_registrations | |
| `github_repo_id` | BIGINT | |
| `github_repo_full_name` | TEXT | `acme/api-server` |
| `default_branch` | TEXT | Usually `main` |
| `doc_persona` | TEXT | Per-repo override |
| `last_processed_sha` | TEXT | For missed-commit detection |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### 2.5 `commit_events`  ← the commit bus

The durability layer. Every push event lands here.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `repo_id` | FK → repositories | |
| `push_id` | TEXT unique | Idempotency key |
| `before_sha` / `after_sha` | TEXT | |
| `branch` | TEXT | |
| `author` | TEXT | Pusher name |
| `commit_count` | INT | Commits in this push |
| `status` | TEXT | `pending` / `processing` / `completed` / `failed` |
| `attempt_count` | INT | max 3 |
| `locked_by` | TEXT | Worker identifier |
| `lock_expires_at` | TIMESTAMPTZ | |
| `error_payload` | JSONB | Failure detail on `failed` |
| `created_at` / `processed_at` | TIMESTAMPTZ | |

**Key constraint**: `UNIQUE (push_id)` enforces idempotent insertion via `ON CONFLICT DO NOTHING`.

### 2.6 `pending_doc_reviews`

A generated doc set awaiting merge into the docbook.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `repo_id` | FK → repositories | |
| `commit_event_id` | FK → commit_events | |
| `persona` | TEXT | `internal` / `dev` |
| `staging_branch` | TEXT | e.g. `docit/staging-<uuid>` |
| `status` | TEXT | `pending` / `merged` / `rejected` |
| `section_count` | INT | |
| `created_at` / `reviewed_at` | TIMESTAMPTZ | |

### 2.7 `doc_tree_nodes`

The hierarchical documentation tree. Self-referencing.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `repo_id` | FK → repositories | |
| `parent_id` | FK → doc_tree_nodes (nullable) | Self-reference for hierarchy |
| `title` | TEXT | e.g. "JWT Refresh" |
| `path` | TEXT | `docs/dev/Authentication/JWT Refresh` |
| `persona` | TEXT | |
| `current_version_id` | FK → doc_versions | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### 2.8 `doc_versions`

Versioned content for a tree node. Enables "v1.0" history alongside `current`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `node_id` | FK → doc_tree_nodes | |
| `version_label` | TEXT | `v1.0`, `v2.1`, etc. |
| `content` | TEXT | Markdown |
| `source_sha` | TEXT | Commit that generated it |
| `created_at` | TIMESTAMPTZ | |

### 2.9 `subscriptions`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `org_id` | FK → org_registrations | |
| `tier` | TEXT | `free` / `team` / `enterprise` |
| `provider` | TEXT | `stripe` / `razorpay` |
| `provider_subscription_id` | TEXT | External ID |
| `status` | TEXT | `active` / `past_due` / `canceled` |
| `current_period_end` | TIMESTAMPTZ | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### 2.10 `usage_events`

Per-endpoint consumption against quota.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `org_id` | FK → org_registrations | |
| `endpoint` | TEXT | e.g. `doc_generation` |
| `quantity` | INT | |
| `occurred_at` | TIMESTAMPTZ | |

### 2.11 `doc_overlays` / `doc_overlay_history`

Non-code admin edits that override generated docs.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `node_id` | FK → doc_tree_nodes | |
| `author_user_id` | FK → users | |
| `reason` | TEXT | Why the overlay was made |
| `content` | TEXT | Overriding markdown |
| `status` | TEXT | `active` / `pr_created` / `merged` / `archived` |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

`doc_overlay_history` mirrors each transition for the audit trail.

### 2.12 `audit_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `actor_user_id` | FK → users (nullable) | |
| `action` | TEXT | `login`, `publish`, `overlay_edit`, `billing_update` |
| `ip_address` | TEXT | |
| `details` | JSONB | Before/after state |
| `created_at` | TIMESTAMPTZ | |

---

## 3. Indexing Strategy

| Table | Index | Purpose |
|---|---|---|
| `commit_events` | `(status, created_at)` | Consumer poll hot-path |
| `commit_events` | `UNIQUE(push_id)` | Idempotency |
| `commit_events` | `(repo_id, after_sha)` | Missed-commit detection |
| `doc_tree_nodes` | `(repo_id, parent_id)` | Tree traversal |
| `subscriptions` | `(org_id, status)` | Quota checks |
| `usage_events` | `(org_id, occurred_at)` | Quota aggregation |

---

## 4. Migrations

Managed by **Alembic**. The migration history lives in `alembic/versions/`. Applying is:

```bash
alembic upgrade head
```

All schema changes must ship as a revision; no hand-edited production schema.

---

## 5. Data Isolation & Multi-Tenancy

- **Org-level isolation**: Every tenant-scoped row carries `org_id`. All queries are filtered by `org_id` derived from the authenticated context.
- **Repo-level isolation**: Doc trees, versions, and overlays are further scoped by `repo_id`.
- **No cross-tenant reads**: The API layer resolves `org_id` from the JWT / OAuth context and injects it into every repository query.
