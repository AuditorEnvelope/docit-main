# lekhak ai / Pustak - Complete Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Git Repositories                         │
│                    (GitHub / GitLab / Bitbucket)                │
└────────────────────────┬────────────────────────────────────────┘
                         │ Webhooks (Push Events)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      COMMIT BUS SERVICE                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Webhook    │→ │ Event Store  │→ │   Replay     │         │
│  │   Handler    │  │  (Postgres)  │  │   Engine     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Commit Events (Ordered)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DOC GENERATION PIPELINE                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Ingest  │→ │  Parse   │→ │Normalize │→ │Summarize │       │
│  │ (Snapshot)│  │  (AST)   │  │  (Model) │  │  (LLM)   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                         ↓                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │   Link   │→ │ Version  │→ │Changelog │                     │
│  │Cross-ref │  │ Publish  │  │Generator │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
└────────────────────────┬────────────────────────────────────────┘
                         │ Doc Nodes + Metadata
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INDEXER SERVICE (RAG)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Embeddings  │→ │  Vector DB   │→ │  Retriever   │         │
│  │  Generator   │  │  (Milvus)    │  │   Engine     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Semantic Search
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SERVICE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Query      │→ │  Retrieval   │→ │   Answer     │         │
│  │  Processor   │  │   + LLM      │  │  Generator   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Answers + Provenance
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ADMIN OVERLAY SERVICE                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Edit UI     │→ │  Overlay DB  │→ │  PR Creator  │         │
│  │  (WYSIWYG)   │  │  (Postgres)  │  │  (Optional)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ Merged Docs
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PUSTAK FRONTEND                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Doc Viewer  │  │  Search UI   │  │  Admin Panel │         │
│  │  (Next.js)   │  │  (Semantic)  │  │  (Overlays)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Component Breakdown

### 1. Commit Bus Service

**Purpose**: Durable, ordered event stream for all commits

**Tech Stack**:

- **Event Store**: PostgreSQL (append-only table)
- **Queue**: Redis + BullMQ for job processing
- **Alternative**: Kafka for scale (future)

**Schema**:

```sql
CREATE TABLE commit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    parent_sha VARCHAR(40)[],
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    branch VARCHAR(255),
    files_changed JSONB,  -- [{path, status, patch}]
    commit_message TEXT,
    push_id VARCHAR(255),
    source VARCHAR(50),  -- github|gitlab|cli
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(repo_id, commit_sha)
);

CREATE INDEX idx_commit_events_repo_processed
    ON commit_events(repo_id, processed, timestamp);
CREATE INDEX idx_commit_events_sha ON commit_events(commit_sha);
```

**API Endpoints**:

```
POST /webhook                    # Receive git webhooks
POST /events                     # Manual event creation
GET  /events?repo=&processed=    # List events
POST /backfill                   # Replay commits
GET  /status                     # Service health
```

### 2. Doc Generation Pipeline

**Purpose**: Transform code → structured, versioned documentation

**Stages**:

1. **Ingest**: Clone/fetch repo at commit SHA
2. **Parse**: AST extraction (TypeScript, Python, Java, Solidity)
3. **Normalize**: Convert to canonical doc model
4. **Summarize**: LLM-based descriptions
5. **Link**: Cross-references and examples
6. **Version**: Store versioned snapshot
7. **Changelog**: Generate human-readable changes

**Doc Model** (Hierarchical):

```json
{
  "id": "uuid",
  "type": "repo|sdk|module|feature|function|class",
  "title": "Payment SDK",
  "path": "/sdks/payment",
  "parent_id": "uuid",
  "children": ["uuid"],
  "metadata": {
    "repo": "my-repo",
    "commit_sha": "abc123",
    "version": "v2.1.0",
    "last_updated": "2025-10-15T00:00:00Z",
    "authors": ["user@example.com"],
    "tags": ["payment", "api"],
    "deprecated": false
  },
  "content": {
    "signature": "function create(options: PaymentOptions): Promise<Payment>",
    "description": "Creates a new payment with the specified options...",
    "parameters": [
      {
        "name": "options",
        "type": "PaymentOptions",
        "required": true,
        "description": "Payment configuration"
      }
    ],
    "returns": {
      "type": "Promise<Payment>",
      "description": "The created payment object"
    },
    "examples": [
      {
        "title": "Basic payment",
        "code": "const payment = await Payment.create({...})",
        "language": "typescript"
      }
    ],
    "related": ["Payment.update", "Payment.cancel"]
  },
  "versions": [
    {
      "version": "v2.1.0",
      "commit_sha": "abc123",
      "changes": "Added timeout parameter"
    }
  ]
}
```

**Storage**:

```sql
CREATE TABLE doc_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- repo|sdk|module|feature|function
    title VARCHAR(500) NOT NULL,
    path VARCHAR(1000) NOT NULL,
    parent_id UUID REFERENCES doc_nodes(id),
    commit_sha VARCHAR(40) NOT NULL,
    version VARCHAR(50),
    content JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_doc_nodes_repo ON doc_nodes(repo_id);
CREATE INDEX idx_doc_nodes_path ON doc_nodes(path);
CREATE INDEX idx_doc_nodes_parent ON doc_nodes(parent_id);
CREATE INDEX idx_doc_nodes_commit ON doc_nodes(commit_sha);
```

### 3. Indexer Service (RAG)

**Purpose**: Semantic search over code and docs

**Tech Stack**:

- **Vector DB**: Milvus (self-hosted) or Pinecone (managed)
- **Embeddings**: OpenAI text-embedding-3-small or sentence-transformers
- **Metadata**: PostgreSQL for provenance

**Vector Schema**:

```python
{
    "id": "uuid",
    "type": "code|doc|diff|overlay",
    "repo_id": "string",
    "commit_sha": "string",
    "node_id": "uuid",  # Reference to doc_nodes
    "path": "string",
    "content": "string",  # Original text
    "embedding": [float],  # 1536 dimensions
    "metadata": {
        "author": "string",
        "timestamp": "ISO8601",
        "version": "string",
        "tags": ["string"]
    }
}
```

**API Endpoints**:

```
POST /index/node         # Index a doc node
POST /index/batch        # Batch indexing
POST /search             # Semantic search
DELETE /index/:id        # Remove from index
```

### 4. Agent Service

**Purpose**: Answer queries with commit-backed evidence

**Query Flow**:

```
User Query
  ↓
Intent Classification (breaking|feature|diff|explanation)
  ↓
Retrieval (top-k from vector DB)
  ↓
Context Assembly (docs + diffs + metadata)
  ↓
LLM Generation (with provenance)
  ↓
Answer + Citations
```

**Memory Tiers**:

- **Session Memory**: Ephemeral (Redis, 1 hour TTL)
- **Long-term Memory**: Persistent (Vector DB)
- **Snapshot Memory**: Per-release checkpoints

**API Endpoints**:

```
POST /query              # Ask a question
POST /diff               # Compare versions
GET  /provenance/:id     # Get source for answer
```

### 5. Admin Overlay Service

**Purpose**: Non-code edits with provenance

**Schema**:

```sql
CREATE TABLE doc_overlays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES doc_nodes(id),
    content JSONB NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    author_name VARCHAR(255),
    reason TEXT,
    status VARCHAR(50) DEFAULT 'active',  -- active|archived|pr_created
    pr_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_overlays_node ON doc_overlays(node_id, status);
```

**Merge Logic**:

```
1. Fetch base doc node (generated from code)
2. Fetch active overlay for node
3. Merge: overlay.content overrides base.content
4. Add provenance metadata:
   - edited_by: overlay.author_name
   - edited_at: overlay.updated_at
   - original_available: true
```

**API Endpoints**:

```
GET  /doc/:node_id                    # Get merged doc
POST /overlay/:node_id                # Create/update overlay
GET  /overlay/:node_id/history        # Overlay history
POST /overlay/:node_id/create-pr      # Generate PR
```

## 🔄 Data Flow Examples

### Example 1: Commit → Doc Generation

```
1. Developer pushes commit abc123
   ↓
2. GitHub webhook → POST /webhook
   ↓
3. Commit Bus stores event in commit_events table
   ↓
4. Event published to Redis queue
   ↓
5. Doc Generator worker picks up event
   ↓
6. Clone repo at abc123, parse TypeScript files
   ↓
7. Extract functions, generate descriptions via LLM
   ↓
8. Store doc nodes in doc_nodes table
   ↓
9. Indexer embeds nodes → Vector DB
   ↓
10. Generate changelog entry
   ↓
11. Mark event as processed
```

### Example 2: Query with Provenance

```
User: "What changed in Payment.create between v2.0 and v2.1?"
   ↓
1. Agent classifies as "diff" query
   ↓
2. Retrieve doc nodes for Payment.create at both versions
   ↓
3. Retrieve commit diffs between versions
   ↓
4. LLM summarizes changes with citations
   ↓
5. Return answer:
   "Added `timeout` parameter (default: 30s) in v2.1.
    Commit: abc123 by user@example.com on 2025-10-14
    File: src/payment/create.ts:45-52"
```

### Example 3: Admin Overlay

```
1. Admin opens Payment.create docs
   ↓
2. Clicks "Edit" → WYSIWYG editor
   ↓
3. Updates description, adds warning
   ↓
4. Saves → POST /overlay/:node_id
   ↓
5. Overlay stored with provenance
   ↓
6. Future viewers see merged content with badge:
   "Edited by admin@example.com on 2025-10-15"
   ↓
7. Optional: Admin clicks "Create PR"
   ↓
8. System generates branch, commits changes, opens PR
```

## 🛠️ Tech Stack Summary

| Component    | Technology       | Alternative           |
| ------------ | ---------------- | --------------------- |
| Backend      | Python (FastAPI) | Node.js (Express)     |
| Event Store  | PostgreSQL       | Kafka                 |
| Job Queue    | Redis + BullMQ   | RabbitMQ              |
| Vector DB    | Milvus           | Pinecone, Weaviate    |
| Embeddings   | OpenAI           | sentence-transformers |
| LLM          | OpenAI GPT-4     | Google Gemini, Groq   |
| Frontend     | Next.js          | React + Vite          |
| Database     | PostgreSQL       | MongoDB               |
| Object Store | S3               | MinIO                 |
| Cache        | Redis            | Memcached             |

## 📊 Database Schema Overview

```sql
-- Core tables
commit_events       -- Event store
doc_nodes          -- Hierarchical docs
doc_overlays       -- Admin edits
changelogs         -- Generated changes

-- Vector DB (Milvus)
code_embeddings    -- Code snippets
doc_embeddings     -- Doc nodes
diff_embeddings    -- Commit diffs

-- Metadata
repositories       -- Repo config
users             -- User accounts
subscriptions     -- Billing
audit_logs        -- Security
```

## 🔐 Security & Access Control

### Authentication

- **Free tier**: No auth (public repos)
- **Team tier**: OAuth (GitHub, GitLab)
- **Enterprise**: SSO (SAML, OIDC)

### Authorization (RBAC)

```
Roles:
- viewer: Read docs
- editor: Edit overlays
- admin: Manage repos, users
- integrator: Configure webhooks, API keys
```

### API Security

- Rate limiting (per tier)
- Token-based auth (JWT)
- Webhook signature validation
- IP whitelisting (Enterprise)

## 💰 Subscription Model

### Free Tier

- 1 public repo
- Daily indexing
- Basic docs (no overlays)
- Community support
- 100 queries/day

### Team Tier ($49/month)

- 10 repos (public + private)
- Real-time indexing
- Admin overlays
- 5 team seats
- Priority support
- 10,000 queries/day
- SSO option

### Enterprise Tier (Custom)

- Unlimited repos
- On-premise deployment
- Fine-grained RBAC
- Audit logs
- SLA guarantees
- Dedicated support
- Unlimited queries
- Custom integrations

## 🎯 X-Factor vs GitBook/BookStack

| Feature         | lekhak ai           | GitBook    | BookStack  |
| --------------- | ------------------- | ---------- | ---------- |
| Code-first      | ✅ Auto-generated   | ❌ Manual  | ❌ Manual  |
| Commit tracking | ✅ Event store      | ❌ No      | ❌ No      |
| Versioning      | ✅ Per-commit       | ⚠️ Manual  | ❌ No      |
| AI Agent        | ✅ RAG + provenance | ❌ No      | ❌ No      |
| Changelog       | ✅ Auto-generated   | ❌ Manual  | ❌ Manual  |
| Admin overlays  | ✅ Non-code edits   | ❌ No      | ✅ Yes     |
| Hierarchical    | ✅ Deep nesting     | ⚠️ Limited | ⚠️ Limited |
| Semantic search | ✅ Vector DB        | ⚠️ Basic   | ⚠️ Basic   |
| Provenance      | ✅ Commit-backed    | ❌ No      | ❌ No      |

## 📈 Scalability Considerations

### Horizontal Scaling

- **Commit Bus**: Multiple consumers (consumer groups)
- **Doc Generator**: Worker pool (BullMQ concurrency)
- **Indexer**: Batch processing
- **Frontend**: CDN + edge caching

### Performance Targets

- Webhook processing: < 100ms
- Doc generation: < 30s per commit
- Query response: < 2s
- Indexing: < 5s per node

### Monitoring

- Event processing lag
- Queue depth
- LLM API latency
- Vector DB query time
- User query success rate

---

**Next Steps**: See `IMPLEMENTATION_PLAN.md` for detailed day-by-day tasks.
