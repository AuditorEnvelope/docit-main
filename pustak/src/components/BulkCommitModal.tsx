"use client";

import { useState, useEffect } from "react";
import { Loader2, X } from "lucide-react";
import { useEditorSession } from "@/contexts/EditorSessionContext";
import { useProjectStructure } from "@/contexts/ProjectStructureContext";
import { useDocbookAPI } from "@/hooks/useDocbookAPI";

interface BulkCommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  repoId: string;
  persona: string;
}

export function BulkCommitModal({
  isOpen,
  onClose,
  orgId,
  repoId,
  persona,
}: BulkCommitModalProps) {
  const { getDirtyFiles, markFileSaved } = useEditorSession();
  const { structure, markAllClean } = useProjectStructure();
  const { bulkSave } = useDocbookAPI();
  const [commitMessage, setCommitMessage] = useState("");
  const [isCommitting, setIsCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirtyFiles = getDirtyFiles();

  useEffect(() => {
    if (isOpen && dirtyFiles.length > 0) {
      const fileNames = dirtyFiles.map((f) => f.name).join(", ");
      const dateTime = new Date().toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
      setCommitMessage(`Update: ${fileNames} - ${dateTime}`);
      setError(null);
    }
  }, [isOpen, dirtyFiles]);

  if (!isOpen) return null;

  const handleCommit = async () => {
    if (!commitMessage.trim() || dirtyFiles.length === 0) return;

    setIsCommitting(true);
    setError(null);

    try {
      // Files already have full paths like "repoId/docs/persona/file.md"
      // Backend expects the same format
      const filesToSave = dirtyFiles.map((file) => ({
        path: file.path,
        content: file.content,
      }));

      await bulkSave({
        orgId,
        repoId,
        persona,
        files: filesToSave,
        commitMessage: commitMessage.trim(),
        branch: "staging",
      });

      // Mark all files as clean in structure context
      markAllClean();
      
      // Mark files as saved in session
      dirtyFiles.forEach((file) => {
        markFileSaved(file.id);
      });

      onClose();
      setCommitMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to commit changes");
    } finally {
      setIsCommitting(false);
    }
  };

  const handleClose = () => {
    if (!isCommitting) {
      onClose();
      setCommitMessage("");
      setError(null);
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
            You have unsaved changes in {dirtyFiles.length} file{dirtyFiles.length !== 1 ? "s" : ""}:
          </p>

          <div className="mb-4 space-y-2 max-h-32 overflow-y-auto">
            {dirtyFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 rounded-lg bg-slate-800/50 px-3 py-2 text-xs"
              >
                <span className="text-slate-300">{file.name}</span>
                <span className="text-slate-500">({file.path})</span>
              </div>
            ))}
          </div>

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
              disabled={isCommitting}
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
            disabled={isCommitting}
            className="text-sm text-slate-400 transition hover:text-slate-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleCommit}
            disabled={isCommitting || !commitMessage.trim() || dirtyFiles.length === 0}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-500/90 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCommitting ? (
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

