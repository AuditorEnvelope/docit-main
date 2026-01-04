/**
 * Document Editor - GitBook/Mintlify Style
 *
 * Clean, document-focused editor with minimal UI
 * Focus on content, not structure
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useWorkspaceStore } from "@/stores/useWorkspaceStore";
import { BlockNoteEditor } from "@/components/BlockNoteEditor";
import { CommitModal } from "@/components/CommitModal";
import {
  Save,
  Clock,
  AlertCircle,
  Loader2,
  CheckCircle2,
  FileText,
  Sparkles,
  ArrowRight,
  BookOpen,
} from "lucide-react";
import { debounce } from "@/lib/utils";

interface DocumentEditorProps {
  orgId: string;
  repoId: string;
}

export function DocumentEditor({ orgId, repoId }: DocumentEditorProps) {
  const {
    activePageId,
    contentCache,
    updateContent,
    getNodeById,
    loadPageContent,
    hasUnsavedChanges,
    pendingChanges,
    structureDirty,
    syncWorkspace,
  } = useWorkspaceStore();

  const [editorContent, setEditorContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const lastSavedRef = useRef<string>("");
  const editorKeyRef = useRef<string>("");
  const lastLoadedPageRef = useRef<string | null>(""); // Track which page was last loaded

  const activePage = activePageId ? getNodeById(activePageId) : null;
  const cachedContent = activePageId ? contentCache[activePageId] : null;
  const hasChanges = hasUnsavedChanges();

  // Debounced save to store
  const debouncedSave = useCallback(
    debounce((pageId: string, content: string) => {
      updateContent(pageId, content);
      lastSavedRef.current = content;
      setIsSaving(false);
    }, 500),
    [updateContent]
  );

  // Load content when active page changes OR when cache is updated (for revert)
  useEffect(() => {
    if (!activePageId) {
      setEditorContent("");
      lastSavedRef.current = "";
      editorKeyRef.current = "";
      setIsLoading(false);
      return;
    }

    // Page changed - always load
    if (lastLoadedPageRef.current !== activePageId) {
      lastLoadedPageRef.current = activePageId;
    }

    // If we have cached content, use it
    if (cachedContent) {
      const content = cachedContent.content || "";
      // Only update if content actually changed (prevents unnecessary re-renders)
      if (content !== lastSavedRef.current) {
        setEditorContent(content);
        lastSavedRef.current = content;
        editorKeyRef.current = `${activePageId}-${Date.now()}`;
      }
      setIsLoading(false);
      return;
    }

    // No cache - fetch from server
    if (activePage) {
      setIsLoading(true);
      const fetchContent = async () => {
        if (!activePage.path) {
          console.error("[DocumentEditor] ❌ No path for page:", {
            pageId: activePageId,
            title: activePage.title,
            page: activePage,
          });
          setEditorContent("");
          setIsLoading(false);
          return;
        }

        try {
          const token = localStorage.getItem("pustak_access_token");
          if (!token) {
            console.error("[DocumentEditor] ❌ No auth token");
            setEditorContent("");
            setIsLoading(false);
            return;
          }

          const BACKEND_URL =
            process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
          const baseUrl = BACKEND_URL.includes("/api/v1")
            ? BACKEND_URL
            : `${BACKEND_URL}/api/v1`;
          const url = `${baseUrl}/workspace/${orgId}/${repoId}/page?path=${encodeURIComponent(
            activePage.path
          )}`;

          console.log("[DocumentEditor] 🔍 Fetching content:", {
            url,
            path: activePage.path,
            pageId: activePageId,
            title: activePage.title,
            orgId,
            repoId,
          });

          const response = await fetch(url, {
            headers: { Authorization: `Bearer ${token}` },
          });

          console.log("[DocumentEditor] 📡 Response:", {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
          });

          if (!response.ok) {
            const errorText = await response.text().catch(() => "");
            console.error("[DocumentEditor] ❌ API Error:", {
              status: response.status,
              statusText: response.statusText,
              error: errorText.substring(0, 500),
              url,
            });
            setEditorContent("");
            setIsLoading(false);
            return;
          }

          const data = await response.json();
          const content = data.content || "";

          console.log("[DocumentEditor] ✅ Content received:", {
            contentLength: content.length,
            hasContent: !!content,
            path: data.path,
          });

          if (content) {
            loadPageContent(activePageId, content);
            setEditorContent(content);
            lastSavedRef.current = content;
            editorKeyRef.current = `${activePageId}-${Date.now()}`;
            console.log("[DocumentEditor] ✅ Content loaded successfully!");
          } else {
            console.warn("[DocumentEditor] ⚠️ Empty content received");
          }
          setIsLoading(false);
        } catch (error) {
          console.error("[DocumentEditor] ❌ Fetch error:", error);
          setEditorContent("");
          setIsLoading(false);
        }
      };

      fetchContent();
    }
  }, [activePageId, cachedContent, activePage, loadPageContent, orgId, repoId]);

  // Separate effect to detect revert (cache content changed but not dirty)
  useEffect(() => {
    if (!activePageId || !cachedContent) return;

    // If cached content changed but is NOT dirty, it was reverted
    const currentCachedContent = cachedContent.content || "";
    const isReverted =
      lastSavedRef.current !== currentCachedContent &&
      !cachedContent.isDirty &&
      lastLoadedPageRef.current === activePageId; // Same page

    if (isReverted) {
      // Only update if content actually changed (not empty to empty)
      if (currentCachedContent !== lastSavedRef.current) {
        setEditorContent(currentCachedContent);
        lastSavedRef.current = currentCachedContent;
        editorKeyRef.current = `${activePageId}-${Date.now()}`;
      }
    }
  }, [activePageId, cachedContent]);

  // Handle content change
  const handleContentChange = useCallback(
    (markdown: string) => {
      setEditorContent(markdown);
      if (activePageId) {
        setIsSaving(true);
        debouncedSave(activePageId, markdown);
      }
    },
    [activePageId, debouncedSave]
  );

  // Handle commit
  const handleCommit = useCallback(
    async (commitMessage: string) => {
      const token = localStorage.getItem("pustak_access_token");
      if (!token) {
        throw new Error("No auth token available");
      }

      setIsCommitting(true);
      try {
        await syncWorkspace(orgId, repoId, token, commitMessage);
        setIsCommitModalOpen(false);
        // Show success notification
      } catch (error) {
        console.error("[DocumentEditor] Commit failed:", error);
        throw error;
      } finally {
        setIsCommitting(false);
      }
    },
    [orgId, repoId, syncWorkspace]
  );

  if (!activePage) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0B0D11]">
        <div className="text-center max-w-2xl px-6">
          {/* Animated Icon - Borderless */}
          <div className="relative mx-auto mb-8">
            <div className="absolute inset-0 bg-blue-500/10 blur-3xl rounded-full animate-pulse" />
            <div className="relative w-24 h-24 mx-auto rounded-2xl flex items-center justify-center border border-white/5">
              <BookOpen className="w-12 h-12 text-blue-400/80" />
            </div>
          </div>

          {/* Welcome Text - Editorial Typography */}
          <h2 className="text-4xl font-bold text-white mb-4 tracking-tight leading-tight">
            Welcome to Your Workspace
          </h2>
          <p className="text-lg text-slate-400 mb-8 leading-relaxed">
            Select a document from the sidebar to start editing, or create a new
            one to begin documenting your project.
          </p>

          {/* Quick Tips - Borderless Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
            <div className="group p-6 rounded-xl border border-white/5 hover:border-white/10 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <Sparkles className="w-5 h-5 text-blue-400/80" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">
                Rich Editor
              </h3>
              <p className="text-xs text-slate-400">
                Write with Markdown or use the visual editor
              </p>
            </div>

            <div className="group p-6 rounded-xl border border-white/5 hover:border-white/10 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircle2 className="w-5 h-5 text-emerald-400/80" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">
                Auto-Save
              </h3>
              <p className="text-xs text-slate-400">
                Your changes are saved automatically
              </p>
            </div>

            <div className="group p-6 rounded-xl border border-white/5 hover:border-white/10 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <ArrowRight className="w-5 h-5 text-purple-400/80" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">
                Quick Publish
              </h3>
              <p className="text-xs text-slate-400">
                Commit and publish with one click
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const changeCount = pendingChanges.size + (structureDirty ? 1 : 0);

  return (
    <div className="h-full flex flex-col bg-[#0B0D11]">
      {/* Editor Content - Borderless Editorial Style */}
      <div className="flex-1">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p className="text-sm">Loading document...</p>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-8 py-12">
            <BlockNoteEditor
              key={editorKeyRef.current || activePageId}
              initialContent={editorContent}
              onChange={handleContentChange}
              editable={true}
              className="min-h-screen"
            />
          </div>
        )}
      </div>

      {/* Commit Modal */}
      <CommitModal
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        onCommit={handleCommit}
        pageTitle={activePage.title}
        isLoading={isCommitting}
      />
    </div>
  );
}
