# DocIt AI — API Specification

**Document:** 03  
**Audience:** Engineers, integrators  
**Related:** `00_WHITEPAPER.md`, `04_DATA_FLOW.md`

Base URL: `https://api.docit.ai/v1` (or `http://localhost:8000/api/v1` locally).

All responses are JSON. All timestamps are ISO-8601 UTC.

---

## Authentication

### GitHub OAuth
```
POST /api/v1/auth/github/login
→ Redirect to GitHub OAuth consent
```

### JWT (HS256)
Every subsequent request includes `Authorization: Bearer <jwt>`. Tokens are short-lived (1h). The JWT payload includes `user_id` and `org_id`.

---

## Webhooks

### Receive GitHub Push
```
POST /api/v1/webhooks/github
Headers:
  X-GitHub-Event: push
  X-Hub-Signature-256: sha256=<hmac>
  Content-Type: application/json

Body: GitHub push event payload
→ 200 (accepted) | 401 (bad signature)
```

Idempotent — duplicate pushes are ignored.

---

## Repositories

### List Org Repos
```
GET /api/v1/repos?org_id=<uuid>
→ 200 { repos: [{ id, name, doc_persona, last_processed_sha, updated_at }] }
```

### Register Repo
```
POST /api/v1/repos
{ org_id, github_repo_id, default_branch?, doc_persona? }
→ 201
```

### Update Persona
```
PATCH /api/v1/repos/:repo_id/persona
{ doc_persona }
→ 200
```

---

## Documentation Generation

### Trigger Manual Generation
```
POST /api/v1/generate
{ repo_id, commit_sha?, persona? }
→ 202 { job_id }
```

### Poll Job Status
```
GET /api/v1/generate/:job_id
→ 200 { status: pending|processing|completed|failed, sections_generated, error? }
```

---

## Docbook Publishing

### Get Staging Status
```
GET /api/v1/docbooks/:org_id/staging
→ 200 { branch: "docit/staging-<uuid>", pending_reviews: [{ id, persona, sections, created_at }] }
```

### Merge Staging → Main
```
POST /api/v1/docbooks/:org_id/merge
{ staging_branch, merge_message? }
→ 200 { merged_review_ids }
```

---

## Overlays

### Create Overlay
```
POST /api/v1/overlays
{ node_id, content, reason, author_user_id }
→ 201
```

### List Overlays
```
GET /api/v1/overlays?node_id=<uuid>
→ 200 { overlays: [{ id, content, status, author, reason, history: [...] }] }
```

### Update Overlay Status
```
PATCH /api/v1/overlays/:id/status
{ status }
→ 200
```

---

## Subscriptions

### Get Subscription
```
GET /api/v1/subscriptions/:org_id
→ 200 { tier, provider, status, current_period_end }
```

### Record Usage
```
POST /api/v1/usage
{ org_id, endpoint, quantity }
→ 201
```

---

## Admin / Platform

### Health Check
```
GET /health
→ 200 { db: ok, worker_live: true, llm_providers: { gemini: ok, groq: ... } }
```

### Audit Logs
```
GET /api/v1/admin/audit?org_id=<uuid>&action?&since?
→ 200 { logs: [{ action, actor, ip, details, created_at }] }
```

---

## Error Format

```json
{ "error": { "code": "E_PROCESSING", "message": "...", "attempt": 2 } }
```

Standard HTTP codes are used (400, 401, 403, 404, 409, 429, 500).
