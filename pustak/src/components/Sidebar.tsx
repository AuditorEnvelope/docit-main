"use client";

import { useState, useEffect } from "react";
import {
  BookOpen,
  ChevronRight,
  ChevronDown,
  FileText,
  Architecture,
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
  docs: {
    summary?: string;
    architecture?: string;
    workflow?: string;
    api?: string;
    changes?: string;
    changelog?: string;
  };
}

export function Sidebar({ onClose }: SidebarProps) {
  const [repos, setRepos] = useState<RepoData[]>([]);
  const [expandedRepos, setExpandedRepos] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching repos - in real app, this would be an API call
    const mockRepos: RepoData[] = [
      {
        name: "hivemind-poc",
        fullName: "AuditorEnvelope/hivemind-poc",
        lastUpdated: "2024-01-15T10:30:00Z",
        docs: {
          summary: "Hivemind POC Documentation",
          architecture: "System Architecture",
          workflow: "Development Workflow",
          api: "API Documentation",
          changes: "Recent Changes",
          changelog: "Changelog",
        },
      },
      {
        name: "doc-ai",
        fullName: "AuditorEnvelope/doc-ai",
        lastUpdated: "2024-01-15T09:15:00Z",
        docs: {
          summary: "DocAI Documentation",
          architecture: "Agent Architecture",
          workflow: "Documentation Workflow",
          api: "API Reference",
          changes: "Change Log",
          changelog: "Version History",
        },
      },
    ];

    setTimeout(() => {
      setRepos(mockRepos);
      setLoading(false);
    }, 1000);
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
    return new Date(dateString).toLocaleDateString("en-US", {
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
        return <Architecture className="w-4 h-4" />;
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
      <div className="h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <span className="font-semibold text-gray-900 dark:text-gray-100">
                Pustak
              </span>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden p-1 rounded-md text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="p-4">
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              Pustak
            </span>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-md text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Documentation Platform
        </p>
      </div>

      {/* Repositories */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
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
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <GitBranch className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {repo.name}
                    </span>
                  </div>
                  {expandedRepos.has(repo.name) ? (
                    <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  )}
                </button>

                {expandedRepos.has(repo.name) && (
                  <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <div className="p-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                        Updated {formatDate(repo.lastUpdated)}
                      </p>

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
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Powered by DocAI</span>
          <span>v1.0.0</span>
        </div>
      </div>
    </div>
  );
}
