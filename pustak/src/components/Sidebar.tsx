"use client";

import { useState, useEffect } from "react";
import {
  BookOpen,
  ChevronRight,
  ChevronDown,
  FileText,
  Building2,
  Code,
  History,
  GitBranch,
  Clock,
  Settings,
  Home,
  X,
} from "lucide-react";

interface SidebarProps {
  onClose: () => void;
}

interface RepoData {
  name: string;
  fullName: string;
  lastUpdated: string;
  description: string;
  hasDocs: boolean;
  docs: {
    summary: string;
    architecture: string;
    workflow: string;
    api: string;
    changes: string;
    changelog: string;
  };
}

export function Sidebar({ onClose }: SidebarProps) {
  const [repos, setRepos] = useState<RepoData[]>([]);
  const [expandedRepos, setExpandedRepos] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load repositories from API route (server-side)
    const loadRepos = async () => {
      try {
        const response = await fetch('/api/repositories');
        if (!response.ok) {
          throw new Error('Failed to fetch repositories');
        }
        
        const repos = await response.json();

        const reposData: RepoData[] = repos.map((repo: any) => ({
          name: repo.name,
          fullName: repo.fullName,
          lastUpdated: repo.lastUpdated,
          description: repo.description,
          hasDocs: repo.hasLocalDocs,
          docs: {
            summary: "Summary",
            architecture: "Architecture",
            workflow: "Workflow",
            api: "API Documentation",
            changes: "Recent Changes",
            changelog: "Changelog",
          },
        }));

        setRepos(reposData);
        setLoading(false);
      } catch (error) {
        console.error("Failed to load repositories:", error);
        setLoading(false);
      }
    };

    loadRepos();
  }, []);

  const toggleRepo = (repoName: string) => {
    const newExpanded = new Set(expandedRepos);
    if (newExpanded.has(repoName)) {
      newExpanded.delete(repoName);
    } else {
      newExpanded.add(repoName);
    }
    setExpandedRepos(newExpanded);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getDocIcon = (docType: string) => {
    switch (docType) {
      case "summary":
        return <Home className="w-4 h-4" />;
      case "architecture":
        return <Building2 className="w-4 h-4" />;
      case "workflow":
        return <GitBranch className="w-4 h-4" />;
      case "api":
        return <Code className="w-4 h-4" />;
      case "changes":
        return <History className="w-4 h-4" />;
      case "changelog":
        return <Clock className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-gray-100 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Pustak
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Documentation Platform
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="flex-1 p-4 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Loading repositories...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-100 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Pustak
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Documentation Platform
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <nav className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Repositories ({repos.length})
        </h3>

        <div className="space-y-2">
          {repos.map((repo) => (
            <div
              key={repo.name}
              className="border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              <button
                onClick={() => toggleRepo(repo.name)}
                className="flex items-center justify-between w-full p-3 text-left text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors rounded-lg"
              >
                <div className="flex items-center space-x-2">
                  <GitBranch className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <span className="font-medium">{repo.name}</span>
                </div>
                {expandedRepos.has(repo.name) ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>

              {expandedRepos.has(repo.name) && (
                <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <div className="p-3 text-xs text-gray-500 dark:text-gray-400">
                    <p className="mb-2">{repo.description}</p>
                    <p className="mb-2">
                      Updated {formatDate(repo.lastUpdated)}
                    </p>

                    {repo.hasDocs ? (
                      <div className="space-y-1">
                        {Object.entries(repo.docs).map(
                          ([docType, docTitle]) => (
                            <a
                              key={docType}
                              href={`/repo/${repo.name}/${docType}`}
                              className="flex items-center space-x-2 p-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                            >
                              {getDocIcon(docType)}
                              <span>{docTitle}</span>
                            </a>
                          )
                        )}
                      </div>
                    ) : (
                      <p className="text-yellow-600 dark:text-yellow-400">
                        No documentation yet. DocAI will generate it soon!
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </nav>

      <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-center text-xs text-gray-500 dark:text-gray-400">
        Powered by DocAI v1.0.0
      </div>
    </div>
  );
}
