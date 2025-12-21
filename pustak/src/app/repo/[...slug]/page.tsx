"use client";

import { useEffect, useState, useCallback } from "react";
import { Layout } from "@/components/Layout";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { BlockNoteEditor } from "@/components/BlockNoteEditor";
import { CommitModal } from "@/components/CommitModal";
import { useAuth } from "@/contexts/AuthContext";
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
  Globe2,
  Edit,
  X,
  Save,
  Loader2,
} from "lucide-react";
import Link from "next/link";

interface RepoPageProps {
  params: Promise<{
    slug: string[];
  }>;
}

const LEGACY_DOC_PATHS: Record<string, string> = {
  summary: "docs/summary.md",
  architecture: "docs/architecture/current.md",
  workflow: "docs/workflow/current.md",
  api: "docs/api.md",
  changelog: "CHANGELOG.md",
  changes: "docs/changes/index.md",
  readme: "README.md",
  quality_report: "docs/QUALITY_REPORT.md",
};

const DOC_TYPE_DISPLAY_MAP: Record<string, string> = {
  summary: "Summary",
  architecture: "Architecture",
  workflow: "Workflow",
  api: "API Documentation",
  changes: "Recent Changes",
  changelog: "Changelog",
  readme: "Documentation",
  quality_report: "Quality Report",
};

const normalizeDocType = (value: string): string => {
  const lower = value.toLowerCase();
  if (lower === "readme") return "summary";
  if (lower === "qualityreport") return "quality_report";
  return lower;
};

const extractDocInfo = (pathSegments: string[]): {
  filePath: string;
  docType: string;
  version: string | null;
} => {
  if (pathSegments.length === 0) {
    return {
      filePath: "README.md",
      docType: "summary",
      version: null,
    };
  }

  const lastSegment = pathSegments[pathSegments.length - 1];
  const hasExtension = lastSegment.includes(".");
  const joinedPath = pathSegments.join("/");

  if (!hasExtension) {
    const legacyPath = LEGACY_DOC_PATHS[lastSegment.toLowerCase()];
    if (legacyPath) {
      return {
        filePath: legacyPath,
        docType: normalizeDocType(lastSegment),
        version: null,
      };
    }

    return {
      filePath: joinedPath,
      docType: normalizeDocType(lastSegment),
      version: null,
    };
  }

  const filePath = joinedPath;
  const fileNameWithoutExt = lastSegment.replace(/\.md$/i, "");
  const versionMatch = fileNameWithoutExt.match(/^(v[\d.]+)-(.*)$/i);

  if (versionMatch) {
    const [, versionValue, docSlug] = versionMatch;
    return {
      filePath,
      docType: normalizeDocType(docSlug),
      version: versionValue,
    };
  }

  return {
    filePath,
    docType: normalizeDocType(fileNameWithoutExt),
    version: null,
  };
};

export default function RepoPage({ params }: RepoPageProps) {
  const { token, isAuthenticated } = useAuth();
  const [content, setContent] = useState<string>("");
  const [editedContent, setEditedContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState<string>("");
  const [version, setVersion] = useState<string | null>(null);
  const [repoName, setRepoName] = useState<string>("");
  const [sourcePath, setSourcePath] = useState<string>("");
  const [orgName, setOrgName] = useState<string>("");
  const [sourceRepo, setSourceRepo] = useState<string>("");
  const [persona, setPersona] = useState<string>("dev");
  const [publicUrl, setPublicUrl] = useState<string>("");
  const [isEditing, setIsEditing] = useState(false);
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [trackedBranch, setTrackedBranch] = useState<string>("staging");

  // Load page only once on mount
  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      try {
        const resolvedParams = await params;
        const slug = resolvedParams.slug;

        if (!slug || slug.length < 2) {
          if (!isMounted) return;
          setError("Invalid repository path");
          setLoading(false);
          return;
        }

        const [orgSegment, repoSegment, ...pathSegments] = slug;
        const repoFullName = `${orgSegment}/${repoSegment}`;

        const repoFolder = pathSegments[0] || "";
        const personaSegment =
          pathSegments.length >= 3 && pathSegments[1].toLowerCase() === "docs"
            ? pathSegments[2]?.toLowerCase() || "dev"
            : "dev";

        const docInfo = extractDocInfo(pathSegments);
        const parsedRepoName = repoFullName;

        if (!isMounted) return;

        setDocType(docInfo.docType);
        setVersion(docInfo.version);
        setRepoName(parsedRepoName);
        setSourcePath(docInfo.filePath);
        setOrgName(orgSegment);
        setSourceRepo(repoFolder);
        setPersona(personaSegment);
        if (orgSegment && repoFolder) {
          setPublicUrl(`https://${orgSegment}.docbook.site/${repoFolder}`);
        } else {
          setPublicUrl("");
        }

        const filePath = docInfo.filePath;

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
          setEditedContent(data.content);
        } else {
          setError("Documentation not found");
        }

        // Fetch tracked branch
        if (isMounted && token && parsedRepoName) {
          try {
            const branchResponse = await fetch(
              `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/v1/repositories/${encodeURIComponent(parsedRepoName)}/tracked-branch`,
              {
                headers: {
                  'Authorization': `Bearer ${token}`,
                },
              }
            );
            if (branchResponse.ok) {
              const branchData = await branchResponse.json();
              if (branchData.tracked_branch) {
                setTrackedBranch(branchData.tracked_branch);
              }
            }
          } catch (err) {
            console.error("Failed to fetch tracked branch:", err);
          }
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
  }, [token]);

  const githubUrl = `https://github.com/${repoName}`;
  const personaLabel = persona ? `${persona.charAt(0).toUpperCase()}${persona.slice(1)}` : "";
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
    const baseTitle = DOC_TYPE_DISPLAY_MAP[docType] || docType;
    return version ? `${baseTitle} ${version}` : baseTitle;
  }, [docType, version]);

  const handleEdit = () => {
    setIsEditing(true);
    setEditedContent(content);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContent(content);
  };

  const handleCommit = async (commitMessage: string, branch?: string) => {
    if (!token || !repoName || !sourcePath) {
      throw new Error("Missing required information for commit");
    }

    setIsCommitting(true);
    try {
      // Always use staging branch
      const commitBranch = branch || "staging";
      const response = await fetch("/api/commit-doc", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          repo: repoName,
          filePath: sourcePath,
          content: editedContent,
          commitMessage,
          branch: commitBranch,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to commit changes");
      }

      // Reload the page content
      const reloadResponse = await fetch(
        `/api/fetch-doc?repo=${encodeURIComponent(repoName)}&filePath=${encodeURIComponent(sourcePath)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (reloadResponse.ok) {
        const reloadData = await reloadResponse.json();
        setContent(reloadData.content);
        setEditedContent(reloadData.content);
      }

      setIsEditing(false);
      setIsCommitModalOpen(false);
    } catch (err) {
      throw err;
    } finally {
      setIsCommitting(false);
    }
  };

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

  const fileName = sourcePath || (version
    ? `docs/${docType}/${version}-${docType}.md`
    : `docs/${docType}.md`);

  return (
    <Layout>
      <div className="flex-1 p-8">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-6 py-4 shadow-[0_25px_70px_-55px_rgba(15,23,42,1)]">
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.3em] text-slate-300 transition hover:border-slate-500 hover:text-white"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </Link>
            </div>

            <div className="mt-4 flex flex-col gap-4 lg:mt-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-slate-100">
                  <span className="rounded-full bg-blue-500/10 p-2 text-blue-300">
                    {getDocIcon(docType)}
                  </span>
                  <h1 className="text-2xl font-semibold tracking-tight">
                    {getDocTitle()}
                  </h1>
                </div>

                {(sourceRepo || personaLabel) && (
                  <div className="flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-3 py-1 text-xs font-medium text-slate-300">
                    {sourceRepo && <span className="uppercase tracking-[0.2em] text-slate-400">{sourceRepo}</span>}
                    {sourceRepo && personaLabel && <span className="opacity-40">•</span>}
                    {personaLabel && <span>{personaLabel} persona</span>}
                  </div>
                )}

                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-3 py-1 text-xs font-medium text-slate-300">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span className="tracking-wide">
                    Updated {lastUpdated.toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {isEditing ? (
                  <>
                    <button
                      onClick={handleCancel}
                      disabled={isCommitting}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-4 py-1.5 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      <span>Cancel</span>
                    </button>
                    <button
                      onClick={() => setIsCommitModalOpen(true)}
                      disabled={isCommitting}
                      className="inline-flex items-center gap-2 rounded-full bg-blue-500/90 px-4 py-1.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/35 transition hover:bg-blue-500 disabled:opacity-50"
                    >
                      {isCommitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Committing...</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4" />
                          <span>Commit Changes</span>
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  <>
                    {isAuthenticated && (
                      <button
                        onClick={handleEdit}
                        className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-4 py-1.5 text-sm font-semibold text-slate-200 transition hover:border-blue-500 hover:text-blue-300"
                      >
                        <Edit className="w-4 h-4" />
                        <span>Edit</span>
                      </button>
                    )}
                {publicUrl && (
                  <a
                    href={publicUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-full bg-blue-500/90 px-4 py-1.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/35 transition hover:bg-blue-500"
                  >
                    <Globe2 className="w-4 h-4" />
                    <span>Preview live docs</span>
                  </a>
                )}
                <a
                  href={githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 px-4 py-1.5 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>View on GitHub</span>
                </a>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="mt-8">
            <p className="text-xs text-slate-500 mb-2">
              Source: {fileName}
            </p>
            {isEditing ? (
              <div className="min-h-[400px]">
                <BlockNoteEditor
                  initialContent={editedContent}
                  onChange={setEditedContent}
                  editable={true}
                />
              </div>
            ) : (
            <MarkdownRenderer content={content} />
            )}
          </div>
        </div>
      </div>

      <CommitModal
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        onCommit={handleCommit}
        pageTitle={getDocTitle()}
        isLoading={isCommitting}
      />
    </Layout>
  );
}
