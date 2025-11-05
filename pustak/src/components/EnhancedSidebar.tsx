"use client";

import { useState, useEffect, JSX } from "react";
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
  Folder,
  Plus,
  AlertCircle,
  Zap,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

interface SidebarProps {
  onClose: () => void;
}

interface DocbookFile {
  name: string;
  type: "file" | "folder";
  files?: DocbookFile[]; // For nested folders
}

interface DocbookFolder extends DocbookFile {
  type: "folder"; // Folders always have type "folder"
}

interface DocbookRepo {
  orgId: string;
  fullName: string;
  hasDocbook: boolean;
  folders: DocbookFile[]; // Top-level items (files and folders)
  hasGeneratedDocs: boolean;
}

export function EnhancedSidebar({ onClose }: SidebarProps) {
  const [docbooks, setDocbooks] = useState<DocbookRepo[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const loadDocbooks = async () => {
      try {
        const userToken = localStorage.getItem("pustak_access_token");

        if (!userToken) {
          console.log("No user token available");
          setLoading(false);
          return;
        }

        // Get user's organizations
        const response = await fetch("/api/user/organizations", {
          headers: {
            Authorization: `Bearer ${userToken}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to fetch organizations");
        }

        const orgsData = await response.json();
        const docbookRepos: DocbookRepo[] = [];

        // For each org, check if docbook repo exists and load its structure
        for (const org of orgsData.organizations || []) {
          const orgLogin = org.login;
          const docbookName = `pustak-docbook-${orgLogin}`;
          
          try {
            // Check if docbook repo exists and get staging branch structure
            const structureResponse = await fetch(
              `/api/docbook/${orgLogin}/structure?branch=staging`,
              {
                headers: {
                  Authorization: `Bearer ${userToken}`,
                },
              }
            );

            if (structureResponse.ok) {
              const structure = await structureResponse.json();
              docbookRepos.push({
                orgId: orgLogin,
                fullName: `${orgLogin}/${docbookName}`,
                hasDocbook: true,
                folders: structure.folders || [],
                hasGeneratedDocs: (structure.folders || []).length > 0,
              });
            } else {
              // Docbook repo doesn't exist
              docbookRepos.push({
                orgId: orgLogin,
                fullName: `${orgLogin}/${docbookName}`,
                hasDocbook: false,
                folders: [],
                hasGeneratedDocs: false,
              });
            }
          } catch (error) {
            console.error(`Error loading docbook for ${orgLogin}:`, error);
            docbookRepos.push({
              orgId: orgLogin,
              fullName: `${orgLogin}/${docbookName}`,
              hasDocbook: false,
              folders: [],
              hasGeneratedDocs: false,
            });
          }
        }

        setDocbooks(docbookRepos);
        setLoading(false);
      } catch (error) {
        console.error("Failed to load docbooks:", error);
        setLoading(false);
      }
    };

    loadDocbooks();
  }, []);

  const toggleFolder = (folderKey: string, href?: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderKey)) {
      newExpanded.delete(folderKey);
    } else {
      newExpanded.add(folderKey);
    }
    setExpandedFolders(newExpanded);

    if (href) {
      router.push(href);
    }
  };

  const isActive = (path: string) => {
    return pathname === path;
  };

  // Recursive component to render nested files/folders
  const renderFileTree = (
    items: DocbookFile[],
    basePath: string[] = [],
    docbookFullName: string
  ): JSX.Element => {
    const repoHrefBase = `/repo/${docbookFullName
      .split("/")
      .map((segment) => encodeURIComponent(segment))
      .join("/")}`;

    const toEncodedPath = (segments: string[]) =>
      segments.map((segment) => encodeURIComponent(segment)).join('/');

    return (
      <div className="space-y-1">
        {items.map((item) => {
          if (basePath.length === 0 && item.type === "file") {
            // Skip top-level files like README.md; only show folders at root
            return null;
          }

          const itemPath = [...basePath, item.name];
          const itemKey = itemPath.join('/');
          const isExpanded = expandedFolders.has(itemKey);

          if (item.type === "file") {
            // Clickable file link using actual file path
            const encodedFilePath = toEncodedPath(itemPath);
            const href = `${repoHrefBase}/${encodedFilePath}`;

            return (
              <a
                key={itemKey}
                href={href}
                className={`flex items-center space-x-2 p-1.5 text-xs rounded transition-colors cursor-pointer ${
                  isActive(href)
                    ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-200"
                }`}
              >
                <FileText className="w-3 h-3 text-gray-400" />
                <span>{item.name}</span>
              </a>
            );
          } else {
            // Expandable folder
            const lowerName = item.name.toLowerCase();
            const defaultHref =
              lowerName === "architecture" || lowerName === "workflow"
                ? `${repoHrefBase}/${toEncodedPath([...itemPath, "current.md"])}`
                : undefined;

            return (
              <div key={itemKey} className="space-y-1">
                <button
                  onClick={() => toggleFolder(itemKey, defaultHref)}
                  className="flex items-center justify-between w-full p-1.5 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <Folder className="w-3 h-3 text-blue-500" />
                    <span>{item.name}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRight className="w-3 h-3" />
                  )}
                </button>
                {isExpanded && item.files && (
                  <div className="ml-4 mt-1">
                    {renderFileTree(item.files, itemPath, docbookFullName)}
                  </div>
                )}
              </div>
            );
          }
        })}
      </div>
    );
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
      {/* Header */}
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

      {/* Content */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Documentation ({docbooks.length})
        </h3>

        <div className="space-y-3">
          {docbooks.map((docbook) => (
            <div key={docbook.orgId} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              {/* Docbook Header */}
              <div className="p-3 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                <div className="flex items-center space-x-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                  <GitBranch className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span>{docbook.orgId}</span>
                </div>
              </div>

              {/* Docbook Content */}
              <div className="p-3">
                {!docbook.hasDocbook ? (
                  // No Docbook Repo
                  <div className="space-y-2">
                    <div className="flex items-start space-x-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-md border border-yellow-200 dark:border-yellow-800">
                      <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-yellow-700 dark:text-yellow-300">
                        <p className="font-medium mb-1">No Docbook Repository Found</p>
                        <p className="text-yellow-600 dark:text-yellow-400">
                          Create a repository named <code className="bg-yellow-100 dark:bg-yellow-900/40 px-1 rounded text-xs">pustak-docbook-{docbook.orgId}</code> to get started.
                        </p>
                      </div>
                    </div>
                    <button className="w-full flex items-center justify-center space-x-2 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-medium transition-colors">
                      <Plus className="w-3 h-3" />
                      <span>Create Docbook</span>
                    </button>
                  </div>
                ) : !docbook.hasGeneratedDocs ? (
                  // Docbook exists but no docs generated
                  <div className="space-y-2">
                    <div className="flex items-start space-x-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                      <Zap className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-blue-700 dark:text-blue-300">
                        <p className="font-medium">No Documents Generated Yet</p>
                        <p className="text-blue-600 dark:text-blue-400 mt-1">
                          Generate documentation for your repositories to see them here.
                        </p>
                      </div>
                    </div>
                    <button className="w-full flex items-center justify-center space-x-2 p-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-xs font-medium transition-colors">
                      <Zap className="w-3 h-3" />
                      <span>Generate Docs</span>
                    </button>
                  </div>
                ) : (
                  // Docbook exists with generated docs
                  <div className="space-y-2">
                    <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-medium">
                      📁 Files in staging branch:
                    </div>
                    
                    {/* Render the file tree starting from root level */}
                    <div className="space-y-2">
                      {renderFileTree(docbook.folders, [], docbook.fullName)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-center text-xs text-gray-500 dark:text-gray-400">
        Powered by Pustak v1.0.0
      </div>
    </div>
  );
}
