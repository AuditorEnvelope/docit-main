"use client";

import { useState, useEffect, JSX } from "react";
import {
  BookOpen,
  ChevronRight,
  ChevronDown,
  FileText,
  GitBranch,
  X,
  Folder,
  Plus,
  Zap,
  Sparkles,
  Globe2,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { mapDocbookPathToDocsSlug } from "@/lib/docsPathMapper";

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
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(),
  );
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const safeSetExpandedFolders = (updater: (draft: Set<string>) => void) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      updater(next);
      return next;
    });
  };

  useEffect(() => {
    const loadDocbooks = async () => {
      try {
        const userToken = localStorage.getItem("DocIt_access_token");

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

        const cleanDocbookFolders = (
          items: DocbookFile[] | undefined,
          docbookName: string,
        ): DocbookFile[] => {
          if (!items || !Array.isArray(items)) return [];
          return items
            .filter((item) => item.name !== docbookName)
            .map((item) =>
              item.type === "folder"
                ? {
                    ...item,
                    files: cleanDocbookFolders(item.files, docbookName),
                  }
                : item,
            );
        };

        // For each org, check if docbook repo exists and load its structure
        for (const org of orgsData.organizations || []) {
          const orgLogin = org.login;
          const docbookName = `DocIt-docbook-${orgLogin}`;

          try {
            // Check if docbook repo exists and get staging branch structure
            const structureResponse = await fetch(
              `/api/docbook/${orgLogin}/structure?branch=staging`,
              {
                headers: {
                  Authorization: `Bearer ${userToken}`,
                },
              },
            );

            if (structureResponse.ok) {
              const structure = await structureResponse.json();
              const cleanedFolders = cleanDocbookFolders(
                structure.folders,
                docbookName,
              );
              docbookRepos.push({
                orgId: orgLogin,
                fullName: `${orgLogin}/${docbookName}`,
                hasDocbook: true,
                folders: cleanedFolders,
                hasGeneratedDocs: cleanedFolders.length > 0,
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
    safeSetExpandedFolders((draft) => {
      if (draft.has(folderKey)) {
        draft.delete(folderKey);
      } else {
        draft.add(folderKey);
      }
    });

    if (href) {
      router.push(href);
    }
  };

  const isActive = (path: string) => {
    return pathname === path;
  };

  useEffect(() => {
    if (!pathname || docbooks.length === 0) {
      return;
    }

    safeSetExpandedFolders((draft) => {
      docbooks.forEach((docbook) => {
        const traverse = (items: DocbookFile[], basePath: string[] = []) => {
          items.forEach((item) => {
            const itemPath = [...basePath, item.name];

            if (item.type === "file") {
              const docRoute = mapDocbookPathToDocsSlug({
                org: docbook.orgId,
                pathSegments: itemPath,
              });

              if (docRoute && pathname === docRoute.href) {
                for (let i = 1; i < itemPath.length; i += 1) {
                  draft.add(itemPath.slice(0, i).join("/"));
                }
              }
              return;
            }

            if (item.files && item.files.length > 0) {
              traverse(item.files, itemPath);
            }
          });
        };

        traverse(docbook.folders);
      });
    });
  }, [pathname, docbooks]);

  // Recursive component to render nested files/folders
  const renderFileTree = (
    items: DocbookFile[],
    basePath: string[] = [],
    docbook: DocbookRepo,
  ): JSX.Element => {
    return (
      <div className="space-y-1">
        {items.map((item) => {
          if (basePath.length === 0 && item.type === "file") {
            return null;
          }

          const itemPath = [...basePath, item.name];
          const itemKey = itemPath.join("/");
          const isExpanded = expandedFolders.has(itemKey);

          if (item.type === "file") {
            const docRoute = mapDocbookPathToDocsSlug({
              org: docbook.orgId,
              pathSegments: itemPath,
            });

            if (!docRoute) {
              return null;
            }

            const href = docRoute.href;

            return (
              <Link
                key={itemKey}
                href={href}
                prefetch={false}
                className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-all duration-150 ${
                  isActive(href)
                    ? "bg-blue-500/15 text-blue-200 ring-1 ring-inset ring-blue-500/40"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                }`}
              >
                <FileText className="h-3 w-3 text-blue-300/80 flex-shrink-0" />
                <span className="truncate overflow-hidden text-ellipsis">
                  {item.name}
                </span>
              </Link>
            );
          }

          const lowerName = item.name.toLowerCase();
          const defaultDocRoute =
            lowerName === "architecture" || lowerName === "workflow"
              ? mapDocbookPathToDocsSlug({
                  org: docbook.orgId,
                  pathSegments: [...itemPath, "current.md"],
                })
              : null;
          const defaultHref = defaultDocRoute?.href;

          return (
            <div key={itemKey} className="space-y-1">
              <button
                onClick={() => toggleFolder(itemKey, defaultHref)}
                className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-800/60"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <Folder className="h-3 w-3 text-blue-300 flex-shrink-0" />
                  <span className="font-medium text-slate-100 truncate overflow-hidden text-ellipsis">
                    {item.name}
                  </span>
                </div>
                <span
                  className={`transition-transform flex-shrink-0 ${
                    isExpanded ? "rotate-180" : "rotate-0"
                  }`}
                >
                  <ChevronDown className="h-3 w-3" />
                </span>
              </button>
              {isExpanded && item.files && (
                <div className="ml-3 border-l border-slate-800/60 pl-3">
                  {renderFileTree(item.files, itemPath, docbook)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex h-full flex-col border-r border-slate-800/60 bg-slate-950/90 text-slate-100">
        <div className="border-b border-slate-800/60 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <BookOpen className="h-6 w-6 text-blue-400" />
              <div>
                <h2 className="text-lg font-semibold text-white">DocIt</h2>
                <p className="text-xs text-slate-400">Documentation Platform</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-slate-500 transition hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="text-center">
            <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-b-2 border-blue-500"></div>
            <p className="text-xs uppercase tracking-widest text-slate-400">
              Loading workspace
            </p>
          </div>
        </div>
        <div className="relative mt-5 space-y-2 rounded-2xl border border-slate-800/70 bg-slate-950/80 p-3 shadow-inner shadow-blue-950/40">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-100">
            <Sparkles className="h-3 w-3 text-blue-300 animate-pulse" />
            Orchestrate delightful docs in minutes
          </div>
          <p className="text-[9px] leading-relaxed text-slate-400">
            DocIt automates docbook staging so every product team ships
            architecture, workflow, and changelog updates with the same polish
            as their code.
          </p>
          <div className="grid gap-1.5 text-[9px] text-slate-300 sm:grid-cols-3">
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-800/80 bg-slate-900/70 px-2 py-1.5 transition duration-300 hover:border-blue-500/50 hover:bg-slate-900/90">
              <Globe2 className="h-3 w-3 text-emerald-300" />
              Multi-org ready
            </div>
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-800/80 bg-slate-900/70 px-2 py-1.5 transition duration-300 hover:border-blue-500/50 hover:bg-slate-900/90">
              <ShieldCheck className="h-3 w-3 text-sky-300" />
              Secure doc pipelines
            </div>
            <div className="flex items-center gap-1.5 rounded-xl border border-slate-800/80 bg-slate-900/70 px-2 py-1.5 transition duration-300 hover:border-blue-500/50 hover:bg-slate-900/90">
              <Zap className="h-3 w-3 text-amber-300" />
              AI-guided updates
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-r border-slate-800/70 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <div className="relative overflow-hidden border-b border-slate-800/70 px-3 py-4">
        <div
          className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.35),_transparent_55%)]"
          aria-hidden
        />
        <div
          className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.25),_transparent_60%)]"
          aria-hidden
        />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-blue-500/20 p-1.5 ring-1 ring-inset ring-blue-400/40">
              <BookOpen className="h-4 w-4 text-blue-300" />
            </div>
            <div>
              <p className="text-[8px] uppercase tracking-[0.15em] text-slate-400">
                Workspace
              </p>
              <h2 className="text-xs font-semibold text-white">
                DocIt Docs Hub
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-slate-700/70 bg-slate-900/70 p-1.5 text-slate-400 transition hover:border-slate-500/70 hover:text-white"
            aria-label="Close sidebar"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
        <div className="relative mt-3 grid grid-cols-2 gap-2 rounded-xl border border-slate-800/70 bg-slate-950/70 p-2 text-[8px] text-slate-400">
          <div className="flex flex-col gap-0.5">
            <span className="uppercase tracking-[0.15em]">Docbooks</span>
            <span className="text-sm font-semibold text-white">
              {docbooks.length}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 text-right">
            <span className="uppercase tracking-[0.15em]">Generated</span>
            <span className="text-sm font-semibold text-emerald-300">
              {docbooks.filter((docbook) => docbook.hasGeneratedDocs).length}
            </span>
          </div>
          <div className="col-span-2 text-[8px] leading-relaxed text-slate-500">
            Navigate your staging documentation and jump straight into
            architecture, workflows, and change logs.
          </div>
        </div>
      </div>

      {/* Content */}
      <nav className="flex-1 space-y-3 overflow-y-auto px-3 py-3 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700/70">
        {docbooks.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/40 p-6 text-center">
            <p className="text-sm font-medium text-slate-200">
              No organizations linked yet
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Connect an organization to automatically discover docbook
              repositories and generated documentation.
            </p>
            <button
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-blue-500/90 px-4 py-2 text-xs font-semibold text-white shadow-lg transition hover:bg-blue-500"
              onClick={() => router.push("/settings")}
            >
              <Plus className="h-3 w-3" />
              Connect organization
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {docbooks.map((docbook) => {
              const showEmptyState = !docbook.hasGeneratedDocs;
              return (
                <div
                  key={docbook.orgId}
                  className="group relative overflow-hidden rounded-3xl border border-slate-800/70 bg-slate-900/60 p-5 transition hover:border-blue-500/40 hover:bg-slate-900/80"
                >
                  <div
                    className="absolute inset-0 opacity-0 transition group-hover:opacity-100"
                    aria-hidden
                  >
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_60%)]" />
                  </div>
                  <div className="relative flex items-start justify-between gap-3">
                    <div>
                      <div className="inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-blue-200">
                        <GitBranch className="h-2.5 w-2.5" />
                        {docbook.orgId}
                      </div>
                      <p className="mt-2 text-[10px] leading-relaxed text-slate-400">
                        {docbook.hasDocbook
                          ? "Linked docbook repository"
                          : "Docbook repository missing"}
                      </p>
                    </div>
                    {/* <div className="flex flex-wrap items-center justify-end gap-2 text-[10px] uppercase tracking-[0.18em]">
                      <span
                        className={`rounded-full px-3 py-1 font-semibold ${
                          docbook.hasDocbook
                            ? "bg-emerald-500/15 text-emerald-200"
                            : "bg-amber-500/15 text-amber-200"
                        }`}
                      >
                        {docbook.hasDocbook ? "Linked" : "Missing"}
                      </span>
                      <span
                        className={`rounded-full px-3 py-1 font-semibold ${
                          docbook.hasGeneratedDocs
                            ? "bg-blue-500/15 text-blue-200"
                            : "bg-slate-700/60 text-slate-300"
                        }`}
                      >
                        {docbook.hasGeneratedDocs ? "Generated" : "Awaiting docs"}
                      </span>
                    </div> */}
                  </div>

                  <div className="relative mt-4 space-y-3">
                    {!docbook.hasDocbook ? (
                      <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
                        <p className="font-semibold">
                          Ready to link your docbook?
                        </p>
                        <p className="mt-2 text-xs text-amber-200/80">
                          Create{" "}
                          <code className="rounded bg-amber-500/20 px-2">
                            DocIt-docbook-{docbook.orgId}
                          </code>{" "}
                          and link it from Settings to start publishing
                          documentation.
                        </p>
                        <button
                          onClick={() => router.push("/settings")}
                          className="mt-3 inline-flex items-center gap-2 rounded-full bg-amber-400/90 px-3 py-1.5 text-xs font-semibold text-amber-950 shadow-lg transition hover:bg-amber-300"
                        >
                          <Plus className="h-3 w-3" />
                          Link docbook repo
                        </button>
                      </div>
                    ) : showEmptyState ? (
                      <div className="rounded-2xl border border-blue-500/40 bg-blue-500/10 p-4 text-sm text-blue-100">
                        <p className="font-semibold">
                          Docs haven&apos;t been generated yet
                        </p>
                        <p className="mt-2 text-xs text-blue-200/80">
                          Kick off a generation run from the dashboard to
                          populate the staging branch with fresh documentation.
                        </p>
                        <button
                          onClick={() => router.push("/dashboard")}
                          className="mt-3 inline-flex items-center gap-2 rounded-full bg-blue-500/90 px-3 py-1.5 text-xs font-semibold text-white shadow-lg transition hover:bg-blue-500"
                        >
                          <Zap className="h-3 w-3" />
                          Generate documentation
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-3 rounded-2xl border border-slate-800/70 bg-slate-900/80 p-3">
                        <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                          Staging file map
                        </p>
                        <div className="space-y-2">
                          {renderFileTree(docbook.folders, [], docbook)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800/70 px-3 py-2.5 text-[8px] text-slate-500">
        <div className="flex items-center justify-between">
          <span>Powered by DocIt v1.0.0</span>
          <button
            onClick={() => router.refresh()}
            className="rounded-full border border-slate-700/70 px-3 py-1 text-[10px] uppercase tracking-[0.35em] text-slate-400 transition hover:border-slate-500/70 hover:text-white"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
