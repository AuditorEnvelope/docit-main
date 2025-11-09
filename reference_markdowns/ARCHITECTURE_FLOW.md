# 🏗️ Architecture Flow - Processor vs Smart Processor

## 📊 VISUAL FLOW DIAGRAM

### **PRIMARY FLOW (Active - Worker.py)**
```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Webhook (Push Event)                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/webhooks/github.py                                          │
│ - Verifies HMAC signature                                       │
│ - Extracts event data                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/services/commit_bus.py (CommitBusService)                   │
│ - Stores event in commit_events table                           │
│ - Event marked as processed = FALSE                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/worker.py (EventConsumerWorker)                             │
│ - Polls commit_events table (every 5 seconds)                  │
│ - Gets unprocessed events                                       │
│ - Converts to webhook payload format                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/services/event/smart_processor.py                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ handle_push_event(payload, github_token, doc_persona)      │ │
│ │                                                             │ │
│ │ 1. Clone repository to temp directory                       │ │
│ │ 2. Checkout specific commit                                 │ │
│ │ 3. Analyze changes (smart_analyze_change)                  │ │
│ │ 4. Generate documentation (generate_smart_documentation)    │ │
│ │ 5. Validate quality (validate_documentation_quality)        │ │
│ │ 6. Publish to docbook (DocbookPublisher.publish_to_docbook)│ │
│ └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/services/docbook/publisher.py                               │
│ - Clones docbook repository                                     │
│ - Checks out staging branch                                     │
│ - Syncs documentation files                                     │
│ - Commits and pushes to staging branch                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ worker.py                                                        │
│ - Marks event as processed = TRUE                               │
│ - Updates processed_at timestamp                                │
└─────────────────────────────────────────────────────────────────┘
```

---

### **SECONDARY FLOW (Optional - Main.py Background Processor)**
```
┌─────────────────────────────────────────────────────────────────┐
│ API Endpoint or Webhook                                         │
│ - Creates Event in events table                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/main.py (Background Processor)                              │
│ - Polls events table (if ENABLE_EVENT_PROCESSOR=True)          │
│ - Gets pending events                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/services/event/processor.py (EventProcessor)                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ EventProcessor.process(event: Event)                        │ │
│ │                                                             │ │
│ │ 1. Routes to handler based on event type                   │ │
│ │ 2. Resolves GitHub App installation ID                     │ │
│ │ 3. Resolves doc_persona                                    │ │
│ │ 4. Gets reader token                                       │ │
│ │ 5. Converts Event model to webhook payload                 │ │
│ │ 6. Calls smart_processor.handle_push_event()               │ │
│ └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ app/services/event/smart_processor.py                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ handle_push_event(payload, github_token, doc_persona)      │ │
│ │                                                             │ │
│ │ [Same as PRIMARY FLOW - does all the actual work]          │ │
│ └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ EventProcessor                                                   │
│ - Updates event status in events table                          │
│ - Marks as COMPLETED or FAILED                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 KEY DIFFERENCES

### **1. Event Storage**

| Flow | Database Table | Model |
|------|----------------|-------|
| **PRIMARY** | `commit_events` | Raw event data (dict) |
| **SECONDARY** | `events` | `Event` model (SQLAlchemy) |

### **2. Worker**

| Flow | Worker | Location |
|------|--------|----------|
| **PRIMARY** | `EventConsumerWorker` | `app/worker.py` |
| **SECONDARY** | `run_event_processor()` | `app/main.py` |

### **3. Processor**

| Flow | Processor | Purpose |
|------|-----------|---------|
| **PRIMARY** | `smart_processor.handle_push_event()` | Direct call - does all work |
| **SECONDARY** | `EventProcessor.process()` → `smart_processor.handle_push_event()` | Wrapper that calls smart_processor |

### **4. When Active**

| Flow | Condition | Default |
|------|-----------|---------|
| **PRIMARY** | Always (worker.py runs independently) | ✅ **ACTIVE** |
| **SECONDARY** | If `ENABLE_EVENT_PROCESSOR=True` | ⚠️ **OPTIONAL** (default: True) |

---

## 💡 WHY TWO SYSTEMS?

### **Primary Flow (worker.py)**
- **Purpose**: Process GitHub webhook events
- **Database**: `commit_events` table (dedicated for commit events)
- **Worker**: Standalone worker process (`python -m app.worker`)
- **Advantages**: 
  - Dedicated worker process
  - Can scale independently
  - Handles commit events specifically

### **Secondary Flow (main.py)**
- **Purpose**: Process generic events (not just commits)
- **Database**: `events` table (generic event storage)
- **Worker**: Background task in main FastAPI app
- **Advantages**:
  - Can handle multiple event types (push, installation, etc.)
  - Integrated with FastAPI app
  - Can process events from API endpoints

### **Common Ground**
- **Both eventually call `smart_processor.handle_push_event()`**
- **Both use the same core documentation generation logic**
- **Both publish to docbook repository**

---

## 🎯 RECOMMENDATION

### **For Production**
1. ✅ **Use PRIMARY FLOW** (worker.py) - This is the main flow for GitHub webhooks
2. ⚠️ **Secondary flow is optional** - Only needed if you want to process generic events from API
3. ✅ **Keep both** - They serve different purposes but use the same core logic

### **For Cleanup**
1. ✅ **Keep `smart_processor.py`** - Core logic, used by both flows
2. ⚠️ **Review `processor.py`** - Only needed if `events` table is used in production
3. ✅ **If `events` table is not used**, you can disable `ENABLE_EVENT_PROCESSOR` and remove `processor.py`

---

## 📋 VERIFICATION CHECKLIST

### **Primary Flow (worker.py)**
- [x] ✅ `worker.py` exists and runs
- [x] ✅ `commit_events` table exists
- [x] ✅ `smart_processor.handle_push_event()` is called
- [x] ✅ Documentation is generated and published

### **Secondary Flow (main.py)**
- [x] ✅ `processor.py` exists
- [ ] ⚠️ `events` table is used in production (verify)
- [x] ✅ `ENABLE_EVENT_PROCESSOR` is configurable
- [x] ✅ `EventProcessor` calls `smart_processor.handle_push_event()`

### **Dependencies**
- [x] ✅ No imports from `@src`
- [x] ✅ `@app` is completely independent
- [x] ✅ All core logic is in `@app`

---

**Generated**: $(date)
**Version**: 1.0

