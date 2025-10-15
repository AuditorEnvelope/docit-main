# Lekhak Ki 📚

**Production-grade, AI-first documentation platform** that automatically generates and maintains comprehensive, hierarchical documentation for your repositories.

## 🎉 What's New - Complete Implementation!

✅ **All 5 Days Completed** - Full production system ready to deploy!

## 🚀 Key Features

### 🔥 Never Lose Commits
- **Durable Event Store**: PostgreSQL-backed commit bus
- **Automatic Replay**: Process missed commits after downtime
- **Retry Logic**: 3 automatic retries on failure

### 🌍 Universal Language Support (14+ Languages!)
- **Python, TypeScript, JavaScript, Go, Rust, Java, C++, C#, Ruby, PHP, Swift, Kotlin, Scala, Elixir, Dart**
- **Polyglot Repositories**: Document multiple languages in one repo
- **Automatic Detection**: No configuration needed

### 🌲 Hierarchical Documentation
- **Deep Tree Structure**: Repo → SDK → Module → Feature → Function
- **Smart Parsing**: Extracts signatures, parameters, docstrings
- **Breadcrumb Navigation**: Easy traversal

### 🤖 AI Agent with Provenance
- **Semantic Search**: Vector DB (Milvus) powered
- **Commit-Backed Answers**: Every answer cites commit SHA
- **RAG System**: Retrieval-Augmented Generation

### ✏️ Admin Overlays
- **Non-Code Edits**: Edit docs without changing code
- **Full Provenance**: Track who, when, why
- **Optional PR Generation**: Push edits back to code

### 💰 Production-Ready Subscriptions
- **3 Pricing Tiers**: Free, Team ($49/mo), Enterprise
- **Feature Gates**: Control access to overlays, SSO, etc.
- **Usage Tracking**: Repos, queries, storage

## 🎯 Quick Start (No OpenAI Required!)

### Minimal Setup (3 Steps)

```bash
# 1. Install dependencies

## 🆕 Recent Updates

### Initial Implementation of Lekhak AI Service with Embeddings and RAG
This monumental commit introduces the core Lekhak AI service, establishing a robust architecture for contextual AI assistance in code. It integrates a commit bus for event processing, an indexing service leveraging a vector database (Milvus) for embeddings, and a RAG (Retrieval Augmented Generation) system to interact with various LLMs (Groq, OpenAI, Google Generative AI). This forms the foundational AI capabilities of the project.

**New Features:**
- Lekhak AI Core Service for RAG and Embeddings
- Commit Bus (AsyncPG) for event-driven architecture
- Event Consumer for processing commit events
- Indexer Service for vectorizing code/docs and storing in Milvus
- Integration with Milvus vector database
- Support for multiple LLM providers (Groq, OpenAI, Google Generative AI)
- Local embeddings generation via Sentence Transformers
- Hierarchical Document Generation for structured knowledge base
- Universal Code Parser for diverse language support
- Subscription Service for external event sources (e.g., webhooks)
- Agent Service for orchestrating AI tasks
- Overlay Service (likely for presenting AI-generated insights)
- Comprehensive documentation for architecture, quick start, and implementation

*Added on 2025-10-15*

pip install -r requirements.txt

# 2. Setup database
createdb lekhak_ki
psql lekhak_ki < schema.sql

# 3. Create .env (only 2 required keys!)
cat > .env << EOF
GITHUB_TOKEN=ghp_your_token
GEMINI_API_KEY=your_gemini_key
DATABASE_URL=postgresql://localhost/lekhak_ki
EOF

# 4. Start everything
docker-compose up -d
```

**That's it! 80% of features work with just these 2 API keys!** ✅

### What You Get

- ✅ Commit Bus (never lose commits)
- ✅ Code parsing (14+ languages)
- ✅ Hierarchical docs
- ✅ Admin overlays
- ✅ Subscriptions
- ⚠️ RAG/Embeddings (optional - needs Milvus)

## 📁 Project Structure

```
lekhak_ki/
├── src/                                    # Backend services
│   ├── commit_bus.py                       # Event store (Day 1)
│   ├── event_consumer.py                   # Event processor (Day 1)
│   ├── hierarchical_doc_generator.py       # Tree builder (Day 2)
│   ├── universal_code_parser.py            # Multi-language parser (Day 2)
│   ├── indexer_service.py                  # Vector DB (Day 3)
│   ├── agent_service.py                    # RAG agent (Day 3)
│   ├── overlay_service.py                  # Admin edits (Day 4)
│   ├── subscription_service.py             # Feature gates (Day 5)
│   └── lekhak_ki_integration.py            # Complete pipeline
├── pustak/                                 # Frontend (Next.js)
├── schema.sql                              # Database (13 tables)
├── docker-compose.yml                      # Complete infrastructure
├── test_lekhak_ki.py                       # Test suite
├── COMPLETE_IMPLEMENTATION.md              # Full docs
├── LANGUAGE_SUPPORT.md                     # Language guide
└── READY_TO_PUSH.md                        # Pre-push checklist
```

## 🔧 Configuration

### Required (2 keys only!)

```env
GITHUB_TOKEN=ghp_your_token              # ✅ Required
GEMINI_API_KEY=your_gemini_key           # ✅ Required (or Groq)
DATABASE_URL=postgresql://localhost/lekhak_ki
```

### Optional

```env
# OpenAI (only for embeddings - can use free alternatives)
OPENAI_API_KEY=sk_xxx                    # ❌ Optional

# Vector DB (only for RAG)
MILVUS_HOST=localhost                    # ❌ Optional
MILVUS_PORT=19530                        # ❌ Optional
# OR
GOOGLE_API_KEY=your_gemini_key
# OR
GROQ_API_KEY=your_groq_key
```

**Frontend (pustak/.env.local)**:
```env
GITHUB_TOKEN=your_github_token
GITHUB_ORG=your_org_name
```

## 📖 How It Works

1. **Commit Detection**: GitHub webhook triggers on push events
2. **Change Analysis**: Smart processor analyzes commit changes
3. **Documentation Generation**: LLM generates comprehensive docs
4. **Version Management**: Tracks versions (v1, v2, etc.)
5. **Display**: Pustak renders beautiful documentation

## 🎨 Pustak Features

- **Multi-Repository Support**: View docs for multiple repos
- **Version Navigation**: Browse different documentation versions
- **Dark/Light Theme**: Beautiful UI with theme support
- **Markdown Rendering**: Rich markdown with syntax highlighting
- **Search**: Quick search across documentation
- **Responsive**: Works on all devices

## 📚 Documentation

- [Quick Start Guide](QUICK_START_GUIDE.md) - Get started quickly
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Deploy to production
- [API Documentation](docs/api.md) - API endpoints
- [Architecture](docs/architecture/current.md) - System architecture
- [Workflow](docs/workflow/current.md) - Development workflow

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with FastAPI, Next.js, and TailwindCSS
- Powered by OpenAI, Google Gemini, and Groq
- Inspired by GitBook

---

**Made with ❤️ by the DocAI team**
