"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { FileNode, useProjectStructure } from "./ProjectStructureContext";

export interface OpenFile {
  id: string; // Unique ID for the tab
  path: string;
  name: string;
  content: string;
  originalContent: string; // To detect changes
  isDirty: boolean;
  lastSaved?: Date;
}

interface EditorSessionContextType {
  openFiles: OpenFile[];
  activeFileId: string | null;
  openFile: (file: FileNode, structure?: { orgId: string; repoId: string } | null) => Promise<void>;
  closeFile: (fileId: string) => void;
  closeFileByPath: (path: string) => void; // Close file by path (for deletion)
  setActiveFile: (fileId: string) => void;
  updateFileContent: (fileId: string, content: string) => void;
  renameFile: (oldPath: string, newPath: string) => void; // Update file path when renamed
  getActiveFile: () => OpenFile | null;
  hasUnsavedChanges: () => boolean;
  getDirtyFiles: () => OpenFile[];
  markFileSaved: (fileId: string) => void;
}

const EditorSessionContext = createContext<EditorSessionContextType | undefined>(undefined);

export function EditorSessionProvider({ children }: { children: ReactNode }) {
  const [openFiles, setOpenFiles] = useState<OpenFile[]>([]);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);

  const openFile = useCallback(
    async (file: FileNode, structure?: { orgId: string; repoId: string } | null): Promise<void> => {
      if (file.type !== "file") return;

      // Check if file is already open
      const existing = openFiles.find((f) => f.path === file.path);
      if (existing) {
        setActiveFileId(existing.id);
        return;
      }

      // Fetch content if not already loaded
      let content = file.content || "";
      
      // If content not in context, fetch from backend
      if (!content && structure) {
        try {
          const token = localStorage.getItem("pustak_access_token");
          if (!token) {
            console.error("No authentication token found");
            return;
          }

          // Use structure context to get correct repo name
          // repoId is the actual repo name like "pustak-docbook-bajrangbalikijai"
          // orgId is the org name like "bajrangbalikijai"
          const fullRepoName = `${structure.orgId}/${structure.repoId}`;
          
          console.log("📄 Fetching file content:", {
            repo: fullRepoName,
            filePath: file.path,
          });

          // Try multiple path variants to avoid 404s from GitHub
          const pathVariants = [
            file.path, // e.g., jaishreram/docs/dev/api.md
            // Remove the first segment (repo folder) -> docs/dev/...
            file.path.split("/").slice(1).join("/"),
            // Remove first two segments if persona duplicated -> dev/...
            file.path.split("/").slice(2).join("/"),
          ].filter(Boolean);

          let fetched = false;
          for (const variant of pathVariants) {
            console.log("📄 Attempting fetch with path variant:", variant);
            const response = await fetch(
              `/api/fetch-doc?repo=${encodeURIComponent(fullRepoName)}&filePath=${encodeURIComponent(variant)}`,
              {
                headers: { Authorization: `Bearer ${token}` },
              }
            );

            console.log("📄 Fetch response status:", response.status, "path:", variant);

            if (response.ok) {
              const data = await response.json();
              content = data.content || "";
              console.log("✅ File content loaded successfully!");
              console.log("📄 Content length:", content.length);
              console.log("📄 Content preview (first 200 chars):", content.substring(0, 200));
              fetched = true;
              break;
            } else {
              const errorData = await response.json().catch(() => ({}));
              console.error("❌ Failed to fetch file variant:", response.status, errorData);
            }
          }

          if (!fetched) {
            console.error("❌ All path variants failed for", file.path);
            content = "";
          }
        } catch (error) {
          console.error("📄 Error fetching file content:", error);
        }
      }

      const newFile: OpenFile = {
        id: `${file.path}-${Date.now()}`,
        path: file.path,
        name: file.name,
        content,
        originalContent: content,
        isDirty: false,
      };

      setOpenFiles((prev) => [...prev, newFile]);
      setActiveFileId(newFile.id);
    },
    [openFiles, setActiveFileId]
  );

  const closeFile = useCallback((fileId: string) => {
    setOpenFiles((prev) => {
      const filtered = prev.filter((f) => f.id !== fileId);
      // If closing active file, switch to another
      if (activeFileId === fileId) {
        const index = prev.findIndex((f) => f.id === fileId);
        const nextActive = filtered[index] || filtered[index - 1] || null;
        setActiveFileId(nextActive?.id || null);
      }
      return filtered;
    });
  }, [activeFileId]);

  const closeFileByPath = useCallback((path: string) => {
    setOpenFiles((prev) => {
      const fileToClose = prev.find((f) => f.path === path);
      if (!fileToClose) return prev;
      
      const filtered = prev.filter((f) => f.path !== path);
      // If closing active file, switch to another
      if (activeFileId === fileToClose.id) {
        const index = prev.findIndex((f) => f.id === fileToClose.id);
        const nextActive = filtered[index] || filtered[index - 1] || null;
        setActiveFileId(nextActive?.id || null);
      }
      return filtered;
    });
  }, [activeFileId]);

  const renameFile = useCallback((oldPath: string, newPath: string) => {
    setOpenFiles((prev) =>
      prev.map((file) => {
        if (file.path === oldPath) {
          return {
            ...file,
            path: newPath,
            id: `${newPath}-${Date.now()}`, // Update ID to match new path
          };
        }
        return file;
      })
    );
  }, []);

  const setActiveFile = useCallback((fileId: string) => {
    if (openFiles.some((f) => f.id === fileId)) {
      setActiveFileId(fileId);
    }
  }, [openFiles]);

  const updateFileContent = useCallback((fileId: string, content: string) => {
    setOpenFiles((prev) =>
      prev.map((file) => {
        if (file.id === fileId) {
          const isDirty = content !== file.originalContent;
          return {
            ...file,
            content,
            isDirty,
          };
        }
        return file;
      })
    );
    
    // Also update ProjectStructureContext if available
    // This ensures the structure context knows about content changes
    try {
      const file = openFiles.find((f) => f.id === fileId);
      if (file) {
        // We'll update this through a callback or effect
        // For now, the structure context will be updated on save
      }
    } catch (error) {
      // Context might not be available, ignore
    }
  }, [openFiles]);

  const getActiveFile = useCallback((): OpenFile | null => {
    if (!activeFileId) return null;
    return openFiles.find((f) => f.id === activeFileId) || null;
  }, [activeFileId, openFiles]);

  const hasUnsavedChanges = useCallback((): boolean => {
    return openFiles.some((f) => f.isDirty);
  }, [openFiles]);

  const getDirtyFiles = useCallback((): OpenFile[] => {
    return openFiles.filter((f) => f.isDirty);
  }, [openFiles]);

  const markFileSaved = useCallback((fileId: string) => {
    setOpenFiles((prev) =>
      prev.map((file) => {
        if (file.id === fileId) {
          return {
            ...file,
            isDirty: false,
            originalContent: file.content,
            lastSaved: new Date(),
          };
        }
        return file;
      })
    );
  }, []);

  return (
    <EditorSessionContext.Provider
      value={{
        openFiles,
        activeFileId,
        openFile,
        closeFile,
        closeFileByPath,
        setActiveFile,
        updateFileContent,
        renameFile,
        getActiveFile,
        hasUnsavedChanges,
        getDirtyFiles,
        markFileSaved,
      }}
    >
      {children}
    </EditorSessionContext.Provider>
  );
}

export function useEditorSession() {
  const context = useContext(EditorSessionContext);
  if (context === undefined) {
    throw new Error("useEditorSession must be used within an EditorSessionProvider");
  }
  return context;
}

