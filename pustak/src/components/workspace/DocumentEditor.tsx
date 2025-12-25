/**
 * Document Editor - GitBook/Mintlify Style
 * 
 * Clean, document-focused editor with minimal UI
 * Focus on content, not structure
 */

'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { BlockNoteEditor } from '@/components/BlockNoteEditor';
import { CommitModal } from '@/components/CommitModal';
import { 
  Save, 
  Clock, 
  AlertCircle, 
  Loader2,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { debounce } from '@/lib/utils';

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
    syncWorkspace
  } = useWorkspaceStore();

  const [editorContent, setEditorContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const lastSavedRef = useRef<string>('');
  const editorKeyRef = useRef<string>('');
  const lastLoadedPageRef = useRef<string>(''); // Track which page was last loaded

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

  // Load content when active page changes (NOT when content changes)
  useEffect(() => {
    // Skip if we've already loaded this page
    if (lastLoadedPageRef.current === activePageId) {
      return;
    }

    lastLoadedPageRef.current = activePageId;

    if (activePageId && cachedContent) {
      const content = cachedContent.content || '';
      setEditorContent(content);
      lastSavedRef.current = content;
      editorKeyRef.current = `${activePageId}-${Date.now()}`;
      setIsLoading(false);
    } else if (activePageId && activePage) {
      setIsLoading(true);
      const fetchContent = async () => {
        if (!activePage.path) {
          setEditorContent('');
          setIsLoading(false);
          return;
        }
        
        try {
          const token = localStorage.getItem('pustak_access_token');
          if (!token) {
            setEditorContent('');
            setIsLoading(false);
            return;
          }
          
          const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
          const baseUrl = BACKEND_URL.includes('/api/v1') ? BACKEND_URL : `${BACKEND_URL}/api/v1`;
          const url = `${baseUrl}/workspace/${orgId}/${repoId}/page?path=${encodeURIComponent(activePage.path)}`;
          
          const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` },
          });
          
          if (!response.ok) {
            setEditorContent('');
            setIsLoading(false);
            return;
          }
          
          const data = await response.json();
          const content = data.content || '';
          loadPageContent(activePageId, content);
          setEditorContent(content);
          lastSavedRef.current = content;
          editorKeyRef.current = `${activePageId}-${Date.now()}`;
          setIsLoading(false);
        } catch (error) {
          console.error('[DocumentEditor] Error fetching content:', error);
          setEditorContent('');
          setIsLoading(false);
        }
      };
      
      fetchContent();
    } else {
      setEditorContent('');
      lastSavedRef.current = '';
      editorKeyRef.current = '';
      setIsLoading(false);
    }
  }, [activePageId, cachedContent, activePage, loadPageContent, orgId, repoId]);

  // Handle content change
  const handleContentChange = useCallback((markdown: string) => {
    setEditorContent(markdown);
    if (activePageId) {
      setIsSaving(true);
      debouncedSave(activePageId, markdown);
    }
  }, [activePageId, debouncedSave]);

  // Handle commit
  const handleCommit = useCallback(async (commitMessage: string) => {
    const token = localStorage.getItem('pustak_access_token');
    if (!token) {
      throw new Error('No auth token available');
    }

    setIsCommitting(true);
    try {
      await syncWorkspace(orgId, repoId, token, commitMessage);
      setIsCommitModalOpen(false);
      // Show success notification
    } catch (error) {
      console.error('[DocumentEditor] Commit failed:', error);
      throw error;
    } finally {
      setIsCommitting(false);
    }
  }, [orgId, repoId, syncWorkspace]);

  if (!activePage) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950">
        <div className="text-center text-slate-400 max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
            <FileText className="w-8 h-8 text-slate-500" />
          </div>
          <p className="text-lg font-medium mb-2">No document selected</p>
          <p className="text-sm">Select a document from the sidebar to start editing</p>
        </div>
      </div>
    );
  }

  const changeCount = pendingChanges.size + (structureDirty ? 1 : 0);

  return (
    <div className="h-full flex flex-col">
      {/* Editor Content - Centered "Paper" Style */}
      <div className="flex-1 bg-slate-950">
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

