# DocIt AI — Product Roadmap

**Document:** 05  
**Audience:** Investors, product stakeholders  
**Related:** `00_WHITEPAPER.md`

---

## Phase 1 — Core (Shipped ✅)

| Milestone | Description |
|---|---|
| M1.1 | GitHub webhook ingestion with HMAC verification |
| M1.2 | Durable commit bus (PostgreSQL) |
| M1.3 | Smart Processor: discovery scanner + understanding builder |
| M1.4 | LLM planning + per-section fan-out |
| M1.5 | Docbook staging branch publishing |
| M1.6 | Hierarchical doc tree (nodes + versions) |
| M1.7 | Dual GitHub App architecture (Reader/Writer) |

**Outcome**: Core documentation generation → publish loop works end-to-end for any codebase.

---

## Phase 2 — Platform (Shipped ✅)

| Milestone | Description |
|---|---|
| M2.1 | Multi-org support via GitHub OAuth |
| M2.2 | Org registration + per-org docbook repos |
| M2.3 | Multi-LLM provider + key pool rotation (Gemini, Groq, DeepSeek, OpenAI, Anthropic) |
| M2.4 | Subscription tiers (Free / Team / Enterprise) |
| M2.5 | Stripe + Razorpay billing |
| M2.6 | Overlay system (admin edits with provenance) |
| M2.7 | Usage analytics + per-endpoint tracking |

**Outcome**: Multi-tenant SaaS with billing. Ready for paid customers.

---

## Phase 3 — Scale (In Progress / Planned)

| Milestone | Description |
|---|---|
| M3.1 | Vector embeddings + Milvus for RAG search |
| M3.2 | Multi-repo cross-reference linking |
| M3.3 | Real-time collaboration (WebSocket) |
| M3.4 | Doc version diff + changelog generation |
| M3.5 | CLI tool (`docit generate` / `docit publish`) |
| M3.6 | Enterprise SSO (SAML / OIDC) |
| M3.7 | Multi-language codebase support (non-Python stacks) |

**Outcome**: Production-grade platform with advanced search and enterprise features.

---

## Phase 4 — Expand (Future)

| Milestone | Description |
|---|---|
| M4.1 | Auto-generated API client SDKs from docs |
| M4.2 | CI/CD integration (PR comment docs preview) |
| M4.3 | Marketplace for doc templates (community) |
| M4.4 | Slack / Teams notification integrations |
| M4.5 | Self-hosted enterprise appliance |
| M4.6 | AI chatbot over docs (RAG-powered assistant) |

**Outcome**: Full documentation operations platform.

---

## Timeline

```
2025 Q3  ████████████  Phase 1 Core
2025 Q4  ████████████  Phase 2 Platform
2026 Q1  ████████░░░░  Phase 3 Scale  (M3.1–M3.3)
2026 Q2  ████████░░░░  Phase 3 Scale  (M3.4–M3.7)
2026 Q3  ██████░░░░░░  Phase 4 Expand (M4.1–M4.3)
2026 Q4  ████░░░░░░░░  Phase 4 Expand (M4.4–M4.6)
```

---

## KPIs

| Metric | Target |
|---|---|
| Time-to-first-doc (per repo) | < 2 minutes |
| Doc freshness | Automatic on every push |
| Uptime | 99.9% |
| LLM cost per repo | < $0.01/doc generation |
| Customer acquisition | 100+ orgs by EOY 2025 |
