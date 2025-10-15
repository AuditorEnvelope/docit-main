# 🧪 Downtime Test - Never Lose Commits

## 🎯 Test Scenario

We'll simulate:
1. Server is DOWN
2. You push commits to GitHub
3. Server comes back UP
4. All commits are processed automatically

---

## 📝 Step-by-Step Test

### Step 1: Make Architectural Changes (Server DOWN)

I've created test files that you'll commit while server is down:

```bash
# These files are ready to commit
- src/test_architecture.py
- src/test_feature.py
- ARCHITECTURE_CHANGES.md
```

### Step 2: Commit While Server is DOWN

```bash
# Make sure server is stopped
# Then commit these changes

git add .
git commit -m "feat: architectural changes while server was down"
git push origin main
```

### Step 3: Start Server (After 10 mins)

```bash
# Start main API
python src/main.py

# In another terminal, start Event Consumer
python src/event_consumer.py
```

### Step 4: Manually Trigger Replay

Since GitHub webhook failed (server was down), manually replay:

```bash
# Option A: Use the replay endpoint
curl -X POST http://localhost:8000/events/replay

# Option B: Simulate the webhook manually
./test_webhook.sh
```

---

## ✅ What Will Happen

1. **Server was down** → GitHub webhook failed
2. **You start server** → Nothing happens yet (webhook already failed)
3. **You trigger replay** → Event Consumer processes all pending events
4. **Docs get generated** → Your architectural changes are documented!

---

## 🎯 Better Solution: GitHub Webhook Retry

GitHub automatically retries failed webhooks:
- Retry 1: Immediately
- Retry 2: After 1 minute
- Retry 3: After 5 minutes
- Retry 4: After 30 minutes
- Retry 5: After 1 hour

So if you start server within 1 hour, GitHub will retry and succeed!

---

## 📊 Test Files Created

I've created these files for you to commit:

1. `src/test_architecture.py` - New architecture component
2. `src/test_feature.py` - New feature
3. `ARCHITECTURE_CHANGES.md` - Documentation

**Commit these while server is down!**
