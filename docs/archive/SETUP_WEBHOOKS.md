# 🔗 Setup GitHub Webhooks

## 🎯 Why You Don't See Commits

Your server is running locally (`http://localhost:8000`) but GitHub can't reach it because:
- GitHub is on the internet
- Your server is on your local machine
- No public URL to send webhooks to

---

## ✅ Solution 1: Test Locally (Quick)

### Run the test script:

```bash
# In a new terminal
cd /Users/harshsrivastava/Desktop/doc_ai
./test_webhook.sh
```

**Watch your Event Consumer terminal** - you'll see it process the fake commit!

---

## ✅ Solution 2: Use ngrok (Expose Local Server)

### Step 1: Install ngrok

```bash
brew install ngrok
```

### Step 2: Start ngrok

```bash
ngrok http 8000
```

You'll see:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### Step 3: Configure GitHub Webhook

1. Go to your GitHub repo
2. Settings → Webhooks → Add webhook
3. **Payload URL**: `https://abc123.ngrok.io/webhook` (use your ngrok URL)
4. **Content type**: `application/json`
5. **Secret**: Your `GITHUB_WEBHOOK_SECRET` from `.env`
6. **Events**: Just the push event
7. Click "Add webhook"

### Step 4: Test It

Push a commit to your repo and watch:
- GitHub sends webhook to ngrok
- ngrok forwards to your local server
- Your server processes it
- Event Consumer picks it up
- Docs get generated! 🎉

---

## ✅ Solution 3: Deploy to Production

Deploy your server to:
- **Render**: `https://your-app.onrender.com/webhook`
- **Railway**: `https://your-app.railway.app/webhook`
- **Heroku**: `https://your-app.herokuapp.com/webhook`

Then configure GitHub webhook with your production URL.

---

## 🧪 Test Without GitHub (Right Now)

### Option A: Use the test script

```bash
./test_webhook.sh
```

### Option B: Manual curl

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{
    "repository": {"full_name": "test/repo"},
    "commits": [{"id": "test123", "message": "Test"}]
  }'
```

---

## 📊 What You'll See

### In Main API Terminal:
```
INFO: 127.0.0.1:54321 - "POST /webhook HTTP/1.1" 200 OK
```

### In Event Consumer Terminal:
```
📥 Processing event: test123
✅ Event processed successfully
```

---

## 🎯 Current Setup Summary

**What's Running:**
- ✅ Main API (localhost:8000)
- ✅ Event Consumer (polling database)
- ✅ Database (lekhak_ai)

**What's Missing:**
- ❌ Public URL (use ngrok or deploy)
- ❌ GitHub webhook configured

**Quick Test:**
```bash
./test_webhook.sh
```

---

## 🚀 Next Steps

1. **Test locally first**: Run `./test_webhook.sh`
2. **See it work**: Watch Event Consumer process the event
3. **Then setup ngrok**: For real GitHub webhooks
4. **Or deploy**: To production for permanent setup

**Try the test script now!** 🎉
