"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  X,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import apiClient from "@/lib/apiClient";

interface DocbookSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  onSuccess: (docbookRepo: string) => void;
  accessToken?: string | null;
}

export default function DocbookSetupModal({
  isOpen,
  onClose,
  orgId,
  onSuccess,
  accessToken,
}: DocbookSetupModalProps) {
  const [docbookRepoName, setDocbookRepoName] = useState(
    `DocIt-docbook-${orgId ? orgId.toLowerCase().replace(/[^a-z0-9-]/g, "") : ""}`,
  );

  // Update repo name when orgId changes
  useEffect(() => {
    if (orgId) {
      setDocbookRepoName(
        `DocIt-docbook-${orgId.toLowerCase().replace(/[^a-z0-9-]/g, "")}`,
      );
    }
  }, [orgId, isOpen]);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [polling, setPolling] = useState(false);
  const [pollingMessage, setPollingMessage] = useState("");
  const [checkingRepo, setCheckingRepo] = useState(false);
  const [repoDetected, setRepoDetected] = useState<boolean | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollAttemptsRef = useRef(0);
  const autoLinkAttemptedRef = useRef(false);
  const MAX_POLL_ATTEMPTS = 24; // 2 minutes at 5s interval

  const githubCreateRepoUrl = `https://github.com/new?name=${docbookRepoName}&private=true&description=DocIt%20Docbook%20Repository`;

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollAttemptsRef.current = 0;
    setPolling(false);
    setPollingMessage("");
  }, []);

  const linkRepo = useCallback(
    async (
      mode: "manual" | "auto" = "manual",
    ): Promise<"linked" | "not_found" | "failed"> => {
      const silent = mode === "auto";

      if (!docbookRepoName.trim()) {
        if (!silent) {
          setError("Please enter the docbook repository name");
        }
        return "failed";
      }

      if (!silent) {
        setLinking(true);
        setError("");
      }

      try {
        const token =
          accessToken ??
          (typeof window !== "undefined"
            ? localStorage.getItem("DocIt_access_token")
            : null);

        if (!token) {
          if (!silent) {
            setError("Authentication token not found. Please log in again.");
          }
          return "failed";
        }

        // Ensure apiClient has access to the latest token if provided explicitly
        if (typeof window !== "undefined" && accessToken) {
          try {
            localStorage.setItem("DocIt_access_token", accessToken);
          } catch {
            // Ignore storage errors; apiClient may still have a token
          }
        }

        await apiClient.post("/docbook/link-repo", {
          org_id: orgId,
          docbook_repo_name: docbookRepoName,
        });

        if (silent) {
          setRepoDetected(true);
          setPollingMessage("Repository detected! Linking now...");
        } else {
          setError("");
        }

        setSuccess(true);
        setTimeout(() => {
          onSuccess(docbookRepoName);
          onClose();
        }, 1500);

        return "linked";
      } catch (err: any) {
        const status = err?.response?.status;
        const detail =
          err?.response?.data?.detail ||
          (err instanceof Error ? err.message : undefined);

        if (status === 404) {
          if (!silent) {
            setError(
              detail ||
                "Repository not found on GitHub. Please create it before linking.",
            );
          }
          return "not_found";
        }

        if (!silent) {
          setError(detail || "Failed to link docbook repository");
        } else {
          console.error("Automatic docbook linking failed", err);
        }

        return "failed";
      } finally {
        if (!silent) {
          setLinking(false);
        }
      }
    },
    [apiBase, docbookRepoName, onClose, onSuccess, orgId],
  );

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;

    setPolling(true);
    setError("");
    setRepoDetected(null);
    setPollingMessage("Waiting for repository...");
    pollAttemptsRef.current = 0;
    autoLinkAttemptedRef.current = false;

    const poll = async () => {
      pollAttemptsRef.current += 1;
      const attempt = pollAttemptsRef.current;
      setPollingMessage(
        `Checking if repository exists... (attempt ${attempt}/${MAX_POLL_ATTEMPTS})`,
      );

      const result = await linkRepo("auto");

      if (result === "linked") {
        stopPolling();
        return;
      }

      if (result === "not_found") {
        setRepoDetected(false);
        setPollingMessage("");
      }

      if (attempt >= MAX_POLL_ATTEMPTS) {
        stopPolling();
        setError(
          "Repository not detected after 2 minutes. Please verify it was created and try refreshing.",
        );
      }
    };

    void poll();
    pollIntervalRef.current = setInterval(() => {
      void poll();
    }, 5000);
  }, [linkRepo, stopPolling, MAX_POLL_ATTEMPTS]);

  useEffect(() => {
    if (isOpen) {
      autoLinkAttemptedRef.current = false;
      setRepoDetected(null);
      setError("");
      setSuccess(false);
    } else {
      stopPolling();
      autoLinkAttemptedRef.current = false;
      setRepoDetected(null);
      setPollingMessage("");
      setCheckingRepo(false);
    }
  }, [isOpen, stopPolling]);

  useEffect(() => {
    return () => {
      stopPolling();
      autoLinkAttemptedRef.current = false;
    };
  }, [stopPolling]);

  const attemptAutoLink = useCallback(async () => {
    setError("");
    setCheckingRepo(true);
    setRepoDetected(null);
    setPollingMessage("Checking if repository exists...");

    const result = await linkRepo("auto");

    setCheckingRepo(false);

    if (result === "not_found") {
      setRepoDetected(false);
      setPollingMessage("");
    } else if (result === "failed") {
      setPollingMessage("");
    }
  }, [linkRepo]);

  useEffect(() => {
    if (!isOpen) {
      autoLinkAttemptedRef.current = false;
      return;
    }

    if (success || linking || polling || checkingRepo) {
      return;
    }

    if (autoLinkAttemptedRef.current) {
      return;
    }

    autoLinkAttemptedRef.current = true;
    void attemptAutoLink();
  }, [attemptAutoLink, checkingRepo, isOpen, linking, polling, success]);

  useEffect(() => {
    autoLinkAttemptedRef.current = false;
    setRepoDetected(null);
  }, [docbookRepoName, orgId]);

  const showStatusCard = useMemo(() => {
    if (success) return false;
    return Boolean(
      pollingMessage ||
      polling ||
      checkingRepo ||
      linking ||
      repoDetected === false,
    );
  }, [checkingRepo, linking, polling, pollingMessage, repoDetected, success]);

  const handleCreateRepoClick = useCallback(() => {
    startPolling();
    window.open(githubCreateRepoUrl, "_blank");
  }, [githubCreateRepoUrl, startPolling]);

  useEffect(() => {
    if (!isOpen) return;

    const handleVisibility = () => {
      if (document.visibilityState !== "visible") {
        return;
      }

      if (success) {
        return;
      }

      autoLinkAttemptedRef.current = false;
      void attemptAutoLink();
    };

    window.addEventListener("focus", handleVisibility);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.removeEventListener("focus", handleVisibility);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [attemptAutoLink, isOpen, success]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-3xl border border-white/10 bg-slate-900 text-slate-100 shadow-[0_30px_120px_rgba(15,23,42,0.65)]">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-400" />
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10 bg-slate-900/80 backdrop-blur">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-400">
              Docbook Setup
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-white">
              Link your documentation repository
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-white/10 bg-white/5 p-2 text-slate-300 transition hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {success ? (
          <div className="px-8 py-14 text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/20">
              <CheckCircle className="h-10 w-10 text-emerald-400" />
            </div>
            <h3 className="mt-6 text-2xl font-semibold text-white">
              Docbook linked successfully
            </h3>
            <p className="mt-3 text-sm text-slate-300">
              Your documentation repository is connected. You’ll start seeing
              docs flow in as soon as we generate them.
            </p>
          </div>
        ) : (
          <div className="px-8 py-10 space-y-8">
            <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 shadow-inner shadow-slate-900/40">
              <header className="flex items-start justify-between gap-4">
                <div>
                  <span className="inline-flex items-center rounded-full bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-blue-200">
                    Step • Link
                  </span>
                  <h3 className="mt-3 text-lg font-semibold text-white">
                    Automatic linking status
                  </h3>
                  <p className="mt-1 text-sm text-slate-300">
                    We’ll sync the GitHub repo for you. If it already exists
                    under your org, the link will complete automatically.
                  </p>
                </div>
              </header>

              {showStatusCard ? (
                <div className="mt-5 rounded-xl border border-blue-400/20 bg-blue-500/10 p-5 text-sm text-blue-100">
                  {(polling || checkingRepo || linking) && (
                    <div className="mb-3 flex items-center gap-3 text-blue-100">
                      <Loader2 className="h-4 w-4 animate-spin text-blue-200" />
                      <span>Working on it…</span>
                    </div>
                  )}
                  <p>
                    {pollingMessage ||
                      (repoDetected === false
                        ? "Repository not detected yet. Create it on GitHub, then refresh the status."
                        : "Waiting for repository status…")}
                  </p>
                </div>
              ) : null}

              {error && (
                <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
                  {error}
                </div>
              )}

              {!polling && !checkingRepo && repoDetected === false && (
                <div className="mt-4 rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-100">
                  Repository not detected yet. Create it on GitHub, then use
                  “Refresh status.”
                </div>
              )}

              <div className="mt-6 flex flex-col gap-3 md:flex-row">
                <button
                  onClick={handleCreateRepoClick}
                  disabled={polling}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-500 via-cyan-500 to-teal-400 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 transition hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {polling ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Checking for repository…
                    </>
                  ) : (
                    <>
                      <ExternalLink className="h-4 w-4" />
                      Create on GitHub
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    autoLinkAttemptedRef.current = false;
                    void attemptAutoLink();
                  }}
                  disabled={checkingRepo || linking || polling}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/25 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {checkingRepo ? "Checking…" : "Refresh status"}
                </button>
              </div>

              {pollingMessage && (
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-blue-400/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-100">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-200" />
                  <span>{pollingMessage}</span>
                </div>
              )}

              {polling && (
                <button
                  onClick={stopPolling}
                  className="mt-3 inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-white transition hover:bg-white/10"
                >
                  Cancel polling
                </button>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
