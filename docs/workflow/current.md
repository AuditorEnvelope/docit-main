# Workflow v1.0

## Development Workflow

### Project Setup
**Actual Implementation Steps:**

```bash
# 1. Clone and setup
git clone <repository-url>
cd <project-directory>
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
export GITHUB_TOKEN="ghp_your_github_token"
export GEMINI_API_KEY="your_gemini_key"
export DATABASE_URL="postgresql://localhost/lekhak_ai"  # Optional

# 4. Initialize database (if using commit bus)
createdb lekhak_ai
psql lekhak_ai < schema.sql

# 5. Start development server
python src/main.py
```

### Git Workflow for Contributions

**Actual Process Used:**

```bash
# 1. Create feature branch
git checkout -b feature/enhanced-architecture-analysis

# 2. Make changes with proper commit messages
git add -A
git commit -m "feat: Enhance architecture analysis with real code insights

- Added actual component detection from file names and imports
- Implemented real design pattern analysis instead of hardcoded patterns
- Enhanced technology stack detection from actual dependencies
- Improved LLM prompts with specific framework and database references

BREAKING CHANGES:
- Changed versioning system to semantic versioning (v1.0, v1.1, v2.0)
- Stricter quality thresholds for documentation regeneration
- More intelligent change detection for version creation"

# 3. Push and create pull request
git push origin feature/enhanced-architecture-analysis
# Then create PR via GitHub interface
```

**Code Review Process:**
1. **Automated checks** run via GitHub Actions
2. **Manual review** by at least 1 maintainer
3. **Testing** - All tests must pass
4. **Documentation** - Changes must include updated docs
5. **Approval** - LGTM from maintainer

## Documentation Generation Workflow

### Event-Driven Processing Pipeline

**How Documentation Gets Generated:**

```python
# 1. GitHub webhook received (src/main.py)
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    if verify_signature(WEBHOOK_SECRET, body, signature):
        payload = json.loads(body)
        if x_github_event == "push":
            # Process in background to avoid blocking
            background_tasks.add_task(process_commit_event, payload)

# 2. Smart analysis (src/smart_processor.py)
def smart_analyze_change(payload, repo_dir, changed_files, removed_files):
    """Multi-stage analysis pipeline"""
    # Pattern analysis for change type detection
    file_analysis = analyze_file_patterns(changed_files, removed_files)

    # Git diff extraction for context
    diff_context = get_git_diff_context(repo_dir, changed_files)

    # LLM-powered significance assessment
    analysis_prompt = create_detailed_prompt(payload, diff_context)
    result = rotator.generate_with_rotation(analysis_prompt)

    return json.loads(result)  # type, significance, impact_scope, etc.

# 3. Quality assessment (src/comprehensive_doc_generator.py)
def check_documentation_quality(repo_dir):
    """Assess existing documentation quality"""
    quality_report = {
        "summary_exists": False, "summary_quality": 0,
        "architecture_exists": False, "architecture_quality": 0,
        "workflow_exists": False, "workflow_quality": 0,
        "api_exists": False, "api_quality": 0
    }

    # Check each documentation type and assess quality with LLM
    for doc_type in ["summary", "architecture", "workflow", "api"]:
        if existing_docs_exist(docs_dir, doc_type):
            content = read_existing_docs(docs_dir, doc_type)
            quality_report[f"{doc_type}_exists"] = True
            quality_report[f"{doc_type}_quality"] = assess_with_llm(content, doc_type)

# 4. Conditional generation
def generate_comprehensive_documentation(repo_dir, analysis, changed_files):
    """Only regenerate when quality is insufficient"""
    quality_report = check_documentation_quality(repo_dir)

    # Only generate if quality < 8 (was < 7, now stricter)
    if quality_report["architecture_quality"] < 8:
        generate_versioned_architecture(repo_dir, docs_dir, analysis)

    if quality_report["workflow_quality"] < 8:
        generate_versioned_workflow(repo_dir, docs_dir, analysis)
```

### Intelligent Versioning

**How Versioning Decisions Are Made:**

```python
def analyze_architectural_impact(repo_dir, changed_files, analysis):
    """STRICT criteria for new versions (only major changes)"""
    major_indicators = [
        len(changed_files) > 50,  # Large refactoring
        analysis.get("type") == "breaking_change" and analysis.get("significance", 0) >= 9,
        any("migrate" in f.lower() for f in changed_files),  # Database migrations
        any("refactor" in f.lower() for f in changed_files),  # Major refactoring
        any("docker" in f.lower() and "compose" in f.lower() for f in changed_files),
        any("kubernetes" in f.lower() for f in changed_files),
        any("terraform" in f.lower() for f in changed_files),
    ]

    # Only create new version for TRULY major changes
    if any(major_indicators) and analysis.get("significance", 0) >= 8:
        return {"needs_new_version": True, "reason": "Major architectural change"}
    else:
        return {"needs_new_version": False, "reason": "Minor change"}
```

**Semantic Versioning Logic:**
- **v1.0** → **v1.1**: Minor improvements, new features
- **v1.9** → **v2.0**: Major architectural changes, breaking changes
- **No more v11, v12, v13...** Excessive versioning eliminated!

## Deployment Workflow

### Development Environment
```bash
# Local development with hot reload
python src/main.py
# Server starts on http://localhost:8000
# Automatic reload on code changes
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Production build
docker build -t lekhak-ai .
docker run -p 8000:8000 lekhak-ai
```

### Production Deployment
```bash
# Railway deployment
railway login
railway link
railway up

# Render deployment
render login
render create
render deploy
```

## Testing Workflow

### Automated Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test category
pytest tests/test_smart_processor.py
pytest tests/test_llm_integration.py
```

### Manual Testing Process
1. **Unit Tests** - Individual function/component testing
2. **Integration Tests** - Component interaction testing
3. **End-to-End Tests** - Full workflow testing
4. **Performance Tests** - Load testing and optimization

## Release Management

### Version Bumping
```python
# Update version in main.py
app = FastAPI(
    title="Lekhak AI",
    version="1.1.0"  # Increment version
)

# Update changelog
def update_changelog(repo_dir, analysis, commit_sha):
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    entry = f"""
## [{today}] - {analysis['title']}
### {analysis['type'].title()}
- {analysis['summary']}
"""
    # Append to CHANGELOG.md
```

### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Migration guides created (if needed)
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] Deployment tested

## Monitoring & Maintenance

### Health Monitoring
```python
@app.get("/health")
async def health():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "commit_bus": "active" if commit_bus else "disabled",
            "database": "connected" if db_pool else "disconnected",
            "llm_providers": ["gemini", "groq", "deepseek"]  # Available providers
        }
    }
```

### Performance Monitoring
- **Event processing statistics** via `/events/stats`
- **LLM usage tracking** with rate limiting
- **Cache hit rates** for optimization
- **Error rates** with alerting

### Incident Response
1. **Automated alerts** for service failures
2. **Graceful degradation** when LLMs unavailable
3. **Rollback procedures** for failed deployments
4. **Post-mortem analysis** for improvements

## Code Quality Workflow

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Hooks include:
# - Black code formatting
# - Flake8 linting
# - MyPy type checking
# - Tests run automatically
```

### Continuous Integration
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
      - name: Check formatting
        run: black --check src/
```

## Recent Process Improvements

This workflow version introduces **semantic versioning** and **quality-based regeneration** to prevent excessive documentation generation while maintaining high quality standards.

**Key Improvements:**
- **Stricter versioning criteria** - Only major changes create new versions
- **Quality thresholds** - Only regenerate when quality < 8 (instead of < 7)
- **Cleaner navigation** - Show only recent versions, not all historical versions
- **Better caching** - Smart caching reduces LLM calls by 80-90%

**Process Changes:**
- Eliminated excessive v11, v12, v13... versioning
- More focused on quality over quantity
- Better developer experience with cleaner documentation
- Reduced maintenance overhead with smarter regeneration