"use client";

import { useState } from "react";
import { Globe, Loader2, CheckCircle, AlertCircle, ExternalLink } from "lucide-react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface PublishToLiveButtonProps {
  repoFullName: string;
  orgId: string;
  repoId: string;
  hasPublished?: boolean;
  lastPublishedAt?: string | null;
  onPublishComplete?: () => void;
  fullWidth?: boolean;
  disabled?: boolean;
}

export function PublishToLiveButton({
  repoFullName,
  orgId,
  repoId,
  hasPublished = false,
  lastPublishedAt,
  onPublishComplete,
  fullWidth = false,
  disabled = false,
}: PublishToLiveButtonProps) {
  const [publishing, setPublishing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [status, setStatus] = useState<{
    type: "success" | "error" | null;
    message: string;
    liveUrl?: string;
  }>({ type: null, message: "" });

  const apiBase = BACKEND_URL.endsWith("/api/v1")
    ? BACKEND_URL
    : `${BACKEND_URL.replace(/\/$/, "")}/api/v1`;

  const handlePublish = async () => {
    const token = localStorage.getItem("pustak_access_token");
    if (!token) {
      setStatus({
        type: "error",
        message: "Not authenticated. Please log in again.",
      });
      return;
    }

    setPublishing(true);
    setShowConfirm(false);
    setStatus({ type: null, message: "" });

    try {
      const response = await fetch(`${apiBase}/docbook/publish-live`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: orgId,
          repo_id: repoId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to publish");
      }

      const data = await response.json();

      setStatus({
        type: "success",
        message: data.message,
        liveUrl: data.live_url,
      });

      if (onPublishComplete) {
        onPublishComplete();
      }
    } catch (error) {
      console.error("Error publishing:", error);
      setStatus({
        type: "error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to publish documentation",
      });
    } finally {
      setPublishing(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "Never";
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        disabled={publishing || disabled}
        className={`${fullWidth ? "w-full" : ""} group relative inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-xs font-semibold transition-all overflow-hidden bg-amber-500/15 text-amber-300 border border-amber-500/25 hover:bg-amber-500/25 hover:border-amber-500/40 hover:shadow-lg hover:shadow-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer`}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-amber-400/0 via-amber-400/10 to-amber-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
        {publishing ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin relative z-10" />
            <span className="relative z-10">Publishing...</span>
          </>
        ) : hasPublished ? (
          <>
            <Globe className="h-3.5 w-3.5 relative z-10" />
            <span className="relative z-10">Republish Live</span>
          </>
        ) : (
          <>
            <Globe className="h-3.5 w-3.5 relative z-10" />
            <span className="relative z-10">Publish to Live</span>
          </>
        )}
      </button>

      {hasPublished && lastPublishedAt && (
        <p className="text-xs text-slate-400 mt-1">
          Last published: {formatDate(lastPublishedAt)}
        </p>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-xl font-semibold text-white mb-3">
              {hasPublished ? "Republish" : "Publish"} to Live?
            </h3>
            <p className="text-slate-300 text-sm mb-4">
              {hasPublished
                ? `This will update the live documentation at https://${orgId}.docbook.site/${repoId} with the latest approved changes from the main branch.`
                : `This will make your documentation publicly accessible at https://${orgId}.docbook.site/${repoId}. Make sure all pending reviews are approved.`}
            </p>

            <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-3 mb-4">
              <p className="text-xs text-blue-200">
                <strong>Note:</strong> Only approved changes from the{" "}
                <code className="bg-blue-800/50 px-1 py-0.5 rounded">main</code>{" "}
                branch will be published. Pending reviews must be approved
                first.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="flex-1 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:shadow-lg"
              >
                {hasPublished ? "Republish" : "Publish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status Toast */}
      {status.type && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md animate-slide-up">
          <div
            className={`rounded-xl border p-4 shadow-xl ${
              status.type === "success"
                ? "border-emerald-400/40 bg-emerald-900/90 text-emerald-100"
                : "border-rose-400/40 bg-rose-900/90 text-rose-100"
            }`}
          >
            <div className="flex items-start gap-3">
              {status.type === "success" ? (
                <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p className="font-semibold text-sm">{status.message}</p>
                {status.liveUrl && (
                  <a
                    href={status.liveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-xs underline hover:no-underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    View live docs
                  </a>
                )}
              </div>
              <button
                onClick={() => setStatus({ type: null, message: "" })}
                className="text-current opacity-70 hover:opacity-100"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
