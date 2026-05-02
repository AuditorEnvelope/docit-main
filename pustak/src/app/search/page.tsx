import { Layout } from "@/components/Layout";
import {
  Search,
  FileText,
  Code,
  Building2,
  GitBranch,
  Clock,
  Filter,
} from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search Documentation",
  description: "Search across all documentation in DocIt",
};

interface SearchPageProps {
  searchParams: Promise<{ q?: string; type?: string; repo?: string }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = params.q || "";
  const typeFilter = params.type;
  const repoFilter = params.repo;

  // Fetch search results server-side
  let results: any[] = [];
  if (query && query.length > 2) {
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      let url = `${backendUrl}/search?query=${encodeURIComponent(query)}`;

      if (repoFilter) {
        url = `${backendUrl}/repos/${repoFilter}/search?query=${encodeURIComponent(
          query,
        )}`;
      }

      const response = await fetch(url, {
        next: { revalidate: 10 },
      });

      if (response.ok) {
        results = await response.json();

        // Apply type filter if specified
        if (typeFilter) {
          results = results.filter((r: any) => r.type === typeFilter);
        }
      }
    } catch (error) {
      console.error("Search error:", error);
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "summary":
        return <FileText className="w-4 h-4" />;
      case "architecture":
        return <Building2 className="w-4 h-4" />;
      case "workflow":
        return <GitBranch className="w-4 h-4" />;
      case "api":
        return <Code className="w-4 h-4" />;
      case "changes":
      case "changelog":
        return <Clock className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "summary":
        return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20";
      case "architecture":
        return "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20";
      case "workflow":
        return "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20";
      case "api":
        return "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20";
      case "changes":
      case "changelog":
        return "text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-900/20";
      default:
        return "text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20";
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <Search className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Search Results
              </h1>
            </div>

            {query && (
              <p className="text-gray-600 dark:text-gray-400">
                Showing results for{" "}
                <span className="font-semibold">&quot;{query}&quot;</span>
                {typeFilter && (
                  <span className="ml-2">
                    in <span className="font-semibold">{typeFilter}</span>
                  </span>
                )}
                {repoFilter && (
                  <span className="ml-2">
                    from <span className="font-semibold">{repoFilter}</span>
                  </span>
                )}
              </p>
            )}
          </div>

          {/* Filters */}
          <div className="mb-6 flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <Filter className="w-4 h-4" />
              <span>Filter by:</span>
            </div>

            {["summary", "architecture", "workflow", "api", "changes"].map(
              (type) => (
                <Link
                  key={type}
                  href={`/search?q=${query}${
                    type === typeFilter ? "" : `&type=${type}`
                  }${repoFilter ? `&repo=${repoFilter}` : ""}`}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    type === typeFilter
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  {type}
                </Link>
              ),
            )}

            {typeFilter && (
              <Link
                href={`/search?q=${query}${
                  repoFilter ? `&repo=${repoFilter}` : ""
                }`}
                className="px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Clear filter
              </Link>
            )}
          </div>

          {/* Results */}
          {!query || query.length <= 2 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Search className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Start searching
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Enter at least 3 characters to search across all documentation
              </p>
            </div>
          ) : results.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
              <FileText className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                No results found
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Try different keywords or check your spelling
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Found {results.length} result{results.length !== 1 ? "s" : ""}
              </p>

              {results.map((result) => (
                <Link
                  key={result.id}
                  href={`/repo/${result.repo_id}/${result.type}`}
                  className="block bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all"
                >
                  <div className="flex items-start gap-4">
                    {/* Type Icon */}
                    <div
                      className={`p-3 rounded-lg ${getTypeColor(result.type)}`}
                    >
                      {getTypeIcon(result.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {result.title}
                        </h3>
                        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 uppercase">
                          {result.type}
                        </span>
                      </div>

                      <p className="text-gray-600 dark:text-gray-400 mb-3 line-clamp-3">
                        {result.content.substring(0, 200)}...
                      </p>

                      <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3" />
                          {result.repo_id}
                        </span>
                        <span>•</span>
                        <span>{result.path}</span>
                        {result.created_at && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(result.created_at).toLocaleDateString()}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
