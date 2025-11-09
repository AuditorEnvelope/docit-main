#!/bin/bash

# Exit on error
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Starting Event Consumer Worker...${NC}"
echo ""

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Activate environment
if [ -d "docai-env" ]; then
    source docai-env/bin/activate
    echo -e "${GREEN}✓${NC} Activated docai-env"
elif [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Activated venv"
fi

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✓${NC} Environment variables loaded"
fi

echo ""
echo -e "${GREEN}✅ Starting worker process...${NC}"
echo ""

# Run the worker
python -m app.worker
