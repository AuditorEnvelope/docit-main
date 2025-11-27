"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  Book,
  Search,
  Menu,
  X,
  ChevronRight,
  ChevronDown,
  ArrowLeft,
  ArrowRight,
  Moon,
  Sun,
  Loader2,
  Link2,
  BookOpen,
} from "lucide-react";
import { useTheme } from "next-themes";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface SidebarItem {
  path: string;
  type: "folder" | "file";
  id: string;
  name: string;
  parent?: string | null;
  source_path?: string;
  children?: SidebarItem[];
}

type ThemeColors = {
  primary: string;
  secondary: string;
  background: string;
  text: string;
};

interface Manifest {
  org_id: string;
  repo_id: string;
  title: string;
  description: string;
  commit_sha: string;
  published_at: string;
  live_url: string;
  sidebar: SidebarItem[];
  navigation: Record<
    string,
    {
      previous: { path: string; source_path?: string; name: string } | null;
      next: { path: string; source_path?: string; name: string } | null;
    }
  >;
  breadcrumbs: { label: string; path: string }[];
  stats: {
    page_count: number;
    last_published_at: string | null;
  };
  theme?: {
    light: ThemeColors;
    dark: ThemeColors;
  };
}

export default function LiveDocsPage() {
  const params = useParams();
  const org = params.org as string;
  const slug = (params.slug as string[]) || [];

  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activePath, setActivePath] = useState<string>("");
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [pageTitle, setPageTitle] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Extract repo from slug (first segment)
  const repo = slug[0] || "";
  const docSegments = useMemo(() => slug.slice(1), [slug]);
  const docSegmentsKey = useMemo(() => docSegments.join("/"), [docSegments]);

  // Use resolvedTheme to avoid hydration issues
  const isLight = mounted ? resolvedTheme === "light" : false;

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!org || !repo) {
      setError("Invalid URL: organization or repository not specified");
      setLoading(false);
      return;
    }

    fetchManifest();
  }, [org, repo]);

  const apiBase = BACKEND_URL.endsWith("/api/v1")
    ? BACKEND_URL
    : `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

  const fetchManifest = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(
        `${apiBase}/docbook/live-manifest/public?org_id=${encodeURIComponent(
          org
        )}&repo_id=${encodeURIComponent(repo)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load manifest: ${response.statusText}`);
      }

      const data = await response.json();
      setManifest(data);
      if (Array.isArray(data.sidebar)) {
        const expanded = new Set<string>();
        const expandAll = (items: SidebarItem[]) => {
          for (const item of items) {
            if (item.type === "folder") {
              expanded.add(item.id);
              if (item.children?.length) {
                expandAll(item.children as SidebarItem[]);
              }
            }
          }
        };
        expandAll(data.sidebar);
        setExpandedNodes(expanded);
      }
      setError(null);
    } catch (err) {
      console.error("Error fetching manifest:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load documentation"
      );
    } finally {
      setLoading(false);
    }
  };

  const fetchContent = async (
    slugSegments: string[],
    displayPath?: string,
    sourceSegments?: string[]
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        org_id: org,
        repo_id: repo,
      });

      const segmentsToUse =
        sourceSegments && sourceSegments.length ? sourceSegments : slugSegments;

      segmentsToUse.forEach((segment) => {
        if (segment) {
          params.append("slug", segment);
        }
      });

      const response = await fetch(
        `${apiBase}/docbook/live-content/public?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load content: ${response.statusText}`);
      }

      const data = await response.json();
      setContent(data.content || "");
      const normalizedPath =
        displayPath || `/${[repo, ...slugSegments].join("/")}`;
      setActivePath(normalizedPath);
      const activeName = normalizedPath.split("/").pop() || repo;
      setPageTitle(activeName.replace(/-/g, " ").replace(/_/g, " "));
      setError(null);
    } catch (err) {
      console.error("Error fetching content:", err);
      setError(err instanceof Error ? err.message : "Failed to load content");
    } finally {
      setLoading(false);
    }
  };

  const fetchContentByPath = async (
    path: string,
    pushHistory = true,
    sourcePath?: string
  ) => {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const segments = normalizedPath.split("/").filter(Boolean);
    const slugSegments = segments.slice(1);

    const sourceNormalized = sourcePath
      ? sourcePath.startsWith("/")
        ? sourcePath
        : `/${sourcePath}`
      : normalizedPath;
    const sourceSegments = sourceNormalized.split("/").filter(Boolean).slice(1);

    if (pushHistory) {
      const nextUrl = `/docs/${org}${normalizedPath}`;
      window.history.pushState({}, "", nextUrl);
    }

    await fetchContent(slugSegments, normalizedPath, sourceSegments);
  };

  useEffect(() => {
    if (!manifest) return;

    if (docSegments.length) {
      const currentPath = `/${[repo, ...docSegments].join("/")}`;
      fetchContent(docSegments, currentPath);
    } else {
      const flatten = (items: SidebarItem[]): SidebarItem[] =>
        items.flatMap((entry) =>
          entry.type === "folder" && entry.children
            ? flatten(entry.children)
            : [entry]
        );
      const firstDoc = flatten(manifest.sidebar).find(
        (item) => item.type === "file"
      );
      if (firstDoc) {
        fetchContentByPath(firstDoc.path, true, firstDoc.source_path);
      } else {
        setError("No published documentation found.");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manifest, docSegmentsKey, repo]);

  const allFiles = useMemo(() => {
    if (!manifest) return [] as SidebarItem[];
    const flatten = (items: SidebarItem[]): SidebarItem[] => {
      return items.flatMap((item) =>
        item.type === "folder" && item.children
          ? [item, ...flatten(item.children)]
          : [item]
      );
    };
    return flatten(manifest.sidebar).filter((item) => item.type === "file");
  }, [manifest]);

  const neighbors = useMemo(() => {
    if (!manifest || !activePath) return { previous: null, next: null };
    return manifest.navigation?.[activePath] ?? { previous: null, next: null };
  }, [manifest, activePath]);

  const dynamicBreadcrumbs = useMemo(() => {
    if (!manifest) return [];
    const base = manifest.breadcrumbs || [];
    if (!activePath) return base;
    const segments = activePath.replace(/^\//, "").split("/").slice(1);
    const crumbs = segments.map((segment, idx) => ({
      label: segment.replace(/-/g, " ").replace(/_/g, " "),
      path: `/docs/${org}/${[repo, ...segments.slice(0, idx + 1)].join("/")}`,
    }));
    return [...base, ...crumbs];
  }, [manifest, activePath, org, repo]);

  useEffect(() => {
    if (copied) {
      const timeout = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timeout);
    }
  }, [copied]);

  useEffect(() => {
    if (searchOpen) {
      const timeout = setTimeout(() => searchInputRef.current?.focus(), 120);
      return () => clearTimeout(timeout);
    }
  }, [searchOpen]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && searchOpen) {
        setSearchOpen(false);
        setSearchQuery("");
      }
      // CMD+K or CTRL+K to open search
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [searchOpen]);

  const toggleNode = (id: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const renderSidebarItems = (items: SidebarItem[], depth = 0) => {
    return items.map((item) => {
      if (item.type === "folder") {
        const isOpen = expandedNodes.has(item.id);
        return (
          <div key={item.id} className="mb-1">
            <button
              onClick={() => toggleNode(item.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isLight
                  ? "text-slate-800 hover:bg-slate-100" // Improved contrast
                  : "text-slate-300 hover:bg-slate-800"
              }`}
              style={{ paddingLeft: `${depth * 16 + 12}px` }}
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${
                  isOpen ? "rotate-90" : ""
                }`}
              />
              <span className="capitalize">{item.name.replace(/-/g, " ")}</span>
            </button>
            {isOpen && item.children && (
              <div className="mt-1">
                {renderSidebarItems(item.children, depth + 1)}
              </div>
            )}
          </div>
        );
      }

      const isActive = activePath === item.path;
      return (
        <button
          key={item.id}
          onClick={() => {
            fetchContentByPath(item.path, true, item.source_path);
            setSidebarOpen(false);
          }}
          className={`mb-1 flex w-full items-center rounded-lg px-3 py-2 text-sm transition-colors ${
            isActive
              ? isLight
                ? "bg-indigo-50 text-indigo-600 font-medium"
                : "bg-indigo-500/10 text-indigo-400 font-medium"
              : isLight
              ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900" // Improved contrast
              : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          }`}
          style={{ paddingLeft: `${depth * 16 + 40}px` }}
        >
          <span className="truncate capitalize">
            {item.name.replace(/-/g, " ")}
          </span>
        </button>
      );
    });
  };

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setCopied(true);
  };

  const handleThemeToggle = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return allFiles;
    const query = searchQuery.toLowerCase();
    return allFiles.filter((item) => item.name.toLowerCase().includes(query));
  }, [allFiles, searchQuery]);

  if (!mounted) {
    return null;
  }

  if (loading && !manifest) {
    return (
      <div
        className={`flex min-h-screen items-center justify-center ${
          isLight ? "bg-white" : "bg-slate-950"
        }`}
      >
        <div className="text-center">
          <Loader2
            className={`mx-auto mb-4 h-8 w-8 animate-spin ${
              isLight ? "text-indigo-600" : "text-indigo-400"
            }`}
          />
          <p className={isLight ? "text-slate-700" : "text-slate-400"}>
            {" "}
            {/* Improved contrast */}
            Loading documentation...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`flex min-h-screen items-center justify-center ${
          isLight ? "bg-white" : "bg-slate-950"
        }`}
      >
        <div className="max-w-md text-center">
          <div
            className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full ${
              isLight ? "bg-red-100" : "bg-red-500/20"
            }`}
          >
            <X
              className={`h-8 w-8 ${isLight ? "text-red-600" : "text-red-400"}`}
            />
          </div>
          <h1
            className={`mb-2 text-2xl font-bold ${
              isLight ? "text-slate-900" : "text-white"
            }`}
          >
            Error
          </h1>
          <p className={isLight ? "text-slate-700" : "text-slate-400"}>
            {" "}
            {/* Improved contrast */}
            {error}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen transition-colors ${
        isLight ? "bg-white" : "bg-slate-950"
      }`}
    >
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="relative flex min-h-screen">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-64 border-r transition-all duration-300 lg:relative lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          } ${
            isLight
              ? "border-slate-300 bg-white" // Improved border contrast
              : "border-slate-800 bg-slate-900"
          }`}
        >
          <div className="flex h-full flex-col">
            {/* Sidebar Header */}
            <div
              className={`flex items-center justify-between border-b px-6 py-4 ${
                isLight ? "border-slate-300" : "border-slate-800"
              } // Improved border contrast
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
                  <Book className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2
                    className={`text-sm font-semibold ${
                      isLight ? "text-slate-900" : "text-white"
                    }`}
                  >
                    {manifest?.title}
                  </h2>
                  <p
                    className={`text-xs ${
                      isLight ? "text-slate-700" : "text-slate-400"
                    } // Improved contrast
                    }`}
                  >
                    {org}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className={`rounded-lg p-1.5 transition-colors lg:hidden ${
                  isLight
                    ? "text-slate-700 hover:bg-slate-100" // Improved contrast
                    : "text-slate-400 hover:bg-slate-800"
                }`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Sidebar Content */}
            <div className="flex-1 overflow-y-auto px-3 py-4">
              {manifest && renderSidebarItems(manifest.sidebar)}
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1">
          {/* Header */}
          <header
            className={`sticky top-0 z-30 border-b backdrop-blur-sm ${
              isLight
                ? "border-slate-300 bg-white/80" // Improved border contrast
                : "border-slate-800 bg-slate-900/80"
            }`}
          >
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className={`rounded-lg p-2 transition-colors lg:hidden ${
                    isLight
                      ? "text-slate-700 hover:bg-slate-100" // Improved contrast
                      : "text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <Menu className="h-5 w-5" />
                </button>

                {/* Breadcrumbs */}
                <nav className="hidden items-center gap-2 text-sm md:flex">
                  {dynamicBreadcrumbs.map((crumb, index) => (
                    <span key={crumb.path} className="flex items-center gap-2">
                      {index > 0 && (
                        <ChevronRight
                          className={`h-4 w-4 ${
                            isLight ? "text-slate-500" : "text-slate-600" // Improved contrast
                          }`}
                        />
                      )}
                      <a
                        href={crumb.path}
                        className={`transition-colors ${
                          index === dynamicBreadcrumbs.length - 1
                            ? isLight
                              ? "font-medium text-slate-900"
                              : "font-medium text-white"
                            : isLight
                            ? "text-slate-700 hover:text-slate-900" // Improved contrast
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {crumb.label}
                      </a>
                    </span>
                  ))}
                </nav>
              </div>

              <div className="flex items-center gap-2">
                {/* Search Button */}
                <button
                  onClick={() => setSearchOpen(true)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                    isLight
                      ? "border-slate-300 text-slate-700 hover:bg-slate-50" // Improved contrast
                      : "border-slate-700 text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <Search className="h-4 w-4" />
                  <span className="hidden sm:inline">Search</span>
                  <kbd
                    className={`hidden rounded border px-1.5 py-0.5 text-xs md:inline ${
                      isLight
                        ? "border-slate-400 bg-slate-100 text-slate-600" // Improved contrast
                        : "border-slate-600 bg-slate-800 text-slate-400"
                    }`}
                  >
                    ⌘K
                  </kbd>
                </button>

                {/* Copy Link Button */}
                <button
                  onClick={handleCopyLink}
                  className={`rounded-lg border p-2 transition-colors ${
                    isLight
                      ? "border-slate-300 text-slate-700 hover:bg-slate-50" // Improved contrast
                      : "border-slate-700 text-slate-400 hover:bg-slate-800"
                  }`}
                  title={copied ? "Copied!" : "Copy link"}
                >
                  <Link2 className="h-4 w-4" />
                </button>

                {/* Theme Toggle */}
                <button
                  onClick={handleThemeToggle}
                  className={`rounded-lg border p-2 transition-colors ${
                    isLight
                      ? "border-slate-300 text-slate-700 hover:bg-slate-50" // Improved contrast
                      : "border-slate-700 text-amber-400 hover:bg-slate-800"
                  }`}
                  title={`Switch to ${isLight ? "dark" : "light"} mode`}
                >
                  {isLight ? (
                    <Moon className="h-4 w-4" />
                  ) : (
                    <Sun className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </header>

          {/* Content - UPDATED SECTION */}
          <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2
                  className={`h-6 w-6 animate-spin ${
                    isLight ? "text-indigo-600" : "text-indigo-400"
                  }`}
                />
              </div>
            ) : (
              <>
                <article
                  className={`prose prose-sm sm:prose-base max-w-none ${
                    isLight
                      ? "prose-slate prose-headings:text-slate-900 prose-p:text-slate-700 prose-li:text-slate-700 prose-strong:text-slate-900"
                      : "prose-invert prose-headings:text-white prose-p:text-slate-300 prose-li:text-slate-300 prose-strong:text-white"
                  } prose-headings:font-semibold prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline prose-pre:bg-slate-900 prose-pre:text-slate-100`}
                >
                  <MarkdownRenderer content={content} />
                </article>

                {/* Navigation */}
                {(neighbors.previous || neighbors.next) && (
                  <div className="mt-8 grid gap-3 border-t pt-6 sm:grid-cols-2">
                    {neighbors.previous && (
                      <button
                        onClick={() =>
                          fetchContentByPath(
                            neighbors.previous!.path,
                            true,
                            neighbors.previous!.source_path
                          )
                        }
                        className={`flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors ${
                          isLight
                            ? "border-slate-300 hover:bg-slate-50" // Improved border contrast
                            : "border-slate-800 hover:bg-slate-800"
                        }`}
                      >
                        <div
                          className={`flex items-center gap-1 text-sm ${
                            isLight ? "text-slate-600" : "text-slate-400"
                          } // Improved contrast
                          }`}
                        >
                          <ArrowLeft className="h-3 w-3" />
                          <span>Previous</span>
                        </div>
                        <span
                          className={`text-sm font-medium ${
                            isLight ? "text-slate-900" : "text-white"
                          }`}
                        >
                          {neighbors.previous.name}
                        </span>
                      </button>
                    )}
                    {neighbors.next && (
                      <button
                        onClick={() =>
                          fetchContentByPath(
                            neighbors.next!.path,
                            true,
                            neighbors.next!.source_path
                          )
                        }
                        className={`flex flex-col items-end gap-1 rounded-lg border p-3 text-right transition-colors ${
                          isLight
                            ? "border-slate-300 hover:bg-slate-50" // Improved border contrast
                            : "border-slate-800 hover:bg-slate-800"
                        } ${!neighbors.previous ? "sm:col-start-2" : ""}`}
                      >
                        <div
                          className={`flex items-center gap-1 text-sm ${
                            isLight ? "text-slate-600" : "text-slate-400"
                          } // Improved contrast
                          }`}
                        >
                          <span>Next</span>
                          <ArrowRight className="h-3 w-3" />
                        </div>
                        <span
                          className={`text-sm font-medium ${
                            isLight ? "text-slate-900" : "text-white"
                          }`}
                        >
                          {neighbors.next.name}
                        </span>
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {/* Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-24 backdrop-blur-sm">
          <div
            className={`w-full max-w-2xl rounded-xl border shadow-2xl ${
              isLight
                ? "border-slate-300 bg-white" // Improved border contrast
                : "border-slate-700 bg-slate-900"
            }`}
          >
            <div
              className={`flex items-center gap-3 border-b px-4 py-3 ${
                isLight ? "border-slate-300" : "border-slate-800"
              } // Improved border contrast
              }`}
            >
              <Search
                className={`h-5 w-5 ${
                  isLight ? "text-slate-500" : "text-slate-500"
                } // Improved contrast
                }`}
              />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search documentation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`flex-1 bg-transparent text-base outline-none placeholder:${
                  isLight ? "text-slate-500" : "text-slate-500"
                } ${isLight ? "text-slate-900" : "text-white"}`}
              />
              <kbd
                className={`rounded border px-2 py-1 text-xs ${
                  isLight
                    ? "border-slate-400 bg-slate-100 text-slate-600" // Improved contrast
                    : "border-slate-700 bg-slate-800 text-slate-400"
                }`}
              >
                ESC
              </kbd>
            </div>

            <div className="max-h-96 overflow-y-auto p-2">
              {filteredResults.length === 0 ? (
                <p
                  className={`py-8 text-center text-sm ${
                    isLight ? "text-slate-600" : "text-slate-400"
                  } // Improved contrast
                  }`}
                >
                  {searchQuery
                    ? `No results found for "${searchQuery}"`
                    : "Type to search..."}
                </p>
              ) : (
                <div className="space-y-1">
                  {filteredResults.map((item) => (
                    <button
                      key={item.path}
                      onClick={() => {
                        fetchContentByPath(item.path, true, item.source_path);
                        setSearchOpen(false);
                        setSearchQuery("");
                      }}
                      className={`flex w-full items-center justify-between rounded-lg px-4 py-3 text-left transition-colors ${
                        isLight ? "hover:bg-slate-100" : "hover:bg-slate-800"
                      }`}
                    >
                      <span
                        className={`truncate capitalize ${
                          isLight ? "text-slate-900" : "text-white"
                        }`}
                      >
                        {item.name.replace(/-/g, " ")}
                      </span>
                      <span
                        className={`ml-4 text-xs ${
                          isLight ? "text-slate-500" : "text-slate-500"
                        } // Improved contrast
                        }`}
                      >
                        {item.path.replace(`/${repo}/`, "")}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
