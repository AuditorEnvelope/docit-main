# 🎓 lekhak ai - Complete Explanation

## What Am I Building?

I'm transforming your DocAI into **lekhak ai** - a production-grade, AI-first documentation platform that's **commit-accurate** and **code-first**.

## 🎯 The Big Picture

### Current State (DocAI)

```
GitHub Push → Webhook → Process Immediately → Generate Docs
                ↓
        If server is down → COMMITS ARE LOST! ❌
```

**Problems:**

- ❌ Commits lost during downtime
- ❌ Flat documentation structure
- ❌ No way to ask "what changed?"
- ❌ Can't edit docs without changing code
- ❌ Not productized

### New State (lekhak ai)

```
GitHub Push → Commit Bus (Event Store) → Queue → Process → Generate Docs
                ↓                          ↓
        Always stored ✅            Replay capability ✅
```

**Solutions:**

- ✅ **Never lose commits** (event store)
- ✅ **Deep hierarchy** (SDK→Module→Feature→Function)
- ✅ **AI Agent** answers with commit evidence
- ✅ **Admin overlays** for non-code edits
- ✅ **Subscription model** for monetization

---

## 🏗️ Architecture Breakdown

### 1. Commit Bus (Event Store)

**What**: Durable storage for every commit event

**Why**: Your current system processes commits immediately. If the server is down for 10 minutes and 5 commits happen, those 5 commits are LOST forever.

**How it works**:

```
1. GitHub webhook arrives
   ↓
2. FIRST: Store in commit_events table (PostgreSQL)
   ↓
3. THEN: Process (can happen later)
   ↓
4. If server was down, on restart:
   - Find all unprocessed events
   - Process them in order
   - No commits lost!
```

**Files**:

- `src/commit_bus.py` - Service to store/retrieve events
- `src/event_consumer.py` - Worker that processes events
- `schema.sql` - Database table `commit_events`

**Example**:

```python
# Webhook arrives
event = CommitEvent(
    repo_id="AuditorEnvelope/lekhak_ai",
    commit_sha="abc123",
    author_name="Harsh",
    timestamp="2025-10-15T21:00:00Z",
    files_changed=[{"path": "src/app.py", "status": "modified"}]
)

# Store it (ALWAYS succeeds, even if processing fails)
await bus.store_event(event)

# Later, consumer processes it
events = await bus.get_unprocessed_events()
for event in events:
    process(event)  # Your existing smart_processor
    mark_processed(event)
```

---

### 2. Hierarchical Documentation

**What**: Deep tree structure instead of flat files

**Why**: Current docs are flat (api.md, architecture.md). Real SDKs have deep structure:

```
Payment SDK
  ├─ Core Module
  │   ├─ Create Feature
  │   │   ├─ create() function
  │   │   ├─ createBatch() function
  │   │   └─ createRecurring() function
  │   └─ Update Feature
  │       ├─ update() function
  │       └─ cancel() function
  └─ Webhooks Module
      └─ ...
```

**How it works**:

```
1. Parse codebase (TypeScript, Python, etc.)
   ↓
2. Build tree structure
   - Detect SDKs (top-level directories)
   - Find modules (subdirectories)
   - Group functions into features
   - Extract function signatures
   ↓
3. Store in doc_nodes table (hierarchical)
   - Each node has parent_id
   - Can traverse up (breadcrumb) or down (children)
   ↓
4. Generate descriptions with LLM
   - Function purpose
   - Parameter explanations
   - Examples
```

**Database Structure**:

```sql
doc_nodes:
  id: uuid
  type: "sdk" | "module" | "feature" | "function"
  title: "Payment SDK"
  path: "/payment-sdk/core/create"
  parent_id: uuid (reference to parent)
  content: {
    signature: "function create(options: PaymentOptions): Promise<Payment>",
    description: "Creates a new payment...",
    parameters: [...],
    examples: [...]
  }
```

**Example**:

```typescript
// Code in repo
export async function createPayment(
  options: PaymentOptions
): Promise<Payment> {
  // ...
}

// Generated doc node
{
  id: "uuid-123",
  type: "function",
  title: "createPayment",
  path: "/payment-sdk/core/createPayment",
  parent_id: "uuid-parent",
  content: {
    signature: "function createPayment(options: PaymentOptions): Promise<Payment>",
    description: "Creates a new payment with the specified options. Returns a Promise that resolves to the created Payment object.",
    parameters: [
      {
        name: "options",
        type: "PaymentOptions",
        required: true,
        description: "Configuration for the payment including amount, currency, and customer details"
      }
    ],
    returns: {
      type: "Promise<Payment>",
      description: "The created payment object with ID and status"
    },
    examples: [
      {
        title: "Basic payment",
        code: "const payment = await createPayment({ amount: 1000, currency: 'USD' })",
        language: "typescript"
      }
    ]
  }
}
```

---

### 3. RAG Agent (Retrieval-Augmented Generation)

**What**: AI that answers questions with commit-backed evidence

**Why**: Users want to ask:

- "What changed in Payment.create between v2.0 and v2.1?"
- "How do I use the new timeout parameter?"
- "Why was this function deprecated?"

Current system can't answer these.

**How it works**:

```
1. User asks question
   ↓
2. Generate embedding (vector) of question
   ↓
3. Search vector DB (Milvus) for similar docs/code
   ↓
4. Retrieve top-k results with metadata:
   - Doc content
   - Commit SHA
   - File path
   - Author
   - Timestamp
   ↓
5. LLM generates answer using retrieved context
   ↓
6. Return answer + provenance (citations)
```

**Components**:

- **Vector DB** (Milvus): Stores embeddings of docs/code
- **Indexer**: Generates embeddings and stores them
- **Agent**: Retrieves + generates answers

**Example**:

```python
# User query
query = "What changed in Payment.create between v2.0 and v2.1?"

# Agent processes
results = await indexer.search(query, top_k=5)
# Results: [
#   {content: "Added timeout parameter...", commit_sha: "abc123", file: "payment.ts"},
#   {content: "Updated examples...", commit_sha: "abc123", file: "examples.md"}
# ]

# LLM generates answer
answer = await agent.query(query)
# Answer:
# "In v2.1, the Payment.create function added a new `timeout` parameter
#  (default: 30 seconds). This allows you to specify how long to wait
#  for payment confirmation.
#
#  Source: commit abc123 by harsh@example.com on 2025-10-14
#  File: src/payment/create.ts:45-52"
```

---

### 4. Admin Overlays

**What**: Edit docs without changing code

**Why**: Sometimes you need to:

- Add warnings ("This is deprecated, use X instead")
- Fix typos in generated descriptions
- Add clarifications
- But you don't want to change the actual code

**How it works**:

```
1. Admin opens doc in UI
   ↓
2. Clicks "Edit" → WYSIWYG editor
   ↓
3. Makes changes
   ↓
4. Saves → stored in doc_overlays table
   ↓
5. When rendering docs:
   - Fetch base doc (generated from code)
   - Fetch overlay (admin edits)
   - Merge: overlay overrides base
   - Show with provenance badge:
     "Edited by admin@example.com on 2025-10-15"
```

**Database**:

```sql
doc_overlays:
  id: uuid
  node_id: uuid (reference to doc_nodes)
  content: {description: "NEW DESCRIPTION", warning: "DEPRECATED"}
  author_name: "admin@example.com"
  status: "active"
  created_at: timestamp
```

**Example**:

```
Base doc (generated from code):
{
  description: "Creates a payment"
}

Overlay (admin edit):
{
  description: "Creates a payment. ⚠️ WARNING: This method is deprecated. Use createPaymentV2 instead.",
  deprecation_notice: "Will be removed in v3.0"
}

Merged doc (shown to users):
{
  description: "Creates a payment. ⚠️ WARNING: This method is deprecated. Use createPaymentV2 instead.",
  deprecation_notice: "Will be removed in v3.0",
  _provenance: {
    edited_by: "admin@example.com",
    edited_at: "2025-10-15T21:00:00Z",
    original_available: true
  }
}
```

---

### 5. Subscription Model

**What**: Pricing tiers with feature gates

**Why**: To monetize the product

**Tiers**:

| Feature        | Free     | Team ($49/mo)         | Enterprise (Custom) |
| -------------- | -------- | --------------------- | ------------------- |
| Repos          | 1 public | 10 (public + private) | Unlimited           |
| Indexing       | Daily    | Real-time             | Real-time           |
| Queries/day    | 100      | 10,000                | Unlimited           |
| Admin overlays | ❌       | ✅                    | ✅                  |
| Team seats     | 1        | 5                     | Unlimited           |
| SSO            | ❌       | Optional              | ✅                  |
| Audit logs     | ❌       | ❌                    | ✅                  |
| On-premise     | ❌       | ❌                    | ✅                  |

**How it works**:

```python
# Check if user can use feature
async def check_feature(user_id: str, feature: str) -> bool:
    subscription = await get_subscription(user_id)
    plan = PLANS[subscription.plan]
    return plan.get(feature, False)

# Example
if await check_feature(user_id, "overlays"):
    # Allow admin edit
else:
    # Show upgrade message
```

---

## 📊 Data Flow Example

### Complete Flow: Commit → Docs → Query

```
1. Developer pushes commit abc123
   ↓
2. GitHub webhook → POST /webhook
   ↓
3. Commit Bus stores event in commit_events table
   {
     event_id: "uuid-1",
     repo_id: "AuditorEnvelope/lekhak_ai",
     commit_sha: "abc123",
     files_changed: [{"path": "src/payment.ts", "status": "modified"}],
     processed: false
   }
   ↓
4. Event Consumer picks up event
   ↓
5. Doc Generator processes:
   - Clones repo at abc123
   - Parses TypeScript files
   - Builds doc tree
   - Generates descriptions with LLM
   - Stores in doc_nodes table
   ↓
6. Indexer creates embeddings:
   - Generates vector for each doc node
   - Stores in Milvus (vector DB)
   - Stores metadata in embeddings_metadata table
   ↓
7. Changelog Generator:
   - Compares with previous version
   - Generates human-readable summary
   - Stores in changelogs table
   ↓
8. Mark event as processed
   ↓
9. User visits Pustak → sees new docs
   ↓
10. User asks: "What changed in Payment.create?"
    ↓
11. Agent:
    - Searches vector DB
    - Retrieves relevant docs + diffs
    - LLM generates answer with citations
    - Returns: "Added timeout parameter (commit abc123)"
```

---

## 🔧 What I've Built So Far

### ✅ Completed Files

1. **`LEKHAK_ai_ARCHITECTURE.md`**

   - Complete system architecture
   - Component diagrams
   - Tech stack decisions

2. **`IMPLEMENTATION_PLAN.md`**

   - 5-day sprint plan
   - Day-by-day tasks
   - Acceptance criteria

3. **`schema.sql`**

   - Complete database schema
   - 10 tables (commit_events, doc_nodes, overlays, etc.)
   - Indexes, views, functions, triggers

4. **`src/commit_bus.py`**

   - FastAPI service for event store
   - Store/retrieve/replay events
   - API endpoints

5. **`src/event_consumer.py`**
   - Worker that processes events
   - Batch processing
   - Retry logic
   - Graceful shutdown

---

## 🚀 Next Steps

### To Complete Day 1 (Commit Bus):

1. **Setup PostgreSQL**

   ```bash
   # Install PostgreSQL
   brew install postgresql

   # Start PostgreSQL
   brew services start postgresql

   # Create database
   createdb lekhak_ai

   # Run schema
   psql lekhak_ai < schema.sql
   ```

2. **Update requirements.txt**

   ```
   asyncpg==0.29.0
   ```

3. **Update .env**

   ```
   DATABASE_URL=postgresql://localhost/lekhak_ai
   ```

4. **Test Commit Bus**

   ```bash
   # Terminal 1: Start Commit Bus service
   cd src
   python commit_bus.py

   # Terminal 2: Start Event Consumer
   python event_consumer.py

   # Terminal 3: Send test event
   curl -X POST http://localhost:8001/events \
     -H "Content-Type: application/json" \
     -d '{
       "repo_id": "test/repo",
       "commit_sha": "abc123",
       "parent_sha": [],
       "author_name": "Test",
       "author_email": "test@example.com",
       "timestamp": "2025-10-15T21:00:00Z",
       "branch": "main",
       "files_changed": [],
       "commit_message": "Test commit"
     }'

   # Check if processed
   curl http://localhost:8001/stats
   ```

5. **Integration Test**
   ```bash
   # Stop event consumer
   # Make 5 test commits (via API)
   # Start event consumer
   # Verify all 5 are processed
   ```

---

## 💡 Key Concepts Explained

### Event Sourcing

Instead of processing events immediately, we **store them first**. This gives us:

- **Replay capability**: Reprocess events after code changes
- **Audit trail**: Complete history of all commits
- **Reliability**: Never lose data during downtime

### Hierarchical Data

Tree structure allows:

- **Navigation**: Breadcrumbs, parent/child links
- **Organization**: Logical grouping (SDK→Module→Feature)
- **Scalability**: Can have unlimited depth

### Vector Embeddings

Convert text to numbers (vectors) so we can:

- **Semantic search**: Find similar content (not just keyword matching)
- **Context retrieval**: Get relevant docs for LLM
- **Provenance**: Track where information came from

### Overlay Pattern

Separate **generated** content from **edited** content:

- **Generated**: Always in sync with code
- **Edited**: Human additions/corrections
- **Merged**: Best of both worlds

---

## 🎯 X-Factor (Why This Beats GitBook)

| Feature              | lekhak ai             | GitBook         |
| -------------------- | --------------------- | --------------- |
| **Source of truth**  | Code (auto-generated) | Manual markdown |
| **Accuracy**         | Always in sync        | Can be outdated |
| **Commit tracking**  | Every commit stored   | No tracking     |
| **Versioning**       | Per-commit            | Manual          |
| **AI Agent**         | Answers with evidence | No AI           |
| **Change detection** | Automatic diffs       | Manual          |
| **Hierarchy**        | Deep (unlimited)      | Limited         |
| **Provenance**       | Commit SHA + author   | None            |

---

## 📚 Resources

- **Architecture**: `LEKHAK_ai_ARCHITECTURE.md`
- **Implementation**: `IMPLEMENTATION_PLAN.md`
- **Database**: `schema.sql`
- **Code**: `src/commit_bus.py`, `src/event_consumer.py`

---

**Questions? Let me know what you want me to build next!** 🚀
