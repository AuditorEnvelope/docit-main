# DocAI (formerly Lekhak AI)

**Next-generation AI-powered documentation system** that automatically analyzes codebases and generates comprehensive, hierarchical documentation with intelligent insights.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (latest version)
- Git
- PostgreSQL (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd doc_ai
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the package in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running the Application

#### Development Server
```bash
uvicorn app.main:app --reload
```

#### Production Server
```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Running the Event Worker
```bash
python -m app.worker
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🛠 Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

### Type Checking
```bash
mypy .
```

## 📦 Deployment

### Environment Variables
Required environment variables are listed in `.env.example`

### Database Migrations
```bash
alembic upgrade head
```

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
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
