# DocIt Setup Guide

## Overview

DocIt is a GitBook-like documentation platform that automatically fetches and displays markdown documentation from your GitHub organization's repositories.

## Prerequisites

- Node.js 18+ installed
- A GitHub account with access to your organization
- GitHub Personal Access Token

## Step 1: Clone and Install

```bash
cd DocIt
npm install
```

## Step 2: Configure Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env.local
```

2. Edit `.env.local` and add your credentials:

```bash
# Get your GitHub Personal Access Token from:
# https://github.com/settings/tokens
# Required scopes:
#   - repo (for private repos)
#   - OR public_repo (for public repos only)
GITHUB_TOKEN=ghp_your_actual_token_here

# Your GitHub organization name
GITHUB_ORG=YourOrgName

# Optional: Backend API URL (if using DocAI backend)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### How to Get a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name (e.g., "DocIt Documentation")
4. Select scopes:
   - For **private repos**: Check `repo` (full control)
   - For **public repos only**: Check `public_repo`
5. Click "Generate token"
6. **IMPORTANT**: Copy the token immediately (you won't see it again!)
7. Paste it into your `.env.local` file

## Step 3: Prepare Your Repositories

DocIt looks for a `/docs` folder in each repository. Create this structure in your repos:

```
your-repo/
├── docs/
│   ├── README.md or SUMMARY.md    # Summary/Overview
│   ├── api.md                     # API Documentation
│   ├── CHANGELOG.md               # Changelog
│   ├── architecture.md            # Architecture docs
│   ├── workflow.md                # Workflow docs
│   └── *.md                       # Any other markdown files (shown in "Changes")
├── src/
└── ...
```

### Supported Documentation Files

DocIt automatically recognizes these files in the `/docs` folder:

- **README.md** or **SUMMARY.md** → Summary section
- **api.md** → API Documentation section
- **CHANGELOG.md** → Changelog section
- **architecture.md** → Architecture section (or uses SUMMARY.md)
- **workflow.md** → Workflow section (or uses README.md)
- **All other .md files** → Recent Changes section

## Step 4: Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Step 5: Build for Production

```bash
npm run build
npm start
```

## How It Works

1. **Repository Discovery**: DocIt fetches all repositories from your GitHub organization using the GitHub API
2. **Docs Detection**: It checks each repository for a `/docs` folder
3. **Content Fetching**: For repos with docs, it fetches all markdown files
4. **Rendering**: The markdown is rendered with syntax highlighting and GitHub-flavored markdown support

## Features

✅ **No Hardcoded Data**: All repository and documentation data is fetched dynamically from GitHub
✅ **Automatic Discovery**: Automatically finds all repos with `/docs` folders
✅ **Real-time Updates**: Uses Next.js caching with revalidation
✅ **Dark Mode**: Built-in dark/light theme support
✅ **Search**: Fast search across all documentation (coming soon)
✅ **Responsive**: Works on desktop, tablet, and mobile

## Troubleshooting

### "No repositories found"

- Check that `GITHUB_TOKEN` is valid and has correct permissions
- Check that `GITHUB_ORG` matches your organization name exactly
- Verify your token has access to the organization

### "Documentation Not Available"

- Ensure the repository has a `/docs` folder
- Check that the folder contains at least one `.md` file
- Verify the token has read access to the repository

### API Rate Limiting

- GitHub API has rate limits (5000 requests/hour for authenticated requests)
- DocIt uses caching to minimize API calls
- If you hit rate limits, wait an hour or upgrade your GitHub plan

## Environment Variables Reference

| Variable                  | Required | Description                  | Example                 |
| ------------------------- | -------- | ---------------------------- | ----------------------- |
| `GITHUB_TOKEN`            | Yes      | GitHub Personal Access Token | `ghp_abc123...`         |
| `GITHUB_ORG`              | Yes      | GitHub organization name     | `AuditorEnvelope`       |
| `NEXT_PUBLIC_BACKEND_URL` | No       | DocAI backend URL (optional) | `http://localhost:8000` |

## Security Notes

⚠️ **NEVER commit your `.env.local` file to Git**
⚠️ **Keep your GitHub token secret**
⚠️ **Rotate tokens regularly**
⚠️ **Use minimal required permissions**

## Next Steps

- Add more markdown files to your `/docs` folders
- Customize the theme in `tailwind.config.js`
- Set up automatic deployment (Vercel, Netlify, etc.)
- Integrate with DocAI for automatic documentation generation

## Support

For issues or questions:

1. Check this guide first
2. Review the GitHub API documentation
3. Check Next.js documentation for deployment issues
