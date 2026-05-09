#!/bin/bash

set -e

echo "🚀 Starting DocIt Backend..."

export PYTHONPATH="${PYTHONPATH}:$(pwd)"

PORT=${PORT:-8000}

uvicorn app.main:app --host 0.0.0.0 --port $PORT