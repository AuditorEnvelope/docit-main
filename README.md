# Lekhak AI

**AI-powered documentation system** that automatically analyzes codebases and generates comprehensive, hierarchical documentation with intelligent insights.

## System Overview

Lekhak AI is a production-grade documentation platform that transforms code analysis into structured, searchable documentation. The system processes Git commits, analyzes code patterns, and generates documentation with AI assistance.

**Core Capabilities:**
- **Intelligent Code Analysis** - Multi-language parsing with AST analysis
- **Hierarchical Documentation** - SDK → Module → Feature → Function structure
- **Event-Driven Processing** - GitHub webhook integration with durable event storage
- **AI-Enhanced Descriptions** - LLM-powered code documentation generation
- **Version Management** - Semantic versioning with change tracking

## Quick Start

### Basic Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (minimal setup)
export GITHUB_TOKEN="ghp_your_token"
export GEMINI_API_KEY="your_gemini_key"

# Start the server
python src/main.py
```

### Database Setup (Optional)

```bash
# Create PostgreSQL database
createdb lekhak_ai

# Run schema
psql lekhak_ai < schema.sql

# Add to environment
export DATABASE_URL="postgresql://localhost/lekhak_ai"

# Start with Docker
docker-compose up -d
```

## Architecture

### System Components
- **Event Consumer** - Processes GitHub webhooks and analyzes commits
- **Smart Processor** - AI-powered code analysis and documentation generation
- **Document Generator** - Creates hierarchical documentation structure
- **Commit Bus** - Durable event storage with replay capabilities

### Data Flow
1. GitHub webhook → Event Consumer → Commit Bus (storage)
2. Smart Processor → Code Analysis → LLM Enhancement → Documentation Generation
3. Generated docs → Version control → GitHub commit

## Configuration

### Required Environment Variables
```bash
GITHUB_TOKEN=ghp_your_github_token        # For webhook processing
GEMINI_API_KEY=your_gemini_key             # For AI documentation
```

### Optional Variables
```bash
DATABASE_URL=postgresql://localhost/lekhak_ai  # For commit bus
OPENAI_API_KEY=sk_your_openai_key             # For embeddings
MILVUS_HOST=localhost                         # For vector search
```

## API Endpoints

- `POST /webhook` - GitHub webhook handler
- `GET /api/repos/{repo}/tree` - Get hierarchical documentation
- `GET /api/repos/{repo}/search` - Search documentation
- `GET /events/stats` - Event processing statistics

**Analysis Features:**
- AST parsing and code structure analysis
- Import/dependency tracking
- Function signature extraction
- Design pattern detection
- Framework identification
