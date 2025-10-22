"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Search, FileText, Code, Building2, GitBranch, Clock, X, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { searchDocs, type SearchResult } from "@/lib/api";

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export function GlobalSearch({ isOpen, onClose }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Search with debouncing
  useEffect(() => {
    let isCancelled = false;

    async function performSearch() {
      if (query.length <= 2) {
        setResults([]);
        setIsSearching(false);
        return;
      }

      setIsSearching(true);

      try {
        const searchResults = await searchDocs(query);
        
        if (!isCancelled) {
          setResults(searchResults);
          setSelectedIndex(0);
          setIsSearching(false);
        }
      } catch (error) {
        console.error("Search error:", error);
        if (!isCancelled) {
          setResults([]);
          setIsSearching(false);
        }
      }
    }

    const debounceTimer = setTimeout(performSearch, 300);

    return () => {
      isCancelled = true;
      clearTimeout(debounceTimer);
    };
  }, [query]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && results[selectedIndex]) {
        e.preventDefault();
        navigateToResult(results[selectedIndex]);
      }
    },
    [results, selectedIndex, onClose]
  );

  const navigateToResult = (result: SearchResult) => {
    // Navigate based on result type
    const repoName = result.repo_id;
    const docType = result.type;
    
    router.push(`/repo/${repoName}/${docType}`);
    onClose();
  };

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

  const highlightMatch = (text: string, query: string) => {
    if (!query) return text;
    
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() ? 
        <mark key={i} className="bg-yellow-200 dark:bg-yellow-900/50 text-gray-900 dark:text-gray-100 px-0.5 rounded">
          {part}
        </mark> : part
    );
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl animate-in zoom-in-95 duration-200">
          {/* Search Input */}
          <div className="flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700">
            <Search className="w-5 h-5 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search documentation... (type at least 3 characters)"
              className="flex-1 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 text-lg"
            />
            {isSearching && <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />}
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-[60vh] overflow-y-auto">
            {query.length > 0 && query.length <= 2 && (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                Type at least 3 characters to search...
              </div>
            )}

            {query.length > 2 && results.length === 0 && !isSearching && (
              <div className="p-8 text-center">
                <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400">
                  No results found for &quot;{query}&quot;
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                  Try different keywords or check your spelling
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div className="py-2">
                {results.map((result, index) => (
                  <button
                    key={result.id}
                    onClick={() => navigateToResult(result)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`w-full text-left px-4 py-3 flex items-start gap-3 transition-colors ${
                      index === selectedIndex
                        ? "bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500"
                        : "hover:bg-gray-50 dark:hover:bg-gray-700/50 border-l-2 border-transparent"
                    }`}
                  >
                    {/* Type Icon */}
                    <div className={`p-2 rounded ${getTypeColor(result.type)}`}>
                      {getTypeIcon(result.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                          {highlightMatch(result.title, query)}
                        </h3>
                        <span className="text-xs text-gray-400 dark:text-gray-500 uppercase">
                          {result.type}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {highlightMatch(result.content.substring(0, 150), query)}...
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {result.repo_id}
                        </span>
                        <span className="text-xs text-gray-400">•</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {result.path}
                        </span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600">
                  ↑↓
                </kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600">
                  ↵
                </kbd>
                Select
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600">
                  ESC
                </kbd>
                Close
              </span>
            </div>
            <span>{results.length} results</span>
          </div>
        </div>
      </div>
    </>
  );
}
