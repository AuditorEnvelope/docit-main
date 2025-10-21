# Lekhak AI 📚

**Production-grade, AI-first documentation platform** that automatically generates and maintains comprehensive, hierarchical documentation for your repositories.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🚀 What is Lekhak AI?

Lekhak AI transforms your codebase into intelligent, searchable documentation automatically. No manual writing, no outdated docs, no lost commits.

**Key Differentiators:**
- 🔥 **Never lose commits** - Durable event store with replay
- 🌍 **14+ languages** - Python, TypeScript, Go, Rust, Java, C++, and more
- 🤖 **AI-powered Q&A** - Ask questions, get answers with commit provenance
- ✏️ **Non-code edits** - Update docs without touching code
- 💰 **Monetization ready** - Built-in subscription management

---

## ⚡ Quick Start (2 Minutes)

### Option 1: Minimal Setup (Works Immediately)

```bash
# 1. Install

## 🆕 Recent Updates

### Activate Automatic Hierarchical Documentation Generation
This change integrates and activates the `hierarchical_doc_generator` into the main application execution flow and file processing logic, ensuring hierarchical documentation is generated automatically.

**New Features:**
- Automatic hierarchical documentation generation during application runtime
- Automatic hierarchical documentation generation during file processing

*Added on 2025-10-21*

pip install -r requirements.txt

# 2. Configure (only 2 keys needed!)
cat > .env << EOF
GITHUB_TOKEN=ghp_your_token
GEMINI_API_KEY=your_gemini_key
EOF

# 3. Run
python src/main.py
```

**✅ You now have:**
- GitHub webhook processing
- Smart doc generation
- Multi-LLM support (Gemini/Groq)
- All core features

### Option 2: Full Features (+ Database)

```bash
# Additional setup for advanced features
createdb lekhak_ai
psql lekhak_ai < schema.sql

# Add to .env
DATABASE_URL=postgresql://localhost/lekhak_ai

# Start all services
docker-compose up -d
```

**✅ You now also have:**
- Commit Bus (never lose commits)
- RAG system with semantic search
- Admin overlays
- Subscription management

---

### 1. 🔥 Never Lose Commits
Durable event store ensures no commits are lost during downtime. Automatic replay processes all missed events.

### 2. 🌍 14+ Languages Supported
Python • TypeScript • JavaScript • Go • Rust • Java • C++ • C# • Ruby • PHP • Swift • Kotlin • Scala • Elixir • Dart

### 3. 🤖 AI-Powered Q&A
Ask questions in natural language, get answers with exact commit references and file locations.

### 4. ✏️ Admin Overlays
Edit documentation without touching code. Full provenance tracking with optional PR generation.

### 5. 💰 Subscription Management
Built-in plans (Free, Team, Enterprise) with feature gates and usage tracking.

**[See complete feature list →](FEATURES.md)**

---

## 📁 Project Structure

```
lekhak-ai/
├── src/
│   ├── main.py                          # 🆕 Production app (all features)
│   ├── app.py                           # Legacy app (minimal)
│   ├── commit_bus.py                    # Event store
│   ├── hierarchical_doc_generator.py    # Tree builder
│   ├── universal_code_parser.py         # Multi-language parser
│   ├── indexer_service.py               # Vector DB integration
│   ├── agent_service.py                 # RAG agent
│   ├── overlay_service.py               # Admin edits
│   └── subscription_service.py          # Feature gates
├── pustak/                              # Frontend (Next.js)
├── schema.sql                           # Database schema (13 tables)
├── docker-compose.yml                   # Infrastructure
├── FEATURES.md                          # Complete feature list
├── PRODUCTION_DEPLOY.md                 # Deployment guide
└── LANGUAGE_SUPPORT.md                  # Language documentation
```

---

## 🔧 Configuration

**Minimum Required (2 keys):**
```env
GITHUB_TOKEN=ghp_xxx
GEMINI_API_KEY=xxx
```

**For Full Features:**
```env
DATABASE_URL=postgresql://localhost/lekhak_ai
```

**Optional:**
```env
OPENAI_API_KEY=sk_xxx          # For OpenAI embeddings
MILVUS_HOST=localhost          # For vector search
```

---

## 📚 Documentation

- **[FEATURES.md](FEATURES.md)** - Complete feature list with examples
- **[PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md)** - Deployment guide
- **[LANGUAGE_SUPPORT.md](LANGUAGE_SUPPORT.md)** - Language support details
- **[API Documentation](docs/api.md)** - API endpoints
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 🚀 Deployment

### Local Development
```bash
python src/main.py
```

### Docker
```bash
docker-compose up -d
```

### Production
See [PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md) for Render, Railway, Heroku, and Vercel deployment guides.

---

## 🎯 Use Cases

- **Multi-language SDKs** - Document Python, Go, TypeScript SDKs in one place
- **API Documentation** - Auto-generate from code with examples
- **Internal Knowledge Base** - Searchable docs with AI Q&A
- **Migration Guides** - Track changes across versions
- **Developer Onboarding** - New devs ask questions, get exact code references

---

## 📊 Tech Stack

**Backend:** FastAPI • PostgreSQL • Milvus • Redis  
**Frontend:** Next.js • React • TailwindCSS • Shadcn/ui  
**AI:** Gemini • Groq • OpenAI • Sentence Transformers  
**Infrastructure:** Docker • Docker Compose

---

## 📝 License

MIT License - see LICENSE file for details

---

**Built with ❤️ for developers who hate writing docs**
