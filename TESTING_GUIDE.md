# 🧪 COMPLETE TESTING GUIDE FOR MULTI-ORG SUPPORT

## **BEFORE YOU START**

### **Prerequisites**
1. ✅ Database migration run: `psql -U postgres -d lekhak_ai < migrations/004_multi_org_support.sql`
2. ✅ Backend running: `python src/core/main.py`
3. ✅ Event consumer running: `python src/core/event_consumer.py`
4. ✅ Frontend running: `cd pustak && npm run dev`

### **Environment Variables**
```bash
# .env file should have:
GITHUB_TOKEN=ghp_xxxxx              # PUSTAK's token (fallback)
GITHUB_ORG=AuditorEnvelope          # PUSTAK's org
WEBHOOK_SECRET=your-webhook-secret  # For app webhook
DATABASE_URL=postgresql://...       # Your database
NGROK_URL=https://xxxxx.ngrok.io   # For local testing
```

---

## **TEST 1: WEBHOOK REGISTRATION (15 minutes)**

### **Goal**: Register an organization and verify webhook is stored

### **Step 1: Get Your GitHub Token**
```bash
# Go to: https://github.com/settings/tokens
# Create new token with scopes:
#   - user:email
#   - read:org
#   - repo
#   - admin:org_hook

# Copy token: ghp_xxxxxxxxxxxxx
```

### **Step 2: Register Organization via API**
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "beta-org-for-pustak"
  }'
```

**Expected Response:**
```json
{
  "status": "registered",
  "org_id": "beta-org-for-pustak",
  "webhook_url": "https://xxxxx.ngrok.io/webhook",
  "message": "Organization 'beta-org-for-pustak' registered!..."
}
```

### **Step 3: Verify in Database**
```bash
# Check org_webhooks table
psql -U postgres -d lekhak_ai -c "SELECT * FROM org_webhooks WHERE org_id = 'beta-org-for-pustak';"

# Expected output:
# id | user_id | org_id | webhook_secret | github_token_id | registered_at
# ---|---------|--------|----------------|-----------------|---------------
# (should have 1 row)
```

### **Step 4: Check Backend Logs**
```bash
# Should see:
# ✅ Webhook registered for org: beta-org-for-pustak
# 📚 Webhook secret: iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY
```

### **✅ TEST 1 PASSED** if:
- ✅ API returns webhook URL
- ✅ org_webhooks table has new row
- ✅ webhook_secret is unique
- ✅ user_id and org_id stored correctly

---

## **TEST 2: EVENT PROCESSING (20 minutes)**

### **Goal**: Push code to registered org and verify event is processed

### **Step 1: Push Code to GitHub**
```bash
# Go to your registered org's repo
# Make a small change (e.g., update README.md)
# Push to GitHub

git add .
git commit -m "Test commit for multi-org"
git push origin main
```

### **Step 2: Monitor Event Consumer Logs**
```bash
# Watch event consumer in real-time
tail -f logs/event_consumer.log

# Or if running in terminal:
# You'll see output like:
```

### **Step 3: Expected Log Output**
```
============================================================
📝 Processing event: ba48c37f-9722-48f5-91f6-81b02126bac3
   Repo: beta-org-for-pustak/College-ERP
   Commit: 9dcdaa34
   Message: Test commit for multi-org
============================================================

✅ Got GitHub token for user aca20dc6-... org beta-org-for-pustak
🔄 Processing with smart_processor...
📁 Changed files: 1 files
🗑️  Removed files: 0 files

✅ Event ba48c37f-9722-48f5-91f6-81b02126bac3 processed successfully
```

### **Step 4: Verify in Database**
```bash
# Check commit_events table
psql -U postgres -d lekhak_ai -c "
  SELECT repo_id, user_id, org_id, processed 
  FROM commit_events 
  WHERE repo_id = 'beta-org-for-pustak/College-ERP' 
  ORDER BY created_at DESC LIMIT 5;
"

# Expected output:
# repo_id | user_id | org_id | processed
# --------|---------|--------|----------
# beta-org-for-pustak/College-ERP | aca20dc6-... | beta-org-for-pustak | t
```

### **Step 5: Check GitHub for Generated Docs**
```bash
# Go to: https://github.com/beta-org-for-pustak/College-ERP
# Look for:
#   - /docs folder created
#   - SUMMARY.md generated
#   - ARCHITECTURE.md generated
#   - Recent commit from docai-bot
```

### **✅ TEST 2 PASSED** if:
- ✅ Event consumer processes event
- ✅ Logs show correct org_id
- ✅ Event marked as processed in database
- ✅ Docs generated in GitHub repo

---

## **TEST 3: MULTI-ORG SCENARIO (30 minutes)**

### **Goal**: Register multiple orgs and verify each uses correct token

### **Step 1: Register Second Organization**
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "another-org"
  }'
```

### **Step 2: Register Third Organization**
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "testing-org"
  }'
```

### **Step 3: Verify All Registered**
```bash
psql -U postgres -d lekhak_ai -c "SELECT org_id, webhook_secret FROM org_webhooks;"

# Expected output:
# org_id | webhook_secret
# -------|----------------
# beta-org-for-pustak | iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY
# another-org | aB2c-dEfGhIjKlMnOpQrStUvWxYzAbCdEfGhIjKlM
# testing-org | xYz9-AbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGhI
```

### **Step 4: Push to Each Org**
```bash
# Push to org 1
cd /path/to/beta-org-for-pustak/repo1
git commit --allow-empty -m "Test from org 1"
git push

# Push to org 2
cd /path/to/another-org/repo2
git commit --allow-empty -m "Test from org 2"
git push

# Push to org 3
cd /path/to/testing-org/repo3
git commit --allow-empty -m "Test from org 3"
git push
```

### **Step 5: Monitor Event Consumer**
```bash
# Watch logs - should see:
# ✅ Got GitHub token for user ... org beta-org-for-pustak
# ✅ Got GitHub token for user ... org another-org
# ✅ Got GitHub token for user ... org testing-org

# Each event processed with CORRECT token for that org!
```

### **Step 6: Verify Each Repo Has Docs**
```bash
# Check each repo on GitHub:
# https://github.com/beta-org-for-pustak/repo1 → has /docs
# https://github.com/another-org/repo2 → has /docs
# https://github.com/testing-org/repo3 → has /docs
```

### **✅ TEST 3 PASSED** if:
- ✅ All 3 orgs registered with unique secrets
- ✅ Each org's event processed independently
- ✅ Each org uses correct GitHub token
- ✅ Docs generated in all 3 repos

---

## **TEST 4: MISSED COMMITS DETECTION (25 minutes)**

### **Goal**: Verify server downtime recovery works for all orgs

### **Step 1: Push Commits While Consumer is Running**
```bash
# Push 5 commits to org 1
for i in {1..5}; do
  git commit --allow-empty -m "Commit $i from org 1"
  git push
done

# Push 3 commits to org 2
for i in {1..3}; do
  git commit --allow-empty -m "Commit $i from org 2"
  git push
done
```

### **Step 2: Verify Events Processed**
```bash
# Check logs - should see all events processed
tail -f logs/event_consumer.log

# Should see:
# ✅ Event ... processed successfully (org 1)
# ✅ Event ... processed successfully (org 2)
```

### **Step 3: Stop Event Consumer**
```bash
# Press Ctrl+C to stop event consumer
# Or: kill <PID>
```

### **Step 4: Push More Commits (While Consumer is Stopped)**
```bash
# Push 5 MORE commits to org 1
for i in {6..10}; do
  git commit --allow-empty -m "Missed commit $i from org 1"
  git push
done

# Push 3 MORE commits to org 2
for i in {4..6}; do
  git commit --allow-empty -m "Missed commit $i from org 2"
  git push
done

# These commits are NOT processed yet (consumer is stopped)
```

### **Step 5: Start Event Consumer Again**
```bash
python src/core/event_consumer.py

# Watch logs - should see:
```

### **Step 6: Expected Log Output**
```
🔍 Checking for missed commits across all orgs...
📊 Found 2 unprocessed events in database
📚 Found 2 unique repos across orgs

🔍 Checking beta-org-for-pustak/repo1...
✅ Found 5 missed commits for beta-org-for-pustak/repo1
   ✅ Stored: 9dcdaa34
   ✅ Stored: 8ecb9923
   ✅ Stored: 7dba8812
   ✅ Stored: 6ca97701
   ✅ Stored: 5b986590

🔍 Checking another-org/repo2...
✅ Found 3 missed commits for another-org/repo2
   ✅ Stored: 4a875489
   ✅ Stored: 3b764378
   ✅ Stored: 2c653267

🎉 Successfully recovered 8 missed commits across all orgs!
   They will be processed automatically
```

### **Step 7: Verify Missed Commits Processed**
```bash
# Check logs - should see:
# ✅ Event ... processed successfully (missed commit 1)
# ✅ Event ... processed successfully (missed commit 2)
# ... (all 8 missed commits)

# Check database:
psql -U postgres -d lekhak_ai -c "
  SELECT COUNT(*) as total_events, 
         COUNT(CASE WHEN processed = true THEN 1 END) as processed
  FROM commit_events;
"

# Expected: all events should be processed = true
```

### **✅ TEST 4 PASSED** if:
- ✅ Missed commits detected for ALL orgs
- ✅ Correct number of commits recovered
- ✅ All missed commits processed
- ✅ Docs generated for missed commits

---

## **TEST 5: ERROR HANDLING (15 minutes)**

### **Goal**: Verify system handles errors gracefully

### **Test 5A: Invalid Organization**
```bash
# Try to register org with invalid token
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer invalid-token" \
  -H "Content-Type: application/json" \
  -d '{"org_id": "invalid-org"}'

# Expected: 401 Unauthorized error
```

### **Test 5B: Missing GitHub Token**
```bash
# Delete token from database
psql -U postgres -d lekhak_ai -c "
  DELETE FROM user_github_tokens 
  WHERE user_id = 'aca20dc6-...';
"

# Push code to org
git commit --allow-empty -m "Test without token"
git push

# Check logs - should see:
# ⚠️  No GitHub token found for user ... org ...
# Falls back to env GITHUB_TOKEN
```

### **Test 5C: Invalid Webhook Secret**
```bash
# Manually send webhook with wrong secret
curl -X POST http://localhost:8000/webhook \
  -H "X-Hub-Signature-256: sha256=wrong-signature" \
  -H "X-GitHub-Event: push" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected: 401 Unauthorized
```

### **✅ TEST 5 PASSED** if:
- ✅ Invalid tokens handled gracefully
- ✅ Falls back to env var when needed
- ✅ Wrong signatures rejected
- ✅ No crashes or data corruption

---

## **QUICK REFERENCE: TESTING COMMANDS**

### **Check Database**
```bash
# View all registered orgs
psql -U postgres -d lekhak_ai -c "SELECT org_id, webhook_secret FROM org_webhooks;"

# View all events
psql -U postgres -d lekhak_ai -c "SELECT repo_id, org_id, processed FROM commit_events ORDER BY created_at DESC LIMIT 10;"

# View unprocessed events
psql -U postgres -d lekhak_ai -c "SELECT repo_id, org_id FROM commit_events WHERE processed = FALSE;"

# Count events by org
psql -U postgres -d lekhak_ai -c "SELECT org_id, COUNT(*) FROM commit_events GROUP BY org_id;"
```

### **Check Logs**
```bash
# Real-time logs
tail -f logs/event_consumer.log

# Last 50 lines
tail -50 logs/event_consumer.log

# Search for errors
grep "❌" logs/event_consumer.log

# Search for specific org
grep "beta-org-for-pustak" logs/event_consumer.log
```

### **Manual API Calls**
```bash
# Register org
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"org_id": "test-org"}'

# Check app installation
curl -X GET "http://localhost:8000/webhook/check-app-installation?org_id=test-org" \
  -H "Authorization: Bearer <JWT>"
```

---

## **TESTING CHECKLIST**

- [ ] **Test 1**: Webhook registration works
- [ ] **Test 2**: Single org event processing works
- [ ] **Test 3**: Multi-org event processing works
- [ ] **Test 4**: Missed commits detected for all orgs
- [ ] **Test 5**: Error handling works correctly

---

## **EXPECTED RESULTS SUMMARY**

| Test | Expected | Status |
|------|----------|--------|
| Webhook Registration | Org stored in DB | ✅ |
| Event Processing | Docs generated | ✅ |
| Multi-Org | Each org uses correct token | ✅ |
| Missed Commits | All orgs recovered | ✅ |
| Error Handling | Graceful fallback | ✅ |

---

## **TROUBLESHOOTING**

### **Problem: "No GitHub token found"**
```
Solution:
1. Check user_github_tokens table
2. Verify token_id in commit_events
3. Check if token is encrypted
4. Fall back to env GITHUB_TOKEN
```

### **Problem: "Webhook secret not found"**
```
Solution:
1. Check org_webhooks table
2. Verify webhook_secret matches
3. Check if org_id is correct
4. Verify signature calculation
```

### **Problem: "Event not processed"**
```
Solution:
1. Check event_consumer is running
2. Check logs for errors
3. Verify database connection
4. Check if event is in commit_events table
```

### **Problem: "Docs not generated"**
```
Solution:
1. Check smart_processor logs
2. Verify GitHub token has permissions
3. Check if repo is accessible
4. Verify git clone/push commands work
```

---

## **NEXT STEPS**

After all tests pass:
1. ✅ Run full test suite
2. ✅ Test with production data
3. ✅ Load testing (100+ orgs)
4. ✅ Deploy to staging
5. ✅ Deploy to production

**Estimated time: 1-2 hours total**
