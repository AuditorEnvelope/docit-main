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
  theme: {
    primary: string;
    secondary: string;
    background: string;
    foreground: string;
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
        `${apiBase}/docbook/live-manifest/public?org_id=${encodeURIComponent(org)}&repo_id=${encodeURIComponent(repo)}`
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
      setError(err instanceof Error ? err.message : "Failed to load documentation");
    } finally {
      setLoading(false);
    }
  };

  const fetchContent = async (
    slugSegments: string[],
    displayPath?: string,
    sourceSegments?: string[],
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        org_id: org,
        repo_id: repo,
      });

      const segmentsToUse = sourceSegments && sourceSegments.length ? sourceSegments : slugSegments;

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
      const normalizedPath = displayPath || `/${[repo, ...slugSegments].join("/")}`;
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
    sourcePath?: string,
  ) => {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const segments = normalizedPath.split("/").filter(Boolean);
    const slugSegments = segments.slice(1);

    const sourceNormalized = sourcePath
      ? (sourcePath.startsWith("/") ? sourcePath : `/${sourcePath}`)
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
          entry.type === "folder" && entry.children ? flatten(entry.children) : [entry],
        );
      const firstDoc = flatten(manifest.sidebar).find((item) => item.type === "file");
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

  const defaultDarkTheme = {
    primary: manifest?.theme.primary ?? "#3b82f6",
    secondary: manifest?.theme.secondary ?? "#8b5cf6",
    background: manifest?.theme.background ?? "#0f172a",
    foreground: manifest?.theme.foreground ?? "#f8fafc",
  };

  const defaultLightTheme = {
    primary: "#2563eb",
    secondary: "#7c3aed",
    background: "#f8fafc",
    foreground: "#0f172a",
  };

  const activeTheme = isLight ? defaultLightTheme : defaultDarkTheme;

  useEffect(() => {
    if (!manifest) return;
    document.documentElement.style.setProperty("--live-primary", activeTheme.primary);
    document.documentElement.style.setProperty("--live-secondary", activeTheme.secondary);
    document.documentElement.style.setProperty("--live-background", activeTheme.background);
    document.documentElement.style.setProperty("--live-foreground", activeTheme.foreground);
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
              className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition ${
                isOpen
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
              style={{ paddingLeft: `${depth * 12 + 12}px` }}
            >
              <span className="flex items-center gap-2">
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                <span className="font-medium capitalize">{item.name.replace(/-/g, " ")}</span>
              </span>
              <span className="text-xs text-slate-500">{item.children?.length ?? 0}</span>
            </button>
            {isOpen && item.children && (
              <div className="space-y-1">{renderSidebarItems(item.children, depth + 1)}</div>
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
          className={`group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
            isActive
              ? "bg-gradient-to-r from-[var(--live-primary)]/20 to-[var(--live-secondary)]/20 text-white"
              : "text-slate-300 hover:bg-white/5 hover:text-white"
          }`}
          style={{ paddingLeft: `${depth * 12 + 28}px` }}
        >
          <span className="truncate capitalize">{item.name.replace(/-/g, " ")}</span>
          {isActive && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[var(--live-primary)]" />}
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

  const subtleText = isLight ? "text-slate-600" : "text-slate-400";
  const mutedBorder = isLight ? "border-slate-200" : "border-white/10";
  const panelBg = isLight ? "bg-white" : "bg-white/5";
  const panelShadow = isLight ? "shadow-xl shadow-slate-200/40" : "shadow-lg shadow-black/30";
  const headerBg = isLight ? "bg-white/90" : "bg-[var(--live-background)]/80";
  const sidebarBg = isLight ? "bg-white" : "bg-white/5";
  const proseSize = "prose-xs sm:prose-sm"; // Even smaller prose size

  if (loading && !manifest) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
          <p className="text-slate-400">Loading documentation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-rose-500/20">
            <X className="h-8 w-8 text-rose-400" />
          </div>
          <h1 className="mb-2 text-2xl font-bold text-white">Error</h1>
          <p className="text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isLight ? "bg-slate-100 text-slate-900" : "bg-[var(--live-background)] text-slate-100"} transition-colors`}>
      <div className="relative flex min-h-screen">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-80 border-r ${mutedBorder} ${sidebarBg} backdrop-blur-xl transition-transform duration-300 lg:relative lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-6 py-6">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--live-primary)] to-[var(--live-secondary)] shadow-lg shadow-[var(--live-primary)]/30">
                  <Book className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-white">{manifest?.title}</h2>
                  <p className="text-xs uppercase tracking-wide text-slate-400">{org}</p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className={`rounded-lg p-1 ${subtleText} transition hover:bg-white/10 hover:text-[var(--live-primary)] lg:hidden`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="mt-2 flex-1 overflow-y-auto px-2 pb-10">
              <div className="space-y-1">
                {manifest && renderSidebarItems(manifest.sidebar)}
              </div>
            </nav>

            <footer className={`border-t ${mutedBorder} px-6 py-5`}>
              <p className={`text-xs ${subtleText}`}>
                Powered by <span className="text-[var(--live-primary)]">Pustak AI</span>
              </p>
              {manifest?.stats?.last_published_at && (
                <p className={`mt-2 text-xs ${subtleText}`}>
                  Last published {new Date(manifest.stats.last_published_at).toLocaleString()}
                </p>
              )}
            </footer>
          </div>
        </aside>

        {/* Main Area */}
        <div className="flex min-h-screen flex-1 flex-col">
          <header className={`sticky top-0 z-40 w-full border-b ${mutedBorder} ${headerBg} backdrop-blur-xl transition-colors`}>
            <div className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-3">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className={`rounded-md border ${mutedBorder} p-1.5 ${subtleText} transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] lg:hidden`}
                >
                  <Menu className="h-5 w-5" />
                </button>
                <nav className="flex items-center gap-2 text-xs font-medium text-slate-300">
                  {dynamicBreadcrumbs.map((crumb, index) => (
                    <span key={crumb.path} className="flex items-center gap-2">
                      {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-slate-500" />}
                      <a href={crumb.path} className="transition hover:text-white">
                        {crumb.label}
                      </a>
                    </span>
                  ))}
                </nav>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleSearchClick}
                  className={`rounded-lg border ${mutedBorder} px-3 py-2 text-xs font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                >
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    <span>Search</span>
                  </div>
                </button>
                <button
                  onClick={handleCopyLink}
                  className={`rounded-lg border ${mutedBorder} px-3 py-2 text-xs font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                >
                  <div className="flex items-center gap-2">
                    <Link2 className="h-4 w-4" />
                    {copied ? "Copied!" : "Share"}
                  </div>
                </button>
                <button
                  onClick={handleThemeToggle}
                  className={`rounded-lg border ${mutedBorder} p-2 transition ${
                    isLight 
                      ? "bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-600 hover:from-indigo-500/20 hover:to-purple-500/20" 
                      : "bg-gradient-to-r from-amber-300/10 to-yellow-300/10 text-amber-400 hover:from-amber-300/20 hover:to-yellow-300/20"
                  }`}
                >
                  {isLight ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </header>

          <main className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-5">
            <section className={`rounded-xl border ${mutedBorder} ${panelBg} px-6 py-6 ${panelShadow} backdrop-blur-md transition-colors`}>
              <header className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h1 className="text-lg font-semibold sm:text-xl">
                    {pageTitle || manifest?.title}
                  </h1>
                  <p className={`mt-1 max-w-2xl text-xs sm:text-sm ${subtleText}`}>
                    {manifest?.description}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <a
                    href={manifest?.live_url}
                    target="_blank"
                    rel="noreferrer"
                    className={`rounded-lg border ${mutedBorder} px-3 py-1.5 text-xs font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                  >
                    Open in GitHub
                  </a>
                </div>
              </header>

              <div className="relative">
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-5 w-5 animate-spin text-[var(--live-primary)]" />
                  </div>
                ) : (
                  <article className={`prose max-w-none ${proseSize} ${isLight ? "prose-slate" : "prose-invert"}`}>
                    <MarkdownRenderer content={content} />
                  </article>
                )}
              </div>

              <footer className={`mt-6 flex flex-col gap-3 border-t ${mutedBorder} pt-4 lg:flex-row lg:items-center lg:justify-between`}>
                <div className={`flex flex-wrap items-center gap-3 text-xs ${subtleText}`}>
                  <span>Commit</span>
                  <span className={`rounded bg-[var(--live-primary)]/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[color:var(--live-foreground)]`}>
                    {manifest?.commit_sha.slice(0, 7)}
                  </span>
                  {manifest?.stats?.last_published_at && (
                    <span>
                      Updated {new Date(manifest.stats.last_published_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
                  {neighbors.previous && (
                    <button
                      onClick={() =>
                        fetchContentByPath(
                          neighbors.previous!.path,
                          true,
                          neighbors.previous!.source_path ?? neighbors.previous!.path,
                        )
                      }
                      className={`group flex w-full items-center justify-between rounded-lg border ${mutedBorder} px-3 py-2 text-xs font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] sm:w-auto sm:max-w-[180px]`}
                    >
                      <div className="flex items-center gap-2">
                        <ArrowLeft className="h-4 w-4 transition group-hover:-translate-x-1" />
                        <span className={`text-xs uppercase tracking-wide ${subtleText}`}>Previous</span>
                      </div>
                      <span className="truncate text-right">{neighbors.previous.name}</span>
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
                      className={`group flex w-full items-center justify-between rounded-lg border ${mutedBorder} px-3 py-2 text-xs font-medium transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)] sm:w-auto sm:max-w-[180px]`}
                    >
                      <span className="max-w-[100px] truncate">{neighbors.next.name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs uppercase tracking-wide ${subtleText}`}>Next</span>
                        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
                      </div>
                    </button>
                  )}
                </div>
              </footer>
            </section>
          </main>
        </div>

        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </div>

      {searchOpen && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/60 backdrop-blur-sm">
          <div className={`mt-32 w-full max-w-xl rounded-2xl border ${mutedBorder} ${panelBg} p-6 ${panelShadow}`}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Search documentation</h2>
              <button
                onClick={() => {
                  setSearchOpen(false);
                  setSearchQuery("");
                }}
                className={`rounded-full border ${mutedBorder} p-1 transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4">
              <div className={`flex items-center gap-3 rounded-xl border ${mutedBorder} bg-white/5 px-4 py-3 transition focus-within:border-[var(--live-primary)]/40`}>
                <Search className="h-4 w-4" />
                <input
                  ref={searchInputRef}
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search pages..."
                  className="h-8 flex-1 bg-transparent text-sm outline-none"
                />
                <kbd className={`hidden rounded border ${mutedBorder} px-2 py-0.5 text-xs ${subtleText} sm:inline`}>
                  Esc
                </kbd>
              </div>
            </div>
            <div className="mt-4 max-h-64 overflow-y-auto pr-1">
              {filteredResults.length === 0 ? (
                <p className={`py-6 text-center text-sm ${subtleText}`}>No pages match “{searchQuery}”.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {filteredResults.map((item) => (
                    <li key={item.path}>
                      <button
                        onClick={() => {
                          fetchContentByPath(item.path, true, item.source_path);
                          setSearchOpen(false);
                          setSearchQuery("");
                        }}
                        className={`flex w-full items-center justify-between rounded-xl border ${mutedBorder} px-4 py-3 text-left transition hover:border-[var(--live-primary)]/40 hover:text-[var(--live-primary)]`}
                      >
                        <span className="truncate capitalize">{item.name.replace(/-/g, " ")}</span>
                        <span className={`text-xs ${subtleText}`}>{item.path.replace(`/${repo}/`, "")}</span>
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
