#!/bin/bash

echo "🧪 Manual Commit Test - Simulate Webhook"
echo "=========================================="
echo ""

# Get latest commit from GitHub
COMMIT_SHA="343940bd"
COMMIT_MSG="feat: add github sync and event consumer updates"

echo "📝 Simulating webhook for commit: $COMMIT_SHA"
echo "   Message: $COMMIT_MSG"
echo ""

# Send webhook to local server
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d "{
    \"repository\": {
      \"full_name\": \"AuditorEnvelope/lekhak_ai\",
      \"name\": \"lekhak_ai\"
    },
    \"ref\": \"refs/heads/main\",
    \"after\": \"$COMMIT_SHA\",
    \"commits\": [{
      \"id\": \"$COMMIT_SHA\",
      \"message\": \"$COMMIT_MSG\",
      \"author\": {
        \"name\": \"Harsh Srivastava\",
        \"email\": \"harsh@example.com\"
      },
      \"timestamp\": \"2025-10-15T19:07:00Z\",
      \"added\": [\"HOW_IT_WORKS.md\", \"src/github_sync.py\"],
      \"modified\": [\"src/event_consumer.py\", \"requirements.txt\"],
      \"removed\": []
    }]
  }"

echo ""
echo ""
echo "✅ Webhook sent!"
echo ""
echo "Check your Event Consumer terminal - it should process the commit!"
