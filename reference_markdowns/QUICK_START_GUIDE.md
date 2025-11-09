# 🚀 Quick Start Guide - @app Architecture

## 📍 START POINT

### Primary Entry: GitHub Webhook
```
POST /api/v1/webhooks/github
↓
app/webhooks/github.py → handle_github_webhook()
↓
CommitBusService.store_event() → Stores in commit_events table
```

### Secondary Entry: Manual Generation
```
POST /api/v1/documentation/generate
↓
app/api/v1/endpoints/documentation.py → generate_documentation()
↓
ManualDocGenerator.generate() → Generates docs on demand
```

### Background Worker: Event Consumer
```
python -m app.worker
↓
EventConsumerWorker.run() → Polls commit_events table
↓
process_event() → Calls smart_processor
```

---

## 🏁 END POINT

### Primary Destination: Docbook Repository
```
DocbookPublisher.publish_to_docbook()
↓
Clones org's docbook repo
↓
Checks out staging branch
↓
Syncs documentation files
↓
Commits and pushes to staging branch
↓
Records pending review in database
```

---

## 🔄 COMPLETE FLOW (Step by Step)

### 1. Webhook Receives Push Event
**File**: `app/webhooks/github.py`
- GitHub sends webhook to `/api/v1/webhooks/github`
- Signature verified using HMAC
- Event type extracted (push, installation, etc.)

### 2. Event Stored in Commit Bus
**File**: `app/services/commit_bus.py`
- `CommitBusService.store_event()` stores event in `commit_events` table
- Event marked as `processed = FALSE`
- Returns `event_id`

### 3. Worker Polls for Events
**File**: `app/worker.py`
- `EventConsumerWorker` polls `commit_events` table every 5 seconds
- Gets unprocessed events (limit: 100)
- For each event: converts to webhook payload format

### 4. Smart Processor Handles Event
**File**: `app/services/event/smart_processor.py`
- `handle_push_event()` is called with payload
- Clones repository to temp directory
- Checks out specific commit
- Analyzes changes using `smart_analyze_change()`

### 5. Documentation Generation
**File**: `app/services/documentation/comprehensive.py`
- `generate_smart_documentation()` orchestrates generation:
  - Summary (`summary.md`)
  - Architecture (`architecture/v1.X-architecture.md`)
  - Workflow (`workflow/v1.X-workflow.md`)
  - API (`api/v1.X-api.md`)
  - Change docs (`changes/`)
  - Changelog (`CHANGELOG.md`)
  - README updates
  - Migration guides

### 6. Quality Validation
**File**: `app/services/documentation/quality_integration.py`
- `validate_documentation_quality()` evaluates docs using LLM
- Writes quality report (`quality-report.json`)

### 7. Docbook Publishing
**File**: `app/services/docbook/publisher.py`
- `DocbookPublisher.publish_to_docbook()` publishes to docbook repo
- Gets writer token (GitHub App installation token)
- Clones docbook repository
- Checks out staging branch (creates if empty)
- Syncs documentation files
- Commits and pushes to staging branch
- Records pending review in database

### 8. Event Marked as Processed
**File**: `app/worker.py`
- Marks event as `processed = TRUE`
- Updates `processed_at` timestamp
- Logs completion

---

## 📊 KEY FILES SUMMARY

### Core Application
- `app/main.py` - FastAPI app initialization
- `app/worker.py` - Background event consumer
- `app/core/config.py` - Configuration settings

### Webhooks
- `app/webhooks/github.py` - GitHub webhook handler

### Event Processing
- `app/services/commit_bus.py` - Event storage
- `app/services/event/smart_processor.py` - Main event processor
- `app/services/event/service.py` - Event CRUD operations
- `app/services/event/processor.py` - Generic event processor (for events table)

### Documentation
- `app/services/documentation/comprehensive.py` - Core doc generation
- `app/services/documentation/change_docs.py` - Change documentation
- `app/services/documentation/quality_integration.py` - Quality validation
- `app/services/documentation/manual_generation.py` - Manual generation

### GitHub Services
- `app/services/github/service.py` - GitHub API operations
- `app/services/github/change_analysis.py` - Change analysis

### Docbook
- `app/services/docbook/publisher.py` - Docbook publishing

### LLM
- `app/services/llm/rotator.py` - LLM rotation
- `app/services/llm/llm_provider.py` - LLM provider interface

---

## 🗑️ FILES TO REMOVE

### Safe to Remove
1. `app/services/processor/` - Empty directory
2. `app/services/generator/` - Empty directory
3. `app/core/event_bus.py` - Unused EventBus system
4. `app/services/event/consumer.py` - Unused EventConsumer
5. `app/services/repos/service.py` - Empty file

### Run Cleanup
```bash
bash cleanup_unused_files.sh
```

---

## ✅ VERIFICATION

### Check Imports (After Cleanup)
```bash
# Should return no results
grep -r "from app.core.event_bus" app/
grep -r "from app.services.event.consumer" app/
grep -r "from app.services.repos.service" app/
```

### Test Flow
```bash
# 1. Start worker
python3 -m app.worker

# 2. Trigger webhook (in another terminal)
curl -X POST http://localhost:8000/api/v1/webhooks/github \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d @webhook_payload.json

# 3. Check worker logs for processing
```

---

## 📋 FILE USAGE TABLE (Quick Reference)

| File | Status | Used By |
|------|--------|---------|
| `app/worker.py` | ✅ Active | Standalone worker |
| `app/services/event/smart_processor.py` | ✅ Active | worker.py, processor.py |
| `app/services/commit_bus.py` | ✅ Active | webhooks/github.py |
| `app/services/documentation/comprehensive.py` | ✅ Active | smart_processor.py |
| `app/services/docbook/publisher.py` | ✅ Active | smart_processor.py |
| `app/core/event_bus.py` | ❌ Unused | None (remove) |
| `app/services/event/consumer.py` | ❌ Unused | None (remove) |
| `app/services/repos/service.py` | ❌ Unused | None (remove) |

---

## 🎯 KEY TAKEAWAYS

1. **Two Event Systems**:
   - `CommitBusService` + `worker.py`: Processes commit events (ACTIVE)
   - `EventProcessor` + `main.py`: Processes generic events (REVIEW)

2. **Documentation Generation**:
   - Automated: GitHub webhook → worker → smart_processor → comprehensive.py
   - Manual: API endpoint → manual_generation.py

3. **Docbook Publishing**:
   - Always publishes to `staging` branch
   - Records pending review in database
   - User can review & approve in frontend

4. **Quality Validation**:
   - Uses LLM to evaluate documentation quality
   - Writes quality report to repository

---

## 📚 Full Documentation

For detailed analysis, see:
- `CODEBASE_ANALYSIS.md` - Comprehensive analysis
- `CLEANUP_SUMMARY.md` - Cleanup recommendations

---

**Version**: 1.0
**Last Updated**: $(date)

