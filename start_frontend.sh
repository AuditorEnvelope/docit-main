#!/bin/bash
# Start Pustak Frontend

echo "🚀 Starting Pustak Frontend..."

cd pustak

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ .env.local file not found. Copy .env.example and configure it."
    exit 1
fi

# Start the development server
echo "✅ Starting Next.js server on http://localhost:3000"
npm run dev
