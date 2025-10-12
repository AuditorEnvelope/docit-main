# GitHub Authentication Setup for Pustak

## Required: GitHub Personal Access Token (PAT)

To access your private repositories, you need to set up a GitHub Personal Access Token.

### Step 1: Create GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a descriptive name: `Pustak Documentation Platform`
4. Select the following scopes:
   - ✅ **repo** (Full control of private repositories)
   - ✅ **read:org** (Read org and team membership)
5. Click "Generate token"
6. **IMPORTANT**: Copy the token immediately (you won't see it again)

### Step 2: Add Token to Environment

Create a file named `.env.local` in your `pustak` directory:

```bash
# In /Users/harshsrivastava/Desktop/doc_ai/pustak/
touch .env.local
```

Add your token to `.env.local`:

```env
GITHUB_TOKEN=your_actual_token_here
```

Replace `your_actual_token_here` with the token you copied from GitHub.

### Step 3: Restart the Development Server

```bash
# Stop the current server (Ctrl+C)
# Then restart
npm run dev
```

## Alternative: Using GitHub App (Advanced)

If you prefer to use a GitHub App (since you mentioned "doc ai is already installed app in the org"):

1. Go to your GitHub App settings
2. Get the App ID, Private Key, and Installation ID
3. Add to `.env.local`:

```env
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY=your_private_key
GITHUB_APP_INSTALLATION_ID=your_installation_id
```

## Verification

After setting up the token, you should see:

- Real repository data from your GitHub organization
- Actual documentation content from your repositories
- No more "Documentation Not Available" messages
- Dynamic repository count based on your actual GitHub org

## Security Notes

- Never commit `.env.local` to Git
- Keep your token secure
- Regenerate the token if compromised
- Use minimal required scopes
