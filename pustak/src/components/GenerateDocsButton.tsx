"use client";

import { useState, useEffect } from "react";
import { Zap, CheckCircle, AlertCircle, Loader2, RefreshCw } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

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
  docPersona: propDocPersona = "internal",
  onGenerationStart,
  onGenerationComplete,
  disabled = false,
  disabledReason,
  fullWidth = false,
}: GenerateDocsButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [docPersona, setDocPersona] = useState<string>(propDocPersona);
  const [isLoadingPersona, setIsLoadingPersona] = useState(false);
  const { token } = useAuth();
  
  // Fetch the current doc_persona from the backend
  useEffect(() => {
    const fetchDocPersona = async () => {
      if (!token || !repoFullName) return;
      
      setIsLoadingPersona(true);
      try {
        const apiBase = BACKEND_URL.endsWith("/api/v1") 
          ? BACKEND_URL 
          : `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;
          
        const response = await fetch(
          `${apiBase}/repositories/${encodeURIComponent(repoFullName)}/doc-persona`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          console.log(`📋 Fetched doc_persona for ${repoFullName}:`, data.doc_persona);
          setDocPersona(data.doc_persona || propDocPersona);
        }
      } catch (err) {
        console.error("Error fetching doc_persona:", err);
        // Fall back to prop value
        setDocPersona(propDocPersona);
      } finally {
        setIsLoadingPersona(false);
      }
    };

    fetchDocPersona();
  }, [repoFullName, token, propDocPersona]);

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

      console.log(`🚀 Generating docs for ${repoFullName} with persona: ${docPersona}`);
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
      className={`group relative flex cursor-pointer items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-xs font-semibold transition-all overflow-hidden ${
        fullWidth ? "w-full" : ""
      } bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 hover:bg-emerald-500/25 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/0 via-emerald-400/10 to-emerald-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
      {hasDocsFolder ? (
        <>
          <RefreshCw className="w-3.5 h-3.5 relative z-10" />
          <span className="relative z-10">Regenerate Docs</span>
        </>
      ) : (
        <>
          <Zap className="w-3.5 h-3.5 relative z-10" />
          <span className="relative z-10">Generate Docs</span>
        </>
      )}
    </button>
  );
}
