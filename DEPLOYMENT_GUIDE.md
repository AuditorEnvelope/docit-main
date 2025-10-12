# 🚀 Pustak Deployment Guide

This guide will help you deploy **Pustak** (your GitBook replacement) and integrate it with your **DocAI** agent.

## 📋 Prerequisites

- Node.js 18+ installed
- GitHub account
- Vercel account (free tier works)
- Your DocAI agent running

## 🎯 Deployment Options

### Option 1: Vercel (Recommended - Free & Easy)

#### Step 1: Deploy Pustak to Vercel

1. **Go to Vercel Dashboard**

   ```
   https://vercel.com/dashboard
   ```

2. **Import Project**

   - Click "New Project"
   - Import from GitHub
   - Select your `doc_ai` repository
   - Set **Root Directory** to `pustak`

3. **Configure Build Settings**

   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "installCommand": "npm install"
   }
   ```

4. **Set Environment Variables**

   ```
   NEXT_PUBLIC_API_URL=https://your-pustak-domain.vercel.app/api
   GITHUB_TOKEN=your_github_token
   DOCAI_WEBHOOK_URL=http://your-docai-domain.herokuapp.com/webhook
   ```

5. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete
   - Note your domain: `https://your-pustak-domain.vercel.app`

#### Step 2: Configure DocAI Integration

1. **Update DocAI Environment**

   ```bash
   # In your DocAI .env file
   PUSTAK_URL=https://your-pustak-domain.vercel.app
   PUSTAK_API_URL=https://your-pustak-domain.vercel.app/api
   ```

2. **Run Integration Script**

   ```bash
   cd /path/to/your/doc_ai
   python3 pustak_integration.py
   ```

3. **Test Integration**
   - Push a code change to any repository
   - Check your Pustak site for updated documentation

### Option 2: Railway

#### Step 1: Deploy to Railway

1. **Connect GitHub**

   - Go to [Railway](https://railway.app)
   - Connect your GitHub account
   - Select your repository

2. **Configure Project**

   - Set **Root Directory** to `pustak`
   - Railway will auto-detect Next.js

3. **Set Environment Variables**

   ```bash
   NEXT_PUBLIC_API_URL=${{RAILWAY_PUBLIC_DOMAIN}}/api
   GITHUB_TOKEN=your_github_token
   ```

4. **Deploy**
   - Railway will automatically deploy
   - Get your domain from the dashboard

### Option 3: Netlify

#### Step 1: Deploy to Netlify

1. **Connect Repository**

   - Go to [Netlify](https://netlify.com)
   - "New site from Git"
   - Select your repository

2. **Configure Build**

   ```yaml
   # netlify.toml
   [build]
     base = "pustak"
     command = "npm run build"
     publish = "pustak/.next"

   [build.environment]
     NODE_VERSION = "18"
   ```

3. **Deploy**
   - Netlify will build and deploy
   - Get your domain

## 🔧 Advanced Configuration

### Custom Domain (Optional)

1. **In Vercel Dashboard**

   - Go to your project
   - Settings → Domains
   - Add your custom domain
   - Configure DNS records

2. **Update Environment Variables**
   ```bash
   NEXT_PUBLIC_API_URL=https://docs.yourcompany.com/api
   ```

### Database Integration (Optional)

For production use, you might want to add a database:

1. **Add Database**

   ```bash
   # Using Vercel Postgres
   vercel storage create postgres
   ```

2. **Update Environment**

   ```bash
   DATABASE_URL=postgresql://...
   ```

3. **Update API Routes**
   - Modify `src/app/api/sync/route.ts`
   - Add database persistence

### Authentication (Optional)

Add authentication to protect your documentation:

1. **Install Auth Package**

   ```bash
   npm install next-auth
   ```

2. **Configure Auth**
   ```typescript
   // src/app/api/auth/[...nextauth]/route.ts
   import NextAuth from "next-auth";
   import GitHubProvider from "next-auth/providers/github";
   ```

## 🧪 Testing Your Deployment

### 1. Health Check

```bash
curl https://your-pustak-domain.vercel.app/api/sync
```

Expected response:

```json
{
  "status": "ok",
  "message": "Pustak API is running",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Test Documentation Sync

```bash
curl -X POST https://your-pustak-domain.vercel.app/api/sync \
  -H "Content-Type: application/json" \
  -d '{
    "repoName": "test-repo",
    "docType": "summary",
    "content": "# Test Documentation\n\nThis is a test."
  }'
```

### 3. Test DocAI Integration

1. Make a code change in any repository
2. Push the change
3. Wait for DocAI to process
4. Check your Pustak site for updates

## 🔄 Auto-Sync Configuration

### DocAI Webhook Integration

1. **Update DocAI Webhook URL**

   ```python
   # In your DocAI configuration
   PUSTAK_WEBHOOK_URL = "https://your-pustak-domain.vercel.app/api/webhook"
   ```

2. **Test Webhook**
   ```bash
   curl -X POST https://your-pustak-domain.vercel.app/api/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "repoName": "test-repo",
       "docType": "changes",
       "content": "# New Changes\n\nUpdated documentation"
     }'
   ```

### GitHub Actions Integration (Optional)

Create a GitHub Action to sync documentation:

```yaml
# .github/workflows/sync-docs.yml
name: Sync Documentation
on:
  push:
    branches: [main]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Sync to Pustak
        run: |
          curl -X POST ${{ secrets.PUSTAK_API_URL }}/sync \
            -H "Authorization: Bearer ${{ secrets.PUSTAK_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"repoName": "${{ github.repository }}", "docType": "summary", "content": "..."}'
```

## 📊 Monitoring & Analytics

### Vercel Analytics (Free)

1. **Enable Analytics**
   - Go to your Vercel project
   - Settings → Analytics
   - Enable Web Analytics

### Custom Monitoring

Add monitoring to your API routes:

```typescript
// src/app/api/sync/route.ts
export async function POST(request: NextRequest) {
  const start = Date.now();

  try {
    // ... your code ...

    // Log success
    console.log(`Sync completed in ${Date.now() - start}ms`);
  } catch (error) {
    // Log error
    console.error(`Sync failed after ${Date.now() - start}ms:`, error);
  }
}
```

## 🔒 Security Considerations

### Environment Variables

- Never commit sensitive tokens to git
- Use Vercel's environment variable system
- Rotate tokens regularly

### API Security

- Add rate limiting to your API routes
- Validate webhook signatures
- Use HTTPS in production

### Access Control

- Consider adding authentication for sensitive documentation
- Use GitHub OAuth for team access
- Implement role-based access control

## 🎉 Success Checklist

- [ ] Pustak deployed and accessible
- [ ] DocAI integration configured
- [ ] Webhook URL updated in DocAI
- [ ] Test sync successful
- [ ] Documentation appears on Pustak
- [ ] Auto-sync working
- [ ] Custom domain configured (optional)
- [ ] Monitoring enabled (optional)

## 🆘 Troubleshooting

### Common Issues

1. **Build Failures**

   - Check Node.js version (18+)
   - Verify all dependencies installed
   - Check for TypeScript errors

2. **API Not Working**

   - Verify environment variables
   - Check Vercel function logs
   - Test API endpoints manually

3. **Sync Not Working**

   - Verify PUSTAK_URL in DocAI
   - Check webhook URL configuration
   - Test webhook manually

4. **Documentation Not Updating**
   - Check DocAI logs
   - Verify repository permissions
   - Test sync API endpoint

### Getting Help

- **Vercel Support**: https://vercel.com/support
- **Next.js Docs**: https://nextjs.org/docs
- **GitHub Issues**: Create an issue in your repository

## 🚀 Next Steps

After successful deployment:

1. **Share with Team**

   - Add team members to Vercel project
   - Share the Pustak URL
   - Set up notifications

2. **Scale Up**

   - Add more repositories
   - Configure custom domains
   - Add advanced features

3. **Monitor Usage**
   - Track documentation views
   - Monitor sync performance
   - Gather user feedback

---

**Congratulations!** 🎉 Your Pustak documentation platform is now live and integrated with DocAI!

Your team now has a beautiful, AI-powered documentation platform that automatically stays up-to-date with your codebase changes.
