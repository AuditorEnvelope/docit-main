#!/bin/bash
set -e
echo "🚀 Starting DocIt Backend..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo "Starting on port: $PORT"  # Add this to see what Railway injects
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}