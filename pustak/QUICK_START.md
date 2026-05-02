# DocIt - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Install Dependencies

```bash
cd DocIt
npm install
```

### Step 2: Set Up Environment Variables

```bash
# Copy the example file
cp .env.example .env.local

# Edit .env.local and add:
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORG=YourOrgName
```

### Step 3: Get GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (for private repos) or `public_repo` (for public only)
4. Copy the token and paste into `.env.local`

### Step 4: Run Development Server

```bash
npm run dev
```

Open http://localhost:3000

### Step 5: Prepare Your Repositories

Create a `/docs` folder in your repositories with markdown files:

```
your-repo/
├── docs/
│   ├── README.md      # Shows in Summary
│   ├── api.md         # Shows in API Documentation
│   └── CHANGELOG.md   # Shows in Changelog
```

## ✅ That's It!

DocIt will automatically:

- Find all repos in your organization
- Detect which ones have `/docs` folders
- Display their documentation beautifully

## 🔧 Troubleshooting

**No repos showing?**

- Check `GITHUB_TOKEN` is valid
- Check `GITHUB_ORG` matches your organization name exactly
- Verify token has correct permissions

**"Documentation Not Available"?**

- Create a `/docs` folder in your repository
- Add at least one `.md` file

## 📚 More Help

- Full setup guide: `SETUP_GUIDE.md`
- All changes made: `CHANGES_SUMMARY.md`
- General info: `README.md`
