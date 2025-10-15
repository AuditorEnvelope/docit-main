# 🚀 Lekhak AI - Complete Feature List

## 📋 Product Overview

**Lekhak AI** is a production-grade, AI-first documentation platform that automatically generates and maintains comprehensive, hierarchical documentation for your code repositories.

---

## ✨ Core Features

### 1. 🔥 **Never Lose Commits** (Commit Bus)
- **Durable Event Store**: PostgreSQL-backed event storage
- **Automatic Replay**: Reprocess missed commits after downtime
- **Retry Logic**: 3 automatic retries on failure
- **Complete Audit Trail**: Track every commit processed
- **Idempotent Processing**: No duplicate processing

**Use Case**: Your server goes down for 2 hours. When it restarts, all 47 missed commits are automatically processed.

---

### 2. 🌍 **Universal Language Support** (14+ Languages)

**Tier 1 (Full AST Parsing):**
- Python
- TypeScript
- JavaScript
- Go
- Rust
- Java

**Tier 2 (Regex Parsing):**
- C/C++
- C#
- Ruby
- PHP
- Swift
- Kotlin
- Scala
- Elixir
- Dart

**Features:**
- Automatic language detection
- Extract functions, classes, interfaces
- Parse signatures, parameters, return types
- Extract docstrings and comments
- Polyglot repository support

**Use Case**: Document a multi-language SDK (Python, Go, TypeScript) in one unified tree.

---

### 3. 🌲 **Hierarchical Documentation**

**Structure:**
```
Repository
├─ SDK (payment-sdk)
│  ├─ Module (core)
│  │  ├─ Feature (Create)
│  │  │  ├─ createPayment()
│  │  │  └─ createBatch()
│  │  └─ Feature (Update)
│  │     └─ updatePayment()
│  └─ Module (webhooks)
│     └─ ...
```

**Features:**
- Unlimited depth tree structure
- Parent-child navigation
- Breadcrumb trails
- Version tracking per node
- Automatic organization by feature

**Use Case**: Navigate from repo → SDK → module → feature → function with full context.

---

### 4. 🤖 **AI Agent with RAG** (Retrieval-Augmented Generation)

**Features:**
- Semantic search (not just keywords)
- Vector DB powered (Milvus)
- Commit-backed answers with provenance
- Multi-LLM support (Gemini, Groq, OpenAI)
- Context-aware responses

**Embeddings Options:**
1. OpenAI (text-embedding-3-small)
2. Gemini (FREE with API key)
3. Local (100% FREE, no API key needed)

**Example Query:**
```
Q: "What changed in Payment.create between v2.0 and v2.1?"

A: "Added `timeout` parameter (default: 30s) in v2.1.
   Source: commit abc123 by harsh@example.com on 2025-10-14
   File: src/payment/create.ts:45-52"
```

**Use Case**: Ask "How do I handle webhook retries?" and get exact code references with commit history.

---

### 5. ✏️ **Admin Overlays** (Non-Code Edits)

**Features:**
- Edit docs without changing code
- Full provenance tracking (who, when, why)
- Edit history with rollback
- Optional PR generation
- Merge with base docs on render

**Example:**
```
Base doc (from code):
  "Creates a payment"

Admin overlay:
  "Creates a payment. ⚠️ DEPRECATED: Use createPaymentV2"

Merged (shown to users):
  "Creates a payment. ⚠️ DEPRECATED: Use createPaymentV2"
  [Edited by admin@example.com on 2025-10-15]
```

**Use Case**: Add deprecation warnings or migration guides without touching code.

---

### 6. 💰 **Subscription Management** (Monetization Ready)

**Plans:**

| Feature | Free | Team ($49/mo) | Enterprise |
|---------|------|---------------|------------|
| Repos | 1 | 10 | Unlimited |
| Indexing | Daily | Real-time | Real-time |
| Queries/day | 100 | 10,000 | Unlimited |
| Overlays | ❌ | ✅ | ✅ |
| SSO | ❌ | Optional | ✅ |
| Support | Community | Email | Dedicated |

**Features:**
- Feature gates (control access)
- Usage tracking (repos, queries, storage)
- Rate limiting
- Upgrade/downgrade flows
- Billing integration ready

**Use Case**: Start free, upgrade to Team when you need overlays and more repos.

---

### 7. 🎨 **Multi-LLM Support**

**Supported Providers:**
- Google Gemini (gemini-2.5-flash)
- Groq (llama-3.3-70b)
- OpenAI (gpt-4, gpt-3.5-turbo)
- DeepSeek (deepseek-chat)

**Features:**
- Automatic fallback on failure
- Quota management
- Provider rotation
- Error tracking
- Health monitoring

**Use Case**: Primary LLM hits quota → automatically switches to backup.

---

### 8. 📊 **Smart Change Detection**

**Features:**
- Analyze commit diffs
- Detect breaking changes
- Generate changelogs automatically
- Track API changes
- Version comparison

**Use Case**: Automatically generate "What's New in v2.1" from commits.

---

### 9. 🔍 **Semantic Search**

**Features:**
- Vector-based similarity search
- Find related code across repos
- Natural language queries
- Context-aware results
- Ranked by relevance

**Use Case**: Search "authentication flow" and find all related functions across multiple files.

---

### 10. 📱 **Beautiful UI** (Pustak)

**Features:**
- GitBook-style interface
- Dark/light mode
- Syntax highlighting
- Interactive navigation
- Mobile responsive
- Search integration

**Tech Stack:**
- Next.js 14
- React
- TailwindCSS
- Shadcn/ui components

---

## 🏗️ Technical Architecture

### Backend Services

1. **Main API** (`main.py`)
   - FastAPI application
   - GitHub webhook handler
   - Route management
   - Service orchestration

2. **Commit Bus** (`commit_bus.py`)
   - Event store (PostgreSQL)
   - Replay capability
   - Audit logging

3. **Event Consumer** (`event_consumer.py`)
   - Background worker
   - Batch processing
   - Retry logic

4. **Doc Generator** (`hierarchical_doc_generator.py`)
   - Code parsing
   - Tree building
   - Version tracking

5. **Code Parser** (`universal_code_parser.py`)
   - Multi-language support
   - AST parsing
   - Regex fallback

6. **Indexer** (`indexer_service.py`)
   - Embedding generation
   - Vector DB integration
   - Batch indexing

7. **Agent** (`agent_service.py`)
   - RAG implementation
   - Query processing
   - Provenance tracking

8. **Overlay Service** (`overlay_service.py`)
   - Edit management
   - History tracking
   - Merge logic

9. **Subscription Service** (`subscription_service.py`)
   - Plan management
   - Feature gates
   - Usage tracking

### Infrastructure

- **Database**: PostgreSQL (13 tables)
- **Vector DB**: Milvus (optional)
- **Cache**: Redis (optional)
- **Queue**: Built-in event bus
- **Deployment**: Docker Compose ready

---

## 🎯 Use Cases

### 1. **Multi-Language SDKs**
Document Python, TypeScript, Go, and Rust SDKs in one place with unified navigation.

### 2. **API Documentation**
Auto-generate API docs from code with examples, parameters, and return types.

### 3. **Internal Knowledge Base**
Build searchable knowledge base from your codebase with AI-powered Q&A.

### 4. **Migration Guides**
Track changes across versions and generate migration guides automatically.

### 5. **Onboarding**
New developers can ask questions and get answers with exact code references.

### 6. **Compliance**
Full audit trail of all changes with commit provenance for compliance requirements.

---

## 📈 Comparison

### vs GitBook

| Feature | Lekhak AI | GitBook |
|---------|-----------|---------|
| Source | Code (auto) | Manual markdown |
| Accuracy | Always in sync | Can be outdated |
| Commit tracking | Every commit | No tracking |
| AI Agent | Yes (with provenance) | No |
| Hierarchy | Unlimited depth | Limited |
| Multi-language | 14+ languages | N/A |

### vs Swagger/OpenAPI

| Feature | Lekhak AI | Swagger |
|---------|-----------|---------|
| Scope | Full codebase | API only |
| Languages | 14+ | API specs |
| AI Q&A | Yes | No |
| Version tracking | Per commit | Manual |
| Code parsing | Automatic | Manual annotations |

### vs Docusaurus

| Feature | Lekhak AI | Docusaurus |
|---------|-----------|-------------|
| Source | Code (auto) | Manual MDX |
| AI Agent | Yes | No |
| Code parsing | Automatic | Manual |
| Versioning | Per commit | Manual |
| Search | Semantic | Text-based |

---

## 🚀 Getting Started

### Minimal Setup (2 API Keys)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
GITHUB_TOKEN=xxx
GEMINI_API_KEY=xxx

# 3. Run
python src/main.py
```

### Full Setup (All Features)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup database
createdb lekhak_ai
psql lekhak_ai < schema.sql

# 3. Configure
GITHUB_TOKEN=xxx
GEMINI_API_KEY=xxx
DATABASE_URL=postgresql://localhost/lekhak_ai

# 4. Start services
docker-compose up -d
```

---

## 📊 Stats

- **Languages Supported**: 14+
- **API Endpoints**: 20+
- **Database Tables**: 13
- **Services**: 9
- **Lines of Code**: 6,000+
- **Documentation**: 4,000+ lines

---

## 🎉 Summary

**Lekhak AI is a complete documentation platform with:**

✅ Never lose commits (durable event store)  
✅ 14+ languages supported  
✅ AI agent with provenance  
✅ Admin overlays (non-code edits)  
✅ Subscription management  
✅ Multi-LLM support  
✅ Semantic search  
✅ Beautiful UI  
✅ Production-ready  

**Ready to deploy and monetize!** 🚀
