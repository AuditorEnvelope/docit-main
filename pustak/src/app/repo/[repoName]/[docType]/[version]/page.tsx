import { Layout } from "@/components/Layout";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  Building2,
  GitBranch,
  ArrowLeft,
  ExternalLink,
  Calendar,
} from "lucide-react";
import Link from "next/link";
import { fetchFileFromGitHub } from "@/lib/realGitHubAPI";
import { fetchAllRepositoriesFromGitHub } from "@/lib/realGitHubAPI";

interface VersionPageProps {
  params: Promise<{
    repoName: string;
    docType: string;
    version: string;
  }>;
}

export default async function VersionPage({ params }: VersionPageProps) {
  const { repoName, docType, version } = await params;

  // Fetch repository info
  const allRepos = await fetchAllRepositoriesFromGitHub();
  const repoInfo = allRepos.find(r => r.name === repoName);
  const githubUrl = repoInfo?.full_name 
    ? `https://github.com/${repoInfo.full_name}` 
    : `https://github.com/${repoName}`;

  // Fetch the specific version file
  let content = "";
  let fileName = "";
  let title = "";

  if (docType === "architecture") {
    fileName = `docs/architecture/${version}-architecture.md`;
    content = await fetchFileFromGitHub(repoName, fileName) || "# Architecture Not Found";
    title = `Architecture ${version.toUpperCase()}`;
  } else if (docType === "workflow") {
    fileName = `docs/workflow/${version}-workflow.md`;
    content = await fetchFileFromGitHub(repoName, fileName) || "# Workflow Not Found";
    title = `Workflow ${version.toUpperCase()}`;
  }

  const lastUpdated = new Date();

  const getDocIcon = () => {
    return docType === "architecture" ? (
      <Building2 className="w-6 h-6" />
    ) : (
      <GitBranch className="w-6 h-6" />
    );
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

              <div className="flex items-center space-x-3">
                {getDocIcon()}
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {title}
                  </h1>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {repoName}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                <Calendar className="w-4 h-4" />
                <span>
                  Updated{" "}
                  {lastUpdated.toLocaleDateString("en-US", {
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
                className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View on GitHub</span>
              </a>
            </div>
          </div>

          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
            <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
              Source: {fileName}
            </div>
            <MarkdownRenderer content={content} />
          </div>
        </div>
      </div>
    </Layout>
  );
}
