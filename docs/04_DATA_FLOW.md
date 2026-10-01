# DocIt AI — Event-Driven Data Flow

**Document:** 04  
**Audience:** Engineers, architects  
**Related:** `01_TECHNICAL_ARCHITECTURE.md`

This document traces the full lifecycle of a single commit event through DocIt AI.

---

## 1. Commit Arrives

```
Developer pushes to main
          │
          ▼
GitHub POSTs webhook ── HMAC-SHA256 verified
          │
          ▼
Extract push metadata (ref, before, after, pusher, files changed)
          │
          ▼
Upsert into commit_events:  status = "pending"  (ON CONFLICT push_id DO NOTHING)
```

**Why upsert?** GitHub may retry the webhook. The `push_id` is the idempotency key.

---

## 2. Worker Claims the Event

```
Event consumer polls every 5s:
  SELECT * FROM commit_events
   WHERE status = 'pending'
   ORDER BY created_at
   LIMIT 100
   FOR UPDATE SKIP LOCKED
```

Claimed events transition: `pending → processing` (set `locked_by` + `lock_expires_at`).

---

## 3. Smart Processor Runs

### Phase A — Discovery & Understanding

1. **Read repo** via Reader GitHub App (contents:read). Get tree of files.
2. **Discovery scanner** emits raw signals: ingress, egress, state, orchestrator, data flows.
3. **Semantic snapshot** extracts framework, API pattern, auth, data layer, deployment signals.
4. **Understanding builder** normalizes into a `system_model` struct.

### Phase B — LLM Planning

5. **Planning call**: "Based on this system model, what top-level documentation sections does this codebase need?"  
   → Adaptive section list (never a fixed template).

### Phase C — Per-Section Fan-Out

6. For each section:
   - Build focused evidence bundle (only files relevant to that section).
   - Construct LLM prompt with: persona rules, evidence, anti-hallucination constraints.
   - Fire async `complete()` via the LLM rotator (voice-locked to one provider/key).
   - Validate output: semantic rules (banned phrases, claimed tech must be in evidence).
   - Retry on failure with repair prompt.

### Phase D — Quality & Publish

7. **Post-generation LLM quality check** across the full doc set.
8. **Structural validation**: markdown headings hierarchy, no orphan nodes.
9. **Docbook publisher**: write to staging branch `docit/staging-<uuid>`, create `pending_doc_reviews` row.

---

## 4. Commit Event Resolved

```
commit_events.status → "completed"
processed_at set
```

If any section failed after retries, event → `failed` (3 attempts max), parked for inspection.

---

## 5. Pending Review → Merge

A human (or automation) inspects the staging branch via GitHub PR. On merge to `main`, the `pending_doc_reviews` row is marked `merged`, and the live docbook tree is updated.

---

## 6. Overlay Integration

Admin edits made via the overlay system are merged into the doc tree before generation. When the next commit event is processed:

- Overlays are applied on top of generated docs.
- Overlay edits retain full provenance (author, reason, timestamp) in `doc_overlay_history`.
- Status lifecycle: `active → pr_created → merged` / `archived`.

---

## 7. Startup Recovery (Missed Commits)

On worker boot:

```
for each org_registration:
  for each repo in org:
    query GitHub API: list commits since repo.last_processed_sha
    for each commit not in commit_events:
      insert (status = "pending")
```

This guarantees zero data loss from downtime windows.

---

## 8. Feedback-Loop Guard

The publisher tags its own commits with the docbook bot identity. The event consumer ignores commits authored by the bot, so publishing docs never triggers another generation cycle.

---

## 9. End-to-End Timing

| Phase | Typical Latency |
|---|---|
| Webhook → DB commit | < 200ms |
| Poll → Claim | ≤ 5s |
| Discovery + Understanding | 1–3s |
| LLM Planning | 2–5s |
| Per-Section Fan-Out (N sections) | 10–30s |
| Quality + Publish | 5–10s |
| **Total (wall clock)** | **~30–60s** |

---

## 10. Failure Modes & Recovery

| Failure | Handling |
|---|---|
| Webhook signature mismatch | 401, no side effects |
| Duplicate push (idempotent) | Ignored |
| LLM 429/500 | Retry with different key, 3 global attempts |
| GitHub API rate limit | Backoff + jitter |
| Worker crash mid-processing | Lock expiry → another worker claims |
| Poison event (3 failures) | Parked in `failed`, inspected manually |
