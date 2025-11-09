# 🚀 @src Quick Reference Guide

## 📋 Quick Lookup Table

### **🔴 CRITICAL FILES (Must Keep as Reference)**

| File | Purpose | Migrated To | Keep For |
|------|---------|-------------|----------|
| `core/commit_bus.py` | Event storage | `app/services/commit_bus.py` | Event storage patterns |
| `core/event_consumer.py` | Worker process | `app/worker.py` | Worker patterns |
| `processors/smart_processor.py` | Core doc generation | `app/services/event/smart_processor.py` | Core logic reference |
| `processors/comprehensive_doc_generator.py` | Doc generation | `app/services/documentation/comprehensive.py` | Doc generation patterns |
| `services/docbook_publisher.py` | Docbook publishing | `app/services/docbook/publisher.py` | Git operations, publishing |
| `utilities/github_dual_app_helper.py` | Dual app helper | `app/utils/github_dual_app.py` | GitHub App patterns |
| `webhooks/webhook_multi_org.py` | Multi-org webhooks | `app/webhooks/github.py` | Webhook patterns |
| `main.py` | Main application | `app/main.py` | API structure, endpoints |

---

### **🟠 IMPORTANT FILES (Good to Keep as Reference)**

| File | Purpose | Migrated To | Keep For |
|------|---------|-------------|----------|
| `core/auth_service.py` | Authentication | `app/services/auth.py` | Auth patterns |
| `core/app_installation_service.py` | App installation | `app/services/github/app_installation_service.py` | GitHub App installation |
| `services/subscription_service.py` | Subscriptions | `app/services/subscription.py` | Subscription patterns |
| `utilities/llm_provider_v2.py` | LLM providers | `app/services/llm/rotator.py` | LLM provider patterns |
| `utilities/github_sync.py` | GitHub sync | `app/utils/github_sync.py` | GitHub sync patterns |
| `routes/github_app_installation.py` | App routes | `app/api/v1/endpoints/auth.py` | App installation routes |

---

### **🟡 MODERATE FILES (Optional Reference)**

| File | Purpose | Migrated To | Keep For |
|------|---------|-------------|----------|
| `core/quality_checker.py` | Quality assessment | `app/services/documentation/quality_checker.py` | Quality patterns |
| `processors/quality_integration.py` | Quality integration | `app/services/documentation/quality_integration.py` | Quality integration |
| `processors/doc_generation_endpoint.py` | API endpoints | `app/api/v1/endpoints/documentation.py` | API endpoint patterns |
| `services/overlay_service.py` | Overlay system | ⚠️ **PARTIAL** - Model in `@app/models/overlay.py` | Overlay patterns (if needed) |
| `services/indexer_service.py` | Vector DB/RAG | ❌ **NOT MIGRATED** | RAG patterns (if needed) |
| `services/agent_service.py` | RAG Q&A | ❌ **NOT MIGRATED** | Q&A patterns (if needed) |
| `webhooks/webhook_handler.py` | Legacy webhooks | `app/webhooks/github.py` | Legacy webhook patterns |
| `webhooks/github_app.py` | GitHub App utils | `app/utils/github_dual_app.py` | GitHub App utils |
| `utilities/github_app_helper.py` | Legacy GitHub App | `app/utils/github_dual_app.py` | Legacy patterns |
| `utilities/universal_code_parser.py` | Code parser | ❓ **UNKNOWN** | Code parsing patterns |

---

### **🟢 LOW PRIORITY FILES (Can Remove)**

| File | Purpose | Status | Action |
|------|---------|--------|--------|
| `references/pustak_integration.py` | Reference | ❌ Not used | Remove |
| `references/stripe_service.py` | Reference | ❌ Not used | Remove |
| `references/test_scripts/` | Test scripts | ❌ Not needed | Remove |
| `integrations/` | Empty directory | ❌ Empty | Remove |

---

## 🎯 Migration Status Summary

### **✅ Fully Migrated (20 files)**
- Core services (commit_bus, event_consumer, auth_service, app_installation_service)
- Processors (smart_processor, comprehensive_doc_generator, quality_integration)
- Services (docbook_publisher, subscription_service)
- Webhooks (webhook_multi_org, webhook_handler, github_app)
- Utilities (github_dual_app_helper, llm_provider_v2, github_sync)
- Routes (github_app_installation)
- Main application (main.py)

### **⚠️ Partially Migrated (1 file)**
- `services/overlay_service.py` - Model exists in `@app/models/overlay.py`, but service may need migration

### **❌ Not Migrated (7 files)**
- `services/indexer_service.py` - RAG/vector DB (not currently used)
- `services/agent_service.py` - RAG Q&A (not currently used)
- `utilities/universal_code_parser.py` - Code parser (unknown status)
- `references/pustak_integration.py` - Reference only
- `references/stripe_service.py` - Reference only
- `references/test_scripts/` - Test scripts
- `integrations/` - Empty directory

---

## 📊 File Importance by Category

### **🔴 CRITICAL (8 files)**
1. `core/commit_bus.py`
2. `core/event_consumer.py`
3. `processors/smart_processor.py`
4. `processors/comprehensive_doc_generator.py`
5. `services/docbook_publisher.py`
6. `utilities/github_dual_app_helper.py`
7. `webhooks/webhook_multi_org.py`
8. `main.py`

### **🟠 IMPORTANT (6 files)**
1. `core/auth_service.py`
2. `core/app_installation_service.py`
3. `services/subscription_service.py`
4. `utilities/llm_provider_v2.py`
5. `utilities/github_sync.py`
6. `routes/github_app_installation.py`

### **🟡 MODERATE (10 files)**
1. `core/quality_checker.py`
2. `processors/quality_integration.py`
3. `processors/doc_generation_endpoint.py`
4. `services/overlay_service.py`
5. `services/indexer_service.py`
6. `services/agent_service.py`
7. `webhooks/webhook_handler.py`
8. `webhooks/github_app.py`
9. `utilities/github_app_helper.py`
10. `utilities/universal_code_parser.py`

### **🟢 LOW (4 files)**
1. `references/pustak_integration.py`
2. `references/stripe_service.py`
3. `references/test_scripts/`
4. `integrations/`

---

## 🚀 Quick Actions

### **Immediate Actions**
1. ✅ Keep all CRITICAL files as reference
2. ✅ Keep all IMPORTANT files as reference
3. ❌ Remove LOW priority files (references, test scripts, empty dirs)

### **After Production Verification**
1. ⚠️ Archive CRITICAL files for future reference
2. ⚠️ Remove MODERATE files that are not needed
3. ⚠️ Retire `@src` directory after 1-2 weeks

### **Future Considerations**
1. ⚠️ Migrate `overlay_service.py` if overlay functionality is needed
2. ⚠️ Migrate `indexer_service.py` if RAG/vector DB is needed
3. ⚠️ Migrate `agent_service.py` if AI Q&A is needed

---

## 📝 Key Insights

1. **Core functionality is migrated** - All critical files are in `@app`
2. **RAG services are not migrated** - IndexerService and AgentService are not currently used
3. **Overlay system is partially migrated** - Model exists, but service may need migration
4. **Test scripts can be removed** - Not needed in production
5. **Reference files can be removed** - Not actively used

---

**Generated**: $(date)
**Version**: 1.0
**Purpose**: Quick reference for @src file importance and migration status

