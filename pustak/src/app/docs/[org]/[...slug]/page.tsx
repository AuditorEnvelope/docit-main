"use client";

import { useEffect, useMemo, useState } from "react";
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
      previous: { path: string; name: string } | null;
      next: { path: string; name: string } | null;
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
  const { theme, setTheme } = useTheme();

  // Extract repo from slug (first segment)
  const repo = slug[0] || "";
  const docSegments = useMemo(() => slug.slice(1), [slug]);
  const docSegmentsKey = useMemo(() => docSegments.join("/"), [docSegments]);
  const docPath = docSegments.join("/");

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

  const fetchContent = async (slugSegments: string[], displayPath?: string) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        org_id: org,
        repo_id: repo,
      });

      slugSegments.forEach((segment) => {
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

  const fetchContentByPath = async (path: string, pushHistory = true) => {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    const segments = normalizedPath.split("/").filter(Boolean);
    const slugSegments = segments.slice(1);

    if (pushHistory) {
      const nextUrl = `/docs/${org}${normalizedPath}`;
      window.history.pushState({}, "", nextUrl);
    }

    await fetchContent(slugSegments, normalizedPath);
  };

  useEffect(() => {
    if (!manifest) return;

    if (docSegments.length) {
      const currentPath = `/${[repo, ...docSegments].join("/")}`;
      fetchContent(docSegments, currentPath);
    } else {
      const firstDoc = manifest.sidebar
        .flatMap((item) => {
          if (item.type === "file") return [item];
          if (item.children) {
            return item.children.filter((child) => child.type === "file");
          }
          return [];
        })
        .find(Boolean);
      if (firstDoc) {
        fetchContentByPath(firstDoc.path);
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

  useEffect(() => {
    if (!manifest) return;
    document.documentElement.style.setProperty("--live-primary", manifest.theme.primary);
    document.documentElement.style.setProperty("--live-secondary", manifest.theme.secondary);
    document.documentElement.style.setProperty("--live-background", manifest.theme.background);
    document.documentElement.style.setProperty("--live-foreground", manifest.theme.foreground);
  }, [manifest]);

  useEffect(() => {
    if (copied) {
      const timeout = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timeout);
    }
  }, [copied]);

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
            fetchContentByPath(item.path);
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
    <div className="min-h-screen bg-[var(--live-background)] text-slate-100">
      <div className="relative flex min-h-screen">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-80 border-r border-white/5 bg-white/5 backdrop-blur-xl transition-transform duration-300 lg:relative lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between px-6 py-6">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--live-primary)] to-[var(--live-secondary)] shadow-lg shadow-[var(--live-primary)]/30">
                  <Book className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">{manifest?.title}</h2>
                  <p className="text-xs uppercase tracking-wide text-slate-400">{org}</p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="rounded-lg p-1 text-slate-400 transition hover:bg-white/10 hover:text-white lg:hidden"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="px-4">
              <button className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:border-white/20">
                <Search className="h-4 w-4" />
                <span>Search documentation</span>
                <kbd className="ml-auto hidden rounded border border-white/20 px-1.5 py-0.5 text-xs text-slate-300 sm:inline">
                  ⌘K
                </kbd>
              </button>
            </div>

            <nav className="mt-6 flex-1 overflow-y-auto px-2 pb-10">
              <div className="space-y-1">
                {manifest && renderSidebarItems(manifest.sidebar)}
              </div>
            </nav>

            <footer className="border-t border-white/10 px-6 py-5">
              <p className="text-xs text-slate-400">
                Powered by <span className="text-[var(--live-primary)]">Pustak AI</span>
              </p>
              {manifest?.stats?.last_published_at && (
                <p className="mt-2 text-xs text-slate-500">
                  Last published {new Date(manifest.stats.last_published_at).toLocaleString()}
                </p>
              )}
            </footer>
          </div>
        </aside>

        {/* Main Area */}
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-[var(--live-background)]/80 backdrop-blur-xl">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="rounded-lg border border-white/10 p-2 text-slate-300 transition hover:border-white/20 hover:text-white lg:hidden"
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
                  onClick={handleCopyLink}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-white/20 hover:text-white"
                >
                  <div className="flex items-center gap-2">
                    <Link2 className="h-4 w-4" />
                    {copied ? "Copied!" : "Share"}
                  </div>
                </button>
                <button
                  onClick={handleThemeToggle}
                  className="rounded-lg border border-white/10 p-2 text-slate-200 transition hover:border-white/20 hover:text-white"
                >
                  {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </header>

          <main className="relative mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-6 py-10">
            <section className="rounded-3xl border border-white/10 bg-white/5 px-8 py-10 shadow-lg backdrop-blur">
              <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-[var(--live-secondary)]">
                    <span>Live Documentation</span>
                    <span className="h-1 w-1 rounded-full bg-[var(--live-secondary)]"></span>
                    <span>{manifest?.stats?.page_count ?? 0} pages</span>
                  </div>
                  <h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
                    {pageTitle || manifest?.title}
                  </h1>
                  <p className="mt-3 max-w-2xl text-sm text-slate-300">
                    {manifest?.description}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <a
                    href={manifest?.live_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-white/10 px-4 py-2 text-xs font-medium text-slate-200 transition hover:border-white/20 hover:text-white"
                  >
                    Open in GitHub
                  </a>
                </div>
              </header>

              <div className="relative">
                {loading ? (
                  <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--live-primary)]" />
                  </div>
                ) : (
                  <article className="prose prose-invert max-w-none">
                    <MarkdownRenderer content={content} />
                  </article>
                )}
              </div>

              <footer className="mt-10 flex flex-col gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>Commit</span>
                  <span className="rounded bg-white/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">
                    {manifest?.commit_sha.slice(0, 7)}
                  </span>
                  {manifest?.stats?.last_published_at && (
                    <span>
                      Updated {new Date(manifest.stats.last_published_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  {neighbors.previous && (
                    <button
                      onClick={() => fetchContentByPath(neighbors.previous!.path)}
                      className="group flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-white/20 hover:text-white"
                    >
                      <ArrowLeft className="h-4 w-4 transition group-hover:-translate-x-1" />
                      <span className="uppercase tracking-wide text-slate-400">Previous</span>
                      <span className="text-slate-200">{neighbors.previous.name}</span>
                    </button>
                  )}
                  {neighbors.next && (
                    <button
                      onClick={() => fetchContentByPath(neighbors.next!.path)}
                      className="group flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-white/20 hover:text-white"
                    >
                      <span className="text-slate-200">{neighbors.next.name}</span>
                      <span className="uppercase tracking-wide text-slate-400">Next</span>
                      <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
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
    </div>
  );
}
