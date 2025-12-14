"use client";

import { useState } from "react";
import { X, GitCommit, Loader2 } from "lucide-react";

interface CommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCommit: (message: string, branch?: string) => Promise<void>;
  defaultBranch?: string;
  isLoading?: boolean;
}

export function CommitModal({
  isOpen,
  onClose,
  onCommit,
  defaultBranch,
  isLoading = false,
}: CommitModalProps) {
  const [commitMessage, setCommitMessage] = useState("");
  const [branch, setBranch] = useState(defaultBranch || "staging");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!commitMessage.trim()) {
      setError("Commit message is required");
      return;
    }

    try {
      await onCommit(commitMessage.trim(), branch);
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
        className="relative w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-blue-500/10 p-2">
              <GitCommit className="h-5 w-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-white">Commit Changes</h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="commit-message"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Commit Message <span className="text-red-400">*</span>
            </label>
            <textarea
              id="commit-message"
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="e.g., Updated API documentation"
              disabled={isLoading}
              className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
              rows={3}
              required
            />
          </div>

          <div>
            <label
              htmlFor="branch"
              className="mb-2 block text-sm font-medium text-slate-300"
            >
              Branch
            </label>
            <input
              id="branch"
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
              placeholder="staging"
            />
            <p className="mt-1.5 text-xs text-slate-400">
              Changes will be committed to this branch
            </p>
          </div>

          {error && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="flex-1 rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-slate-600 hover:bg-slate-800 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !commitMessage.trim()}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-500/90 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/35 transition hover:bg-blue-500 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Committing...</span>
                </>
              ) : (
                <>
                  <GitCommit className="h-4 w-4" />
                  <span>Commit Changes</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

