"use client";

import { useState, useEffect, useRef } from "react";
import { Search, FileText, X, Clock, Hash } from "lucide-react";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SearchResult {
  id: string;
  title: string;
  content: string;
  type:
    | "summary"
    | "architecture"
    | "workflow"
    | "api"
    | "changes"
    | "changelog";
  repo: string;
  lastUpdated: string;
}

export function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Mock search results
  const mockResults: SearchResult[] = [
    {
      id: "1",
      title: "Authentication System",
      content: "OAuth2 authentication with JWT tokens...",
      type: "api",
      repo: "hivemind-poc",
      lastUpdated: "2024-01-15T10:30:00Z",
    },
    {
      id: "2",
      title: "System Architecture",
      content: "Microservices architecture with Redis...",
      type: "architecture",
      repo: "hivemind-poc",
      lastUpdated: "2024-01-15T09:15:00Z",
    },
    {
      id: "3",
      title: "Recent Changes",
      content: "Added new authentication features...",
      type: "changes",
      repo: "doc-ai",
      lastUpdated: "2024-01-15T08:45:00Z",
    },
  ];

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (query.length > 2) {
      // Simulate search - in real app, this would be an API call
      const filtered = mockResults.filter(
        (result) =>
          result.title.toLowerCase().includes(query.toLowerCase()) ||
          result.content.toLowerCase().includes(query.toLowerCase()) ||
          result.repo.toLowerCase().includes(query.toLowerCase())
      );
      setResults(filtered);
      setSelectedIndex(0);
    } else {
      setResults([]);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      // Navigate to selected result
      window.location.href = `/repo/${results[selectedIndex].repo}/${results[selectedIndex].type}`;
      onClose();
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "summary":
        return <FileText className="w-4 h-4" />;
      case "architecture":
        return <Hash className="w-4 h-4" />;
      case "workflow":
        return <Clock className="w-4 h-4" />;
      case "api":
        return <Hash className="w-4 h-4" />;
      case "changes":
        return <Clock className="w-4 h-4" />;
      case "changelog":
        return <Clock className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "summary":
        return "text-green-600 dark:text-green-400";
      case "architecture":
        return "text-blue-600 dark:text-blue-400";
      case "workflow":
        return "text-purple-600 dark:text-purple-400";
      case "api":
        return "text-orange-600 dark:text-orange-400";
      case "changes":
        return "text-yellow-600 dark:text-yellow-400";
      case "changelog":
        return "text-gray-600 dark:text-gray-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-start justify-center min-h-screen pt-16 px-4">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-96">
          {/* Search input */}
          <div className="flex items-center p-4 border-b border-gray-200 dark:border-gray-700">
            <Search className="w-5 h-5 text-gray-400 mr-3" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Search documentation..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 outline-none"
            />
            <button
              onClick={onClose}
              className="ml-3 p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto">
            {query.length === 0 && (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>Start typing to search documentation...</p>
              </div>
            )}

            {query.length > 0 && query.length <= 2 && (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <p>Type at least 3 characters to search</p>
              </div>
            )}

            {query.length > 2 && results.length === 0 && (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <p>No results found for "{query}"</p>
              </div>
            )}

            {results.map((result, index) => (
              <a
                key={result.id}
                href={`/repo/${result.repo}/${result.type}`}
                onClick={onClose}
                className={`flex items-start p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                  index === selectedIndex ? "bg-gray-50 dark:bg-gray-800" : ""
                }`}
              >
                <div className={`mr-3 ${getTypeColor(result.type)}`}>
                  {getTypeIcon(result.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {result.title}
                    </h3>
                    <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-1 rounded">
                      {result.repo}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                    {result.content}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Updated {new Date(result.lastUpdated).toLocaleDateString()}
                  </p>
                </div>
              </a>
            ))}
          </div>

          {/* Footer */}
          {results.length > 0 && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center space-x-4">
                  <span>↑↓ Navigate</span>
                  <span>↵ Select</span>
                  <span>Esc Close</span>
                </div>
                <span>
                  {results.length} result{results.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
