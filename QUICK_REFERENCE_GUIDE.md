# 🚀 LEKHAK AI - QUICK REFERENCE GUIDE

> **TL;DR - Everything You Need to Know**

---

## 🎯 WHAT IS LEKHAK AI?

An **AI-powered documentation generator** that:
- Listens for GitHub push events via webhooks
- Automatically generates docs (architecture, workflow, API)
- Supports unlimited organizations
- Stores versioned documentation
- Integrates with billing system

---

## 🔄 THE COMPLETE FLOW (5 Minutes)

### **Step 1: User Logs In**
```
User clicks "Login with GitHub"
  ↓
Redirected to GitHub OAuth
  ↓
User authorizes app
  ↓
GitHub redirects back with code
  ↓
Backend exchanges code for token
  ↓
User data stored in `users` table
  ↓
Token stored in `user_github_tokens` table
  ↓
JWT tokens generated and returned
```

### **Step 2: User Registers Organization**
```
User clicks "Register Webhook" for "my-org"
  ↓
Frontend: POST /webhook/register {org_id: "my-org"}
  ↓
Backend stores in `org_registrations` table
  ↓
Backend stores in `org_webhooks` table with user's token
  ↓
User installs GitHub App on organization
  ↓
GitHub sends installation webhook
  ↓
Backend stores in `github_installations` table
```

### **Step 3: Developer Pushes Code**
```
Developer: git push
  ↓
GitHub sends webhook to POST /webhook
  ↓
Backend verifies webhook signature
  ↓
Extracts org from repo name ("my-org/my-repo" → "my-org")
  ↓
Looks up user from `org_registrations` table
  ↓
Creates CommitEvent object with user's token
  ↓
Stores in `commit_events` table
  ↓
Returns 200 OK immediately
```

### **Step 4: Event Consumer Processes Event**
```
Event Consumer polls `commit_events` table every 5 seconds
  ↓
Finds unprocessed event
  ↓
Gets user's GitHub token from `user_github_tokens` table
  ↓
Clones repository using token
  ↓
Analyzes code files
  ↓
Calls LLM (Gemini → Groq → DeepSeek) to generate docs
  ↓
Commits docs to GitHub
  ↓
Stores in `doc_versions` table
  ↓
Updates `repo_sync_state` table with latest SHA
  ↓
Marks event as processed in `commit_events` table
```

---

## 📊 CRITICAL TABLES (Must Understand)

| Table | Purpose | Key Columns | Used By |
|-------|---------|-------------|---------|
| `users` | User profile | id, github_id, username, email | All |
| `user_github_tokens` | GitHub tokens | user_id, github_token, token_id | event_consumer, webhook |
| `org_registrations` | Org-user mapping | user_id, org_id | webhook, event_consumer |
| `org_webhooks` | Webhook config | user_id, org_id, github_token_id | webhook |
| `commit_events` | Event queue | repo_id, commit_sha, user_id, org_id, processed | webhook, event_consumer |
| `repo_sync_state` | Last processed SHA | org_id, repo_id, last_processed_sha | event_consumer |
| `doc_versions` | Generated docs | repo_id, commit_sha, architecture_doc, ... | frontend |
| `sessions` | User sessions | user_id, access_token, refresh_token | auth |

---

## 🔑 KEY FILES

| File | Purpose | Key Function |
|------|---------|--------------|
| `src/main.py` | FastAPI server | Routes, middleware, service init |
| `src/webhooks/webhook_multi_org.py` | Webhook handler | Extract org context, attach user |
| `src/core/commit_bus.py` | Event queue | Store/retrieve events |
| `src/core/event_consumer.py` | Event processor | Poll and process events |
| `src/core/auth_service.py` | Authentication | OAuth, JWT tokens |
| `src/processors/smart_processor.py` | Doc generator | LLM calls, doc generation |

---

## 🌍 ENVIRONMENT VARIABLES

```bash
# GitHub
GITHUB_CLIENT_ID=Ov23lif8Bs...
GITHUB_CLIENT_SECRET=xxx...
GITHUB_WEBHOOK_SECRET=xxx...

# Database
DATABASE_URL=postgresql://localhost/lekhak_ai

# LLM
GEMINI_API_KEY=xxx...
GROQ_API_KEY=xxx...
DEEPSEEK_API_KEY=xxx...

# Frontend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 🚨 CURRENT ISSUES

### **Security** 🔴
- GitHub tokens stored in plaintext
- JWT tokens stored in plaintext
- No encryption for sensitive data

### **Performance** 🟡
- No caching
- No indexes on frequently queried columns
- Multiple database queries per webhook

### **Reliability** 🟡
- No error handling
- No monitoring
- No logging
- No backups

### **Scalability** 🟡
- Single event consumer
- No load balancing
- No horizontal scaling

---

## ✅ WHAT'S WORKING

- ✅ Multi-org support
- ✅ GitHub OAuth
- ✅ Webhook handling
- ✅ Event queue
- ✅ Documentation generation
- ✅ LLM fallback (Gemini → Groq → DeepSeek)
- ✅ GitHub integration
- ✅ Async processing

---

## 🛠️ QUICK FIXES (Priority Order)

### **Priority 1: Security (Do First)**
```python
# Encrypt GitHub tokens
from cryptography.fernet import Fernet
cipher = Fernet(os.getenv("ENCRYPTION_KEY"))
encrypted = cipher.encrypt(token.encode())
```

### **Priority 2: Performance**
```sql
-- Add indexes
CREATE INDEX idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX idx_org_registrations_org_id ON org_registrations(org_id);
```

### **Priority 3: Cleanup**
```sql
-- Remove unused tables
DROP TABLE event_processing_log;
DROP TABLE doc_nodes;
DROP TABLE overlay_history;
DROP TABLE embeddings_metadata;
```

### **Priority 4: Monitoring**
```python
# Add logging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Processing event {event_id}")
```

---

## 📈 METRICS TO TRACK

- **Webhook latency:** Time from webhook received to event stored
- **Processing latency:** Time from event stored to docs generated
- **Success rate:** % of events processed successfully
- **Error rate:** % of events that failed
- **Token usage:** API calls to LLM providers
- **Database queries:** Query count and duration

---

## 🔍 DEBUGGING TIPS

### **Check if webhook was received:**
```sql
SELECT * FROM commit_events 
WHERE org_id = 'my-org' 
ORDER BY created_at DESC 
LIMIT 5;
```

### **Check if event was processed:**
```sql
SELECT * FROM commit_events 
WHERE id = 'event_id' 
AND processed = true;
```

### **Check last processed commit:**
```sql
SELECT * FROM repo_sync_state 
WHERE org_id = 'my-org' 
AND repo_id = 'my-repo';
```

### **Check if docs were generated:**
```sql
SELECT * FROM doc_versions 
WHERE repo_id = 'my-org/my-repo' 
ORDER BY created_at DESC 
LIMIT 1;
```

### **Check user's organizations:**
```sql
SELECT org_id FROM org_registrations 
WHERE user_id = 'user_id';
```

### **Check user's GitHub token:**
```sql
SELECT github_token FROM user_github_tokens 
WHERE user_id = 'user_id' 
LIMIT 1;
```

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] Encrypt GitHub tokens
- [ ] Add database indexes
- [ ] Remove unused tables
- [ ] Add error handling
- [ ] Add logging
- [ ] Add monitoring
- [ ] Set up backups
- [ ] Configure CORS properly
- [ ] Use environment variables
- [ ] Add rate limiting
- [ ] Add health checks
- [ ] Set up CI/CD
- [ ] Add tests
- [ ] Document API
- [ ] Set up alerts

---

## 📞 COMMON QUESTIONS

**Q: Why is my webhook not being processed?**
A: Check if org is registered in `org_registrations` table. If not, go to dashboard and click "Register Webhook".

**Q: Why is my event stuck in pending?**
A: Check `commit_events` table for error_message. Event Consumer might be down or GitHub token might be invalid.

**Q: How do I see generated docs?**
A: Check `doc_versions` table. Docs are also pushed to GitHub in `/docs` folder.

**Q: How do I add a new organization?**
A: 1. Install GitHub App on org, 2. Go to dashboard, 3. Click "Register Webhook", 4. Push code to trigger docs generation.

**Q: How do I check if Event Consumer is running?**
A: Run `python -m src.core.event_consumer`. You should see startup logs and polling messages.

---

## 📚 DOCUMENTATION FILES

- **SYSTEM_ARCHITECTURE_PART1.md** - Database schema and tables
- **SYSTEM_ARCHITECTURE_PART2.md** - File architecture and flows
- **SYSTEM_ARCHITECTURE_PART3.md** - Optimization and production readiness
- **DATABASE_SCHEMA_DIAGRAM.md** - Visual diagrams and relationships
- **QUICK_REFERENCE_GUIDE.md** - This file

---

## 🎓 LEARNING PATH

1. **Start here:** QUICK_REFERENCE_GUIDE.md (this file)
2. **Understand database:** SYSTEM_ARCHITECTURE_PART1.md
3. **Understand code:** SYSTEM_ARCHITECTURE_PART2.md
4. **Optimize system:** SYSTEM_ARCHITECTURE_PART3.md
5. **Visualize schema:** DATABASE_SCHEMA_DIAGRAM.md

---

## 💡 KEY INSIGHTS

1. **Multi-org support** is the biggest feature - each org has its own token
2. **Webhook handler** is the bottleneck - optimize `get_org_context_from_repo()`
3. **Event Consumer** is the heart - if it's down, nothing gets processed
4. **GitHub tokens** are the most sensitive data - encrypt them!
5. **Async processing** is why the system is fast - webhooks return immediately

---

## 🎯 NEXT STEPS

1. **This week:** Fix security issues (encrypt tokens)
2. **Next week:** Add monitoring and logging
3. **Next 2 weeks:** Add tests and CI/CD
4. **Next month:** Deploy to production

---

**You've got this! 🚀**
