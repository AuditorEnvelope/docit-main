#!/bin/bash

echo "🧪 Testing webhook with fake commit..."
echo ""

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d '{
    "repository": {
      "full_name": "test/repo",
      "name": "repo"
    },
    "ref": "refs/heads/main",
    "commits": [
      {
        "id": "abc123",
        "message": "Test commit",
        "author": {
          "name": "Test User",
          "email": "test@example.com"
        },
        "timestamp": "2025-10-16T00:00:00Z",
        "added": ["test.py"],
        "modified": [],
        "removed": []
      }
    ]
  }'

echo ""
echo "✅ Webhook sent!"
echo ""
echo "Check your Event Consumer terminal - you should see it processing!"
