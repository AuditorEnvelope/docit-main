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
  Network,
} from "lucide-react";
import Link from "next/link";
import { loadRepoDocumentation } from "@/lib/dynamicGitHubLoader";
import { fetchAllRepositoriesFromGitHub } from "@/lib/realGitHubAPI";

interface RepoPageProps {
  params: Promise<{
    repoName: string;
    docType: string;
  }>;
}``

// Helper functions to safely extract content and fileName
function getContent(
  doc: string | { content: string } | undefined,
  fallback = ""
) {
  if (!doc) return fallback;
  return typeof doc === "string" ? doc : doc.content;
}

function getFileName(
  doc: string | { fileName?: string } | undefined,
  fallback = ""
) {
  if (!doc) return fallback;
  return typeof doc === "string" ? fallback : doc.fileName || fallback;
}

export default async function RepoPage({ params }: RepoPageProps) {
  const { repoName, docType } = await params;

  // Fetch repository info to get the full name and org
  const allRepos = await fetchAllRepositoriesFromGitHub();
  const repoInfo = allRepos.find(r => r.name === repoName);
  const githubUrl = repoInfo?.full_name 
    ? `https://github.com/${repoInfo.full_name}` 
    : `https://github.com/${repoName}`;

  // Load documentation from GitHub
  const githubDocs = await loadRepoDocumentation(repoName);
  const lastUpdated = new Date();
  
  // Debug: Log what we got
  console.log(`[${repoName}] Loaded docs:`, {
    hasReadme: !!githubDocs?.readme,
    readmeLength: githubDocs?.readme?.length || 0,
    hasSummary: !!githubDocs?.summary,
    summaryLength: githubDocs?.summary?.length || 0,
  });

  // Check if docs are available
  const hasDocs = !!(
    githubDocs?.readme ||
    githubDocs?.summary ||
    githubDocs?.api ||
    githubDocs?.changelog ||
    githubDocs?.changes?.length > 0
  );

  if (!hasDocs) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Documentation Not Available
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              The repository "{repoName}" doesn't have a docs folder yet.
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mb-8">
              Create a /docs folder with markdown files in your repository to see documentation here.
            </p>
            <div className="space-x-4">
              <Link
                href="/"
                className="inline-flex items-center space-x-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Home</span>
              </Link>
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View on GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // Extract content and fileName safely
  let content = "";
  let title = "";
  let fileName = "";

  switch (docType) {
    case "summary":
      content = githubDocs?.readme || githubDocs?.summary || "# No Summary Available";
      fileName = "README.md or docs/SUMMARY.md";
      title = "Summary";
      break;
    case "api":
      content = githubDocs?.api || "# No API Documentation Available";
      fileName = "docs/api.md";
      title = "API Documentation";
      break;
    case "changelog":
      content = githubDocs?.changelog || "# No Changelog Available";
      fileName = "CHANGELOG.md (root) or docs/CHANGELOG.md";
      title = "Changelog";
      break;
    case "changes":
      if (githubDocs?.changes && githubDocs.changes.length > 0) {
        content = githubDocs.changes.map((c) => c.content).join("\n\n---\n\n");
        fileName = `docs/changes/ (${githubDocs.changes.length} files)`;
      } else {
        content = "# No Changes Available";
        fileName = "docs/changes/";
      }
      title = "Recent Changes";
      break;
    case "architecture":
      content = githubDocs?.architecture || "# No Architecture Documentation Available";
      fileName = "docs/architecture/current.md";
      title = "Architecture";
      break;
    case "workflow":
      content = githubDocs?.workflow || "# No Workflow Documentation Available";
      fileName = "docs/workflow/current.md";
      title = "Workflow";
      break;
    default:
      content = "# Document Not Found";
      fileName = "unknown.md";
      title = "Document Not Found";
  }

  const getDocIcon = (type: string) => {
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
  };

  const getDocTitle = (type: string) => {
    switch (type) {
      case "summary":
        return "Summary";
      case "architecture":
        return "Architecture";
      case "workflow":
        return "Workflow";
      case "api":
        return "API Documentation";
      case "changes":
        return "Recent Changes";
      case "changelog":
        return "Changelog";
      default:
        return type;
    }
  };

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
                    {getDocTitle(docType)}
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

              <Link
                href={`/repo/${repoName}/tree`}
                className="inline-flex items-center space-x-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                <Network className="w-4 h-4" />
                <span>Tree View</span>
              </Link>

              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View on GitHub</span>
              </a>
            </div>
          </div>

          {/* Version Links for Architecture and Workflow */}
          {(docType === "architecture" || docType === "workflow") && (
            <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                {docType === "architecture" ? "Architecture" : "Workflow"} Versions
              </h3>
              <div className="flex flex-wrap gap-2">
                {docType === "architecture" && githubDocs?.architectureVersions.map((v) => (
                  <Link
                    key={v.version}
                    href={`/repo/${repoName}/${docType}/${v.version}`}
                    className="px-3 py-1 bg-white dark:bg-gray-800 border border-blue-300 dark:border-blue-700 rounded-md text-sm text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                  >
                    {v.version.toUpperCase()}
                  </Link>
                ))}
                {docType === "workflow" && githubDocs?.workflowVersions.map((v) => (
                  <Link
                    key={v.version}
                    href={`/repo/${repoName}/${docType}/${v.version}`}
                    className="px-3 py-1 bg-white dark:bg-gray-800 border border-blue-300 dark:border-blue-700 rounded-md text-sm text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                  >
                    {v.version.toUpperCase()}
                  </Link>
                ))}
              </div>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-2">
                Click a version to view its documentation
              </p>
            </div>
          )}

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
