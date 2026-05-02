/**
 * Canvas Editor Component
 *
 * Multi-file aware markdown editor with:
 * - Auto-save to global store (debounced)
 * - Seamless tab switching without losing content
 * - Optimistic UI updates
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useWorkspaceStore } from "@/stores/useWorkspaceStore";
import { Save, Clock, AlertCircle } from "lucide-react";
import { debounce } from "@/lib/utils";
import { BlockNoteEditor } from "@/components/BlockNoteEditor";

interface CanvasEditorProps {
  orgId: string;
  repoId: string;
}

export function CanvasEditor({ orgId, repoId }: CanvasEditorProps) {
  const {
    activePageId,
    contentCache,
    updateContent,
    getNodeById,
    loadPageContent,
  } = useWorkspaceStore();

  const [editorContent, setEditorContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const lastSavedRef = useRef<string>("");
  const editorKeyRef = useRef<string>(""); // Force re-render when switching files

  const activePage = activePageId ? getNodeById(activePageId) : null;
  const cachedContent = activePageId ? contentCache[activePageId] : null;

  // Debounced save to store
  const debouncedSave = useCallback(
    debounce((pageId: string, content: string) => {
      updateContent(pageId, content);
      lastSavedRef.current = content;
      setIsSaving(false);
    }, 500),
    [updateContent],
  );

  // Load content when active page changes
  useEffect(() => {
    if (activePageId && cachedContent) {
      // Content is in cache - use it
      const content = cachedContent.content || "";
      setEditorContent(content);
      lastSavedRef.current = content;
      editorKeyRef.current = `${activePageId}-${Date.now()}`; // Force re-render
      setIsLoading(false);
    } else if (activePageId && activePage) {
      // Page not in cache - load from backend
      setIsLoading(true);
      const fetchContent = async () => {
        if (!activePage.path) {
          console.warn("[CanvasEditor] No path for page:", activePageId);
          setEditorContent("");
          setIsLoading(false);
          return;
        }

        try {
          const token = localStorage.getItem("DocIt_access_token");
          if (!token) {
            console.error("[CanvasEditor] No auth token");
            setEditorContent("");
            setIsLoading(false);
            return;
          }

          const BACKEND_URL =
            process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
          const baseUrl = BACKEND_URL.includes("/api/v1")
            ? BACKEND_URL
            : `${BACKEND_URL}/api/v1`;
          const url = `${baseUrl}/workspace/${orgId}/${repoId}/page?path=${encodeURIComponent(activePage.path)}`;

          console.log("[CanvasEditor] Fetching content from:", url);

          const response = await fetch(url, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            console.error(
              "[CanvasEditor] Failed to fetch content:",
              response.status,
              response.statusText,
            );
            setEditorContent("");
            setIsLoading(false);
            return;
          }

          const data = await response.json();
          console.log(
            "[CanvasEditor] Content loaded, length:",
            data.content?.length || 0,
          );

          // Load content into store
          const content = data.content || "";
          loadPageContent(activePageId, content);
          setEditorContent(content);
          lastSavedRef.current = content;
          editorKeyRef.current = `${activePageId}-${Date.now()}`; // Force re-render
          setIsLoading(false);
        } catch (error) {
          console.error("[CanvasEditor] Error fetching content:", error);
          setEditorContent("");
          setIsLoading(false);
        }
      };

      fetchContent();
    } else {
      setEditorContent("");
      lastSavedRef.current = "";
      editorKeyRef.current = "";
      setIsLoading(false);
    }
  }, [activePageId, cachedContent, activePage, loadPageContent, orgId, repoId]);

  // Handle content change from BlockNote editor
  const handleContentChange = useCallback(
    (markdown: string) => {
      setEditorContent(markdown);

      if (activePageId) {
        setIsSaving(true);
        debouncedSave(activePageId, markdown);
      }
    },
    [activePageId, debouncedSave],
  );

  const isDirty = cachedContent?.isDirty || false;
  const hasUnsavedChanges = editorContent !== lastSavedRef.current;

  if (!activePage) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center text-slate-400">
          <p className="text-lg">No page selected</p>
          <p className="text-sm mt-2">
            Select a page from the sidebar or create a new one
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      {/* Editor Header */}
      <div className="flex-shrink-0 border-b border-slate-800 bg-slate-900 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">
              {activePage.title}
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              {activePage.path || "Untitled document"}
            </p>
          </div>

          {/* Save Status */}
          <div className="flex items-center gap-3">
            {isSaving && (
              <span className="flex items-center gap-2 text-sm text-slate-400">
                <Clock className="w-4 h-4 animate-pulse" />
                Saving...
              </span>
            )}

            {!isSaving && isDirty && (
              <span className="flex items-center gap-2 text-sm text-amber-400">
                <AlertCircle className="w-4 h-4" />
                Unpublished changes
              </span>
            )}

            {!isSaving && !isDirty && hasUnsavedChanges && (
              <span className="flex items-center gap-2 text-sm text-emerald-400">
                <Save className="w-4 h-4" />
                All changes saved
              </span>
            )}

            {activePage.isTempNode && (
              <span className="px-3 py-1 text-xs font-semibold text-amber-400 bg-amber-500/10 rounded-full">
                New Document
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Editor Canvas */}
      <div className="flex-1 overflow-hidden bg-slate-950">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-slate-400">
              <Clock className="w-6 h-6 animate-pulse mx-auto mb-2" />
              <p>Loading content...</p>
            </div>
          </div>
        ) : (
          <div className="h-full w-full">
            <BlockNoteEditor
              key={editorKeyRef.current || activePageId} // Force re-render when switching files
              initialContent={editorContent}
              onChange={handleContentChange}
              editable={true}
              className="h-full"
            />
          </div>
        )}
      </div>

      {/* Editor Footer (Optional - Word Count, etc.) */}
      <div className="flex-shrink-0 border-t border-slate-800 bg-slate-900 px-6 py-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            {editorContent.split(/\s+/).filter(Boolean).length} words ·{" "}
            {editorContent.length} characters
          </span>

          {cachedContent?.lastModified && (
            <span>
              Last modified:{" "}
              {new Date(cachedContent.lastModified).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
