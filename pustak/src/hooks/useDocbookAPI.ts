"use client";

import { useCallback } from "react";
import { FileNode } from "@/contexts/ProjectStructureContext";

// Helper: Remove repo name from file paths
// Paths come in as: "repoId/docs/persona/file.md"
// Backend expects: "docs/persona/file.md"
function normalizeFilePath(filePath: string, repoId?: string): string {
  if (!filePath) return "";
  
  // If path starts with repoId, remove it
  if (repoId && filePath.startsWith(repoId + "/")) {
    return filePath.slice(repoId.length + 1);
  }
  
  // If path starts with "repoId/" pattern but we don't have repoId,
  // try to detect and remove first segment
  const segments = filePath.split("/");
  if (segments.length > 1 && segments[0] && !segments[0].startsWith("docs")) {
    // First segment is likely the repo name, remove it
    return segments.slice(1).join("/");
  }
  
  return filePath;
}

interface CreatePageRequest {
  orgId: string;
  repoId: string;
  persona: string;
  parentPath: string;
  fileName: string;
  content?: string;
}

interface DeletePageRequest {
  orgId: string;
  repoId: string;
  persona: string;
  filePath: string;
}

interface RenamePageRequest {
  orgId: string;
  repoId: string;
  persona: string;
  oldPath: string;
  newPath: string;
}

interface UpdateStructureRequest {
  orgId: string;
  repoId: string;
  persona: string;
  structure: FileNode[];
}

interface BulkSaveRequest {
  orgId: string;
  repoId: string;
  persona: string;
  files: Array<{
    path: string;
    content: string;
  }>;
  commitMessage: string;
  branch?: string;
}

export function useDocbookAPI() {
  const getToken = useCallback(() => {
    return localStorage.getItem("pustak_access_token");
  }, []);

  const createPage = useCallback(
    async (request: CreatePageRequest): Promise<FileNode> => {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const response = await fetch("/api/docbook/create-page", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: request.orgId,
          repo_id: request.repoId,
          persona: request.persona,
          parent_path: request.parentPath,
          fileName: request.fileName,
          content: request.content || '',
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.error('Create page failed:', {
          status: response.status,
          statusText: response.statusText,
          error,
          request: {
            org_id: request.orgId,
            repo_id: request.repoId,
            persona: request.persona,
            parent_path: request.parentPath,
            fileName: request.fileName,
          }
        });
        throw new Error(error.detail || error.message || "Failed to create page");
      }

      return response.json();
    },
    [getToken]
  );

  const deletePage = useCallback(
    async (request: DeletePageRequest): Promise<void> => {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      // Normalize file path to remove repo name
      const normalizedPath = normalizeFilePath(request.filePath, request.repoId);

      const response = await fetch("/api/docbook/delete-page", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: request.orgId,
          repo_id: request.repoId,
          persona: request.persona,
          file_path: normalizedPath,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || error.message || "Failed to delete page");
      }
    },
    [getToken]
  );

  const renamePage = useCallback(
    async (request: RenamePageRequest): Promise<FileNode> => {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      // Normalize paths to remove repo name
      const normalizedOldPath = normalizeFilePath(request.oldPath, request.repoId);
      const normalizedNewPath = normalizeFilePath(request.newPath, request.repoId);

      const response = await fetch("/api/docbook/rename-page", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: request.orgId,
          repo_id: request.repoId,
          persona: request.persona,
          old_path: normalizedOldPath,
          new_path: normalizedNewPath,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || error.message || "Failed to rename page");
      }

      return response.json();
    },
    [getToken]
  );

  const updateStructure = useCallback(
    async (request: UpdateStructureRequest): Promise<void> => {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const response = await fetch("/api/docbook/update-structure", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: request.orgId,
          repo_id: request.repoId,
          persona: request.persona,
          structure: request.structure,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || error.message || "Failed to update structure");
      }
    },
    [getToken]
  );

  const bulkSave = useCallback(
    async (request: BulkSaveRequest): Promise<{ commit_sha: string; html_url: string }> => {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const response = await fetch("/api/docbook/bulk-save", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: request.orgId,
          repo_id: request.repoId,
          persona: request.persona,
          files: request.files,
          commit_message: request.commitMessage,
          branch: request.branch || 'staging',
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || error.message || "Failed to save files");
      }

      return response.json();
    },
    [getToken]
  );

  return {
    createPage,
    deletePage,
    renamePage,
    updateStructure,
    bulkSave,
  };
}

