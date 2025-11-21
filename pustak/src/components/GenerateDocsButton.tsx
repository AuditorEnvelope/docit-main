"use client";

import { useState } from "react";
import { Zap, CheckCircle, AlertCircle, Loader2, RefreshCw } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";

interface GenerateDocsButtonProps {
  repoName: string;
  repoFullName: string;
  hasDocsFolder: boolean;
  docPersona?: string;
  onGenerationStart?: () => void;
  onGenerationComplete?: () => void;
  disabled?: boolean;
  disabledReason?: string;
  fullWidth?: boolean;
}

export function GenerateDocsButton({
  repoName,
  repoFullName,
  hasDocsFolder,
  docPersona = "internal",
  onGenerationStart,
  onGenerationComplete,
  disabled = false,
  disabledReason,
  fullWidth = false,
}: GenerateDocsButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const { token } = useAuth();

  const handleGenerate = async () => {
    if (disabled) {
      return;
    }

    if (!token) {
      setError("Authentication required to generate docs");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setSuccess(false);

    try {
      onGenerationStart?.();

      const response = await fetch("/api/generate-docs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          repoName: repoFullName,
          repoShortName: repoName,
          docPersona,
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

  if (disabled) {
    return (
      <div
        className={`flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300 ${
          fullWidth ? "w-full" : ""
        }`}
      >
        <button
          type="button"
          disabled
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600 text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 cursor-not-allowed ${
            fullWidth ? "w-full justify-center" : ""
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>Generate Docs</span>
        </button>
        {disabledReason && <span className="leading-snug">{disabledReason}</span>}
      </div>
    );
  }

  if (isGenerating) {
    return (
      <div
        className={`flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-700 rounded-md text-sm text-blue-700 dark:text-blue-300 ${
          fullWidth ? "w-full justify-center" : ""
        }`}
      >
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Generating...</span>
      </div>
    );
  }

  if (success) {
    return (
      <div
        className={`flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 rounded-md text-sm text-green-700 dark:text-green-300 ${
          fullWidth ? "w-full justify-center" : ""
        }`}
      >
        <CheckCircle className="w-4 h-4" />
        <span>Docs Generated!</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`flex items-center space-x-2 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-md text-sm text-red-700 dark:text-red-300 ${
          fullWidth ? "w-full justify-center" : ""
        }`}
      >
        <AlertCircle className="w-4 h-4" />
        <span>{error}</span>
        <button
          type="button"
          onClick={() => setError(null)}
          className="ml-2 text-xs underline"
        >
          Dismiss
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={handleGenerate}
      disabled={isGenerating}
      className={`flex cursor-pointer items-center space-x-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        fullWidth ? "w-full justify-center" : ""
      } ${
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
