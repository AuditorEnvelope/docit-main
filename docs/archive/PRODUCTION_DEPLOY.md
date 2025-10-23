# 🚀 Production Deployment Guide

## 🎯 Quick Deploy (2 Options)

### Option 1: Minimal (No Database) - **READY NOW**

```bash
# What works:
✅ GitHub webhooks
✅ Smart doc generation
✅ Multi-LLM support
✅ Pustak frontend
✅ All existing features

# Start:
python src/main.py
```

**API Keys Needed:**
- `GITHUB_TOKEN`
- `GEMINI_API_KEY` (or GROQ_API_KEY)

---

### Option 2: Full Features (With Database)

```bash
# What you get additionally:
✅ Commit Bus (never lose commits)
✅ 14+ language support
✅ RAG system
✅ Admin overlays
✅ Subscriptions

# Setup:
createdb lekhak_ai
psql lekhak_ai < schema.sql

# Start:
docker-compose up -d
```

**Additional Keys:**
- `DATABASE_URL=postgresql://localhost/lekhak_ai`

---

## 📋 Step-by-Step Production Setup

### 1. Prerequisites

```bash
# Install PostgreSQL
brew install postgresql  # Mac
# OR
sudo apt-get install postgresql  # Linux

# Start PostgreSQL
brew services start postgresql  # Mac
# OR
sudo systemctl start postgresql  # Linux
```

### 2. Database Setup

```bash
# Create database
createdb lekhak_ai

# Run schema
psql lekhak_ai < schema.sql

# Verify
psql lekhak_ai -c "SELECT COUNT(*) FROM commit_events;"
```

### 3. Environment Configuration

```bash
# Create .env
cat > .env << EOF
# Required
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_secret_here
GEMINI_API_KEY=your_gemini_key_here

# Database
DATABASE_URL=postgresql://localhost/lekhak_ai

# Optional (for RAG)
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Optional (for OpenAI embeddings)
# OPENAI_API_KEY=sk_your_key_here
EOF
```

### 4. Install Dependencies

```bash
# Activate virtual environment
source docai-env/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Verify
pip list | grep -E "fastapi|asyncpg|pymilvus"
```

### 5. Start Services

#### Option A: Docker Compose (Recommended)

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Option B: Manual

```bash
# Terminal 1: Main API
python src/main.py

# Terminal 2: Event Consumer (optional)
python src/event_consumer.py

# Terminal 3: Frontend
cd pustak && npm run dev
```

### 6. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Feature list
curl http://localhost:8000/admin/features

# Test webhook (with valid signature)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"repository": {"full_name": "test/repo"}}'
```

---

## 🌐 Production Deployment Platforms

### Render

```yaml
# render.yaml
services:
  - type: web
    name: lekhak-ai-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python src/main.py
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: lekhak-ai-db
          property: connectionString
      - key: GITHUB_TOKEN
        sync: false
      - key: GEMINI_API_KEY
        sync: false

  - type: web
    name: lekhak-ai-frontend
    env: node
    buildCommand: cd pustak && npm install && npm run build
    startCommand: cd pustak && npm start

databases:
  - name: lekhak-ai-db
    databaseName: lekhak_ai
    user: lekhak_ai
```

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add PostgreSQL
railway add postgresql

# Deploy
railway up
```

### Vercel (Frontend Only)

```bash
cd pustak
vercel deploy --prod
```

### Heroku

```bash
# Create app
heroku create lekhak-ai

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git push heroku main

# Set env vars
heroku config:set GITHUB_TOKEN=xxx
heroku config:set GEMINI_API_KEY=xxx
```

---

## 🔒 Security Checklist

### Before Production:

- [ ] Change `GITHUB_WEBHOOK_SECRET` to strong random value
- [ ] Use environment variables (never commit `.env`)
- [ ] Enable HTTPS (use reverse proxy like nginx)
- [ ] Set up rate limiting
- [ ] Configure CORS properly (not `allow_origins=["*"]`)
- [ ] Enable database SSL
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure backups (database)
- [ ] Set up logging (structured logs)
- [ ] Use secrets manager (AWS Secrets, Vault)

### Security Updates:

```bash
# Update .env.example (remove actual keys)
# Update CORS in main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring

### Health Endpoints

```bash
# Basic health
GET /health

# Detailed status
GET /

# Feature list
GET /admin/features

# Event stats (if commit bus enabled)
GET /events/stats
```

### Logging

```python
# Add to main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics

```bash
# Install prometheus client
pip install prometheus-client

# Add metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

webhook_requests = Counter('webhook_requests_total', 'Total webhook requests')
processing_time = Histogram('processing_seconds', 'Time spent processing')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 🔄 CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          python -m pytest test_lekhak_ai.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to production
        run: |
          # Your deployment script
          ./deploy.sh
```

---

## 🎯 Performance Optimization

### Database

```sql
-- Add indexes
CREATE INDEX idx_commit_events_repo ON commit_events(repo_id);
CREATE INDEX idx_commit_events_status ON commit_events(status);
CREATE INDEX idx_doc_nodes_parent ON doc_nodes(parent_id);
```

### Caching

```bash
# Add Redis
docker run -d -p 6379:6379 redis

# Update .env
REDIS_URL=redis://localhost:6379
```

### Load Balancing

```nginx
# nginx.conf
upstream lekhak_ai {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://lekhak_ai;
    }
}
```

---

## 📈 Scaling

### Horizontal Scaling

```bash
# Run multiple API instances
python src/main.py --port 8000 &
python src/main.py --port 8001 &
python src/main.py --port 8002 &

# Use nginx for load balancing
```

### Database Scaling

```bash
# Read replicas
DATABASE_READ_URL=postgresql://replica/lekhak_ai

# Connection pooling
pip install psycopg2-pool
```

### Queue Workers

```bash
# Run multiple event consumers
python src/event_consumer.py &
python src/event_consumer.py &
python src/event_consumer.py &
```

---

## 🆘 Troubleshooting

### Common Issues

1. **"Module not found" errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database connection failed**
   ```bash
   # Check PostgreSQL is running
   pg_isready
   
   # Check connection string
   psql $DATABASE_URL
   ```

3. **Webhook signature verification failed**
   ```bash
   # Check GITHUB_WEBHOOK_SECRET matches GitHub settings
   ```

4. **Import errors in new services**
   ```bash
   # Services gracefully degrade if dependencies missing
   # Check logs for warnings
   ```

---

## ✅ Production Checklist

### Pre-Launch:
- [ ] All tests passing
- [ ] Database schema applied
- [ ] Environment variables set
- [ ] HTTPS configured
- [ ] Monitoring enabled
- [ ] Backups configured
- [ ] Error tracking (Sentry)
- [ ] Rate limiting enabled
- [ ] CORS configured
- [ ] Secrets secured

### Post-Launch:
- [ ] Monitor error rates
- [ ] Check database performance
- [ ] Verify webhook processing
- [ ] Test all features
- [ ] Monitor resource usage
- [ ] Set up alerts

---

## 🎉 You're Ready!

**Your Lekhak AI platform is production-ready!**

- ✅ Graceful degradation (works with/without database)
- ✅ Comprehensive error handling
- ✅ Scalable architecture
- ✅ Security best practices
- ✅ Monitoring ready
- ✅ CI/CD ready

**Deploy with confidence! 🚀**
