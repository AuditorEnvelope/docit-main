# DocIt AI — Glossary

**Document:** 06  
**Audience:** All stakeholders

| Term | Definition |
|---|---|
| **DocIt AI** | The platform — automated documentation generation, publishing, and ops. |
| **Docbook** | An organization's documentation repository (`{org}/docit-docbook-{org}`). Contains both `internal` and `dev` persona trees. |
| **Doc Persona** | A per-repo configuration: `internal` (engineer-facing deep-dive) or `dev` (developer-facing, user-facing). |
| **Commit Bus** | The durable PostgreSQL event store that holds every push event before it is processed. The durability backbone. |
| **Smart Processor** | The core event handler that orchestrates discovery, understanding, LLM planning, fan-out generation, validation, and publishing. |
| **Discovery Scanner** | First-principles codebase analysis that emits raw structural signals (ingress, egress, state, orchestrator, data flows) without hardcoded patterns. |
| **Semantic Snapshot** | Framework, API pattern, auth, data layer, and deployment-target signals extracted from codebase evidence. |
| **Understanding Builder** | Normalizes discovery + snapshot into a typed system model used to seed LLM prompts. |
| **LLM Planning Call** | A single LLM call asking "what sections does THIS specific codebase need" — adaptive, never assumes tech stack. |
| **Fan-Out** | Parallel per-section LLM generation. Each section gets focused evidence + the shared system model. |
| **Voice Lock** | Pinning one LLM provider/key for an entire generation run so all sections share a consistent doc voice. |
| **Overlay** | A non-code admin edit that overrides generated docs without changing source code. Full provenance via `doc_overlay_history`. |
| **Pending Review** | A generated doc set awaiting merge into the docbook's main branch. Created when the publisher pushes to staging. |
| **Docbook Publisher** | Writes generated docs to staging branch via the Writer GitHub App. |
| **Reader / Writer GitHub Apps** | Dual-app architecture: Reader (`contents:read`) for generation; Writer (`contents:write`) for publishing. Follows GitHub security best practice. |
| **Installation Token** | Short-lived GitHub token scoped to an org's app installation, used for API calls. |
| **Commit Event** | A single push event stored in `commit_events` with full metadata (author, SHAs, branch, push ID). |
| **Missed-Commit Detection** | Worker startup recovery: queries GitHub API across all orgs for commits since the last processed SHA. |
| **LLMRotator** | Manages per-provider key pools with health tracking (error counts, in-flight, rate-limit disable), automatic slot rotation, and daily quota detection. |
| **Doc Tree Node** | A node in the hierarchical documentation tree (SDK → Module → Feature → Function). Self-referencing via `parent_id`. |
| **Doc Version** | A versioned snapshot of a tree node's content. Enables `current` + `v1.0` history side-by-side. |
| **Staging Branch** | A short-lived branch (`docit/staging-<uuid>`) where generated docs land before merge to docbook main. |
| **Feedback-Loop Guard** | Publisher skips commits authored by the docbook bot so publishing docs never triggers new generation. |
| **Subscription Tier** | Free (1 repo, daily indexing, no overlays) / Team (10 repos, realtime, overlays) / Enterprise (unlimited, SSO). |
| **Usage Event** | Per-endpoint consumption record against subscription quota. |
| **Overlay Status Lifecycle** | `active → pr_created → merged` / `archived`. |
| **HMAC-SHA256** | GitHub webhook signature verification algorithm. |
| **JWT (HS256)** | Session tokens for API auth, short-lived (1h). |
| **Asyncpg** | Async PostgreSQL driver used by SQLAlchemy. |
| **Alembic** | Database migration tool. |
