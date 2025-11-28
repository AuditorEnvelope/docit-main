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
  Folder,
  FileText,
  Copy,
  Shield,
  Globe,
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

const TOC_INDENT_CLASSES = ["pl-0", "pl-3", "pl-6", "pl-9", "pl-12"];

export default function LiveDocsPage() {
  const params = useParams();
  const org = params.org as string;
  const repo = params.repo as string;
  const persona = params.persona as string;
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

  useEffect(() => {
    if (!org || !repo || !persona) {
      setError("Invalid URL: organization, repository, or persona not specified");
      setLoading(false);
      return;
    }

    fetchManifest();
  }, [org, repo, persona]);

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
        )}&repo_id=${encodeURIComponent(repo)}&persona=${encodeURIComponent(persona)}`
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
        persona: persona,
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
        displayPath || `/${[repo, persona, ...slugSegments].join("/")}`;
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
    const slugSegments = segments.slice(2); // Skip repo and persona

    const sourceNormalized = sourcePath
      ? sourcePath.startsWith("/")
        ? sourcePath
        : `/${sourcePath}`
      : normalizedPath;
    const sourceSegments = sourceNormalized.split("/").filter(Boolean).slice(2);

    if (pushHistory) {
      const nextUrl = `/docs/${org}${normalizedPath}`;
      window.history.pushState({}, "", nextUrl);
    }

    await fetchContent(slugSegments, normalizedPath, sourceSegments);
  };

  useEffect(() => {
    if (!manifest) return;

    if (slug.length) {
      const currentPath = `/${[repo, persona, ...slug].join("/")}`;
      fetchContent(slug, currentPath);
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
  }, [manifest, repo, persona, slug.join("/")]);

  // Rest of the component remains the same, with minor modifications to include persona in paths

  // ... (rest of the component code)

  return (
    <div
      className={`min-h-screen transition-colors ${
        isLight ? "bg-white" : "bg-slate-950"
      }`}
      style={{
        color: isLight ? "#000000" : "#e2e8f0",
      }}
    >
      {/* Persona Indicator */}
      <div className={`fixed top-0 right-0 z-50 px-4 py-2 m-4 rounded-full text-sm font-medium ${
        persona === "internal" 
          ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" 
          : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      }`}>
        <div className="flex items-center gap-1">
          {persona === "internal" ? (
            <>
              <Shield className="h-4 w-4" />
              <span>Internal</span>
            </>
          ) : (
            <>
              <Globe className="h-4 w-4" />
              <span>Developer</span>
            </>
          )}
        </div>
      </div>
      
      {/* Rest of the UI */}
      {/* ... */}
    </div>
  );
}
