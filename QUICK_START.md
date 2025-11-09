# 🚀 Quick Start Guide

## Starting the Application

### 1. Start API Server

```bash
./start.sh
```

✅ **Server will run at:** http://localhost:8000

- **Swagger Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc  
- **Health Check:** http://localhost:8000/health

### 2. Start Background Worker (Optional)

In a **separate terminal**, run the event consumer:

```bash
./run-worker.sh
```

This processes commit events in the background.

---

## How to Run Commands

### Start API Server
```bash
./start.sh
```

### Start Event Consumer Worker
```bash
./run-worker.sh
```

Or manually:
```bash
python -m app.worker
```

---

## What Each Component Does

### 🌐 API Server (`./start.sh`)
- **Handles HTTP requests**
- GitHub OAuth authentication
- Repository management
- Subscription management
- Documentation endpoints
- Webhook handling

### 🔄 Event Consumer (`./run-worker.sh`)
- **Processes background jobs**
- Reads from commit_events table
- Generates documentation
- Processes missed commits
- Runs independently from API server

---

## Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://localhost/lekhak_ai

# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# GitHub Apps
GITHUB_READER_PRIVATE_KEY=your_reader_key
GITHUB_WRITER_PRIVATE_KEY=your_writer_key

# LLM
OPENAI_API_KEY=your_openai_key

# Background Processing
ENABLE_EVENT_PROCESSOR=true  # Enable in-process event processing
EVENT_PROCESSOR_INTERVAL_SECONDS=60
MAX_EVENTS_PER_BATCH=100
```

---

## Event Processing Options

You have **2 options** for processing events:

### Option 1: Separate Worker Process (Recommended for Production)
```bash
# Terminal 1: API Server
./start.sh

# Terminal 2: Event Worker
./run-worker.sh
```

**Pros:** Isolation, can scale independently, better resource management

### Option 2: In-Process Background Task
Set in `.env`:
```bash
ENABLE_EVENT_PROCESSOR=true
```

Then just run:
```bash
./start.sh
```

**Pros:** Simpler setup, single process

---

## Troubleshooting

### Error: "No module named 'greenlet'"
```bash
source docai-env/bin/activate
pip install greenlet
```

### Error: "asyncio extension requires an async driver"
Check your DATABASE_URL uses `postgresql+asyncpg://` not `postgresql://`

### Error: Database connection failed
Make sure PostgreSQL is running:
```bash
# Check if database exists
psql -l | grep lekhak_ai

# Create if needed
createdb lekhak_ai
```

### Port 8000 already in use
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --port 8001
```

---

## API Endpoints

### Authentication
- `GET /api/v1/auth/github` - Start GitHub OAuth
- `GET /api/v1/auth/callback` - OAuth callback  
- `GET /api/v1/auth/me` - Get current user

### Repositories
- `GET /api/v1/repositories` - List repos
- `POST /api/v1/repositories` - Register repo
- `DELETE /api/v1/repositories/{id}` - Remove repo

### Subscriptions
- `GET /api/v1/subscriptions/plans` - Available plans
- `GET /api/v1/subscriptions/me` - Your subscription
- `POST /api/v1/subscriptions/upgrade` - Upgrade plan

### Events
- `GET /api/v1/events` - List events
- `POST /api/v1/events` - Create event
- `GET /api/v1/events/{id}` - Get event details

### Webhooks
- `POST /api/v1/webhooks/github` - GitHub webhook endpoint

---

## Development Workflow

### 1. Start Development
```bash
# Activate environment
source docai-env/bin/activate

# Start server with auto-reload
./start.sh
```

### 2. Test API
Visit http://localhost:8000/docs to test endpoints interactively

### 3. View Logs
Server logs appear in the terminal where you ran `./start.sh`

### 4. Stop Server
Press `Ctrl+C` in the terminal

---

## Production Deployment

### 1. Update Environment
```bash
# Set production database
DATABASE_URL=postgresql+asyncpg://user:pass@prod-host/pustak

# Disable debug
DEBUG=false

# Set proper secrets
JWT_SECRET=your-secure-secret
SECRET_KEY=your-secure-secret
```

### 2. Run with Gunicorn (Production)
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 3. Run Worker Separately
```bash
# Use a process manager like systemd or supervisor
python -m app.worker
```

---

## Need Help?

- **API Documentation:** http://localhost:8000/docs
- **Check Logs:** Terminal output shows all activity
- **Database Issues:** Check DATABASE_URL in `.env`
- **Worker Not Processing:** Check EVENT_PROCESSOR_INTERVAL_SECONDS

---

**✅ You're all set! Start the server and begin building!**
