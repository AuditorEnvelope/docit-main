"use client";

import { useEffect, useState, useCallback } from "react";
import { Layout } from "@/components/Layout";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  Home,
  Building2,
  GitBranch,
  Code,
  History,
  Clock,
  ArrowLeft,
  ExternalLink,
  Calendar,
  FileText,
} from "lucide-react";
import Link from "next/link";

interface RepoPageProps {
  params: Promise<{
    slug: string[];
  }>;
}

export default function RepoPage({ params }: RepoPageProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState<string>("");
  const [version, setVersion] = useState<string | null>(null);
  const [repoName, setRepoName] = useState<string>("");

  // Load page only once on mount
  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      try {
        const resolvedParams = await params;
        const slug = resolvedParams.slug;

        // Parse docType and version from slug
        const lastSegment = slug[slug.length - 1];
        const isVersioned = lastSegment?.match(/^v\d+(\.\d+)?$/);

        let parsedDocType: string;
        let parsedVersion: string | null = null;

        if (isVersioned) {
          parsedVersion = lastSegment;
          parsedDocType = slug[slug.length - 2];
        } else {
          parsedDocType = lastSegment;
        }

        const repoNameSegments = isVersioned ? slug.slice(0, -2) : slug.slice(0, -1);
        const parsedRepoName = repoNameSegments.join("/");

        if (!isMounted) return;

        setDocType(parsedDocType);
        setVersion(parsedVersion);
        setRepoName(parsedRepoName);

        // Determine file path based on docType
        let filePath: string;
        if (parsedVersion) {
          filePath = `docs/${parsedDocType}/${parsedVersion}-${parsedDocType}.md`;
        } else {
          const fileMap: Record<string, string> = {
            summary: "README.md",
            architecture: "docs/architecture/current.md",
            workflow: "docs/workflow/current.md",
            api: "docs/api.md",
            changelog: "CHANGELOG.md",
            changes: "docs/changes/",
          };
          filePath = fileMap[parsedDocType] || "README.md";
        }

        // Fetch content from backend via /api/fetch-doc
        const userToken = localStorage.getItem('pustak_access_token');
        const response = await fetch(
          `/api/fetch-doc?repo=${encodeURIComponent(parsedRepoName)}&filePath=${encodeURIComponent(filePath)}`,
          {
            headers: userToken ? { 'Authorization': `Bearer ${userToken}` } : {},
          }
        );
        if (!response.ok) {
          if (!isMounted) return;
          setError(response.status === 401 ? 'Not authenticated' : 'Failed to fetch documentation');
          setLoading(false);
          return;
        }

        const data = await response.json();

        if (!isMounted) return;

        if (data.content) {
          setContent(data.content);
        } else {
          setError("Documentation not found");
        }
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load documentation");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      isMounted = false;
    };
  }, []);

  const githubUrl = `https://github.com/${repoName}`;
  const lastUpdated = new Date();

  const getDocIcon = useCallback((type: string) => {
    switch (type) {
      case "summary":
        return <Home className="w-5 h-5" />;
      case "architecture":
        return <Building2 className="w-5 h-5" />;
      case "workflow":
        return <GitBranch className="w-5 h-5" />;
      case "api":
        return <Code className="w-5 h-5" />;
      case "changes":
        return <History className="w-5 h-5" />;
      case "changelog":
        return <Clock className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  }, []);

  const getDocTitle = useCallback(() => {
    const titles: Record<string, string> = {
      summary: "Summary",
      architecture: "Architecture",
      workflow: "Workflow",
      api: "API Documentation",
      changes: "Recent Changes",
      changelog: "Changelog",
    };
    const baseTitle = titles[docType] || docType;
    return version ? `${baseTitle} ${version}` : baseTitle;
  }, [docType, version]);

  if (loading) {
    return (
      <Layout>
        <div className="flex-1 p-8">
          <div className="max-w-6xl mx-auto">
            <p className="text-gray-600 dark:text-gray-400">Loading documentation...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !content) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              {version ? `${docType.toUpperCase()} ${version} Not Found` : "Documentation Not Available"}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {error || "The documentation for this repository is not available."}
            </p>
            <Link
              href="/"
              className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Home</span>
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  const fileName = version
    ? `docs/${docType}/${version}-${docType}.md`
    : `docs/${docType}.md`;

  return (
    <Layout>
      <div className="flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </Link>

              <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />

              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  {getDocIcon(docType)}
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {getDocTitle()}
                  </h1>
                </div>

                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {repoName}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                <Calendar className="w-4 h-4" />
                <span>
                  Updated{" "}
                  {lastUpdated.toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>

              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 px-3 py-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View on GitHub</span>
              </a>
            </div>
          </div>

          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Source: {fileName}
            </p>
            <MarkdownRenderer content={content} />
          </div>
        </div>
      </div>
    </Layout>
  );
}
