# 🧹 CLEANUP & RESTRUCTURE PLAN

## **PHASE 1B: DELETE UNUSED FILES (5 minutes)**

```bash
# Files to DELETE (completely unused)
rm /Users/harshsrivastava/Desktop/doc_ai/src/webhook_handler.py
rm /Users/harshsrivastava/Desktop/doc_ai/src/agent_service.py
rm /Users/harshsrivastava/Desktop/doc_ai/src/indexer_service.py
rm /Users/harshsrivastava/Desktop/doc_ai/src/lekhak_ai_integration.py
rm /Users/harshsrivastava/Desktop/doc_ai/src/pustak_integration.py
rm /Users/harshsrivastava/Desktop/doc_ai/src/hierarchical_doc_generator.py

# Files to KEEP (will integrate later)
# event_consumer_multi_org.py - Keep until Phase 4 integration
```

**Result:** 6 files deleted, 19 files remain

---

## **PHASE 1C: RESTRUCTURE INTO FOLDERS (30 minutes)**

### **Step 1: Create folder structure**

```bash
mkdir -p /Users/harshsrivastava/Desktop/doc_ai/src/core
mkdir -p /Users/harshsrivastava/Desktop/doc_ai/src/processors
mkdir -p /Users/harshsrivastava/Desktop/doc_ai/src/services
mkdir -p /Users/harshsrivastava/Desktop/doc_ai/src/utilities
mkdir -p /Users/harshsrivastava/Desktop/doc_ai/src/reference
```

### **Step 2: Move files to folders**

```bash
# CORE
mv /Users/harshsrivastava/Desktop/doc_ai/src/main.py /Users/harshsrivastava/Desktop/doc_ai/src/core/
mv /Users/harshsrivastava/Desktop/doc_ai/src/commit_bus.py /Users/harshsrivastava/Desktop/doc_ai/src/core/
mv /Users/harshsrivastava/Desktop/doc_ai/src/event_consumer.py /Users/harshsrivastava/Desktop/doc_ai/src/core/
mv /Users/harshsrivastava/Desktop/doc_ai/src/webhook_multi_org.py /Users/harshsrivastava/Desktop/doc_ai/src/core/

# PROCESSORS
mv /Users/harshsrivastava/Desktop/doc_ai/src/smart_processor.py /Users/harshsrivastava/Desktop/doc_ai/src/processors/
mv /Users/harshsrivastava/Desktop/doc_ai/src/comprehensive_doc_generator.py /Users/harshsrivastava/Desktop/doc_ai/src/processors/
mv /Users/harshsrivastava/Desktop/doc_ai/src/quality_integration.py /Users/harshsrivastava/Desktop/doc_ai/src/processors/

# SERVICES
mv /Users/harshsrivastava/Desktop/doc_ai/src/auth_service.py /Users/harshsrivastava/Desktop/doc_ai/src/services/
mv /Users/harshsrivastava/Desktop/doc_ai/src/subscription_service.py /Users/harshsrivastava/Desktop/doc_ai/src/services/
mv /Users/harshsrivastava/Desktop/doc_ai/src/stripe_service.py /Users/harshsrivastava/Desktop/doc_ai/src/services/
mv /Users/harshsrivastava/Desktop/doc_ai/src/overlay_service.py /Users/harshsrivastava/Desktop/doc_ai/src/services/

# UTILITIES
mv /Users/harshsrivastava/Desktop/doc_ai/src/github_sync.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/github_app.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/quality_checker.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/universal_code_parser.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/canonical_model.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/llm_provider_v2.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/
mv /Users/harshsrivastava/Desktop/doc_ai/src/doc_generation_endpoint.py /Users/harshsrivastava/Desktop/doc_ai/src/utilities/

# REFERENCE (for Phase 4 integration)
mv /Users/harshsrivastava/Desktop/doc_ai/src/event_consumer_multi_org.py /Users/harshsrivastava/Desktop/doc_ai/src/reference/
```

### **Step 3: Create __init__.py files**

```bash
touch /Users/harshsrivastava/Desktop/doc_ai/src/core/__init__.py
touch /Users/harshsrivastava/Desktop/doc_ai/src/processors/__init__.py
touch /Users/harshsrivastava/Desktop/doc_ai/src/services/__init__.py
touch /Users/harshsrivastava/Desktop/doc_ai/src/utilities/__init__.py
touch /Users/harshsrivastava/Desktop/doc_ai/src/reference/__init__.py
```

---

## **PHASE 1D: UPDATE IMPORTS (1 hour)**

### **Files that need import updates:**

#### **1. src/core/main.py**

```python
# OLD:
from commit_bus import CommitBusService
from subscription_service import SubscriptionService
from overlay_service import OverlayService
from smart_processor import handle_push_event as legacy_handle_push
from quality_checker import DocumentationQualityChecker, DocumentationQuality
from auth_service import AuthService, get_current_user, get_optional_user, User
from webhook_multi_org import webhook_multi_org

# NEW:
from core.commit_bus import CommitBusService
from services.subscription_service import SubscriptionService
from services.overlay_service import OverlayService
from processors.smart_processor import handle_push_event as legacy_handle_push
from utilities.quality_checker import DocumentationQualityChecker, DocumentationQuality
from services.auth_service import AuthService, get_current_user, get_optional_user, User
from core.webhook_multi_org import webhook_multi_org
```

#### **2. src/core/event_consumer.py**

```python
# OLD:
from commit_bus import CommitBusService, CommitEvent
from smart_processor import handle_push_event
from github_sync import GitHubSync

# NEW:
from core.commit_bus import CommitBusService, CommitEvent
from processors.smart_processor import handle_push_event
from utilities.github_sync import GitHubSync
```

#### **3. src/processors/smart_processor.py**

```python
# OLD:
from github_app import get_installation_token
from llm_provider_v2 import get_rotator
from comprehensive_doc_generator import generate_comprehensive_documentation

# NEW:
from utilities.github_app import get_installation_token
from utilities.llm_provider_v2 import get_rotator
from processors.comprehensive_doc_generator import generate_comprehensive_documentation
```

#### **4. src/processors/smart_processor.py (line 133)**

```python
# OLD:
from quality_integration import validate_documentation_quality

# NEW:
from processors.quality_integration import validate_documentation_quality
```

#### **5. src/processors/comprehensive_doc_generator.py**

```python
# OLD:
from llm_provider_v2 import get_rotator

# NEW:
from utilities.llm_provider_v2 import get_rotator
```

#### **6. src/processors/quality_integration.py**

```python
# OLD:
from quality_checker import DocumentationQualityChecker

# NEW:
from utilities.quality_checker import DocumentationQualityChecker
```

#### **7. src/core/webhook_multi_org.py**

```python
# No imports from src - No changes needed
```

#### **8. src/services/subscription_service.py**

```python
# OLD (if any):
from auth_service import ...

# NEW (if needed):
from services.auth_service import ...
```

#### **9. src/utilities/universal_code_parser.py**

```python
# No imports from src - No changes needed
```

---

## **FINAL STRUCTURE**

```
src/
├─ __init__.py
│
├─ core/
│  ├─ __init__.py
│  ├─ main.py                    (FastAPI server)
│  ├─ commit_bus.py              (Event store)
│  ├─ event_consumer.py          (Event processor)
│  └─ webhook_multi_org.py       (Webhook handler)
│
├─ processors/
│  ├─ __init__.py
│  ├─ smart_processor.py         (Doc generation orchestration)
│  ├─ comprehensive_doc_generator.py (Doc generation)
│  └─ quality_integration.py     (Quality integration)
│
├─ services/
│  ├─ __init__.py
│  ├─ auth_service.py            (OAuth, JWT)
│  ├─ subscription_service.py    (Billing)
│  ├─ stripe_service.py          (Stripe API)
│  └─ overlay_service.py         (UI overlays)
│
├─ utilities/
│  ├─ __init__.py
│  ├─ github_sync.py             (Missed commits)
│  ├─ github_app.py              (GitHub App JWT)
│  ├─ quality_checker.py         (Quality validation)
│  ├─ universal_code_parser.py   (Code parsing)
│  ├─ canonical_model.py         (Data models)
│  ├─ llm_provider_v2.py         (LLM provider)
│  └─ doc_generation_endpoint.py (Doc endpoint)
│
└─ reference/
   ├─ __init__.py
   └─ event_consumer_multi_org.py (Reference for Phase 4)
```

---

## **SUMMARY**

| Action | Files | Time |
|--------|-------|------|
| Delete unused | 6 files | 5 min |
| Create folders | 5 folders | 5 min |
| Move files | 19 files | 10 min |
| Create __init__.py | 5 files | 5 min |
| Update imports | 9 files | 30 min |
| **TOTAL** | | **55 min** |

---

## **READY TO PROCEED?**

Once you approve, I'll:
1. ✅ Delete 6 unused files
2. ✅ Create folder structure
3. ✅ Move files to folders
4. ✅ Update all imports
5. ✅ Test that everything still works

Then we'll move to **Phase 3: Multi-Org Implementation** 🚀

**Shall I proceed?**
