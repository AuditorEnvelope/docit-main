"use client";

import { useState } from "react";
import { Zap, CheckCircle, AlertCircle, Loader2, RefreshCw } from "lucide-react";

interface GenerateDocsButtonProps {
  repoName: string;
  repoFullName: string;
  hasDocsFolder: boolean;
  onGenerationStart?: () => void;
  onGenerationComplete?: () => void;
}

export function GenerateDocsButton({
  repoName,
  repoFullName,
  hasDocsFolder,
  onGenerationStart,
  onGenerationComplete,
}: GenerateDocsButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setSuccess(false);

    try {
      onGenerationStart?.();

      const response = await fetch("/api/generate-docs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          repoName: repoFullName,
          repoShortName: repoName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to generate docs");
      }

      setSuccess(true);
      onGenerationComplete?.();

      // Reset success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsGenerating(false);
    }
  };

  if (isGenerating) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700 rounded-md text-sm text-blue-700 dark:text-blue-300">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Generating...</span>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 rounded-md text-sm text-green-700 dark:text-green-300">
        <CheckCircle className="w-4 h-4" />
        <span>Docs Generated!</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-md text-sm text-red-700 dark:text-red-300">
        <AlertCircle className="w-4 h-4" />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <button
      onClick={handleGenerate}
      disabled={isGenerating}
      className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        hasDocsFolder
          ? "bg-purple-50 dark:bg-purple-900/20 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/40"
          : "bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {hasDocsFolder ? (
        <>
          <RefreshCw className="w-4 h-4" />
          <span>Regenerate Docs</span>
        </>
      ) : (
        <>
          <Zap className="w-4 h-4" />
          <span>Generate Docs</span>
        </>
      )}
    </button>
  );
}
