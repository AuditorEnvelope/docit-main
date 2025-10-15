# lekhak ai - 5-Day Implementation Plan

## Day 1: Commit Bus + Event Store

**Goal**: Reliable commit tracking with replay

### Tasks

1. Add PostgreSQL schema for `commit_events` table
2. Create `src/commit_bus.py` service
3. Update webhook handler to store events first
4. Build event consumer worker
5. Add backfill/replay endpoints

**Acceptance**: 5 commits while offline → all processed on restart

## Day 2: Hierarchical Doc Generation

**Goal**: Deep structure (SDK→Module→Feature→Function)

### Tasks

1. Add `doc_nodes` schema (hierarchical)
2. Create `src/hierarchical_doc_generator.py`
3. Build TypeScript parser
4. Implement tree builder
5. Generate LLM descriptions

**Acceptance**: Sample SDK → nested docs with examples

## Day 3: RAG System + Agent

**Goal**: Semantic search with provenance

### Tasks

1. Setup Milvus vector DB
2. Create `src/indexer_service.py`
3. Build embedding generation
4. Implement `src/agent_service.py`
5. Add provenance tracking

**Acceptance**: "What changed?" → answer with commit SHA

## Day 4: Admin Overlay System

**Goal**: Non-code edits with provenance

### Tasks

1. Add `doc_overlays` schema
2. Create `src/overlay_service.py`
3. Build merge logic
4. Add edit UI in Pustak
5. Optional: PR generation

**Acceptance**: Admin edit → displayed with provenance

## Day 5: Subscription Model

**Goal**: Productization ready

### Tasks

1. Add `subscriptions` schema
2. Create `src/subscription_service.py`
3. Implement feature gates
4. Document pricing tiers
5. Add GTM strategy

**Acceptance**: Feature gates work per plan

---

See `LEKHAK_ai_ARCHITECTURE.md` for detailed architecture.
