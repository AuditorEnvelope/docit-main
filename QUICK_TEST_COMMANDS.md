# ⚡ QUICK TEST COMMANDS - COPY & PASTE

## **SETUP COMMANDS**

### Start Backend
```bash
cd /Users/harshsrivastava/Desktop/doc_ai
python src/core/main.py
```

### Start Event Consumer
```bash
cd /Users/harshsrivastava/Desktop/doc_ai
python src/core/event_consumer.py
```

### Start Frontend
```bash
cd /Users/harshsrivastava/Desktop/doc_ai/pustak
npm run dev
```

---

## **TEST 1: WEBHOOK REGISTRATION**

### Register Organization
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "beta-org-for-pustak"
  }'
```

### Expected Response
```json
{
  "status": "registered",
  "org_id": "beta-org-for-pustak",
  "webhook_url": "https://xxxxx.ngrok.io/webhook",
  "message": "Organization 'beta-org-for-pustak' registered!..."
}
```

### Verify in Database
```bash
psql -U postgres -d lekhak_ai -c "SELECT * FROM org_webhooks WHERE org_id = 'beta-org-for-pustak';"
```

---

## **TEST 2: EVENT PROCESSING**

### Push Code to GitHub
```bash
cd /path/to/your/repo
git commit --allow-empty -m "Test commit for multi-org"
git push origin main
```

### Watch Event Consumer Logs
```bash
tail -f logs/event_consumer.log
```

### Check Database for Event
```bash
psql -U postgres -d lekhak_ai -c "
  SELECT repo_id, org_id, processed 
  FROM commit_events 
  WHERE repo_id LIKE '%beta-org-for-pustak%' 
  ORDER BY created_at DESC LIMIT 5;
"
```

### Check GitHub for Generated Docs
```bash
# Go to: https://github.com/beta-org-for-pustak/College-ERP
# Look for /docs folder and recent commits from docai-bot
```

---

## **TEST 3: MULTI-ORG REGISTRATION**

### Register Org 2
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id": "another-org"}'
```

### Register Org 3
```bash
curl -X POST http://localhost:8000/webhook/register \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id": "testing-org"}'
```

### Verify All Registered
```bash
psql -U postgres -d lekhak_ai -c "SELECT org_id, webhook_secret FROM org_webhooks;"
```

### Push to Each Org
```bash
# Org 1
cd /path/to/org1/repo && git commit --allow-empty -m "Test org 1" && git push

# Org 2
cd /path/to/org2/repo && git commit --allow-empty -m "Test org 2" && git push

# Org 3
cd /path/to/org3/repo && git commit --allow-empty -m "Test org 3" && git push
```

### Verify Each Org Processed
```bash
# Watch logs - should see:
# ✅ Got GitHub token for user ... org beta-org-for-pustak
# ✅ Got GitHub token for user ... org another-org
# ✅ Got GitHub token for user ... org testing-org
```

---

## **TEST 4: MISSED COMMITS DETECTION**

### Push Commits While Consumer Running
```bash
for i in {1..5}; do
  git commit --allow-empty -m "Commit $i"
  git push
done
```

### Stop Event Consumer
```bash
# Press Ctrl+C in the terminal where it's running
# Or: kill <PID>
```

### Push More Commits (While Stopped)
```bash
for i in {6..10}; do
  git commit --allow-empty -m "Missed commit $i"
  git push
done
```

### Start Event Consumer Again
```bash
python src/core/event_consumer.py
```

### Watch for Missed Commits Recovery
```bash
# Should see in logs:
# 🔍 Checking for missed commits across all orgs...
# ✅ Found X missed commits for org/repo
# 🎉 Successfully recovered X missed commits across all orgs!
```

### Verify All Processed
```bash
psql -U postgres -d lekhak_ai -c "
  SELECT COUNT(*) as total_events, 
         COUNT(CASE WHEN processed = true THEN 1 END) as processed
  FROM commit_events;
"
```

---

## **DATABASE QUERIES**

### View All Registered Orgs
```bash
psql -U postgres -d lekhak_ai -c "SELECT org_id, webhook_secret FROM org_webhooks;"
```

### View All Events
```bash
psql -U postgres -d lekhak_ai -c "SELECT repo_id, org_id, processed FROM commit_events ORDER BY created_at DESC LIMIT 20;"
```

### View Unprocessed Events
```bash
psql -U postgres -d lekhak_ai -c "SELECT repo_id, org_id FROM commit_events WHERE processed = FALSE;"
```

### Count Events by Org
```bash
psql -U postgres -d lekhak_ai -c "SELECT org_id, COUNT(*) as count FROM commit_events GROUP BY org_id;"
```

### View GitHub Tokens
```bash
psql -U postgres -d lekhak_ai -c "SELECT user_id, org_id, is_active FROM user_github_tokens;"
```

### Delete All Test Data
```bash
psql -U postgres -d lekhak_ai -c "
  DELETE FROM commit_events WHERE org_id IN ('beta-org-for-pustak', 'another-org', 'testing-org');
  DELETE FROM org_webhooks WHERE org_id IN ('beta-org-for-pustak', 'another-org', 'testing-org');
"
```

---

## **LOG MONITORING**

### Real-time Logs
```bash
tail -f logs/event_consumer.log
```

### Last 50 Lines
```bash
tail -50 logs/event_consumer.log
```

### Search for Errors
```bash
grep "❌" logs/event_consumer.log
```

### Search for Specific Org
```bash
grep "beta-org-for-pustak" logs/event_consumer.log
```

### Search for Success
```bash
grep "✅" logs/event_consumer.log
```

---

## **API ENDPOINTS**

### Register Webhook
```bash
POST /webhook/register
Authorization: Bearer <JWT>
Content-Type: application/json
Body: {"org_id": "org-name"}
```

### Check App Installation
```bash
GET /webhook/check-app-installation?org_id=org-name
Authorization: Bearer <JWT>
```

### Get User Organizations
```bash
GET /auth/user/organizations
Authorization: Bearer <JWT>
```

---

## **TESTING CHECKLIST**

- [ ] Backend running on http://localhost:8000
- [ ] Event consumer running
- [ ] Frontend running on http://localhost:3000
- [ ] Database migration completed
- [ ] Test org registered
- [ ] Push event received
- [ ] Event processed successfully
- [ ] Docs generated in GitHub
- [ ] Multi-org test passed
- [ ] Missed commits detected
- [ ] All events marked as processed

---

## **TROUBLESHOOTING QUICK FIXES**

### Event Not Processing?
```bash
# Check if consumer is running
ps aux | grep event_consumer

# Check logs
tail -50 logs/event_consumer.log

# Check database connection
psql -U postgres -d lekhak_ai -c "SELECT 1;"

# Check unprocessed events
psql -U postgres -d lekhak_ai -c "SELECT COUNT(*) FROM commit_events WHERE processed = FALSE;"
```

### Webhook Not Registered?
```bash
# Check org_webhooks table
psql -U postgres -d lekhak_ai -c "SELECT * FROM org_webhooks;"

# Check if user_id is correct
psql -U postgres -d lekhak_ai -c "SELECT * FROM users LIMIT 1;"

# Check if token exists
psql -U postgres -d lekhak_ai -c "SELECT * FROM user_github_tokens LIMIT 1;"
```

### Docs Not Generated?
```bash
# Check smart_processor logs
grep "smart_processor" logs/event_consumer.log

# Check if token has permissions
# Try manually cloning with token:
git clone https://x-access-token:YOUR_TOKEN@github.com/org/repo.git

# Check if repo is accessible
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/org/repo
```

---

## **EXPECTED LOG OUTPUTS**

### Successful Registration
```
✅ Webhook registered for org: beta-org-for-pustak
📚 Webhook secret: iUy1-fNxjT0EhfXmEDll69kDpHuoPljUUWDxYaS8OY
```

### Successful Event Processing
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

### Successful Missed Commits Recovery
```
🔍 Checking for missed commits across all orgs...
📚 Found 2 unique repos across orgs

🔍 Checking beta-org-for-pustak/repo1...
✅ Found 5 missed commits for beta-org-for-pustak/repo1

🎉 Successfully recovered 5 missed commits across all orgs!
```
