"use client";

import { Layout } from "@/components/Layout";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { useState, useEffect } from "react";
import {
  BookOpen,
  GitBranch,
  Clock,
  FileText,
  Building2,
  Code,
  History,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";

const mockContent = `# Welcome to Pustak

**Pustak** (पुस्तक) is a beautiful, AI-powered documentation platform that automatically generates and maintains documentation for your repositories.

## 🚀 Features

### 📚 Multi-Repository Support
- Organize documentation across multiple repositories
- Each repository gets its own documentation space
- Automatic discovery and indexing of repositories

### 🤖 AI-Powered Documentation
- Automatically generated documentation from code changes
- Smart analysis of significant changes
- Context-aware documentation creation

### 🎨 Beautiful Interface
- Clean, GitBook-inspired design
- Dark and light themes
- Responsive layout for all devices
- Fast search across all documentation

### 🔄 Real-time Updates
- Automatic synchronization with repository changes
- Live updates when new documentation is generated
- Version history and change tracking

## 📖 Documentation Structure

Each repository's documentation includes:

### 📋 Summary
- Project overview and purpose
- Key features and capabilities
- Getting started guide

### 🏗️ Architecture
- System architecture diagrams
- Component relationships
- Technology stack details

### 🔄 Workflow
- Development workflow
- CI/CD processes
- Deployment procedures

### 🔌 API Documentation
- Endpoint documentation
- Request/response examples
- Authentication details

### 📝 Changes
- Recent changes and updates
- Feature additions and modifications
- Bug fixes and improvements

### 📚 Changelog
- Version history
- Release notes
- Breaking changes

## 🛠️ Powered by DocAI

Pustak is powered by **DocAI**, an intelligent documentation agent that:

- Analyzes code changes automatically
- Generates comprehensive documentation
- Maintains consistency across repositories
- Scales with your organization

## 🎯 Getting Started

1. **Explore Repositories**: Use the sidebar to navigate between different repositories
2. **Search Documentation**: Use the search feature (⌘K) to find specific topics
3. **Browse by Category**: Navigate through different documentation sections
4. **Stay Updated**: Check the Changes section for recent updates

## 🔮 Future Roadmap

- **Collaborative Editing**: Real-time collaborative documentation editing
- **Version Control**: Git-like versioning for documentation
- **API Integration**: REST API for programmatic access
- **Advanced Search**: AI-powered semantic search
- **Custom Themes**: Customizable themes and branding
- **Export Options**: PDF, HTML, and other export formats

---

*Pustak is continuously evolving. Stay tuned for more features and improvements!*
`;

export default function HomePage() {
  const [stats, setStats] = useState({
    repositories: 0,
    documents: 0,
    updates: 0,
    lastUpdate: "Loading...",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const response = await fetch('/api/repositories');
        if (!response.ok) {
          throw new Error('Failed to fetch repositories');
        }
        const repos = await response.json();
        const repoCount = repos.length;
        
        // Calculate total documents (6 doc types per repo)
        const docCount = repoCount * 6;
        
        // Get the most recent update time
        const mostRecent = repos.reduce((latest: Date, repo: any) => {
          const repoDate = new Date(repo.lastUpdated);
          return repoDate > latest ? repoDate : latest;
        }, new Date(0));
        
        const now = new Date();
        const diffMs = now.getTime() - mostRecent.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);
        
        let lastUpdateStr = "Just now";
        if (diffDays > 0) {
          lastUpdateStr = `${diffDays}d ago`;
        } else if (diffHours > 0) {
          lastUpdateStr = `${diffHours}h ago`;
        }
        
        setStats({
          repositories: repoCount,
          documents: docCount,
          updates: repoCount * 8, // Approximate updates
          lastUpdate: lastUpdateStr,
        });
        setLoading(false);
      } catch (error) {
        console.error("Failed to load stats:", error);
        setLoading(false);
      }
    }
    
    loadStats();
  }, []);

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-800 dark:to-gray-900 py-16">
          <div className="max-w-4xl mx-auto px-6">
            <div className="text-center">
              <div className="flex items-center justify-center space-x-3 mb-6">
                <BookOpen className="w-12 h-12 text-blue-600 dark:text-blue-400" />
                <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">
                  Pustak
                </h1>
              </div>
              <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
                Beautiful, AI-powered documentation platform that automatically
                generates and maintains documentation for your repositories.
              </p>

              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-center space-x-2 mb-2">
                    <GitBranch className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {loading ? "..." : stats.repositories}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Repositories
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-center space-x-2 mb-2">
                    <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {loading ? "..." : stats.documents}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Documents
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-center space-x-2 mb-2">
                    <History className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {loading ? "..." : stats.updates}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Updates
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-center space-x-2 mb-2">
                    <Clock className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                    <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {loading ? "..." : stats.lastUpdate}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Last Update
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="py-16">
          <div className="max-w-6xl mx-auto px-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
              <div className="text-center">
                <div className="bg-blue-100 dark:bg-blue-900 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  AI-Powered
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Automatically generates documentation from your code changes
                  using advanced AI.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-green-100 dark:bg-green-900 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <TrendingUp className="w-8 h-8 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Always Updated
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Documentation stays in sync with your codebase automatically.
                </p>
              </div>

              <div className="text-center">
                <div className="bg-purple-100 dark:bg-purple-900 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Users className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Team Ready
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Designed for teams with collaborative features and
                  organization-wide access.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-6 pb-16">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="p-8">
              <MarkdownRenderer content={mockContent} />
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
