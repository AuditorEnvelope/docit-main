# Architecture v1.0

## System Overview

Lekhak AI is built as a **distributed event-driven system** with three main processing stages. The architecture follows a **microservices pattern** with clear separation of concerns and **async processing** throughout.

```
GitHub Webhook → Event Consumer → Smart Analysis → Documentation Generation → Git Commit
                     ↓                    ↓                    ↓
              Commit Bus Storage    LLM Enhancement    Version Control
                     ↓                    ↓                    ↓
              Durable Events       AI-Powered Docs    Auto-Push to GitHub
```

## Core Components

### Event Consumer (`src/main.py`)
**Purpose:** Handles GitHub webhooks and orchestrates the documentation pipeline

**Key Implementation:**
```python
@app.post("/webhook")
async def webhook(request: Request, x_hub_signature_256: str = Header(None)):
    """GitHub webhook handler with signature verification"""
    body = await request.body()
    if not verify_signature(WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    if x_github_event == "push":
        background_tasks.add_task(process_commit_event, payload)
```

**Responsibilities:**
- HMAC signature verification for security
- Background task processing to avoid blocking
- Event routing to appropriate handlers

### Smart Processor (`src/smart_processor.py`)
**Purpose:** AI-powered code analysis and documentation generation engine

**Key Implementation:**
```python
def smart_analyze_change(payload, repo_dir, changed_files, removed_files):
    """Multi-stage analysis pipeline"""
    # 1. Pattern analysis
    file_analysis = analyze_file_patterns(changed_files, removed_files)

    # 2. Git diff context extraction
    diff_context = get_git_diff_context(repo_dir, changed_files)

    # 3. LLM-powered significance assessment
    analysis_prompt = f"""You are DocAI, an expert code analysis AI..."""
    result = rotator.generate_with_rotation(analysis_prompt)

    return analysis  # JSON response with type, significance, impact
```

**Advanced Features:**
- **Multi-language AST parsing** (Python, TypeScript, JavaScript, Go, Rust, Java, C++)
- **Import dependency tracking** with usage frequency analysis
- **Design pattern detection** across 20+ patterns
- **Framework identification** (FastAPI, React, Django, etc.)
- **Technology stack analysis** (databases, deployment tools)

### Document Generator (`src/comprehensive_doc_generator.py`)
**Purpose:** Creates comprehensive documentation with quality assessment

**Key Implementation:**
```python
def generate_comprehensive_documentation(repo_dir, analysis, changed_files):
    """Main documentation orchestrator"""
    docs_dir = Path(repo_dir) / "docs"

    # 1. Quality assessment
    quality_report = check_documentation_quality(repo_dir)

    # 2. Conditional generation based on quality
    if quality_report["architecture_quality"] < 8:
        generate_versioned_architecture(repo_dir, docs_dir, analysis)

    # 3. Update navigation
    update_summary_navigation(docs_dir)
```

**Quality Management:**
- **Dynamic quality assessment** using LLM evaluation
- **Semantic versioning** (v1.0, v1.1, v2.0) instead of incremental
- **Content freshness detection** to avoid unnecessary regeneration

## Technology Stack

### Backend Technologies
- **FastAPI** - Modern async web framework with automatic OpenAPI generation
- **AsyncPG** - High-performance PostgreSQL client with connection pooling
- **Pydantic** - Data validation and serialization
- **Python 3.8+** - Type hints and modern async/await patterns

### AI Integration
- **LLM Rotator** - Automatic failover between Gemini, Groq, and DeepSeek
- **Intelligent caching** - Reduces API costs with smart cache management
- **Fallback mechanisms** - Ensures functionality even when LLMs are unavailable

### Database & Storage
- **PostgreSQL** - Primary database for event storage and metadata
- **AsyncPG** - Non-blocking database operations
- **Connection pooling** - Efficient resource management

### Deployment & Infrastructure
- **Docker** - Containerization with multi-stage builds
- **GitHub Actions** - CI/CD pipeline automation
- **Environment-based configuration** - 12-factor app compliance

## Design Patterns Used

### Event-Driven Architecture
```python
async def process_commit_event(payload: dict):
    """Process commit event through commit bus or legacy processor"""
    if commit_bus:
        # Durable storage first
        event_id = await commit_bus.store_event(event)
        return {"status": "queued", "event_id": event_id}
    else:
        # Fallback processing
        legacy_handle_push(payload)
        return {"status": "processed", "method": "legacy"}
```

### Strategy Pattern (LLM Provider Selection)
```python
class LLMRotator:
    """Manages multiple LLM providers with automatic failover"""
    def __init__(self, providers: List[str]):
        self.providers = providers
        self.current_provider = 0

    async def generate_with_rotation(self, prompt: str) -> str:
        """Try providers in order until one succeeds"""
        for provider in self.providers:
            try:
                response = await self.call_provider(provider, prompt)
                return response
            except Exception as e:
                continue
        return None
```

### Repository Pattern (Data Access)
```python
class CommitBusService:
    """Durable event storage with replay capabilities"""
    async def store_event(self, event: CommitEvent) -> str:
        """Store commit event with full metadata"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                INSERT INTO commit_events (repo_id, commit_sha, ...)
                VALUES ($1, $2, ...) RETURNING id
            """, event.repo_id, event.commit_sha)
```

## Data Flow Architecture

### 1. Event Ingestion
```
GitHub Push → Webhook → Signature Verification → Background Task
     ↓
Event Storage (PostgreSQL) → Queue for Processing
```

### 2. Code Analysis Pipeline
```
Repository Clone → Git Checkout → File Pattern Analysis → LLM Enhancement
     ↓                    ↓                    ↓
AST Parsing       Diff Extraction    Significance Scoring
     ↓                    ↓                    ↓
Import Analysis   Context Building   Impact Assessment
```

### 3. Documentation Generation
```
Quality Check → Conditional Generation → AI Enhancement → File Creation
     ↓                    ↓                    ↓
Existing Docs    Architecture/Workflow    LLM Descriptions   Markdown Files
     ↓                    ↓                    ↓
Navigation Update    Version Management    Git Commit
```

### 4. Persistence & Distribution
```
Documentation Files → Git Add → Commit with SHA → Push to GitHub
     ↓                    ↓                    ↓
Version Control    Provenance Tracking    Auto-Deployment
```

## Performance Optimizations

### Caching Strategy
- **LLM response caching** based on content hash
- **File analysis caching** to avoid re-parsing unchanged files
- **Quality assessment caching** to reduce redundant evaluations

### Rate Limiting
- **GitHub API limits** - Smart backoff and retry logic
- **LLM API limits** - Provider rotation and caching
- **Database connections** - Connection pooling and reuse

### Error Handling
- **Graceful degradation** when LLMs are unavailable
- **Retry mechanisms** with exponential backoff
- **Fallback documentation** generation for critical failures

## Security Considerations

### Authentication & Authorization
- **HMAC signature verification** for all GitHub webhooks
- **Environment variable validation** for API keys
- **Input sanitization** for all user-provided data

### Data Protection
- **No sensitive data storage** in documentation
- **Commit hash isolation** for security
- **Access logging** for audit trails

## Recent Improvements

This version introduces **enhanced code analysis** with real AST parsing, **semantic versioning** instead of excessive incremental versions, and **quality-based regeneration** to avoid unnecessary documentation updates.

**Key Changes:**
- Improved component detection from actual file names and imports
- Real design pattern analysis instead of hardcoded patterns
- Better technology stack detection from actual dependencies
- More intelligent versioning that only creates versions for major changes

## Future Architecture Evolution

### Planned Enhancements
- **Hierarchical documentation tree** (currently disabled due to LLM costs)
- **Vector search integration** for semantic code search
- **Multi-tenant architecture** for SaaS deployment
- **Plugin system** for language-specific analyzers

### Scalability Considerations
- **Horizontal scaling** of analysis workers
- **Database sharding** for large codebases
- **CDN integration** for documentation delivery
- **Microservices migration** for better isolation