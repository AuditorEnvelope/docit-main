# DocAI Smart 🤖

AI-powered documentation platform that automatically generates and maintains comprehensive documentation for your repositories.

## 🚀 Features

- **Automatic Documentation Generation**: Generates comprehensive docs from code changes
- **Multi-LLM Support**: Works with OpenAI, Google Gemini, and Groq
- **Smart Change Detection**: Analyzes commits and generates relevant documentation
- **Version Control**: Tracks documentation versions (v1, v2, etc.)
- **Beautiful UI**: Pustak - GitBook-style documentation viewer
- **GitHub Integration**: Automatic webhook processing

## 📁 Project Structure

```
doc_ai/
├── src/                          # Source code
│   ├── app.py                    # Main FastAPI application
│   ├── github_app.py             # GitHub webhook handler
│   ├── processor.py              # Basic documentation processor
│   ├── smart_processor.py        # Smart change analyzer
│   ├── comprehensive_doc_generator.py  # Comprehensive doc generator
│   ├── llm_provider_v2.py        # Multi-LLM provider
│   └── pustak_integration.py     # Pustak integration
├── pustak/                       # Documentation viewer (Next.js)
│   ├── src/
│   │   ├── app/                  # Next.js app router
│   │   ├── components/           # React components
│   │   └── lib/                  # Utilities and API clients
│   └── public/                   # Static assets
├── docs/                         # Generated documentation
│   ├── SUMMARY.md                # Navigation structure
│   ├── api.md                    # API documentation
│   ├── architecture/             # Architecture docs (versioned)
│   ├── workflow/                 # Workflow docs (versioned)
│   └── changes/                  # Change documentation
├── CHANGELOG.md                  # Project changelog
├── DEPLOYMENT_GUIDE.md           # Deployment instructions
├── QUICK_START_GUIDE.md          # Quick start guide
└── requirements.txt              # Python dependencies
```

## 🏃 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- GitHub account with API token

### 1. Setup Backend (DocAI)

```bash
# Clone repository
git clone https://github.com/AuditorEnvelope/doc_ai.git
cd doc_ai

# Create virtual environment
python -m venv docai-env
source docai-env/bin/activate  # On Windows: docai-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# - GITHUB_TOKEN
# - GITHUB_ORG
# - OPENAI_API_KEY (or GOOGLE_API_KEY, or GROQ_API_KEY)

# Start server
cd src
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 2. Setup Frontend (Pustak)

```bash
# In a new terminal
cd pustak

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with:
# - GITHUB_TOKEN
# - GITHUB_ORG

# Start development server
npm run dev
```

Visit http://localhost:3000 to view your documentation!

## 🔧 Configuration

### Environment Variables

**Backend (.env)**:
```env
GITHUB_TOKEN=your_github_token
GITHUB_ORG=your_org_name
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Choose one LLM provider:
OPENAI_API_KEY=your_openai_key
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
