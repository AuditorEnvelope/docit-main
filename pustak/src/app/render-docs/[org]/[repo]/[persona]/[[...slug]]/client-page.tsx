"use client";

// Deployment Sync: Force rebuild of route tree
// Note: Client components cannot use server-side exports like dynamic/revalidate

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
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
  Folder,
  FileText,
  Copy,
} from "lucide-react";
import { useTheme } from "next-themes";
import nextDynamic from "next/dynamic";

const MarkdownRenderer = nextDynamic(
  () => import("@/components/MarkdownRenderer").then((mod) => mod.MarkdownRenderer),
  { ssr: false }
);

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

interface BreadcrumbItem {
  label: string;
  path: string;
  uniquePath?: string;
}

interface HeadingItem {
  id: string;
  level: number;
  text: string;
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
  breadcrumbs: BreadcrumbItem[];
  stats: {
    page_count: number;
    last_published_at: string | null;
  };
  theme?: {
    light: ThemeColors;
    dark: ThemeColors;
  };
}

const TOC_INDENT_CLASSES = ["pl-0", "pl-3", "pl-6", "pl-9", "pl-12"];

interface LiveDocsPageProps {
  initialParams?: {
    org: string;
    repo: string;
    persona: string;
    slug?: string[];
  };
}

export default function LiveDocsPage({ initialParams }: LiveDocsPageProps = {}) {
  console.log("[Page] 🟢 RENDER-DOCS PAGE COMPONENT EXECUTED");
  console.log("[Page] 🟢 URL Path Pattern: /render-docs/[org]/[repo]/[persona]/[...slug]");

  // Use initialParams if provided (server-side), otherwise use useParams (client navigation)
  const clientParams = useParams();
  const params = initialParams || clientParams;
  console.log("[Page] 🟢 Using params:", params, "from:", initialParams ? "server" : "client");

  // STRICT EXTRACTION - NO GUESSING
  const org = params.org as string;
  const repo = params.repo as string;
  const persona = params.persona as string;
  // The slug is ONLY what comes after the persona
  const rawSlug = params.slug;
  const slug = Array.isArray(rawSlug)
    ? rawSlug
    : typeof rawSlug === "string"
    ? [rawSlug]
    : [];
  const slugKey = slug.join("/");

  useEffect(() => {
    console.log("🐛 [CLIENT DEBUG] Mounted. Params:", params);
  }, [params]);

  const manifestKey = useMemo(
    () => `${org ?? ""}::${repo ?? ""}::${persona ?? ""}`,
    [org, repo, persona]
  );

  const fetchedManifestKeyRef = useRef<string | null>(null);
  const fetchedContentKeyRef = useRef<string | null>(null);

  console.log(`[Page] 🟢 Loaded: Org=${org}, Repo=${repo}, Persona=${persona}`);

  // Verify the migration worked - if repo is "docs", throw an error
  if (repo === "docs") {
    throw new Error("MIGRATION FAILED: 'docs' should not be a repo name. The Next.js router is still using the wrong route.");
  }

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
  const [headings, setHeadings] = useState<HeadingItem[]>([]);

  // Use resolvedTheme to avoid hydration issues
  const isLight = mounted ? resolvedTheme === "light" : true; // Default to light theme

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    const previousFontSize = root.style.fontSize;
    root.style.fontSize = "90%";
    return () => {
      root.style.fontSize = previousFontSize;
    };
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    if (isLight) {
      root.style.setProperty("--tw-text-opacity", "1");
      root.classList.remove("dark");
    } else {
      root.classList.add("dark");
    }
  }, [isLight, mounted]);

  const apiBase = BACKEND_URL.endsWith("/api/v1")
    ? BACKEND_URL
    : `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

  const fetchManifest = useCallback(async (options: { force?: boolean } = {}) => {
    const currentKey = manifestKey;
    if (!options.force && fetchedManifestKeyRef.current === currentKey) {
      console.log("[Page] 🟢 Manifest fetch skipped (duplicate key)", currentKey);
      return;
    }

    fetchedManifestKeyRef.current = currentKey;
    try {
      setLoading(true);
      setError(null);

      const url = `${apiBase}/docbook/live-manifest/public?org_id=${encodeURIComponent(
        org
      )}&repo_id=${encodeURIComponent(repo)}&persona=${encodeURIComponent(
        persona
      )}`;

      console.log("[Page] 🟢 MANIFEST API CALL");
      console.log("[Page] 🟢 URL:", url);
      console.log("[Page] 🟢 Parameters:", {
        org_id: org,
        repo_id: repo,
        persona: persona,
      });

      const response = await fetch(url);

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
      fetchedManifestKeyRef.current = null;
      setError(
        err instanceof Error ? err.message : "Failed to load documentation"
      );
    } finally {
      setLoading(false);
    }
  }, [apiBase, manifestKey, org, repo, persona]);

  useEffect(() => {
    if (!org || !repo || !persona) {
      console.warn("[Page] 🟥 Missing route params", {
        org,
        repo,
        persona,
      });
      setError("Invalid documentation URL");
      setLoading(false);
      return;
    }

    console.log(
      "[Page] 🟢 useEffect triggered, fetching manifest with:",
      { org, repo, persona }
    );
    fetchManifest().catch((err) => {
      console.error("[Page] 🟥 Manifest fetch failed:", err);
    });
  }, [fetchManifest, org, repo, persona]);

  const fetchContent = useCallback(async (
    slugSegments: string[],
    displayPath?: string,
    sourceSegments?: string[],
    options: { force?: boolean } = {}
  ) => {
    setLoading(true);
    setError(null);

    try {
      console.log("[Page] 🟢 CONTENT API CALL");
      console.log("[Page] 🟢 Parameters:", {
        org_id: org,
        repo_id: repo,
        persona: persona,
        slugSegments,
        displayPath,
        sourceSegments,
      });

      const params = new URLSearchParams({
        org_id: org,
        repo_id: repo,
        persona: persona,
      });

      const segmentsToUse =
        sourceSegments && sourceSegments.length ? sourceSegments : slugSegments;

      const contentKey = `${manifestKey}::${
        segmentsToUse.length ? segmentsToUse.join("/") : "SUMMARY.md"
      }`;
      if (!options.force && fetchedContentKeyRef.current === contentKey) {
        console.log("[Page] 🟢 Content fetch skipped (duplicate key)", contentKey);
        setLoading(false);
        return;
      }

      fetchedContentKeyRef.current = contentKey;

      segmentsToUse.forEach((segment) => {
        if (segment) {
          params.append("slug", segment);
        }
      });

      const url = `${apiBase}/docbook/live-content/public?${params.toString()}`;
      console.log("[Page] 🟢 CONTENT URL:", url);
      console.log("[Page] 🟢 Slug parameters:", segmentsToUse);

      const response = await fetch(url);

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
      fetchedContentKeyRef.current = null;
      setError(err instanceof Error ? err.message : "Failed to load content");
    } finally {
      setLoading(false);
    }
  }, [apiBase, manifestKey, org, repo, persona]);

  useEffect(() => {
    if (!manifest) return;

    if (slug.length) {
      fetchContent([...slug]).catch((err) =>
        console.error("[Page] 🟥 Content fetch failed:", err)
      );
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
        fetchContent(["SUMMARY.md"], firstDoc.path, ["SUMMARY.md"]).catch(
          (err) => console.error("[Page] 🟥 Default content fetch failed:", err)
        );
      } else {
        setError("No published documentation found.");
      }
    }
  }, [fetchContent, manifest, repo, slug, slugKey]);

  const renderSidebarItems = (items: SidebarItem[], depth = 0) => {
    return items.map((item, index) => {
      const isFolder = item.type === "folder";
      const label = item.name.replace(/-/g, " ");
      const isRoot = depth === 0;

      if (isFolder) {
        const isOpen = expandedNodes.has(item.id);
        const wrapperClass = [
          "mb-1",
          isRoot
            ? isLight
              ? "mt-6 first:mt-3 border-t border-slate-200/70 first:border-transparent pt-4 first:pt-2"
              : "mt-6 first:mt-3 border-t border-slate-800/70 first:border-transparent pt-4 first:pt-2"
            : "",
        ]
          .filter(Boolean)
          .join(" ");

        const buttonClass = [
          "flex w-full items-center gap-2 rounded-lg pr-3 transition-colors",
          isRoot
            ? "py-2 text-[0.7rem] font-semibold uppercase tracking-[0.32em]"
            : "py-2 text-sm font-medium",
          isLight
            ? "text-slate-700 hover:bg-slate-100"
            : "text-slate-300 hover:bg-slate-800/60",
        ].join(" ");

        return (
          <div key={item.id} className={wrapperClass}>
            <button
              onClick={() => toggleNode(item.id)}
              className={buttonClass}
              style={{ paddingLeft: `${depth * 16 + 16}px` }}
            >
              <div className="flex items-center gap-2">
                <ChevronRight
                  className={`h-4 w-4 shrink-0 transition-transform ${
                    isOpen ? "rotate-90" : ""
                  }`}
                />
                <Folder className="h-4 w-4 shrink-0" />
                <span className={isRoot ? "tracking-[0.32em]" : "capitalize"}>
                  {isRoot ? label.toUpperCase() : label}
                </span>
              </div>
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
      const itemPadding = depth * 16 + 32;

      return (
        <button
          key={item.id}
          onClick={() => {
            fetchContentByPath(item.path, true, item.source_path);
            setSidebarOpen(false);
          }}
          className={`mb-1 flex w-full items-center gap-2 rounded-lg py-2 pr-3 text-sm transition-colors ${
            isActive
              ? isLight
                ? "bg-indigo-50 text-indigo-600 font-medium"
                : "bg-indigo-500/10 text-indigo-300 font-medium"
              : isLight
              ? "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
              : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          }`}
          style={{ paddingLeft: `${itemPadding}px` }}
        >
          <FileText className="h-4 w-4 shrink-0" />
          <span className="truncate capitalize">{label}</span>
        </button>
      );
    });
  };

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

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleThemeToggle = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
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
      const nextUrl = `/render-docs/${org}/${repo}/${persona}${normalizedPath}`;
      window.history.pushState({}, "", nextUrl);
    }

    await fetchContent(slugSegments, normalizedPath, sourceSegments, {
      force: true,
    });
  };

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
      path: `/render-docs/${org}/${repo}/${persona}/${segments.slice(0, idx + 1).join("/")}`,
      uniquePath: `/render-docs/${org}/${repo}/${persona}/${segments.slice(0, idx + 1).join("/")}__${idx}`,
    }));
    return [...base, ...crumbs];
  }, [manifest, activePath, org, repo, persona]);

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
      style={{
        color: isLight ? "#000000" : "#e2e8f0",
      }}
    >

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className="relative flex min-h-screen lg:h-screen lg:overflow-hidden">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-64 border-r transition-all duration-300 lg:relative lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          } ${
            isLight
              ? "border-slate-300 bg-white" 
              : "border-slate-800 bg-slate-900"
          }`}
        >
          <div className="flex h-full flex-col">
            {/* Sidebar Header */}
            <div
              className={`flex items-center justify-between border-b px-6 py-4 ${
                isLight ? "border-slate-300" : "border-slate-800"
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
                    ? "text-slate-700 hover:bg-slate-100"
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

            {/* Sidebar Footer */}
            <div
              className={`px-4 py-5 ${
                isLight
                  ? "border-t border-slate-200 bg-white"
                  : "border-t border-slate-800 bg-slate-900"
              }`}
            >
              <div
                className={`rounded-xl p-4 text-center shadow-sm ${
                  isLight
                    ? "bg-gradient-to-r from-indigo-50 via-white to-purple-50"
                    : "bg-slate-800/60"
                }`}
              >
                <p
                  className={`text-[10px] font-semibold uppercase tracking-[0.35em] ${
                    isLight ? "text-slate-500" : "text-slate-400"
                  }`}
                >
                  Powered by
                </p>
                <p
                  className={`mt-2 text-lg font-bold ${
                    isLight ? "text-indigo-600" : "text-indigo-300"
                  }`}
                >
                  Pustak
                </p>
                <p
                  className={`mt-3 text-xs leading-relaxed ${
                    isLight ? "text-slate-500" : "text-slate-400"
                  }`}
                >
                  Beautiful AI-generated documentation, always in sync.
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex min-h-screen flex-1 flex-col lg:overflow-hidden">
          {/* Header */}
          <header
            className={`sticky top-0 z-30 border-b backdrop-blur-sm ${
              isLight
                ? "border-slate-300 bg-white/85"
                : "border-slate-800 bg-slate-900/80"
            }`}
          >
            <div className="flex flex-col gap-3 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-1 items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className={`rounded-lg p-2 transition-colors lg:hidden ${
                    isLight
                      ? "text-slate-700 hover:bg-slate-100"
                      : "text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <Menu className="h-5 w-5" />
                </button>

                {/* Breadcrumbs */}
                <nav
                  className="hidden flex-1 items-center gap-2 text-sm md:flex"
                  aria-label="Breadcrumb"
                >
                  {dynamicBreadcrumbs.map((crumb, index) => {
                    const isLast = index === dynamicBreadcrumbs.length - 1;
                    return (
                      <span
                        key={crumb.uniquePath || crumb.path}
                        className="flex items-center gap-2"
                      >
                        {index > 0 && (
                          <ChevronRight
                            className={`h-4 w-4 ${
                              isLight ? "text-slate-400" : "text-slate-600"
                            }`}
                          />
                        )}
                        <a
                          href={crumb.path}
                          className={`transition-colors ${
                            isLast
                              ? isLight
                                ? "text-base font-semibold text-slate-900"
                                : "text-base font-semibold text-white"
                              : isLight
                              ? "text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 hover:text-slate-800"
                              : "text-xs font-semibold uppercase tracking-[0.3em] text-slate-500/80 hover:text-slate-200"
                          }`}
                        >
                          {isLast ? crumb.label : crumb.label}
                        </a>
                      </span>
                    );
                  })}
                </nav>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Search Trigger */}
                <button
                  onClick={() => setSearchOpen(true)}
                  className={`hidden min-w-[240px] items-center justify-between rounded-full border px-4 py-2 text-sm shadow-sm transition-all md:flex ${
                    isLight
                      ? "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900"
                      : "border-slate-800 bg-slate-900 text-slate-400 hover:border-slate-700 hover:text-slate-100"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    <span className="text-xs uppercase tracking-[0.3em]">
                      Search
                    </span>
                  </span>
                  <kbd
                    className={`rounded border px-1.5 py-0.5 text-xs ${
                      isLight
                        ? "border-slate-300 bg-slate-100 text-slate-600"
                        : "border-slate-700 bg-slate-800 text-slate-400"
                    }`}
                  >
                    ⌘K
                  </kbd>
                </button>

                {/* Copy Page */}
                <button
                  onClick={handleCopyLink}
                  className={`flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-colors ${
                    isLight
                      ? "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900"
                      : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-slate-100"
                  }`}
                >
                  <Copy className="h-4 w-4" />
                  <span>{copied ? "Copied" : "Copy Link"}</span>
                </button>

                {/* Theme Toggle */}
                <button
                  onClick={handleThemeToggle}
                  className={`flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-colors ${
                    isLight
                      ? "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900"
                      : "border-slate-800 bg-slate-900 text-amber-400 hover:border-slate-700 hover:text-amber-300"
                  }`}
                  title={`Switch to ${isLight ? "dark" : "light"} mode`}
                >
                  {isLight ? (
                    <>
                      <Moon className="h-4 w-4" />
                      <span>Dark</span>
                    </>
                  ) : (
                    <>
                      <Sun className="h-4 w-4" />
                      <span>Light</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="flex-1 overflow-y-visible lg:overflow-y-auto">
            <div className="mx-auto max-w-10xl px-6 py-6 sm:px-8 lg:ml-8 lg:mr-4 lg:px-6">
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
                  <div className="flex flex-col gap-10 lg:flex-row">
                    <article className="min-w-0 flex-1 pb-16 lg:mt-14 lg:px-14 lg:pb-24">
                      <MarkdownRenderer
                        content={content}
                        isLight={isLight}
                        className="space-y-6"
                        onHeadingsChange={setHeadings}
                      />

                      {/* Navigation */}
                      {(neighbors.previous || neighbors.next) && (
                        <div className="mt-10 grid gap-3 border-t pt-6 sm:grid-cols-2">
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
                                  ? "border-slate-300 hover:bg-slate-50"
                                  : "border-slate-800 hover:bg-slate-800"
                              }`}
                            >
                              <div
                                className={`flex items-center gap-1 text-sm ${
                                  isLight ? "text-slate-600" : "text-slate-400"
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
                                  ? "border-slate-300 hover:bg-slate-50"
                                  : "border-slate-800 hover:bg-slate-800"
                              }`}
                            >
                              <div
                                className={`flex items-center gap-1 text-sm ${
                                  isLight ? "text-slate-600" : "text-slate-400"
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
                    </article>
                  </div>
                </>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24">
          <div
            className="fixed inset-0 bg-black/20 backdrop-blur-sm dark:bg-slate-900/80"
            onClick={() => setSearchOpen(false)}
          />
          <div
            className={`relative w-full max-w-2xl rounded-lg shadow-2xl ${isLight ? "bg-white" : "bg-slate-900"}`}
          >
            <div className="flex items-center border-b px-4 py-3">
              <Search
                className={`mr-3 h-5 w-5 ${isLight ? "text-slate-500" : "text-slate-400"}`}
              />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search documentation..."
                className={`flex-1 bg-transparent text-sm outline-none ${isLight ? "text-slate-900" : "text-white"}`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    setSearchOpen(false);
                  }
                }}
                autoFocus
              />
              <button
                onClick={() => setSearchOpen(false)}
                className={`rounded p-1 ${isLight ? "text-slate-500 hover:bg-slate-100" : "text-slate-400 hover:bg-slate-800"}`}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-2">
              {filteredResults.length === 0 ? (
                <div className="p-4 text-center">
                  <p className={isLight ? "text-slate-500" : "text-slate-400"}>
                    No results found.
                  </p>
                </div>
              ) : (
                <div className="flex flex-col gap-1">
                  {filteredResults.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        fetchContentByPath(item.path, true, item.source_path);
                        setSearchOpen(false);
                      }}
                      className={`flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${isLight ? "hover:bg-slate-100" : "hover:bg-slate-800"}`}
                    >
                      <FileText className={`h-4 w-4 shrink-0 ${isLight ? "text-slate-500" : "text-slate-400"}`} />
                      <span className={`font-medium ${isLight ? "text-slate-900" : "text-white"}`}>
                        {item.name.replace(/-/g, " ").replace(/_/g, " ")}
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
