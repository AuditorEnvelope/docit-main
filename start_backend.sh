#!/bin/bash
# Start DocAI Backend

echo "🚀 Starting DocAI Backend..."

# Activate virtual environment
if [ -d "docai-env" ]; then
    source docai-env/bin/activate
else
    echo "❌ Virtual environment not found. Run: python -m venv docai-env"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Copy .env.example and configure it."
    exit 1
fi

# Start the server
echo "✅ Starting FastAPI server on http://localhost:8000"
uvicorn src.core.main:app --host 0.0.0.0 --port 8000 --reload
