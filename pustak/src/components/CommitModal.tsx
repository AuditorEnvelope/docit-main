"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

interface CommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCommit: (message: string, branch?: string) => Promise<void>;
  pageTitle?: string;
  isLoading?: boolean;
}

export function CommitModal({
  isOpen,
  onClose,
  onCommit,
  pageTitle = "Documentation",
  isLoading = false,
}: CommitModalProps) {
  const [commitMessage, setCommitMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Auto-fill commit message when modal opens
  useEffect(() => {
    if (isOpen) {
      const now = new Date();
      const dateTime = now.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
      setCommitMessage(`Update: ${pageTitle} - ${dateTime}`);
      setError(null);
    }
  }, [isOpen, pageTitle]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!commitMessage.trim()) {
      setError("Commit message is required");
      return;
    }

    try {
      // Always commit to staging branch
      await onCommit(commitMessage.trim(), "staging");
      setCommitMessage("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to commit changes");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setCommitMessage("");
      setError(null);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-md rounded-lg border border-slate-800 bg-slate-900/95 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-white">Save Changes</h2>
        </div>

        {/* Body */}
        <div className="mb-6">
          <p className="text-sm text-slate-300 mb-4">
            Your changes will be saved to the staging environment.
          </p>

          <div>
            <label
              htmlFor="commit-message"
              className="mb-1.5 block text-xs font-medium text-slate-400"
            >
              Commit Message
            </label>
            <textarea
              id="commit-message"
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-xs text-slate-300 placeholder:text-slate-500 focus:border-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-600 disabled:opacity-50"
              rows={2}
              required
            />
          </div>

          {error && (
            <div className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-4">
          <button
            type="button"
            onClick={handleClose}
            disabled={isLoading}
            className="text-sm text-slate-400 transition hover:text-slate-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={isLoading || !commitMessage.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-500/90 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <span>Save to Staging</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

