"use client";

import { Layout } from "@/components/Layout";
import { useState, useEffect } from "react";
import { useAuth } from '@/contexts/AuthContext';
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
  Search,
} from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default function HomePage() {
  const { token, user } = useAuth();
  const [stats, setStats] = useState({
    repositories: 0,
    documents: 0,
    updates: 0,
    lastUpdate: "N/A",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      // If user is logged in, fetch their actual stats
      if (token) {
        try {
          const response = await fetch(`${BACKEND_URL}/auth/repositories`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          if (response.ok) {
            const data = await response.json();
            const repos = data.repositories || [];
            const repoCount = repos.length;
            
            // Calculate total documents (6 doc types per repo)
            const docCount = repoCount * 6;
            
            // Get the most recent update time
            if (repos.length > 0) {
              const mostRecent = repos.reduce((latest: Date, repo: any) => {
                const repoDate = new Date(repo.updated_at);
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
                updates: repoCount * 8,
                lastUpdate: lastUpdateStr,
              });
            }
          }
        } catch (error) {
          console.error("Failed to load stats:", error);
        }
      }
      // If not logged in, show generic stats
      setLoading(false);
    }
    
    loadStats();
  }, [token]);

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

              {/* Quick Search */}
              <div className="max-w-xl mx-auto mb-8">
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    // Trigger search modal via keyboard shortcut
                    const event = new KeyboardEvent('keydown', {
                      key: 'k',
                      metaKey: true,
                      bubbles: true,
                      cancelable: true
                    });
                    document.dispatchEvent(event);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-400 dark:hover:border-blue-600 transition-colors group cursor-pointer"
                >
                  <Search className="w-5 h-5 text-gray-400 group-hover:text-blue-500 pointer-events-none" />
                  <span className="flex-1 text-left text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300 pointer-events-none">
                    Search documentation...
                  </span>
                  <kbd className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded pointer-events-none">
                    ⌘K
                  </kbd>
                </button>
              </div>

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

        {/* Welcome Section */}
        <div className="max-w-4xl mx-auto px-6 pb-16">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Welcome to Pustak
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Pustak (पुस्तक) is an AI-powered documentation platform that automatically generates
              and maintains documentation for your repositories. Select a repository from the sidebar
              to explore its documentation.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                  🚀 AI-Powered
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Automatically generates documentation from your code changes using advanced AI
                </p>
              </div>
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <h3 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                  🔄 Real-time Updates
                </h3>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Automatic synchronization with repository changes and live updates
                </p>
              </div>
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">
                  📚 Multi-Repository
                </h3>
                <p className="text-sm text-purple-700 dark:text-purple-300">
                  Organize documentation across multiple repositories with automatic discovery
                </p>
              </div>
              <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <h3 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">
                  🎨 Beautiful Interface
                </h3>
                <p className="text-sm text-orange-700 dark:text-orange-300">
                  Clean, GitBook-inspired design with dark mode and responsive layout
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
