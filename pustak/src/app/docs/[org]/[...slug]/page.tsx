"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  Book,
  Search,
  Menu,
  X,
  ChevronRight,
  Home,
  ChevronDown,
  ChevronUp,
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
  const { theme, setTheme } = useTheme();

  // Extract repo from slug (first segment)
  const repo = slug[0] || "";
  const docSegments = useMemo(() => slug.slice(1), [slug]);
  const docSegmentsKey = useMemo(() => docSegments.join("/"), [docSegments]);
  const docPath = docSegments.join("/");
  const isLight = theme === "light";

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

  const activeEntry = useMemo(
    () => allFiles.find((item) => item.path === activePath),
    [allFiles, activePath]
  );

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

  // Define theme colors based on light/dark mode
  const activeTheme = useMemo(() => {
    const defaultTheme = {
      primary: isLight ? "#4f46e5" : "#6366f1",
      secondary: isLight ? "#8b5cf6" : "#a78bfa",
      background: isLight ? "#f8fafc" : "#0f172a",
      text: isLight ? "#334155" : "#f1f5f9",
    };

    const hasThemeMode = (
      theme: any
    ): theme is { light: ThemeColors; dark: ThemeColors } => {
      return theme && (theme.light !== undefined || theme.dark !== undefined);
    };

    if (manifest?.theme && hasThemeMode(manifest.theme)) {
      const mode = isLight ? "light" : "dark";
      return manifest.theme[mode] || defaultTheme;
    }

    return defaultTheme;
  }, [isLight, manifest?.theme]);

  useEffect(() => {
    if (!manifest) return;
    document.documentElement.style.setProperty(
      "--live-primary",
      activeTheme.primary
    );
    document.documentElement.style.setProperty(
      "--live-secondary",
      activeTheme.secondary
    );
    document.documentElement.style.setProperty(
      "--live-background",
      activeTheme.background
    );
    document.documentElement.style.setProperty("--live-text", activeTheme.text);
    document.body.style.backgroundColor = activeTheme.background;
  }, [manifest, activeTheme]);

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
          <div key={item.id} className="space-y-1">
            <button
              onClick={() => toggleNode(item.id)}
              className={`flex w-full items-center justify-between rounded-lg px-2 py-1 text-xs transition ${
                isOpen
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
              style={{ paddingLeft: `${depth * 10 + 10}px` }}
            >
              <span className="flex items-center gap-1">
                {isOpen ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
                <span className="font-medium capitalize">
                  {item.name.replace(/-/g, " ")}
                </span>
              </span>
              <span className="text-[9px] text-slate-500">
                {item.children?.length ?? 0}
              </span>
            </button>
            {isOpen && item.children && (
              <div className="space-y-1">
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
          className={`group flex w-full items-center gap-1 rounded-md px-2 py-1 text-[10px] transition ${
            isActive
              ? "bg-gradient-to-r from-[var(--live-primary)]/20 to-[var(--live-secondary)]/20 text-white"
              : "text-slate-300 hover:bg-white/5 hover:text-white"
          }`}
          style={{ paddingLeft: `${depth * 10 + 20}px` }}
        >
          <span className="truncate capitalize">
            {item.name.replace(/-/g, " ")}
          </span>
          {isActive && (
            <span className="ml-auto h-1 w-1 rounded-full bg-[var(--live-primary)]" />
          )}
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
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const handleSearchClick = () => {
    setSearchOpen(true);
  };

  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return allFiles;
    const query = searchQuery.toLowerCase();
    return allFiles.filter((item) => item.name.toLowerCase().includes(query));
  }, [allFiles, searchQuery]);

  // UI style variables based on theme
  const subtleText = isLight ? "text-slate-400" : "text-slate-400";
  const mutedBorder = isLight ? "border-slate-200" : "border-white/10";
  const panelBg = isLight ? "bg-white" : "bg-white/5";
  const panelShadow = isLight
    ? "shadow-sm shadow-slate-100/40"
    : "shadow-sm shadow-black/20";
  const headerBg = isLight ? "bg-white/95" : "bg-[var(--live-background)]/80";
  const sidebarBg = isLight ? "bg-white" : "bg-slate-900";
  const proseSize = "prose-xs sm:prose-xs";

  if (loading && !manifest) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-3 border-blue-500 border-t-transparent"></div>
          <p className="text-slate-400">Loading documentation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/20">
            <X className="h-6 w-6 text-rose-400" />
          </div>
          <h1 className="mb-2 text-xl font-bold text-white">Error</h1>
          <p className="text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen ${
        isLight
          ? "bg-slate-100 text-slate-700"
          : "bg-[var(--live-background)] text-slate-100"
      } transition-colors`}
    >
      <div className="relative flex min-h-screen">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-48 border-r ${mutedBorder} ${sidebarBg} backdrop-blur-xl transition-transform duration-300 lg:relative lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-1.5">
                <div className="flex h-4 w-4 items-center justify-center rounded-md bg-gradient-to-br from-[var(--live-primary)] to-[var(--live-secondary)] shadow-sm shadow-[var(--live-primary)]/20">
                  <Book className="h-2.5 w-2.5 text-white" />
                </div>
                <div>
                  <h2 className="text-[10px] font-semibold text-white">
                    {manifest?.title}
                  </h2>
                  <p className="text-[8px] uppercase tracking-wide text-slate-400">
                    {org}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className={`rounded-md p-1 ${subtleText} transition hover:bg-white/10 hover:text-[var(--live-primary)] lg:hidden`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-1.5 py-1.5 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-200">
              {manifest && renderSidebarItems(manifest.sidebar)}
            </div>

            <footer className={`border-t ${mutedBorder} px-2 py-1.5`}>
              <div className="text-[9px] text-slate-400">Documentation</div>
            </footer>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1">
          <header
            className={`sticky top-0 z-40 border-b ${mutedBorder} ${headerBg} backdrop-blur-xl`}
          >
            <div className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className={`rounded-md border ${mutedBorder} p-1 ${subtleText} transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] lg:hidden`}
                >
                  <Menu className="h-4 w-4" />
                </button>
                <div className="px-1">
                  <nav className="flex flex-wrap items-center gap-1 overflow-x-auto text-[10px] font-medium text-slate-300">
                    {dynamicBreadcrumbs.map((crumb, index) => (
                      <span
                        key={crumb.path}
                        className="flex items-center gap-1"
                      >
                        {index > 0 && (
                          <ChevronRight className="h-3 w-3 text-slate-500" />
                        )}
                        <a
                          href={crumb.path}
                          className="transition hover:text-white"
                        >
                          {crumb.label}
                        </a>
                      </span>
                    ))}
                  </nav>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleSearchClick}
                  className={`rounded-md border ${mutedBorder} px-2 py-1 text-[10px] font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                >
                  <div className="flex items-center gap-1">
                    <Search className="h-3 w-3" />
                    <span>Search</span>
                  </div>
                </button>
                <button
                  onClick={handleCopyLink}
                  className={`rounded-md border ${mutedBorder} px-2 py-1 text-[10px] font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                >
                  <div className="flex items-center gap-1">
                    <Link2 className="h-3 w-3" />
                    {copied ? "Copied!" : "Share"}
                  </div>
                </button>
                <button
                  onClick={handleThemeToggle}
                  className={`rounded-md border ${mutedBorder} p-1.5 transition ${
                    isLight
                      ? "bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-600 hover:from-indigo-500/20 hover:to-purple-500/20"
                      : "bg-gradient-to-r from-amber-300/10 to-yellow-300/10 text-amber-400 hover:from-amber-300/20 hover:to-yellow-300/20"
                  }`}
                >
                  {isLight ? (
                    <Moon className="h-3 w-3" />
                  ) : (
                    <Sun className="h-3 w-3" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden">
              <div className="px-3 pt-1">
                <div className="rounded-sm border border-[var(--live-primary)]/10 bg-[var(--live-primary)]/5 px-1.5 py-1">
                  <h2 className="flex items-center gap-1 text-[9px] font-medium text-[var(--live-primary)]">
                    <BookOpen className="h-2.5 w-2.5" />
                    <span>Documentation</span>
                  </h2>
                </div>
              </div>
            </div>
          </header>

          <div className="p-3">
            {loading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-[var(--live-primary)]" />
              </div>
            ) : (
              <article className={`prose ${proseSize} max-w-none ${isLight ? "prose-slate" : "prose-invert"}`}>
                <MarkdownRenderer content={content} />
              </article>
            )}
          </div>

          {/* Navigation buttons */}
          <div className="mx-auto max-w-2xl px-3 pb-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
              {neighbors.previous && (
                <button
                  onClick={() =>
                    fetchContentByPath(
                      neighbors.previous!.path,
                      true,
                      neighbors.previous!.source_path ?? neighbors.previous!.path,
                    )
                  }
                  className={`group flex w-full items-center justify-between rounded-md border ${mutedBorder} px-2 py-1 text-[10px] font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] sm:max-w-[140px]`}
                >
                  <div className="flex items-center gap-1">
                    <ArrowLeft className="h-3 w-3 transition group-hover:-translate-x-0.5" />
                    <span className="text-[9px] uppercase tracking-wide text-slate-500">Previous</span>
                  </div>
                  <span className="max-w-[60px] truncate">{neighbors.previous.name}</span>
                </button>
              )}
              {neighbors.next && (
                <button
                  onClick={() =>
                    fetchContentByPath(
                      neighbors.next!.path,
                      true,
                      neighbors.next!.source_path ?? neighbors.next!.path,
                    )
                  }
                  className={`group flex w-full items-center justify-between rounded-md border ${mutedBorder} px-2 py-1 text-[10px] font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] sm:max-w-[140px]`}
                >
                  <span className="max-w-[60px] truncate">{neighbors.next.name}</span>
                  <div className="flex items-center gap-1">
                    <span className="text-[9px] uppercase tracking-wide text-slate-500">Next</span>
                    <ArrowRight className="h-3 w-3 transition group-hover:translate-x-0.5" />
                  </div>
                </button>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-16 backdrop-blur-sm">
          <div
            className={`w-full max-w-md rounded-md border ${mutedBorder} ${panelBg} ${panelShadow} p-3`}
          >
            <div className="mb-3 flex items-center gap-2">
              <Search className={`h-3.5 w-3.5 ${subtleText}`} />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search documentation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-6 flex-1 bg-transparent text-xs outline-none"
              />
              <kbd
                className={`hidden rounded border ${mutedBorder} px-1 py-0.5 text-[8px] ${subtleText} sm:inline`}
              >
                Esc
              </kbd>
            </div>
            <div className="mt-3 max-h-64 overflow-y-auto pr-1">
              {filteredResults.length === 0 ? (
                <p className={`py-4 text-center text-xs ${subtleText}`}>
                  No pages match "{searchQuery}".
                </p>
              ) : (
                <ul className="space-y-1 text-[10px]">
                  {filteredResults.map((item) => (
                    <li key={item.path}>
                      <button
                        onClick={() => {
                          fetchContentByPath(item.path, true, item.source_path);
                          setSearchOpen(false);
                          setSearchQuery("");
                        }}
                        className={`flex w-full items-center justify-between rounded-md border ${mutedBorder} px-2 py-1.5 text-left transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                      >
                        <span className="truncate capitalize">
                          {item.name.replace(/-/g, " ")}
                        </span>
                        <span className={`text-[8px] ${subtleText}`}>
                          {item.path.replace(`/${repo}/`, "")}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
