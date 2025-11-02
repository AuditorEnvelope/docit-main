# 🔧 GitHub App Setup Guide

**Create a GitHub App to connect repositories to Pustak**

---

## Step 1: Create GitHub App

1. Go to: https://github.com/settings/apps/new

2. Fill in the details:

### **Basic Information**

- **GitHub App name**: `Pustak AI` (or `pustak-ai-dev` for testing)
- **Homepage URL**: `http://localhost:3000`
- **Callback URL**: `http://localhost:3000/auth/github-app/callback`
- **Setup URL**: `http://localhost:3000/setup`
- **Webhook URL**: `http://your-server.com/webhook` (or use ngrok for local dev)
- **Webhook secret**: Generate one with `openssl rand -hex 32`

### **Permissions**

**Repository permissions:**

- Contents: **Read-only** (to read code)
- Metadata: **Read-only** (required)
- Pull requests: **Read & write** (to comment on PRs)
- Webhooks: **Read & write** (to manage webhooks)

**Subscribe to events:**

- [x] Push
- [x] Pull request
- [x] Repository

### **Where can this GitHub App be installed?**

- Select: **Any account** (for public use)
- Or: **Only on this account** (for testing)

3. Click **Create GitHub App**

---

## Step 2: Get Your App Details

After creating the app:

1. **App ID**: Copy this (you'll see it at the top)
2. **Client ID**: Copy this
3. **Client Secret**: Click "Generate a new client secret" and copy it
4. **Private Key**: Click "Generate a private key" and download the `.pem` file

---

## Step 3: Update Your .env

Add these to your `.env` file:

```bash
# GitHub App (for repository access)
GITHUB_APP_ID=your_app_id_here
GITHUB_APP_CLIENT_ID=your_client_id_here
GITHUB_APP_CLIENT_SECRET=your_client_secret_here
GITHUB_PRIVATE_KEY_PATH=./pustak-ai.pem
GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret_here
```

---

## Step 4: Update Dashboard Button

Replace the URL in `/pustak/src/app/dashboard/page.tsx`:

```typescript
window.open(
  "https://github.com/apps/YOUR-APP-NAME/installations/new",
  "_blank"
);
```

Replace `YOUR-APP-NAME` with your actual app name (e.g., `pustak-ai-dev`)

---

## Step 5: Test Installation

1. Restart your frontend: `cd pustak && npm run dev`
2. Go to dashboard: http://localhost:3000/dashboard
3. Click "Install GitHub App"
4. Select repositories to connect
5. Click "Install"

---

## Quick Setup (For Now)

**For immediate testing**, you can use the existing OAuth app:

Update the button to just show a message:

```typescript
onClick={() => {
  alert('GitHub App setup required! See GITHUB_APP_SETUP.md for instructions.');
}}
```

---

## What's Next?

Once the GitHub App is installed:

1. User installs app on their repos
2. GitHub sends webhook to your backend
3. Backend stores installation ID
4. Backend can now access user's repos
5. AI generates documentation automatically

---

**Need help?** Check the GitHub Apps documentation:
https://docs.github.com/en/apps/creating-github-apps
