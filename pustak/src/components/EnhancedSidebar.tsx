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
  Home,
  X,
} from "lucide-react";
import { usePathname } from "next/navigation";

interface SidebarProps {
  onClose: () => void;
}

interface RepoData {
  name: string;
  fullName: string;
  lastUpdated: string;
  description: string;
  hasDocs: boolean;
  hasDocsFolder: boolean;
  architectureVersions: Array<{ version: string; fileName: string }>;
  workflowVersions: Array<{ version: string; fileName: string }>;
}

export function EnhancedSidebar({ onClose }: SidebarProps) {
  const [repos, setRepos] = useState<RepoData[]>([]);
  const [expandedRepos, setExpandedRepos] = useState<Set<string>>(new Set());
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  useEffect(() => {
    const loadRepos = async () => {
      try {
        // Get user's GitHub token from localStorage
        const userToken = localStorage.getItem('pustak_access_token');
        
        if (!userToken) {
          console.log('No user token available - using default repos');
          setLoading(false);
          return;
        }

        // Pass user token to backend
        const response = await fetch('/api/repositories', {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch repositories');
        }
        
        const reposData = await response.json();

        // Map repos directly - versions come from backend
        const mappedRepos = reposData.map((repo: any) => ({
          name: repo.name,
          fullName: repo.full_name || repo.fullName,
          lastUpdated: repo.updated_at || repo.lastUpdated,
          description: repo.description || 'No description available',
          hasDocs: repo.hasDocsFolder || false,  // Use hasDocsFolder from backend
          hasDocsFolder: repo.hasDocsFolder || false,
          architectureVersions: repo.architectureVersions || [],
          workflowVersions: repo.workflowVersions || [],
        }));

        setRepos(mappedRepos);
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

  const toggleSection = (sectionKey: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionKey)) {
      newExpanded.delete(sectionKey);
    } else {
      newExpanded.add(sectionKey);
    }
    setExpandedSections(newExpanded);
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

  const isActive = (path: string) => {
    return pathname === path;
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
                    <p className="mb-3">
                      Updated {formatDate(repo.lastUpdated)}
                    </p>

                    {repo.hasDocs ? (
                      <div className="space-y-1">
                        {/* Summary */}
                        <a
                          href={`/repo/${repo.fullName}/summary`}
                          className={`flex items-center space-x-2 p-2 text-sm rounded-md transition-colors ${
                            isActive(`/repo/${repo.fullName}/summary`)
                              ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          }`}
                        >
                          {getDocIcon("summary")}
                          <span>Summary</span>
                        </a>

                        {/* Architecture with versions */}
                        <div>
                          <button
                            onClick={() => toggleSection(`${repo.fullName}-architecture`)}
                            className={`flex items-center justify-between w-full p-2 text-sm rounded-md transition-colors ${
                              isActive(`/repo/${repo.fullName}/architecture`)
                                ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                            }`}
                          >
                            <div className="flex items-center space-x-2">
                              {getDocIcon("architecture")}
                              <span>Architecture</span>
                            </div>
                            {repo.architectureVersions.length > 0 && (
                              expandedSections.has(`${repo.fullName}-architecture`) ? (
                                <ChevronDown className="w-3 h-3" />
                              ) : (
                                <ChevronRight className="w-3 h-3" />
                              )
                            )}
                          </button>
                          
                          {expandedSections.has(`${repo.fullName}-architecture`) && repo.architectureVersions.length > 0 && (
                            <div className="ml-6 mt-1 space-y-1">
                              {repo.architectureVersions.map((v) => (
                                <a
                                  key={v.version}
                                  href={`/repo/${repo.fullName}/architecture/${v.version}`}
                                  className={`block p-1.5 text-xs rounded transition-colors ${
                                    isActive(`/repo/${repo.fullName}/architecture/${v.version}`)
                                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                                  }`}
                                >
                                  {v.version.toUpperCase()}
                                </a>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Workflow with versions */}
                        <div>
                          <button
                            onClick={() => toggleSection(`${repo.fullName}-workflow`)}
                            className={`flex items-center justify-between w-full p-2 text-sm rounded-md transition-colors ${
                              isActive(`/repo/${repo.fullName}/workflow`)
                                ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                            }`}
                          >
                            <div className="flex items-center space-x-2">
                              {getDocIcon("workflow")}
                              <span>Workflow</span>
                            </div>
                            {repo.workflowVersions.length > 0 && (
                              expandedSections.has(`${repo.fullName}-workflow`) ? (
                                <ChevronDown className="w-3 h-3" />
                              ) : (
                                <ChevronRight className="w-3 h-3" />
                              )
                            )}
                          </button>
                          
                          {expandedSections.has(`${repo.fullName}-workflow`) && repo.workflowVersions.length > 0 && (
                            <div className="ml-6 mt-1 space-y-1">
                              {repo.workflowVersions.map((v) => (
                                <a
                                  key={v.version}
                                  href={`/repo/${repo.fullName}/workflow/${v.version}`}
                                  className={`block p-1.5 text-xs rounded transition-colors ${
                                    isActive(`/repo/${repo.fullName}/workflow/${v.version}`)
                                      ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
                                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                                  }`}
                                >
                                  {v.version.toUpperCase()}
                                </a>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* API */}
                        <a
                          href={`/repo/${repo.fullName}/api`}
                          className={`flex items-center space-x-2 p-2 text-sm rounded-md transition-colors ${
                            isActive(`/repo/${repo.fullName}/api`)
                              ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          }`}
                        >
                          {getDocIcon("api")}
                          <span>API Documentation</span>
                        </a>

                        {/* Changes */}
                        <a
                          href={`/repo/${repo.fullName}/changes`}
                          className={`flex items-center space-x-2 p-2 text-sm rounded-md transition-colors ${
                            isActive(`/repo/${repo.fullName}/changes`)
                              ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          }`}
                        >
                          {getDocIcon("changes")}
                          <span>Recent Changes</span>
                        </a>

                        {/* Changelog */}
                        <a
                          href={`/repo/${repo.fullName}/changelog`}
                          className={`flex items-center space-x-2 p-2 text-sm rounded-md transition-colors ${
                            isActive(`/repo/${repo.fullName}/changelog`)
                              ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                              : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                          }`}
                        >
                          {getDocIcon("changelog")}
                          <span>Changelog</span>
                        </a>
                      </div>
                    ) : null}
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
