# 🏗️ LEKHAK AI - SYSTEM ARCHITECTURE DEEP DIVE (PART 3)

> **Optimization Recommendations, Production Readiness, Database Cleanup**

---

## 🚀 OPTIMIZATION RECOMMENDATIONS

### **PRIORITY 1: SECURITY FIXES (Do Immediately)**

#### **Issue 1: Plaintext GitHub Tokens**
**Problem:** Tokens stored in plaintext in `users.github_access_token` and `user_github_tokens.github_token`

**Risk:** If database is compromised, all GitHub tokens are exposed

**Solution:**
```python
# 1. Use encryption library (e.g., cryptography)
from cryptography.fernet import Fernet

# 2. Generate encryption key from environment
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

# 3. Encrypt tokens before storing
encrypted_token = cipher.encrypt(github_token.encode())

# 4. Decrypt when needed
decrypted_token = cipher.decrypt(encrypted_token).decode()
```

**Migration:**
```sql
-- 1. Add encrypted_token column
ALTER TABLE user_github_tokens ADD COLUMN encrypted_token TEXT;

-- 2. Encrypt existing tokens
UPDATE user_github_tokens 
SET encrypted_token = pgcrypto.pgp_sym_encrypt(github_token, 'encryption_key')
WHERE encrypted_token IS NULL;

-- 3. Drop old column
ALTER TABLE user_github_tokens DROP COLUMN github_token;
```

---

#### **Issue 2: CORS Configuration**
**Current:** Hardcoded localhost URLs

**Better:**
```python
# Use environment variable
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

#### **Issue 3: JWT Token Storage**
**Current:** Tokens stored in plaintext in `sessions.access_token`

**Better:**
```python
# Hash tokens before storing
import hashlib

hashed_token = hashlib.sha256(access_token.encode()).hexdigest()

# Store hashed version
await conn.execute(
    "INSERT INTO sessions (user_id, access_token_hash, ...)",
    user_id, hashed_token, ...
)

# On validation, hash incoming token and compare
incoming_hash = hashlib.sha256(incoming_token.encode()).hexdigest()
session = await conn.fetchrow(
    "SELECT * FROM sessions WHERE access_token_hash = $1",
    incoming_hash
)
```

---

### **PRIORITY 2: DATABASE OPTIMIZATION**

#### **Missing Indexes**
```sql
-- Add indexes for fast lookups
CREATE INDEX idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX idx_commit_events_processed ON commit_events(processed);
CREATE INDEX idx_org_registrations_user_id ON org_registrations(user_id);
CREATE INDEX idx_org_registrations_org_id ON org_registrations(org_id);
CREATE INDEX idx_org_webhooks_org_id ON org_webhooks(org_id);
CREATE INDEX idx_user_github_tokens_user_id ON user_github_tokens(user_id);
CREATE INDEX idx_doc_versions_repo_id ON doc_versions(repo_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
```

#### **Data Type Optimization**
```sql
-- Current: VARCHAR(255) for everything
-- Better: Use appropriate types

-- Before
CREATE TABLE users (
    id UUID,
    github_id INTEGER,
    email VARCHAR(255),
    username VARCHAR(255),
    ...
);

-- After
CREATE TABLE users (
    id UUID PRIMARY KEY,
    github_id INTEGER UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,  -- Shorter
    name VARCHAR(255),
    avatar_url VARCHAR(2048),  -- URLs can be long
    plan VARCHAR(50) DEFAULT 'free',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### **PRIORITY 3: TABLE CLEANUP**

#### **Tables to Remove (Not Used)**

```sql
-- 1. event_processing_log - Debug only
DROP TABLE IF EXISTS event_processing_log CASCADE;

-- 2. doc_nodes - Hierarchical structure not used
DROP TABLE IF EXISTS doc_nodes CASCADE;

-- 3. overlay_history - Change history not needed
DROP TABLE IF EXISTS overlay_history CASCADE;

-- 4. embeddings_metadata - Vector search not implemented
DROP TABLE IF EXISTS embeddings_metadata CASCADE;

-- 5. repositories - Use GitHub API instead
DROP TABLE IF EXISTS repositories CASCADE;

-- 6. user_repositories - Use GitHub API instead
DROP TABLE IF EXISTS user_repositories CASCADE;

-- 7. payment_events - Not implemented
DROP TABLE IF EXISTS payment_events CASCADE;

-- 8. api_usage - Rate limiting not implemented
DROP TABLE IF EXISTS api_usage CASCADE;
```

**Impact:** Reduces schema complexity, improves migration speed

---

#### **Tables to Consolidate**

**Current:**
```
users.github_access_token
user_github_tokens.github_token
```

**Better:** Remove from `users`, keep only in `user_github_tokens`

```sql
-- 1. Migrate data
INSERT INTO user_github_tokens (user_id, github_token)
SELECT id, github_access_token FROM users
WHERE github_access_token IS NOT NULL;

-- 2. Drop from users
ALTER TABLE users DROP COLUMN github_access_token;
```

---

### **PRIORITY 4: PERFORMANCE IMPROVEMENTS**

#### **Issue: Slow Webhook Handler**

**Current:**
```python
async def get_org_context_from_repo(repo_full_name):
    # Makes 3 separate database queries
    # Query 1: org_webhooks
    # Query 2: org_registrations
    # Query 3: commit_events
```

**Better: Single Query with UNION**
```python
async def get_org_context_from_repo(repo_full_name):
    org_id = repo_full_name.split('/')[0]
    
    # Single query with priority
    result = await conn.fetchrow("""
        SELECT user_id, org_id, github_token_id, 1 as priority
        FROM org_webhooks
        WHERE org_id = $1
        
        UNION ALL
        
        SELECT or.user_id, or.org_id, ugt.token_id, 2
        FROM org_registrations or
        LEFT JOIN user_github_tokens ugt ON or.user_id = ugt.user_id
        WHERE or.org_id = $1
        
        UNION ALL
        
        SELECT ce.user_id, ce.org_id, NULL, 3
        FROM commit_events ce
        WHERE ce.org_id = $1 AND ce.user_id IS NOT NULL
        
        ORDER BY priority
        LIMIT 1
    """, org_id)
    
    return dict(result) if result else None
```

---

#### **Issue: Event Consumer Polling**

**Current:**
```python
# Polls every 5 seconds
# Fetches 10 events at a time
# Processes max 3 concurrent
```

**Better: Batch Processing**
```python
async def process_events():
    while True:
        # Get all pending events
        events = await commit_bus.get_pending_events(limit=100)
        
        if not events:
            await asyncio.sleep(5)
            continue
        
        # Process in batches of 5
        for batch in chunks(events, 5):
            tasks = [process_event(e) for e in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
```

---

### **PRIORITY 5: MONITORING & LOGGING**

#### **Add Structured Logging**
```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use structured logs
logger.info(json.dumps({
    "event": "webhook_received",
    "org_id": org_id,
    "repo_id": repo_id,
    "timestamp": datetime.now().isoformat()
}))
```

#### **Add Metrics**
```python
from prometheus_client import Counter, Histogram

# Metrics
webhook_received = Counter('webhook_received_total', 'Total webhooks received')
event_processed = Counter('event_processed_total', 'Total events processed')
event_failed = Counter('event_failed_total', 'Total events failed')
processing_time = Histogram('event_processing_seconds', 'Event processing time')

# Usage
webhook_received.inc()

with processing_time.time():
    await process_event(event)
```

---

## 📊 PRODUCTION READINESS CHECKLIST

### **Security**
- [ ] Encrypt GitHub tokens in database
- [ ] Hash JWT tokens in sessions table
- [ ] Use environment variables for all secrets
- [ ] Implement rate limiting on API endpoints
- [ ] Add request validation (Pydantic models)
- [ ] Implement CSRF protection
- [ ] Add SQL injection prevention (use parameterized queries)
- [ ] Implement API key authentication for webhooks

### **Performance**
- [ ] Add database indexes
- [ ] Implement caching (Redis)
- [ ] Add query optimization
- [ ] Implement connection pooling
- [ ] Add CDN for static assets
- [ ] Implement pagination for list endpoints
- [ ] Add database query monitoring

### **Reliability**
- [ ] Implement error handling and retries
- [ ] Add health check endpoints
- [ ] Implement graceful shutdown
- [ ] Add database backups
- [ ] Implement monitoring and alerting
- [ ] Add logging and log aggregation
- [ ] Implement circuit breakers for external APIs

### **Scalability**
- [ ] Implement horizontal scaling
- [ ] Use load balancer
- [ ] Implement database replication
- [ ] Use message queue (RabbitMQ, Kafka)
- [ ] Implement caching layer
- [ ] Use CDN for assets

### **Code Quality**
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add end-to-end tests
- [ ] Implement CI/CD pipeline
- [ ] Add code coverage reporting
- [ ] Implement linting and formatting
- [ ] Add documentation

---

## 🗑️ TABLE CLEANUP PLAN

### **Phase 1: Backup (Do First)**
```bash
# Backup entire database
pg_dump postgresql://localhost/lekhak_ai > backup_$(date +%Y%m%d).sql

# Backup specific tables
pg_dump -t event_processing_log postgresql://localhost/lekhak_ai > event_processing_log.sql
```

### **Phase 2: Remove Unused Tables**
```sql
-- Remove in this order (respecting foreign keys)
DROP TABLE IF EXISTS event_processing_log CASCADE;
DROP TABLE IF EXISTS doc_nodes CASCADE;
DROP TABLE IF EXISTS overlay_history CASCADE;
DROP TABLE IF EXISTS embeddings_metadata CASCADE;
DROP TABLE IF EXISTS repositories CASCADE;
DROP TABLE IF EXISTS user_repositories CASCADE;
DROP TABLE IF EXISTS payment_events CASCADE;
DROP TABLE IF EXISTS api_usage CASCADE;
```

### **Phase 3: Consolidate Data**
```sql
-- Move github_access_token from users to user_github_tokens
INSERT INTO user_github_tokens (user_id, github_token, is_active)
SELECT id, github_access_token, true
FROM users
WHERE github_access_token IS NOT NULL
ON CONFLICT DO NOTHING;

-- Remove from users
ALTER TABLE users DROP COLUMN github_access_token;
```

### **Phase 4: Add Indexes**
```sql
CREATE INDEX idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX idx_commit_events_processed ON commit_events(processed);
CREATE INDEX idx_org_registrations_user_id ON org_registrations(user_id);
CREATE INDEX idx_org_registrations_org_id ON org_registrations(org_id);
CREATE INDEX idx_org_webhooks_org_id ON org_webhooks(org_id);
CREATE INDEX idx_user_github_tokens_user_id ON user_github_tokens(user_id);
CREATE INDEX idx_doc_versions_repo_id ON doc_versions(repo_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
```

---

## 📈 FINAL SCHEMA (After Cleanup)

### **13 Tables (Down from 21)**

**User Management (3):**
- users
- user_github_tokens
- sessions

**Organization Management (3):**
- org_registrations
- org_webhooks
- github_installations

**Event Processing (3):**
- commit_events
- repo_sync_state
- audit_logs

**Documentation (2):**
- doc_versions
- doc_overlays

**Billing (2):**
- subscriptions
- changelogs

---

## 🎯 NEXT STEPS

### **Immediate (This Week)**
1. ✅ Backup database
2. ✅ Remove unused tables
3. ✅ Add indexes
4. ✅ Encrypt GitHub tokens

### **Short Term (Next 2 Weeks)**
1. ✅ Implement error handling
2. ✅ Add monitoring
3. ✅ Add unit tests
4. ✅ Implement caching

### **Medium Term (Next Month)**
1. ✅ Implement CI/CD
2. ✅ Add load testing
3. ✅ Implement horizontal scaling
4. ✅ Add API documentation

### **Long Term (Next Quarter)**
1. ✅ Implement vector search (embeddings)
2. ✅ Add advanced analytics
3. ✅ Implement subscription billing
4. ✅ Add multi-language support

---

## 📚 SUMMARY

**Your system is:**
- ✅ **Functionally complete** - All core features working
- ✅ **Multi-org ready** - Supports unlimited organizations
- ⚠️ **Security needs work** - Tokens in plaintext
- ⚠️ **Performance adequate** - Works but could be optimized
- ❌ **Not production-ready** - Missing monitoring, error handling

**To reach production:**
1. Fix security issues (encrypt tokens)
2. Add monitoring and logging
3. Implement error handling and retries
4. Add tests
5. Deploy with load balancer
6. Set up backups and disaster recovery

**Estimated effort:** 2-3 weeks for full production readiness
