'use client';

import { useEditor } from '@/contexts/EditorContext';
import { X, Save, Circle, Loader2 } from 'lucide-react';
import BlockNoteEditorClient from './BlockNoteEditorClient';
import { useState } from 'react';

interface MultiPageEditorProps {
  repo: string;
}

export function MultiPageEditor({ repo }: MultiPageEditorProps) {
  const { 
    state, 
    closePage, 
    setActivePagePath, 
    updatePageContent, 
    markPageSaved, 
    getDirtyPages,
    hasUnsavedChanges 
  } = useEditor();
  
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveSingle = async (path: string, content: string) => {
    setSaving(true);
    setSaveError(null);
    
    try {
      const userToken = localStorage.getItem('pustak_access_token');
      
      if (!userToken) {
        throw new Error('Not authenticated');
      }

      const response = await fetch('/api/commit-doc', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`,
        },
        body: JSON.stringify({
          repo,
          filePath: path,
          content,
          commitMessage: `docs: Update ${path.split('/').pop()}`,
          branch: 'staging',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save changes');
      }

      markPageSaved(path);
      console.log('✅ Saved:', path);
    } catch (error) {
      console.error('Save error:', error);
      setSaveError(error instanceof Error ? error.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAll = async () => {
    const dirtyPages = getDirtyPages();
    
    if (dirtyPages.length === 0) {
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      const userToken = localStorage.getItem('pustak_access_token');
      
      if (!userToken) {
        throw new Error('Not authenticated');
      }

      const operations = dirtyPages.map(page => ({
        action: 'update',
        path: page.path,
        content: page.content,
      }));

      const response = await fetch('/api/pages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`,
        },
        body: JSON.stringify({
          action: 'batch',
          repo,
          operations,
          commit_message: `docs: Update ${dirtyPages.length} page${dirtyPages.length > 1 ? 's' : ''}`,
          branch: 'staging',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save changes');
      }

      // Mark all pages as saved
      dirtyPages.forEach(page => markPageSaved(page.path));
      console.log(`✅ Saved ${dirtyPages.length} pages`);
    } catch (error) {
      console.error('Batch save error:', error);
      setSaveError(error instanceof Error ? error.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleCloseTab = (path: string) => {
    if (hasUnsavedChanges(path)) {
      if (confirm('You have unsaved changes. Close anyway?')) {
        closePage(path);
      }
    } else {
      closePage(path);
    }
  };

  const openPages = Array.from(state.openPages.values());
  const activePage = openPages.find(p => p.path === state.activePagePath);
  const dirtyCount = getDirtyPages().length;

  return (
    <div className="flex h-full flex-col bg-slate-950">
      {/* Tab Bar */}
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/50 px-4">
        <div className="flex flex-1 items-center gap-2 overflow-x-auto scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700">
          {openPages.map(page => {
            const fileName = page.path.split('/').pop()?.replace('.md', '') || 'Untitled';
            const isActive = page.path === state.activePagePath;
            
            return (
              <div
                key={page.path}
                className={`group flex items-center gap-2 border-b-2 px-4 py-3 text-sm transition cursor-pointer ${
                  isActive
                    ? 'border-blue-500 bg-slate-900 text-blue-200'
                    : 'border-transparent text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
                onClick={() => setActivePagePath(page.path)}
                title={page.path}
              >
                {page.isDirty && (
                  <Circle className="h-2 w-2 fill-orange-400 text-orange-400" />
                )}
                <span className="max-w-[150px] truncate">{fileName}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCloseTab(page.path);
                  }}
                  className="rounded p-1 opacity-0 transition hover:bg-slate-700 group-hover:opacity-100"
                  aria-label="Close tab"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {saveError && (
            <div className="text-xs text-red-400" title={saveError}>
              Save failed
            </div>
          )}
          
          {dirtyCount > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save All ({dirtyCount})
            </button>
          )}
        </div>
      </div>

      {/* Editor Content */}
      <div className="flex-1 overflow-auto">
        {activePage ? (
          <div className="h-full">
            <BlockNoteEditorClient
              initialContent={activePage.content}
              onChange={(content) => {
                updatePageContent(activePage.path, content);
              }}
            />
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-slate-400">
            <div className="text-center">
              <p className="text-lg font-medium text-slate-300">No page selected</p>
              <p className="mt-2 text-sm">
                Select a page from the sidebar to start editing
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Status Bar */}
      {activePage && (
        <div className="border-t border-slate-800 bg-slate-900/30 px-4 py-2 text-xs text-slate-400">
          <div className="flex items-center justify-between">
            <span>{activePage.path}</span>
            <div className="flex items-center gap-4">
              {activePage.isDirty && (
                <span className="flex items-center gap-1 text-orange-400">
                  <Circle className="h-2 w-2 fill-current" />
                  Unsaved changes
                </span>
              )}
              {activePage.lastSaved && (
                <span>
                  Last saved: {new Date(activePage.lastSaved).toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
