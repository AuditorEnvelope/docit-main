"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Book, Search, Menu, X, ChevronRight, Home } from "lucide-react";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface SidebarItem {
  section?: string;
  page?: string;
  path: string;
  type: "folder" | "file";
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
      const firstDoc = manifest.sidebar.find((item) => item.type === "file");
      if (firstDoc) {
        fetchContentByPath(firstDoc.path);
      } else {
        setError("No published documentation found.");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manifest, docSegmentsKey, repo]);

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
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-slate-800 bg-slate-900 transition-transform lg:relative lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar Header */}
          <div className="border-b border-slate-800 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-500">
                  <Book className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="font-semibold text-white">{manifest?.title}</h2>
                  <p className="text-xs text-slate-400">{org}</p>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <div className="space-y-1">
              {manifest?.sidebar.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    fetchContentByPath(item.path);
                    setSidebarOpen(false);
                  }}
                  className={`w-full text-left rounded-lg px-3 py-2 text-sm transition ${
                    activePath === item.path
                      ? "bg-blue-500/20 text-blue-300 font-medium"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {item.type === "folder" && <ChevronRight className="h-4 w-4" />}
                    <span>{item.section || item.page}</span>
                  </div>
                </button>
              ))}
            </div>
          </nav>

          {/* Footer */}
          <div className="border-t border-slate-800 p-4 text-center">
            <p className="text-xs text-slate-500">
              Powered by <span className="text-blue-400">Pustak AI</span>
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-slate-400 hover:text-white"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Home className="h-4 w-4" />
                <ChevronRight className="h-4 w-4" />
                <span>{repo}</span>
                {docPath && (
                  <>
                    <ChevronRight className="h-4 w-4" />
                    <span className="text-white">{docPath}</span>
                  </>
                )}
              </div>
            </div>

            <button className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-600 hover:text-white">
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline">Search</span>
              <kbd className="hidden rounded bg-slate-700 px-1.5 py-0.5 text-xs sm:inline">⌘K</kbd>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto max-w-4xl px-6 py-12">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
            </div>
          ) : (
            <article className="prose prose-invert prose-slate max-w-none">
              <MarkdownRenderer content={content} />
            </article>
          )}
        </main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
