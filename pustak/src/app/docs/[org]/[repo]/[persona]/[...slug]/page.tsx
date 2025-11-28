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

export default function LiveDocsPage({ params: pageParams }: any) {
  console.log('[DOCS_DEBUG] 🚀 NEW PAGE COMPONENT EXECUTED', { pageParams });
  console.log('[DOCS_DEBUG] 🔍 URL Path Pattern: /docs/[org]/[repo]/[persona]/[...slug]');
  console.log('[DOCS_DEBUG] 📚 Component: LiveDocsPage in [org]/[repo]/[persona]/[...slug]/page.tsx');
  
  // Get params from useParams hook for client components
  const params = useParams();
  console.log('[DOCS_DEBUG] 🔍 useParams() result:', params);
  
  // Use either the props params (for server component) or useParams (for client component)
  const org = (pageParams?.org || params?.org) as string;
  
  // CRITICAL FIX: Handle the case where repo=docs and persona=org
  let repo = (pageParams?.repo || params?.repo) as string;
  let persona = (pageParams?.persona || params?.persona) as string;
  const slug = ((pageParams?.slug || params?.slug) as string[]) || [];
  
  console.log('[DOCS_DEBUG] 📚 Original params:', { org, repo, persona, slug });
  
  // If repo is 'docs' and persona is the org name, fix the parameters
  if (repo === 'docs' && persona === org && slug.length >= 1) {
    // First slug segment should be the actual repo
    repo = slug[0];
    // Use 'dev' as the default persona
    persona = 'dev';
    console.log('[DOCS_DEBUG] 🔄 FIXED PARAMETERS: repo=' + repo + ', persona=' + persona);
  }
  
  console.log('[DOCS_DEBUG] 📚 Final params:', { org, repo, persona, slug });

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
      
      const url = `${apiBase}/docbook/live-manifest/public?org_id=${encodeURIComponent(
        org
      )}&repo_id=${encodeURIComponent(repo)}&persona=${encodeURIComponent(persona)}`;
      
      console.log('[DOCS_DEBUG] 📡 MANIFEST API CALL');
      console.log('[DOCS_DEBUG] 📡 URL:', url);
      console.log('[DOCS_DEBUG] 📡 Parameters:', {
        org_id: org,
        repo_id: repo,
        persona: persona
      });
      
      console.log(`🔍 Fetching manifest with: org=${org}, repo=${repo}, persona=${persona}`);
      
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
      setError(
        err instanceof Error ? err.message : "Failed to load documentation"
      );
    } finally {
      setLoading(false);
    }
  };

  const sanitizeSegments = (segments: string[]): string[] => {
    const normalized = [...segments].filter(Boolean);
    const removable = new Set(["docs", org, repo, persona]);

    while (normalized.length && removable.has(normalized[0])) {
      normalized.shift();
    }

    return normalized;
  };

  const fetchContent = async (
    slugSegments: string[],
    displayPath?: string,
    sourceSegments?: string[]
  ) => {
    setLoading(true);
    setError(null);

    try {
      // Special case for SUMMARY.md which is at the root of persona folder
      const isSummary = slugSegments.length === 1 && slugSegments[0] === "SUMMARY" || 
                       (slugSegments.length === 2 && slugSegments[0] === persona && slugSegments[1] === "SUMMARY") ||
                       (slugSegments.length >= 1 && slugSegments[slugSegments.length-1] === "SUMMARY.md");
      
      // Always sanitize slug segments for path display, even if we don't use them for the API call
      const sanitizedSlugSegments = sanitizeSegments(slugSegments);
      const sanitizedSourceSegments =
        sourceSegments && sourceSegments.length
          ? sanitizeSegments(sourceSegments)
          : undefined;
      
      console.log('[DOCS_DEBUG] 📡 CONTENT API CALL');
      console.log('[DOCS_DEBUG] 📡 Parameters:', {
        org_id: org,
        repo_id: repo,
        persona: persona,
        slugSegments,
        sanitizedSlugSegments,
        sanitizedSourceSegments,
        isSummary
      });
      
      console.log(
        `🔍 Fetching content with: org=${org}, repo=${repo}, persona=${persona}, slugSegments=${JSON.stringify(
          slugSegments
        )}, isSummary=${isSummary}`
      );

      const params = new URLSearchParams({
        org_id: org,
        repo_id: repo,
        persona: persona,
      });
      
      // For SUMMARY.md, just request it directly without any extra path segments
      if (isSummary) {
        params.append("slug", "SUMMARY.md");
      } else {
        // Normal case - use the sanitized segments
        const segmentsToUse =
          sanitizedSourceSegments && sanitizedSourceSegments.length
            ? sanitizedSourceSegments
            : sanitizedSlugSegments;

        segmentsToUse.forEach((segment) => {
          if (segment) {
            params.append("slug", segment);
          }
        });
      }
      
      const url = `${apiBase}/docbook/live-content/public?${params.toString()}`;
      console.log('[DOCS_DEBUG] 📡 CONTENT URL:', url);
      console.log('[DOCS_DEBUG] 📡 Final params:', params.toString());

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to load content: ${response.statusText}`);
      }

      const data = await response.json();
      setContent(data.content || "");
      const normalizedPath =
        displayPath || `/${[repo, persona, ...sanitizedSlugSegments].join("/")}`;
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
    const slugSegments = sanitizeSegments(segments);

    const sourceNormalized = sourcePath
      ? sourcePath.startsWith("/")
        ? sourcePath
        : `/${sourcePath}`
      : normalizedPath;
    const sourceSegmentsRaw = sourceNormalized.split("/").filter(Boolean);
    const sourceSegments = sanitizeSegments(sourceSegmentsRaw);

    if (pushHistory) {
      const nextUrl = `/docs/${org}${normalizedPath}`;
      window.history.pushState({}, "", nextUrl);
    }

    const displayPath = `/${[repo, persona, ...slugSegments].join("/")}`;

    await fetchContent(slugSegments, displayPath, sourceSegments);
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
      {/* Debug Banner */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-green-500 text-white p-2 text-center font-bold">
        NEW PAGE COMPONENT: /docs/[org]/[repo]/[persona]/[...slug]/page.tsx
        <br />
        org={org}, repo={repo}, persona={persona}, slug={JSON.stringify(slug)}
      </div>
      <div className="h-16"></div> {/* Spacer to prevent content from being hidden under banner */}
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
