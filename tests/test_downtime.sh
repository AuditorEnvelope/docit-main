#!/bin/bash

echo "🧪 DOWNTIME TEST - Never Lose Commits"
echo "======================================"
echo ""

echo "📋 Test Scenario:"
echo "1. Server is DOWN"
echo "2. You commit changes"
echo "3. Wait 10 minutes"
echo "4. Start server"
echo "5. Commits are processed automatically"
echo ""

echo "📁 Files ready to commit:"
echo "  - src/test_architecture.py (ArchitectureManager)"
echo "  - src/test_feature.py (DocumentationSyncManager, DowntimeRecoveryManager)"
echo "  - ARCHITECTURE_CHANGES.md (Documentation)"
echo ""

echo "🚀 STEP 1: Make sure server is STOPPED"
echo "   (Press Ctrl+C in the terminal running python src/main.py)"
echo ""
read -p "Press Enter when server is stopped..."

echo ""
echo "✅ Server stopped"
echo ""

echo "🚀 STEP 2: Commit the changes"
echo ""

git status

echo ""
read -p "Ready to commit? Press Enter to continue..."

git add src/test_architecture.py src/test_feature.py ARCHITECTURE_CHANGES.md DOWNTIME_TEST.md test_downtime.sh

git commit -m "feat: architectural changes during downtime test

- Added ArchitectureManager for component tracking
- Added DocumentationSyncManager for real-time sync  
- Added DowntimeRecoveryManager for downtime recovery
- Testing commit bus never-lose-commits feature

This commit was made while the server was down to test
the commit bus recovery mechanism."

echo ""
echo "✅ Changes committed locally"
echo ""

echo "🚀 STEP 3: Push to GitHub (webhook will fail - server is down)"
echo ""
read -p "Press Enter to push..."

git push origin main

echo ""
echo "✅ Pushed to GitHub"
echo "⚠️  GitHub webhook failed (server is down)"
echo ""

echo "⏰ STEP 4: Wait 10 minutes (or just a few seconds for testing)"
echo ""
echo "During this time:"
echo "  - Server is still down"
echo "  - GitHub will retry the webhook automatically"
echo "  - Retries: 1min, 5min, 30min, 1hr, 2hr"
echo ""
read -p "Press Enter when ready to start server (or wait 10 mins)..."

echo ""
echo "🚀 STEP 5: Start the server"
echo ""
echo "Open TWO new terminals and run:"
echo ""
echo "Terminal 1:"
echo "  cd /Users/harshsrivastava/Desktop/doc_ai"
echo "  source docai-env/bin/activate"
echo "  python src/main.py"
echo ""
echo "Terminal 2:"
echo "  cd /Users/harshsrivastava/Desktop/doc_ai"
echo "  source docai-env/bin/activate"
echo "  python src/event_consumer.py"
echo ""
read -p "Press Enter when both servers are running..."

echo ""
echo "⏳ Waiting for GitHub webhook retry..."
echo "   (GitHub retries every 1min, 5min, 30min...)"
echo ""
echo "OR manually trigger the webhook:"
echo ""
echo "  ./test_webhook.sh"
echo ""
read -p "Press Enter after you see the commit processed..."

echo ""
echo "🎉 STEP 6: Verify documentation was generated"
echo ""

echo "Checking database for new documentation..."
psql lekhak_ai -c "SELECT name, type, path FROM doc_nodes WHERE path LIKE '%test_%' ORDER BY created_at DESC LIMIT 10;"

echo ""
echo "Checking commit events..."
psql lekhak_ai -c "SELECT event_id, repo_id, commit_sha, processed, created_at FROM commit_events ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "✅ TEST COMPLETE!"
echo ""
echo "Expected results:"
echo "  - 3 new doc_nodes (ArchitectureManager, DocumentationSyncManager, DowntimeRecoveryManager)"
echo "  - 1 processed commit_event"
echo "  - Documentation generated for all new classes"
echo ""
echo "🎉 Lekhak AI never loses commits! 🚀"
