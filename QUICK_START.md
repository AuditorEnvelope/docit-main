# 🚀 lekhak ai - Quick Start Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- GitHub Personal Access Token

## 🏃 Quick Start (5 minutes)

### 1. Clone and Setup

```bash
cd /Users/harshsrivastava/Desktop/doc_ai

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add to `.env`:

```env
# GitHub
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORG=AuditorEnvelope
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# LLM (choose one)
OPENAI_API_KEY=sk-your_key_here

# Database (Docker will use these)
DATABASE_URL=postgresql://lekhak:lekhak_password@localhost:5432/lekhak_ai
REDIS_URL=redis://localhost:6379
```

### 2. Start All Services

```bash
# Start everything with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Services started:**

- ✅ PostgreSQL (port 5432) - Event store & docs
- ✅ Redis (port 6379) - Job queue
- ✅ Milvus (port 19530) - Vector DB for RAG
- ✅ Commit Bus (port 8001) - Event store API
- ✅ Event Consumer - Processes commits
- ✅ Backend (port 8000) - Main API
- ✅ Frontend (port 3000) - Pustak UI

### 3. Verify Everything Works

```bash
# Check Commit Bus
curl http://localhost:8001/
# Should return: {"service": "Commit Bus", "status": "ok"}

# Check Backend
curl http://localhost:8000/
# Should return: {"service": "DocAI webhook", "status": "ok"}

# Check Frontend
open http://localhost:3000
# Should show Pustak UI
```

### 4. Test Commit Bus

```bash
# Send a test commit event
curl -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "test/repo",
    "commit_sha": "abc123",
    "parent_sha": [],
    "author_name": "Test User",
    "author_email": "test@example.com",
    "timestamp": "2025-10-15T21:00:00Z",
    "branch": "main",
    "files_changed": [{"path": "test.py", "status": "modified"}],
    "commit_message": "Test commit"
  }'

# Check if it was processed
curl http://localhost:8001/stats
# Should show: {"total": 1, "processed": 1, "pending": 0, "failed": 0}
```

### 5. Test Downtime Recovery

```bash
# Stop event consumer
docker-compose stop event_consumer

# Send 5 test commits
for i in {1..5}; do
  curl -X POST http://localhost:8001/events \
    -H "Content-Type: application/json" \
    -d "{
      \"repo_id\": \"test/repo\",
      \"commit_sha\": \"commit$i\",
      \"parent_sha\": [],
      \"author_name\": \"Test\",
      \"author_email\": \"test@example.com\",
      \"timestamp\": \"2025-10-15T21:00:00Z\",
      \"branch\": \"main\",
      \"files_changed\": [],
      \"commit_message\": \"Test commit $i\"
    }"
done

# Check pending events
curl http://localhost:8001/stats
# Should show: {"pending": 5, ...}

# Restart consumer
docker-compose start event_consumer

# Wait 30 seconds, then check again
sleep 30
curl http://localhost:8001/stats
# Should show: {"pending": 0, "processed": 6, ...}
```

**✅ Success!** All 5 commits were processed after restart.

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repositories                      │
└────────────────────┬────────────────────────────────────────┘
                     │ Webhooks
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Backend (port 8000)                                         │
│  ├─ Webhook Handler → Stores in Commit Bus                  │
│  └─ Smart Processor → Generates docs                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Commit Bus (port 8001)                                      │
│  ├─ Event Store (PostgreSQL)                                │
│  └─ API (store/retrieve/replay events)                      │
└────────────────────┬────────────────────────────────────────┘
                     │ Queue
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Event Consumer                                              │
│  ├─ Polls for unprocessed events                            │
│  ├─ Processes each commit                                   │
│  └─ Marks as processed                                      │
└────────────────────┬────────────────────────────────────────┘
                     │ Generated Docs
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                  │
│  ├─ commit_events (event store)                             │
│  ├─ doc_nodes (hierarchical docs)                           │
│  ├─ doc_overlays (admin edits)                              │
│  └─ changelogs (auto-generated)                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Frontend (port 3000)                                        │
│  └─ Pustak - Beautiful doc viewer                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Development Workflow

### Start Services Individually

```bash
# Start only database
docker-compose up -d postgres redis

# Start backend locally (for development)
cd src
source ../docai-env/bin/activate
uvicorn app:app --reload

# Start commit bus locally
python commit_bus.py

# Start event consumer locally
python event_consumer.py

# Start frontend locally
cd pustak
npm run dev
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f event_consumer
docker-compose logs -f commit_bus
docker-compose logs -f backend
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U lekhak -d lekhak_ai

# Run queries
SELECT * FROM commit_events ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM doc_nodes WHERE type = 'function';
SELECT * FROM changelogs ORDER BY timestamp DESC;

# Check stats
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE processed = TRUE) as processed,
  COUNT(*) FILTER (WHERE processed = FALSE) as pending
FROM commit_events;
```

### Redis Access

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check keys
KEYS *

# Monitor commands
MONITOR
```

---

## 🧪 Testing

### Test Commit Bus

```bash
# Run tests
cd src
pytest tests/test_commit_bus.py -v

# Test replay
python -m pytest tests/test_replay.py -v
```

### Test Event Consumer

```bash
# Create test events
python scripts/create_test_events.py --count 10

# Watch consumer process them
docker-compose logs -f event_consumer
```

### Test End-to-End

```bash
# 1. Make a real commit to your repo
cd /path/to/your/repo
echo "test" >> test.txt
git add test.txt
git commit -m "Test commit for lekhak ai"
git push

# 2. Check webhook was received
docker-compose logs backend | grep "POST /webhook"

# 3. Check event was stored
curl http://localhost:8001/events | jq

# 4. Check event was processed
docker-compose logs event_consumer | grep "Processing event"

# 5. Check docs were generated
curl http://localhost:8000/repos/your-repo/docs | jq
```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check ports are available
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Backend
lsof -i :8001  # Commit Bus
lsof -i :3000  # Frontend

# Restart everything
docker-compose down
docker-compose up -d
```

### Events not processing

```bash
# Check consumer is running
docker-compose ps event_consumer

# Check consumer logs
docker-compose logs event_consumer

# Check for pending events
curl http://localhost:8001/stats

# Manually restart consumer
docker-compose restart event_consumer
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready -U lekhak

# Reset database
docker-compose down -v  # WARNING: Deletes all data
docker-compose up -d postgres
```

### Frontend not loading

```bash
# Check frontend logs
docker-compose logs frontend

# Check environment variables
docker-compose exec frontend env | grep GITHUB

# Restart frontend
docker-compose restart frontend
```

---

## 📚 Next Steps

1. **Setup GitHub Webhook**

   - Go to your repo → Settings → Webhooks
   - Add webhook: `https://your-domain.com/webhook`
   - Secret: Use value from `.env`
   - Events: Just push events

2. **Test with Real Commits**

   - Make commits to your repo
   - Watch them flow through the system
   - Check generated docs in Pustak

3. **Explore Features**

   - View hierarchical docs
   - Check changelogs
   - Test admin overlays (coming soon)
   - Try RAG agent (coming soon)

4. **Continue Implementation**
   - See `IMPLEMENTATION_PLAN.md` for Day 2-5 tasks
   - Build hierarchical doc generator
   - Add RAG system
   - Implement admin overlays

---

## 🆘 Need Help?

- **Architecture**: See `LEKHAK_ai_ARCHITECTURE.md`
- **Explanation**: See `LEKHAK_ai_EXPLAINED.md`
- **Implementation**: See `IMPLEMENTATION_PLAN.md`
- **Database**: See `schema.sql`

---

**You now have a production-ready commit bus that never loses commits!** 🎉
