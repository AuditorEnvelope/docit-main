# DocIt AI — Whitepaper

**Version:** 1.0  
**Date:** October 2025  
**Status:** Production-Ready  
**Repository:** https://github.com/AuditorEnvelope/doc_ai

---

## Executive Summary

DocIt AI is an AI-powered documentation automation platform that solves one of software engineering's most persistent productivity drains: keeping documentation in sync with code. Every engineering team knows the problem — documentation rots within days of a code change, yet manual documentation is expensive, inconsistent, and rarely updated. DocIt AI eliminates this friction by automatically generating, publishing, and maintaining hierarchical documentation whenever code is pushed to a repository.

The platform ingests GitHub push events through a durable commit bus, analyzes codebases using multi-model LLM calls with structured evidence gathering, and publishes generated documentation to organization-controlled "docbook" repositories — all without requiring engineers to change their workflow.

**Key Value Proposition:** Documentation is generated and published automatically on every push, keeping docs alive without engineer effort.

---

## Problem Statement

### The Documentation Decay Problem

Software documentation has a half-life measured in days, not years. Studies consistently show that:

- **80%** of documentation becomes outdated within 30 days of code changes
- Engineers spend an estimated **20–30%** of their time searching for or reconstructing documentation
- API documentation errors cause **40%+** of integration bugs in third-party developer ecosystems
- Manual documentation processes create a "write once, never update" anti-pattern

### Why Existing Solutions Fail

| Approach | Limitation |
|---|---|
| Static site generators (MkDocs, Docusaurus) | Require manual updates; docs drift from code |
| AI code assistants (Copilot, ChatGPT) | Generate snippets, not structured documentation |
| API scrapers / Swagger | Only document APIs, not architecture, workflows, or data models |
| Manual doc teams | Expensive, slow, inconsistent coverage |
| LLM agents (generic) | No codebase context, hallucinate, no publishing pipeline |

DocIt AI addresses every gap: it is **codebase-aware** (reads actual source), **hierarchical** (SDK → Module → Feature → Function), **persona-adaptive** (internal vs. developer-facing), and **publishes automatically** to GitHub.

---

## Solution Architecture

DocIt AI is built as a **three-tier event-driven system**:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  GitHub      │───▶│  Commit Bus  │───▶│  Smart       │
│  Webhook     │    │  (PostgreSQL)│    │  Processor   │
│  + Dual Apps │    │              │    │  (Python)    │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │  Docbook        │
                                      │  Publisher      │
                                      │  (Staging Branch)│
                                      └─────────────────┘
```

### Tier 1: Event Ingestion (GitHub Webhooks)

- Receives push events via HMAC-verified GitHub webhooks
- Supports both single-app and dual-app (Reader + Writer) GitHub App authentication
- Stores events durably in PostgreSQL with idempotent handling (ON CONFLICT)
- Multi-org aware: tracks `user_id`, `org_id`, `installation_id` per event
- Handles missed commits on worker startup via GitHub API sync

### Tier 2: Commit Bus + Event Consumer

- **Durable event store**: All commits stored in `commit_events` table with full metadata (author, files changed, branch, push ID)
- **Background worker**: Polls for unprocessed events every 5 seconds
- **Multi-org replay**: On startup, queries GitHub API across all registered orgs to find missed commits during downtime
- **Batch processing**: Up to 100 events per batch, 3 retries on failure

### Tier 3: Smart Documentation Generation

The heart of DocIt AI — a multi-phase LLM pipeline:

1. **Discovery Scanner**: Reads the codebase with zero hardcoded patterns — discovers ingress points, egress points, state models, orchestrators, data flows, and architecture signals purely from evidence
2. **Semantic Snapshot**: Extracts framework signals, API patterns, auth patterns, data layer information, deployment targets
3. **Understanding Builder**: Transforms raw discovery data into a structured system model (components, data flows, API surface, storage, integrations)
4. **Planning Call (LLM)**: Asks the LLM what sections THIS specific codebase needs — fully adaptive, never assumes tech stack
5. **Per-Section Fan-Out**: Each section gets its own LLM call with targeted evidence, semantic validation, and selective retry — all async parallel
6. **Quality Validation**: Post-generation LLM quality check + structural validation
7. **Docbook Publishing**: Pushes to staging branch, creates pending review record

---

## Key Features

### 1. Multi-Persona Documentation

Each repository can be configured for different documentation personas:

- **Internal**: Surgeon's manual for engineers — deep technical detail, data flows, failure modes, exact file paths
- **Developer/Public**: User-facing guide — no internal code exposure, step-by-step workflows, plain language

The LLM prompt system enforces persona-appropriate content through strict anti-hallucination rules and writing constraints.

### 2. Multi-LLM Provider with Key Pool Rotation

DocIt AI supports five LLM providers with automatic failover:

| Provider | Model | Key Pool |
|---|---|---|
| Gemini | `gemini-2.5-flash` / `gemini-2.0-flash` | N keys, health-tracked slots |
| Groq | `llama-3.3-70b-versatile` | N keys, LRU slot selection |
| DeepSeek | `deepseek-chat` | N keys |
| OpenAI | `gpt-4` | Fallback |
| Anthropic | `claude-3-opus` | Fallback |

The `LLMRotator` manages per-key health tracking (error counts, in-flight requests, rate-limit disable), automatic slot rotation on transient failures, and daily quota detection.

### 3. Hierarchical Documentation Tree

Generated documentation follows a tree structure:

```
SDK/
├── Authentication/
│   ├── JWT Refresh/
│   │   ├── current.md
│   │   └── v1.0-JWT Refresh.md
│   └── OAuth Flow/
│       ├── current.md
│       └── v1.0-OAuth Flow.md
├── Payment Processing/
│   ├── Card Charges/
│   └── Refunds/
└── Webhooks/
```

Each node tracks version history, parent relationships, and content metadata.

### 4. Docbook Publishing Workflow

- Generates docs into `docs/internal/` and `docs/dev/` folders
- Publishes to `{org}/docit-docbook-{org}` staging branch
- Creates pending review records in database
- Supports doc_persona configuration per repository
- Avoids feedback loops by skipping docbook bot commits

### 5. Overlay System

Non-code documentation edits with full provenance:

- Admin edits override generated docs without changing code
- Every edit tracked with author, reason, timestamp
- Status lifecycle: active → pr_created → merged/archived
- Overlay history table for full audit trail

### 6. Subscription & Billing

Three-tier subscription model:

| Tier | Repos | Indexing | Overlays | Seats |
|---|---|---|---|---|
| Free | 1 | Daily | No | 1 |
| Team | 10 | Realtime | Yes | 5 |
| Enterprise | Unlimited | Realtime | Yes + SSO | Unlimited |

Payment via Stripe and Razorpay. Usage tracking with per-endpoint analytics.

### 7. Multi-Org Support

- Organizations register via GitHub OAuth
- Each org has its own GitHub App installations (Reader + Writer)
- Worker discovers orgs via `org_registrations` table
- Per-org docbook repositories
- Installation tracking in `github_installations` and `app_installations` tables

---

## Technical Stack

### Backend
| Component | Technology |
|---|---|
| Framework | FastAPI 0.120+ |
| Language | Python 3.11 |
| Database | PostgreSQL (asyncpg) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT (HS256) + GitHub OAuth |
| HTTP Client | httpx, aiohttp |
| LLM SDK | google-generativeai, groq, openai |

### Frontend
| Component | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS 4 |
| State | Zustand |
| Editor | BlockNote |

### Infrastructure
| Component | Technology |
|---|---|
| Container | Docker + docker-compose |
| Queue | Redis (planned) |
| Vector DB | Milvus (planned) |
| Deployment | Railway-compatible |

---

## Security Architecture

- **HMAC webhook verification**: All GitHub webhooks verified with SHA-256 signatures
- **GitHub App JWT**: Short-lived JWTs (10 min) with RS256 signing for app authentication
- **Installation tokens**: Per-org installation access tokens with scoped permissions (read/write)
- **Dual-app isolation**: Reader app (contents:read) and Writer app (contents:write) are completely separate GitHub Apps
- **Token masking**: All logs mask GitHub tokens and API keys
- **Audit logging**: Every action logged with user, timestamp, IP, and changes
- **Rate limiting**: Per-endpoint rate limiting via middleware

---

## Competitive Advantages

1. **Fully Adaptive LLM Planning**: Unlike template-based doc generators, DocIt AI's planning call determines what sections a codebase actually needs — no generic "Overview, Architecture, API" boilerplate
2. **Anti-Hallucination Enforcement**: Evidence-only rules with strict banned phrases; LLM cannot invent technologies not present in the codebase
3. **Voice-Locked Fan-Out**: All sections generated with the same provider/key for uniform documentation voice
4. **Dual GitHub App Architecture**: Reader/Writer separation follows GitHub's security best practice — documentation generation uses read-only app, publishing uses write-only app
5. **Multi-Org by Design**: Built for SaaS from day one — each org gets isolated docbook repos, installations, and subscriptions
6. **Durable Event Processing**: Commit bus ensures no commits are lost; missed commit detection on startup; idempotent event handling

---

## Roadmap

| Phase | Feature | Status |
|---|---|---|
| 1 | Core documentation generation | ✅ Production |
| 2 | Docbook publishing workflow | ✅ Production |
| 3 | Multi-org support | ✅ Production |
| 4 | Subscription/billing (Stripe + Razorpay) | ✅ Production |
| 5 | Overlay system | ✅ Production |
| 6 | Vector embeddings + RAG search | 🔲 Planned |
| 7 | Real-time collaboration | 🔲 Planned |
| 8 | CLI tool | 🔲 Planned |

---

## Market Position

DocIt AI occupies a unique intersection: it is not just a documentation generator, not just a dev tools platform, and not just an LLM application — it is an **automated documentation operations platform** that bridges the gap between code and knowledge. The target market includes:

- **SaaS companies** with public APIs needing developer documentation
- **Engineering orgs** with internal SDKs and libraries
- **Open source projects** seeking automated README and docs updates
- **Technical writing teams** needing draft generation at scale

---

## Appendix: Glossary

| Term | Definition |
|---|---|
| Docbook | Organization's documentation repository (staging + main branches) |
| Doc Persona | Configuration determining internal vs. developer-facing documentation |
| Commit Bus | Durable event store for all git commits |
| Overlay | Non-code admin edit to generated documentation |
| Smart Processor | Core event handler that orchestrates analysis, generation, and publishing |
| Discovery Scanner | First-principles codebase analysis producing raw structural signals |
| Understanding Builder | Structured system model from discovery signals |
| Fan-Out | Parallel per-section LLM generation |
| Voice Lock | Using the same LLM provider/key across all sections for consistency |
