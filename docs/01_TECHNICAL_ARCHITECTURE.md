# DocIt AI — Technical Architecture

**Document:** 01  
**Audience:** Technical reviewers, engineers, CTO-level evaluators  
**Related:** `00_WHITEPAPER.md`, `02_DATABASE_SCHEMA.md`, `04_DATA_FLOW.md`

---

## 1. System Overview

DocIt AI is an asynchronous, event-driven documentation generation service. It is composed of four independent runtime roles that share a single FastAPI codebase and a single PostgreSQL database:

| Role | Entry Point | Responsibility |
|---|---|---|
| **API Server** | `uvicorn app.main:app` | Serves REST endpoints, handles webhooks, auth, billing |
| **Event Worker** | Background task / `event_consumer` | Consumes commit events, orchestrates generation |
| **LLM Orchestrator** | In-process module | Multi-provider LLM calls with rotation and failover |
| **Docbook Publisher** | In-process module | Writes generated docs to org docbook repos via GitHub API |

A single process can run all roles (production default), or they can be split across containers for scale-out. The durable commit bus is what makes splitting safe — events survive restarts and can be consumed by any worker.

---

## 2. High-Level Data Flow

```
 Developer pushes code
           │
           ▼
 ┌─────────────────────┐
 │  GitHub             │  push event
 │  (webhook)          │  HMAC-SHA256 signed
 └─────────┬───────────┘
           │ POST /api/v1/webhooks/github
           ▼
 ┌─────────────────────┐
 │  Webhook Handler    │  verify signature, extract
 │  (app/api)          │  push payload, resolve org/repo
 └─────────┬───────────┘
           │ idempotent insert
           ▼
 ┌─────────────────────┐
 │  commit_events      │  status = "pending"
 │  (PostgreSQL)       │
 └─────────┬───────────┘
           │ poll every 5s
           ▼
 ┌─────────────────────┐
 │  Event Consumer     │  claim batch, mark "processing"
 │  (event_consumer)   │
 └─────────┬───────────┘
           │ for each event
           ▼
 ┌─────────────────────┐
 │  Smart Processor    │  read repo via GitHub API
 └─────────┬───────────┘
           │
           ├──────────────────────────────┐
           ▼                              ▼
   ┌─────────────────┐          ┌──────────────────┐
   │ Discovery       │          │ Semantic Snapshot │
   │ Scanner         │          │                  │
   └────────┬────────┘          └────────┬─────────┘
            │                            │
            ▼                            ▼
   ┌─────────────────────────────────────────┐
   │  Understanding Builder                  │
   │  (system model)                         │
   └─────────────────────┬───────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────┐
   │  LLM Planning Call                      │
   │  "what sections does THIS codebase need" │
   └─────────────────────┬───────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────┐
   │  Per-Section Fan-Out (async parallel)   │
   │  ┌───┐ ┌───┐ ┌───┐ ┌───┐                │
   │  │ S1│ │ S2│ │ S3│ │ S4│  each with     │
   │  └───┘ └───┘ └───┘ └───┘  targeted ev.  │
   └─────────────────────┬───────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────┐
   │  Quality Validation (LLM + structural)  │
   └─────────────────────┬───────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────┐
   │  Docbook Publisher                      │
   │  write staging branch + pending review  │
   └─────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Webhook Ingestion

- Endpoint: `POST /api/v1/webhooks/github`
- **Signature verification**: GitHub signs the `X-Hub-Signature-256` header with the app webhook secret. The handler recomputes `sha256(secret + payload)` and compares. Any mismatch → `401`.
- **Event filtering**: Only `push` events are processed. All other event types (`ping`, `issues`, etc.) are acknowledged and ignored.
- **Payload extraction**: From the `push` payload, extract:
  - `ref` → branch name (only `main` / default branch processed)
  - `before` / `after` → commit SHAs
  - `repository.id`, `repository.full_name` → repo identity
  - `pusher.name` → commit author
- **Multi-app routing**: Depending on which GitHub App's secret verifies the signature, the event is attributed to the correct `installation_id` and thus the correct org.
- **Idempotency**: Each push has a unique `push_id`. The insert uses `ON CONFLICT (push_id) DO NOTHING` so replayed webhooks never create duplicate events.

### 3.2 Commit Bus & Event Consumer

- **Storage**: `commit_events` table holds every commit ever received, with full metadata. This is the durability layer — the API can be down for hours and no commit is lost.
- **Polling loop**: The consumer wakes every 5 seconds, queries `WHERE status = 'pending' ORDER BY created_at LIMIT 100`, and claims them atomically.
- **Claim semantics**: Events are transitioned `pending → processing` with a `locked_by` worker identifier and a `lock_expires_at` timestamp. If a worker dies mid-processing, the lock expires and another worker picks up the event. This gives at-least-once semantics with safe re-entry.
- **Retries**: Each event allows up to 3 attempts (`attempt_count`). On final failure it transitions to `status = 'failed'` and is surfaced for manual inspection.
- **Startup replay**: On worker boot, a recovery routine queries the GitHub API for each registered org's repos, lists recent commits since the last processed SHA, and inserts any missed events into the bus. This closes the gap from downtime.

### 3.3 Smart Processor

The smart processor is the orchestration heart. For a single claimed commit event it runs:

1. **Repo read**: Uses the **Reader** GitHub App's installation token to clone/list the repo contents via GitHub API. This is the only capability the reader app has (`contents:read`).
2. **Discovery Scan**: A deterministic, pattern-agnostic pass that reads file headers, entrypoints, manifests, and config to emit raw structural signals (see §4).
3. **Semantic Snapshot**: Framework detection, API route extraction, auth mechanism identification, data-layer introspection.
4. **Understanding Build**: Normalizes the two raw outputs into a typed system model used to seed LLM prompts.
5. **Planning**: A single LLM call asks which top-level doc sections this specific codebase warrants. The result is a dynamic section list — never a fixed template.
6. **Fan-Out**: Each section is generated in a parallel async task. Each task gets a **focused evidence bundle** (only the files relevant to that section) plus the shared system model.
7. **Validation**: An LLM quality pass checks for hallucinated content and banned claims; a structural pass verifies markdown integrity and hierarchy.
8. **Publish**: On success, hand off to the publisher.

### 3.4 LLM Orchestrator (Rotator)

The `LLMRotator` abstracts five providers behind one interface:

```python
class LLMRotator:
    async def complete(self, provider, model, prompt, *, max_tokens) -> str
    async def pick_slot(self, provider) -> KeySlot
    def record_success(self, slot)
    def record_error(self, slot, transient: bool)
```

- **Key pools**: Each provider holds N API keys. Slots are tracked with `in_flight`, `error_count`, `daily_quota_hit`, and `last_error`.
- **Slot selection**: LRU among healthy slots (lowest `in_flight` first). A slot that recently hit a 429 is disabled for a backoff window.
- **Voice lock**: For a single generation run, the orchestrator pins one `provider + key` for all section fan-outs so the doc voice is consistent across sections. Failover to a new key only happens on hard failure.
- **Daily quota detection**: When a provider reports a daily quota error, the slot is marked `daily_quota_hit` and excluded until the UTC day rolls over.

### 3.5 Docbook Publisher

- Uses the **Writer** GitHub App's installation token (`contents:write`).
- Target repo: `{org}/docit-docbook-{org}`.
- Writes generated files under `docs/{persona}/...` where persona ∈ {`internal`, `dev`}.
- Pushes to a **staging branch** (never `main` directly) and creates a pending review record in `pending_doc_reviews`.
- A human (or automation) later merges staging → main, which is the docbook's live tree.
- **Feedback-loop guard**: The publisher checks commit authorship. Commits authored by the docbook bot are skipped so that publishing docs does not trigger a new generation event.

---

## 4. Discovery Scanner (First-Principles Analysis)

The discovery scanner is deliberately free of hardcoded language/framework patterns. It works from **evidence**:

| Signal | How it's detected |
|---|---|
| **Ingress points** | Files that define route handlers, message consumers, or server listeners |
| **Egress points** | Outbound HTTP clients, SDK calls, queue producers, third-party API usage |
| **State models** | ORM classes, database schema files, persistence layers |
| **Orchestrators** | Modules that coordinate multiple components (services, use-cases, controllers) |
| **Data flows** | Call-graph edges between ingress → orchestrator → state/egress |
| **Architecture signals** | Layer separation, DI containers, event emitters, middleware chains |

The scanner emits a JSON structure that the understanding builder turns into a stable system model. This is what makes DocIt AI portable across stacks — it never assumes a framework.

---

## 5. Concurrency Model

- **Async everywhere**: The entire backend is built on `async`/`await` (FastAPI + asyncpg + httpx/aiohttp). No thread-based blocking in the request or worker paths.
- **Fan-out parallelism**: Section generation uses `asyncio.gather` so N sections generate concurrently, bounded by a semaphore to respect provider rate limits.
- **Per-key in-flight accounting**: The rotator's `in_flight` counter prevents a single key from being over-subscribed during fan-out.
- **Durable claim locks**: As described in §3.2, processing is idempotent-safe via the lock + `attempt_count` mechanism.

---

## 6. Error Handling & Resilience

- **Transient LLM failures** (429, 500, timeout): requeue to another key; after 3 global attempts, mark event failed.
- **GitHub API failures**: exponential backoff with jitter; rate-limit headers (`x-ratelimit-remaining`) respected.
- **Partial generation**: If a section fails validation, that section is retried with a "repair" prompt; other sections are unaffected.
- **Poison events**: Events that fail 3 times are parked in `failed` state with a full error payload for inspection — they never block the queue.

---

## 7. Observability

- **Structured logging**: Every LLM call, every section generation, every publish is logged with provider, model, key-slot (masked), latency, and token counts.
- **Audit log**: `audit_logs` table records user-facing actions (login, publish, overlay edit, billing) with actor, IP, timestamp, and before/after state.
- **Usage tracking**: `usage_events` records per-endpoint consumption against subscription quotas.
- **Health endpoint**: `GET /health` reports DB connectivity, worker liveness, and LLM provider availability.

---

## 8. Deployment Topology

| Environment | Shape |
|---|---|
| **Local** | `docker-compose up` — API + worker + Postgres in one host |
| **Staging** | Single container, all roles, Postgres + Redis |
| **Production** | API container(s) × N, worker container(s) × M, shared Postgres. Scale workers horizontally; the commit bus load-balances events. |

Railway-compatible: single deploy target with env-var configuration, Postgres add-on, Redis add-on (planned).

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| Durable commit bus over in-memory queue | Commits must never be lost; Postgres gives us durability + queryability for free |
| Dual GitHub Apps (Reader/Writer) | Least-privilege: generation can't accidentally publish; publishing can't read unrelated code |
| LLM planning over fixed templates | Generic "Overview/Architecture/API" docs are useless; adaptive sections match the codebase |
| Voice-locked fan-out | Mixed-provider generation produces inconsistent doc voice; pinning one key avoids it |
| Staging branch + review record | Docs are high-trust artifacts; a human/automation gate before they hit `main` |
| Evidence-only prompting | Anti-hallucination: LLM can only describe what the discovery scanner actually found |
