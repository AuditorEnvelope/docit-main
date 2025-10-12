# Pustak 📚

**Pustak** (पुस्तक) is a beautiful, AI-powered documentation platform that automatically generates and maintains documentation for your repositories. It's designed to replace GitBook and scale across your entire organization.

## ✨ Features

### 🚀 **Multi-Repository Support**

- Organize documentation across multiple repositories
- Each repository gets its own documentation space
- Automatic discovery and indexing of repositories

### 🤖 **AI-Powered Documentation**

- Automatically generated documentation from code changes
- Smart analysis of significant changes
- Context-aware documentation creation

### 🎨 **Beautiful Interface**

- Clean, GitBook-inspired design
- Dark and light themes
- Responsive layout for all devices
- Fast search across all documentation

### 🔄 **Real-time Updates**

- Automatic synchronization with repository changes
- Live updates when new documentation is generated
- Version history and change tracking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DocAI Agent   │    │   GitHub API    │    │   Pustak Web    │
│                 │    │                 │    │                 │
│ - Webhook       │───▶│ - Repository    │◀───│ - Next.js App   │
│ - Smart         │    │ - Documentation │    │ - API Routes    │
│   Processor     │    │ - Changes       │    │ - Real-time UI  │
│ - LLM Provider  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
pustak/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── api/               # API routes
│   │   │   ├── sync/          # Sync with DocAI
│   │   │   └── webhook/       # Webhook handlers
│   │   ├── repo/              # Repository pages
│   │   │   └── [repoName]/    # Dynamic repo routes
│   │   │       └── [docType]/ # Dynamic doc type routes
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   └── providers.tsx      # Theme providers
│   ├── components/            # React components
│   │   ├── Layout.tsx         # Main layout
│   │   ├── Sidebar.tsx        # Navigation sidebar
│   │   ├── SearchModal.tsx    # Search functionality
│   │   └── MarkdownRenderer.tsx # Markdown rendering
│   └── lib/                   # Utilities
│       └── api.ts             # API integration
├── public/                    # Static assets
├── vercel.json               # Vercel deployment config
└── package.json              # Dependencies
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- DocAI agent running (for full functionality)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd pustak
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Run development server**

   ```bash
   npm run dev
   ```

4. **Open your browser**
   ```
   http://localhost:3000
   ```

### Environment Variables

Create a `.env.local` file:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:3000/api
GITHUB_TOKEN=your_github_token
DOCAI_WEBHOOK_URL=http://localhost:8000/webhook

# Optional: Database (for production)
DATABASE_URL=your_database_url
```

## 🎯 Usage

### Navigation

- **Sidebar**: Browse repositories and documentation
- **Search**: Use `⌘K` to search across all documentation
- **Theme**: Toggle between light and dark themes

### Documentation Structure

Each repository includes:

- **Summary**: Project overview and getting started
- **Architecture**: System design and components
- **Workflow**: Development and deployment processes
- **API**: API documentation and examples
- **Changes**: Recent updates and modifications
- **Changelog**: Version history and release notes

## 🔧 Development

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checks
```

### Adding New Features

1. **Components**: Add new components in `src/components/`
2. **Pages**: Add new pages in `src/app/`
3. **API**: Add new API routes in `src/app/api/`
4. **Styling**: Use Tailwind CSS classes

### Code Structure

- **Components**: Reusable UI components
- **Pages**: Route-based pages using App Router
- **API Routes**: Serverless API endpoints
- **Lib**: Utility functions and API integration

## 🚀 Deployment

### Vercel (Recommended)

1. **Connect to Vercel**

   ```bash
   npx vercel
   ```

2. **Configure environment variables**

   - Set `GITHUB_TOKEN`
   - Set `DOCAI_WEBHOOK_URL`
   - Set `NEXT_PUBLIC_API_URL`

3. **Deploy**
   ```bash
   npx vercel --prod
   ```

### Other Platforms

Pustak can be deployed to any platform that supports Next.js:

- Netlify
- AWS Amplify
- Railway
- DigitalOcean App Platform

## 🔗 Integration with DocAI

### Webhook Configuration

1. **In DocAI agent**, update the webhook URL:

   ```python
   # In your DocAI config
   PUSTAK_WEBHOOK_URL = "https://your-pustak-domain.com/api/webhook"
   ```

2. **DocAI will automatically notify Pustak** when new documentation is generated

### Manual Sync

You can also trigger manual sync:

```bash
curl -X POST https://your-pustak-domain.com/api/sync \
  -H "Content-Type: application/json" \
  -d '{"repoName": "your-repo", "docType": "summary", "content": "..."}'
```

## 🎨 Customization

### Themes

- Modify `tailwind.config.js` for custom colors
- Add new themes in `src/app/providers.tsx`

### Layout

- Customize `src/components/Layout.tsx`
- Modify sidebar in `src/components/Sidebar.tsx`

### Styling

- Use Tailwind CSS classes
- Add custom CSS in `src/app/globals.css`

## 📊 Performance

### Optimization Features

- **Static Generation**: Pre-built pages for fast loading
- **Image Optimization**: Automatic image optimization
- **Code Splitting**: Automatic code splitting
- **Caching**: Intelligent caching strategies

### Monitoring

- Built-in performance monitoring
- Real-time metrics
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **DocAI**: The intelligent documentation agent
- **Next.js**: The React framework
- **Tailwind CSS**: The CSS framework
- **Vercel**: The deployment platform

## 📞 Support

- **Documentation**: Check this README and inline comments
- **Issues**: Create an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

---

**Pustak** - Beautiful documentation, powered by AI 🤖📚
