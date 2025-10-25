# 🗺️ COMPLETE ROADMAP - Deep Dive → Cleanup → Restructure → Multi-Org

## **EXECUTIVE SUMMARY**

You have 25 Python files in `/src`. Here's what we're doing:

1. **PHASE 1: DEEP DIVE** ✅ COMPLETE
   - Analyzed every file
   - Identified what's used vs unused
   - Found 6 files to delete
   - Found structure issues

2. **PHASE 2: CLEANUP & RESTRUCTURE** ⏳ READY
   - Delete 6 unused files
   - Create 5 folders
   - Move 19 files to folders
   - Update 9 files with new imports
   - Time: ~1 hour

3. **PHASE 3: MULTI-ORG IMPLEMENTATION** ⏳ NEXT
   - Database schema
   - Webhook registration
   - Event consumer integration
   - Missed commits detection
   - Time: 8-12 hours

---

## **PHASE 1: DEEP DIVE ANALYSIS ✅ COMPLETE**

### **Key Findings**

**Files to DELETE (6 files):**
- ❌ webhook_handler.py - Old, replaced by webhook_multi_org.py
- ❌ hierarchical_doc_generator.py - Disabled, causing issues
- ❌ agent_service.py - Unused
- ❌ indexer_service.py - Unused
- ❌ lekhak_ai_integration.py - Unused
- ❌ pustak_integration.py - Unused

**Files to KEEP (19 files):**

**CORE (6 files):**
- ✅ main.py - FastAPI server
- ✅ commit_bus.py - Event store
- ✅ event_consumer.py - Event processor
- ✅ webhook_multi_org.py - Webhook handler
- ✅ auth_service.py - Authentication
- ✅ subscription_service.py - Billing

**PROCESSORS (3 files):**
- ✅ smart_processor.py - Doc generation orchestration
- ✅ comprehensive_doc_generator.py - Main doc generator
- ✅ quality_integration.py - Quality integration

**SERVICES (3 files):**
- ✅ stripe_service.py - Stripe API
- ✅ overlay_service.py - UI overlays

**UTILITIES (7 files):**
- ✅ github_sync.py - Missed commits detection
- ✅ github_app.py - GitHub App JWT
- ✅ quality_checker.py - Quality validation
- ✅ universal_code_parser.py - Code parsing
- ✅ canonical_model.py - Data models
- ✅ llm_provider_v2.py - LLM provider
- ✅ doc_generation_endpoint.py - Doc endpoint

**REFERENCE (1 file):**
- ⏳ event_consumer_multi_org.py - Keep for Phase 4 integration

### **Critical Issues Found**

1. **Missed Commits Detection is BROKEN**
   - `event_consumer.py` line 254-269
   - Hardcoded to only check "AuditorEnvelope/lekhak_ai"
   - Doesn't check other orgs
   - ❌ NEEDS FIX: Implement check_missed_commits_all_orgs()

2. **Multi-Org Support NOT Integrated**
   - `event_consumer_multi_org.py` has the code
   - But it's NOT integrated into `event_consumer.py`
   - ❌ NEEDS INTEGRATION: Phase 4

3. **Files Not Organized**
   - All 19 files in one directory
   - Hard to navigate
   - ✅ WILL FIX: Phase 2 restructure

---

## **PHASE 2: CLEANUP & RESTRUCTURE ⏳ READY**

### **Step 1: Delete 6 Unused Files (5 minutes)**

```bash
rm src/webhook_handler.py
rm src/agent_service.py
rm src/indexer_service.py
rm src/lekhak_ai_integration.py
rm src/pustak_integration.py
rm src/hierarchical_doc_generator.py
```

### **Step 2: Create Folder Structure (5 minutes)**

```
src/
├─ core/                    (4 files)
├─ processors/              (3 files)
├─ services/                (4 files)
├─ utilities/               (7 files)
└─ reference/               (1 file)
```

### **Step 3: Move Files to Folders (10 minutes)**

See CLEANUP_AND_RESTRUCTURE_PLAN.md for exact commands

### **Step 4: Update Imports (30 minutes)**

Update 9 files with new import paths:
- main.py
- event_consumer.py
- smart_processor.py
- comprehensive_doc_generator.py
- quality_integration.py
- subscription_service.py
- And others

### **Result After Phase 2**

```
✅ Clean, organized structure
✅ 6 unused files deleted
✅ 19 files organized into 5 folders
✅ All imports updated
✅ System still works
✅ Ready for Phase 3
```

---

## **PHASE 3: MULTI-ORG IMPLEMENTATION ⏳ NEXT**

### **What We're Fixing**

**Current Problem:**
- Webhook works for any org (GitHub sends data)
- Missed commits only work for PUSTAK's repo (hardcoded)
- Multi-org token support not integrated
- Server downtime recovery broken for other orgs

**After Implementation:**
- ✅ Webhook works for any org
- ✅ Missed commits work for ALL orgs
- ✅ Each org uses their own token
- ✅ Server downtime recovery works for 1000+ orgs

### **8 Implementation Phases**

| Phase | Task | Time | Files |
|-------|------|------|-------|
| 1 | Database schema | 1h | schema.sql |
| 2 | Webhook registration endpoint | 2h | core/main.py |
| 3 | Multi-org webhook handler | 1h | core/webhook_multi_org.py (verify) |
| 4 | Event consumer integration | 2h | core/event_consumer.py |
| 5 | Smart processor update | 1h | processors/smart_processor.py |
| 6 | Missed commits detection | 2h | core/event_consumer.py |
| 7 | Testing | 2h | Test scripts |
| 8 | Cleanup & docs | 1h | Documentation |
| **TOTAL** | | **12h** | |

### **Phase 3 Detailed Steps**

#### **Phase 3.1: Database Schema (1 hour)**

Create tables:
```sql
CREATE TABLE org_webhooks (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    org_id VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255) UNIQUE,
    github_token_id UUID NOT NULL,
    registered_at TIMESTAMP,
    UNIQUE(user_id, org_id)
);

CREATE TABLE user_github_tokens (
    token_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    org_id VARCHAR(255),
    github_token TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP
);

ALTER TABLE commit_events
ADD COLUMN user_id UUID,
ADD COLUMN org_id VARCHAR(255),
ADD COLUMN github_token_id UUID;
```

#### **Phase 3.2: Webhook Registration (2 hours)**

Add endpoint to `core/main.py`:
```python
@app.post("/webhook/register")
async def register_webhook(request: WebhookRegisterRequest, user = Depends(get_current_user)):
    """Register webhook for an organization"""
    # Generate webhook_secret
    # Store org context
    # Return webhook URL
```

#### **Phase 3.3: Multi-Org Webhook Handler (1 hour)**

Verify `core/webhook_multi_org.py`:
```python
async def webhook_multi_org(...):
    # Try to find org from signature
    # Fall back to env var
    # Verify signature
    # Add context to payload
```

#### **Phase 3.4: Event Consumer Integration (2 hours)**

Update `core/event_consumer.py`:
```python
async def get_github_token(self, user_id: str, token_id: str):
    """Get org's GitHub token from DB"""
    # Query user_github_tokens table
    # Return token

async def process_event(self, event: dict):
    """Process event with org's token"""
    # Extract user_id, org_id, token_id
    # Get org's token
    # Pass to smart_processor
```

#### **Phase 3.5: Smart Processor Update (1 hour)**

Update `processors/smart_processor.py`:
```python
def handle_push_event(payload, github_token=None):
    """Use provided token or fall back to env var"""
    if not github_token:
        github_token = os.getenv("GITHUB_TOKEN")
    # Rest of logic uses github_token
```

#### **Phase 3.6: Missed Commits Detection (2 hours)**

Update `core/event_consumer.py`:
```python
async def check_missed_commits_all_orgs(self):
    """Check for missed commits across ALL orgs"""
    # Get all unique (org_id, repo_id) pairs
    # For each org:
    #   - Get org's token
    #   - Query GitHub for that org's repo
    #   - Store missed commits
```

#### **Phase 3.7: Testing (2 hours)**

Test with:
- Company A (new org)
- Company B (new org)
- Server downtime scenarios
- 10+ orgs

#### **Phase 3.8: Cleanup & Docs (1 hour)**

- Delete `reference/event_consumer_multi_org.py`
- Update documentation
- Create migration guide

---

## **TIMELINE**

```
Phase 1: Deep Dive Analysis
├─ Status: ✅ COMPLETE
└─ Time: 3 hours (already done)

Phase 2: Cleanup & Restructure
├─ Status: ⏳ READY
├─ Time: ~1 hour
└─ Start: After your approval

Phase 3: Multi-Org Implementation
├─ Status: ⏳ NEXT
├─ Time: 12 hours
└─ Start: After Phase 2 complete

TOTAL TIME: ~16 hours
```

---

## **WHAT YOU GET**

### **After Phase 2 (Clean Code)**
- ✅ 6 unused files deleted
- ✅ 19 files organized into 5 folders
- ✅ Clear separation of concerns
- ✅ Easy to navigate
- ✅ Easy to maintain

### **After Phase 3 (Multi-Org Support)**
- ✅ Webhook works for ANY org
- ✅ Missed commits work for ALL orgs
- ✅ Each org uses their own token
- ✅ Server downtime recovery works
- ✅ Scales to 1000+ orgs
- ✅ Enterprise-ready

---

## **DECISION NEEDED**

**Should I proceed with Phase 2 (Cleanup & Restructure)?**

If YES:
1. I'll delete 6 unused files
2. Create 5 folders
3. Move 19 files
4. Update all imports
5. Verify everything works
6. Then start Phase 3

**Shall I proceed?** 🚀

---

## **DOCUMENTS CREATED**

1. ✅ PHASE1_DEEP_DIVE_ANALYSIS.md - Detailed analysis of all 25 files
2. ✅ CLEANUP_AND_RESTRUCTURE_PLAN.md - Exact steps for Phase 2
3. ✅ COMPLETE_ROADMAP.md - This document

---

## **NEXT ACTIONS**

1. **Review** PHASE1_DEEP_DIVE_ANALYSIS.md
2. **Review** CLEANUP_AND_RESTRUCTURE_PLAN.md
3. **Approve** Phase 2 execution
4. **Wait** for Phase 2 to complete
5. **Start** Phase 3 (Multi-Org Implementation)

---

**Ready to clean up and restructure?** 🧹✨
