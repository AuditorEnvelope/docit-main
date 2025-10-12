# Quick Start Guide - Test Your New Documentation System

## 🚀 5-Minute Test

### Step 1: Start DocAI Backend (Terminal 1)

```bash
cd /Users/harshsrivastava/Desktop/doc_ai
source docai-env/bin/activate
python app.py
```

**You should see**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Gemini provider initialized
✅ Groq provider initialized
🚀 Initialized 3 LLM providers
```

### Step 2: Start Pustak Frontend (Terminal 2)

```bash
cd /Users/harshsrivastava/Desktop/doc_ai/pustak
npm run dev
```

**You should see**:
```
▲ Next.js 15.5.4 (Turbopack)
- Local:        http://localhost:3000
✓ Ready in 1090ms
```

### Step 3: Make a Test Commit (Terminal 3)

```bash
# Go to any monitored repo (e.g., lekhak_ai itself)
cd /Users/harshsrivastava/Desktop/doc_ai

# Make an empty commit to trigger DocAI
git commit --allow-empty -m "Test: Comprehensive documentation generation"
git push
```

### Step 4: Watch DocAI Logs (Terminal 1)

You'll see something like:
```
📁 Changed files: 0 files
🗑️  Removed files: 0 files
RUN: git clone ...
RUN: git checkout --detach abc123...
✅ Gemini provider initialized
🔄 Trying Gemini (attempt 1)
✅ Success with Gemini
✅ Significant change detected: Test comprehensive documentation

🔍 Checking documentation quality...
📊 Checking documentation quality...
📋 Quality Report: {
  "summary_exists": true,
  "summary_quality": 4,
  "architecture_exists": false,
  "architecture_quality": 0,
  "workflow_exists": false,
  "workflow_quality": 0,
  "needs_generation": ["summary", "architecture", "workflow", "api"]
}

📝 Generating comprehensive README/Summary...
🔄 Generating comprehensive summary with LLM...
✅ Created docs/SUMMARY.md
✅ Updated README.md

🏗️  Generating architecture documentation...
🔄 Generating architecture v1 with LLM...
✅ Created docs/architecture/v1-architecture.md
✅ Updated docs/architecture/current.md

🔄 Generating workflow documentation...
🔄 Generating workflow v1 with LLM...
✅ Created docs/workflow/v1-workflow.md
✅ Updated docs/workflow/current.md

📡 Generating API documentation...
🔄 Generating API documentation with LLM...
✅ Created docs/api.md

✅ Updated docs/SUMMARY.md
✅ Comprehensive documentation generation complete!

📝 Created detailed change documentation: ...
📝 Updated CHANGELOG.md
📝 Updated SUMMARY.md for GitBook navigation
RUN: git add docs/ README.md CHANGELOG.md || true
RUN: git commit -m 'docs: ...'
RUN: git push ...
✅ Documentation changes committed and pushed
```

### Step 5: Check Pustak (Browser)

1. **Open**: http://localhost:3000
2. **Click**: On "lekhak_ai" (or your test repo)
3. **Navigate** to:
   - **Summary** - Should show comprehensive README
   - **Architecture** - Should show v1 Architecture
   - **Workflow** - Should show v1 Workflow
   - **API** - Should show API documentation

## 🎯 What to Expect

### Summary Page (Before vs After)

**Before** (Your screenshot):
```
Summary
• Home
• DOC_AI_RUN_LOG
• processor.py

Changes
• [Links to changes]
```

**After** (Now):
```
# DocAI - Intelligent Documentation Generator

## Overview
DocAI is an intelligent documentation generation system that automatically
creates and maintains comprehensive documentation for your codebase...

## Architecture
- FastAPI backend for webhook handling
- Multi-provider LLM support (Gemini, Groq, DeepSeek)
- Smart change analysis and documentation generation
- GitBook integration for beautiful docs

## Getting Started
### Prerequisites
- Python 3.8+
- GitHub App credentials
- LLM API keys

### Installation
1. Clone the repository
2. Install dependencies: pip install -r requirements.txt
3. Configure environment variables
4. Run: python app.py

## Usage
[Detailed usage examples...]

## Project Structure
```
/
├── app.py                 # Main FastAPI application
├── smart_processor.py     # Smart documentation processor
├── comprehensive_doc_generator.py  # Doc generation engine
├── llm_provider_v2.py    # Multi-provider LLM interface
└── docs/                  # Generated documentation
```

## API Overview
[API endpoints and usage...]

## Development
[Development guide...]

## Documentation
- [Architecture](architecture/current.md)
- [Workflow](workflow/current.md)
- [API Reference](api.md)
- [Recent Changes](changes/)
```

### Architecture Page

```
# Architecture v1

## System Overview
DocAI is built as a microservices architecture with the following components:

### Core Components

#### 1. Webhook Handler (app.py)
- Receives GitHub webhook events
- Validates payloads
- Routes to appropriate processors
- FastAPI-based REST API

#### 2. Smart Processor (smart_processor.py)
- Analyzes code changes
- Determines significance
- Orchestrates documentation generation
- Manages git operations

#### 3. Documentation Generator (comprehensive_doc_generator.py)
- Quality assessment engine
- Codebase analyzer
- LLM-powered content generation
- Versioning system

#### 4. LLM Provider (llm_provider_v2.py)
- Multi-provider support (Gemini, Groq, DeepSeek)
- Automatic failover
- Rate limiting
- Response caching

## Technology Stack
- **Backend**: Python 3.8+, FastAPI
- **LLM**: Google Gemini, Groq, DeepSeek
- **VCS**: GitHub API, GitPython
- **Documentation**: Markdown, GitBook

## Data Flow
1. GitHub sends webhook → FastAPI receives
2. Smart Processor analyzes changes
3. Documentation Generator assesses quality
4. LLM generates comprehensive docs
5. Git commits and pushes
6. Pustak displays

## Scalability
- Stateless design for horizontal scaling
- Async processing with FastAPI
- LLM provider rotation for reliability

## Security
- GitHub App authentication
- Webhook signature verification
- Environment-based secrets
- No hardcoded credentials

[More detailed sections...]
```

### Workflow Page

```
# Workflow v1

## Development Workflow

### Setup
1. Clone repository:
   ```bash
   git clone https://github.com/AuditorEnvelope/doc_ai.git
   cd doc_ai
   ```

2. Create virtual environment:
   ```bash
   python -m venv docai-env
   source docai-env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

### Development Process
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Test locally
4. Commit: `git commit -m "feat: your feature"`
5. Push: `git push origin feature/your-feature`
6. Create Pull Request

## Deployment Workflow

### Staging Deployment
1. Merge to `develop` branch
2. Automatic deployment to staging
3. Run smoke tests
4. Validate documentation generation

### Production Deployment
1. Create release PR from `develop` to `main`
2. Review and approve
3. Merge to `main`
4. Tag release: `git tag v1.0.0`
5. Push tag: `git push --tags`
6. Automatic deployment to production

## CI/CD Pipeline
[Pipeline stages...]

[More detailed sections...]
```

## 🧪 Test Versioning

### Make a Major Architectural Change

```bash
cd /Users/harshsrivastava/Desktop/doc_ai

# Create a significant architectural change
echo "# New Database Architecture" > database_refactor.md
git add database_refactor.md
git commit -m "Major refactor: New database architecture with PostgreSQL"
git push
```

**Expected Result**:
- DocAI detects major architectural change
- Creates `docs/architecture/v2-architecture.md`
- Updates `docs/architecture/current.md`
- Updates `docs/SUMMARY.md`

**In Pustak, you'll see**:
```
Architecture
├── V2 Architecture (current) ← NEW!
└── V1 Architecture (previous)
```

## 📊 Monitoring

### Check Documentation Quality

```bash
# After DocAI runs, check the generated docs
cd /Users/harshsrivastava/Desktop/doc_ai

# View generated summary
cat docs/SUMMARY.md

# View architecture
cat docs/architecture/v1-architecture.md

# View workflow
cat docs/workflow/v1-workflow.md

# View API docs
cat docs/api.md
```

### Check Pustak Display

1. Visit http://localhost:3000
2. Click on repo
3. Navigate through sections
4. Verify content is comprehensive
5. Check width is comfortable (wider now!)

## 🎯 Success Criteria

✅ **DocAI Logs show**:
- Quality checking
- Documentation generation
- Version creation (if applicable)
- Successful commit and push

✅ **GitHub shows**:
- New commit from docai-bot
- Updated docs/ directory
- New/updated SUMMARY.md
- Architecture/workflow versions

✅ **Pustak shows**:
- Comprehensive Summary (not just links!)
- Detailed Architecture
- Step-by-step Workflow
- Complete API docs
- Wider content area
- Beautiful formatting

## 🐛 Troubleshooting

### DocAI not generating docs?
```bash
# Check logs for errors
# Verify LLM API keys
echo $GEMINI_API_KEY
echo $GROQ_API_KEY

# Test LLM connection
python -c "from llm_provider_v2 import get_rotator; r = get_rotator(); print(r.generate('test', max_tokens=10))"
```

### Pustak not showing new docs?
```bash
# Wait 30 seconds for cache to expire
# Hard refresh: Cmd+Shift+R
# Check GitHub to verify docs were pushed
```

### Quality score too low?
```bash
# Check the quality assessment in logs
# Adjust threshold in comprehensive_doc_generator.py if needed
# QUALITY_THRESHOLD = 7  # Lower this if needed
```

## 🎉 You're Done!

If you see:
- ✅ Comprehensive Summary
- ✅ Detailed Architecture
- ✅ Step-by-step Workflow
- ✅ Complete API docs
- ✅ Wider, comfortable layout

**Congratulations! Your vision is now reality!** 🚀✨

## 📚 Next Steps

1. **Monitor**: Watch a few more commits to see the system in action
2. **Test Versioning**: Make major changes to see v2, v3 creation
3. **Customize**: Adjust quality thresholds and triggers as needed
4. **Enjoy**: Never write documentation manually again!

---

**Questions? Check `COMPREHENSIVE_DOCUMENTATION_SYSTEM.md` for full details!**
