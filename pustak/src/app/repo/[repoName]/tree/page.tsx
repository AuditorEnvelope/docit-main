import { TreeSidebar } from "@/components/TreeSidebar";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

interface PageProps {
  params: {
    repoName: string;
  };
}

export default async function TreePage({ params }: PageProps) {
  const { repoName } = await params;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-80 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-y-auto">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <Link
              href={`/repo/${repoName}/summary`}
              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-3"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Docs</span>
            </Link>
            <h1 className="text-lg font-semibold truncate">{repoName}</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Hierarchical Documentation
            </p>
          </div>
          <TreeSidebar repoName={repoName} />
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto flex items-center justify-center">
          <div className="text-center max-w-md px-4">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
              <svg
                className="w-12 h-12 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
              Documentation Tree
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Navigate through the hierarchical structure of your codebase. Click on any node in the sidebar to view its documentation.
            </p>
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-left">
              <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                Structure
              </h3>
              <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <li>📦 <strong>SDKs</strong> - Top-level packages</li>
                <li>📂 <strong>Modules</strong> - Subdirectories</li>
                <li>⚡ <strong>Features</strong> - Logical groupings</li>
                <li>🔧 <strong>Functions</strong> - Individual functions</li>
              </ul>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
