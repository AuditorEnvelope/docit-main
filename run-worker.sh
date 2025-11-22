#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Starting Event Consumer Worker...${NC}"
echo ""

# Use conda environment (you already activated manually)
echo -e "${GREEN}✓${NC} Using Conda environment: $CONDA_DEFAULT_ENV"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✓${NC} Environment variables loaded"
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
fi

echo ""
echo -e "${GREEN}✅ Starting worker process...${NC}"
echo ""

python -m app.worker
