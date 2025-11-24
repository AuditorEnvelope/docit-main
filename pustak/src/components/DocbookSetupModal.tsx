"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { X, ExternalLink, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface DocbookSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  onSuccess: (docbookRepo: string) => void;
}

export default function DocbookSetupModal({
  isOpen,
  onClose,
  orgId,
  onSuccess,
}: DocbookSetupModalProps) {
  const [step, setStep] = useState<"create" | "link">("create");
  const [docbookRepoName, setDocbookRepoName] = useState(
    `pustak-docbook-${orgId ? orgId.toLowerCase().replace(/[^a-z0-9-]/g, "") : ""}`
  );

  // Update repo name when orgId changes
  useEffect(() => {
    if (orgId) {
      setDocbookRepoName(
        `pustak-docbook-${orgId.toLowerCase().replace(/[^a-z0-9-]/g, "")}`
      );
    }
  }, [orgId, isOpen]);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [polling, setPolling] = useState(false);
  const [pollingMessage, setPollingMessage] = useState("");
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 24; // 2 minutes at 5s interval

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const apiBase = BACKEND_URL.endsWith("/api/v1")
    ? BACKEND_URL
    : `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

  const githubCreateRepoUrl = `https://github.com/new?name=${docbookRepoName}&private=true&description=Pustak%20Docbook%20Repository`;

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
    setPolling(false);
    setPollingMessage("");
  }, []);

  const checkRepoExists = useCallback(async (): Promise<boolean> => {
    try {
      const token = localStorage.getItem("pustak_access_token");
      if (!token) return false;

      const response = await fetch(
        `https://api.github.com/repos/${orgId}/${docbookRepoName}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
          },
        }
      );

      return response.ok;
    } catch (err) {
      console.error("Error checking repo existence:", err);
      return false;
    }
  }, [orgId, docbookRepoName]);

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;

    setPolling(true);
    setError("");
    pollAttemptsRef.current = 0;

    const poll = async () => {
      pollAttemptsRef.current += 1;
      const attempt = pollAttemptsRef.current;
      setPollingMessage(
        `Checking if repository exists... (attempt ${attempt}/${MAX_POLL_ATTEMPTS})`
      );

      const exists = await checkRepoExists();

      if (exists) {
        stopPolling();
        setPollingMessage("Repository detected! Linking now...");
        await handleLinkRepo();
        return;
      }

      if (attempt >= MAX_POLL_ATTEMPTS) {
        stopPolling();
        setError(
          "Repository not detected after 2 minutes. Please verify it was created and try linking manually."
        );
      }
    };

    void poll();
    pollIntervalRef.current = setInterval(() => {
      void poll();
    }, 5000);
  }, [checkRepoExists, stopPolling, MAX_POLL_ATTEMPTS]);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  const handleLinkRepo = async () => {
    if (!docbookRepoName.trim()) {
      setError("Please enter the docbook repository name");
      return;
    }

    setLinking(true);
    setError("");

    try {
      const token = localStorage.getItem("pustak_access_token");
      if (!token) {
        setError("Authentication token not found. Please log in again.");
        return;
      }
      const response = await fetch(`${apiBase}/docbook/link-repo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: orgId,
          docbook_repo_name: docbookRepoName,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to link docbook repository");
      }

      setSuccess(true);
      setTimeout(() => {
        onSuccess(docbookRepoName);
        onClose();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLinking(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            📚 Setup Docbook Repository
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {success ? (
            <div className="text-center py-8">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                ✅ Docbook Linked Successfully!
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Your documentation repository is now connected and ready to use.
              </p>
            </div>
          ) : (
            <>
              {/* Step Indicator */}
              <div className="flex gap-4 mb-8">
                <button
                  onClick={() => setStep("create")}
                  className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-colors ${
                    step === "create"
                      ? "bg-blue-500 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  Step 1: Create Repo
                </button>
                <button
                  onClick={() => setStep("link")}
                  className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-colors ${
                    step === "link"
                      ? "bg-blue-500 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  Step 2: Link Repo
                </button>
              </div>

              {/* Step 1: Create Repository */}
              {step === "create" && (
                <div className="space-y-4">
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      📝 Repository Name
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      We recommend naming your repository:
                    </p>
                    <code className="block bg-gray-100 dark:bg-gray-700 p-3 rounded text-sm text-gray-900 dark:text-white mb-3">
                      {docbookRepoName}
                    </code>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      This includes your organization ID to avoid naming conflicts.
                    </p>
                  </div>

                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      ✅ Repository Settings
                    </h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <li>✓ Visibility: Private (recommended)</li>
                      <li>✓ Description: Auto-filled</li>
                      <li>✓ Initialize with README: Yes</li>
                    </ul>
                  </div>

                  <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                      📚 Repository Structure
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Your docbook will be organized like this:
                    </p>
                    <pre className="bg-gray-100 dark:bg-gray-700 p-3 rounded text-xs text-gray-900 dark:text-white overflow-x-auto">
{`pustak-docbook-{org}/
├── repo-a/
│   ├── internal/
│   │   ├── README.md
│   │   ├── architecture/
│   │   └── workflow/
│   └── developer/
│       ├── README.md
│       └── api.md
└── repo-b/
    └── ...`}
                    </pre>
                  </div>

                  <button
                    onClick={() => {
                      window.open(githubCreateRepoUrl, "_blank");
                      startPolling();
                    }}
                    disabled={polling}
                    className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {polling ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Waiting for repository...
                      </>
                    ) : (
                      <>
                        <ExternalLink className="w-4 h-4" />
                        Create Repository on GitHub
                      </>
                    )}
                  </button>

                  {polling && pollingMessage && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-blue-400" />
                      <p className="text-sm text-blue-600 dark:text-blue-400">
                        {pollingMessage}
                      </p>
                    </div>
                  )}

                  {polling && (
                    <button
                      onClick={stopPolling}
                      className="w-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-semibold py-3 px-4 rounded-lg transition-colors"
                    >
                      Cancel polling
                    </button>
                  )}

                  <button
                    onClick={() => {
                      stopPolling();
                      setStep("link");
                    }}
                    disabled={polling}
                    className="w-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 disabled:bg-gray-400 text-gray-900 dark:text-white font-semibold py-3 px-4 rounded-lg transition-colors"
                  >
                    Next: Link Repository
                  </button>
                </div>
              )}

              {/* Step 2: Link Repository */}
              {step === "link" && (
                <div className="space-y-4">
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                        Make sure you've created the repository first!
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Click "Create Repository on GitHub" in Step 1 if you haven't already.
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      Repository Name
                    </label>
                    <input
                      type="text"
                      value={docbookRepoName}
                      onChange={(e) => setDocbookRepoName(e.target.value)}
                      placeholder="pustak-docbook-your-org"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      Enter the exact name of the repository you created on GitHub
                    </p>
                  </div>

                  {error && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                      <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                    </div>
                  )}

                  <button
                    onClick={handleLinkRepo}
                    disabled={linking}
                    className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
                  >
                    {linking ? "Linking..." : "Link Repository"}
                  </button>

                  <button
                    onClick={() => setStep("create")}
                    className="w-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-semibold py-3 px-4 rounded-lg transition-colors"
                  >
                    Back to Step 1
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
