#!/bin/bash
# Start DocAI Backend

echo "🚀 Starting DocAI Backend..."

# Check if running inside Conda env
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "❌ Conda environment not active. Run: conda activate lekhak"
    exit 1
else
    echo "✅ Using Conda environment: $CONDA_DEFAULT_ENV"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Copy .env.example and configure it."
    exit 1
fi

# Start the server
cd src
echo "✅ Starting FastAPI server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
