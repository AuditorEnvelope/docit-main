#!/bin/bash

# Exit on error
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Starting Event Consumer Worker...${NC}"
echo ""

# Ensure conda env is active
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo -e "${YELLOW}⚠️ Conda env not active.${NC}"
    echo "Run: conda activate lekhak"
    exit 1
else
    echo -e "${GREEN}✓${NC} Using conda env: $CONDA_DEFAULT_ENV"
fi

# Set Python path
export PYTHONPATH="$(pwd):${PYTHONPATH}"

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
