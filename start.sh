#!/bin/bash

# Exit on error
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting DocIt AI Development Environment...${NC}"
echo ""

# Set Python path to include the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo -e "${GREEN}✓${NC} PYTHONPATH set to: ${PYTHONPATH}"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python version: ${python_version}"

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d "docai-env" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment created"
    
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    pip install --upgrade pip -q
    pip install -e ".[dev]" -q
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    # Activate existing venv
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✓${NC} Activated venv"
    elif [ -d "docai-env" ]; then
        source docai-env/bin/activate
        echo -e "${GREEN}✓${NC} Activated docai-env"
    fi
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}ℹ️  Please update the .env file with your configuration and restart${NC}"
        exit 1
    else
        echo -e "${RED}❌ No .env or .env.example found${NC}"
        echo -e "${YELLOW}Creating minimal .env file...${NC}"
        cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/pustak

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# GitHub Apps
GITHUB_READER_APP_ID=2072879
GITHUB_READER_PRIVATE_KEY=
GITHUB_WRITER_APP_ID=2229202
GITHUB_WRITER_PRIVATE_KEY=

# LLM
OPENAI_API_KEY=

# Security
JWT_SECRET=change-me-in-production-$(openssl rand -hex 32)
SECRET_KEY=change-me-in-production-$(openssl rand -hex 32)

# Debug
DEBUG=true
EOF
        echo -e "${GREEN}✓${NC} Created .env file. Please configure it."
        exit 1
    fi
fi

# Load environment variables
set -a
source .env
set +a
echo -e "${GREEN}✓${NC} Environment variables loaded"

echo ""
echo -e "${GREEN}✅ Starting DocIt AI server...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📚 API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "${YELLOW}📚 ReDoc:             ${GREEN}http://localhost:8000/redoc${NC}"
echo -e "${YELLOW}❤️  Health Check:      ${GREEN}http://localhost:8000/health${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
