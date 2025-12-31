/**
 * Workspace Sidebar - Root Container
 * 
 * Main sidebar component that renders the recursive tree
 * and provides global actions (Add Root Page, Sync, etc.)
 */

'use client';

import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { SidebarNode } from './SidebarNode';
import { FolderPlus, FilePlus, Upload, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface WorkspaceSidebarProps {
  orgId: string;
  repoId: string;
  onPageSelect?: (pageId: string) => void;
}

export function WorkspaceSidebar({ orgId, repoId, onPageSelect }: WorkspaceSidebarProps) {
  const {
    fileTree,
    addNode,
    hasUnsavedChanges,
    syncWorkspace,
    isSyncing,
    pendingChanges,
    structureDirty
  } = useWorkspaceStore();
  const { token } = useAuth();

  const handleSync = async () => {
    if (!token) {
      console.error('No auth token available');
      return;
    }
    
    try {
      await syncWorkspace(orgId, repoId, token);
      // Show success toast (implement toast system separately)
      console.log('✅ All changes saved!');
    } catch (error) {
      console.error('❌ Sync failed:', error);
      // Show error toast
    }
  };

  const changeCount = pendingChanges.size + (structureDirty ? 1 : 0);
  const hasChanges = hasUnsavedChanges();

  return (
    <div className="h-full flex flex-col bg-slate-900 border-r border-slate-800">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">Workspace</h2>
          
          {/* Sync Status */}
          {hasChanges && (
            <span className="text-xs text-amber-400 px-2 py-1 bg-amber-500/10 rounded">
              {changeCount} unsaved
            </span>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => addNode(null, 'page')}
            className="
              flex-1 flex items-center justify-center gap-2
              px-3 py-2 text-sm font-medium text-slate-200
              bg-slate-800 hover:bg-slate-700 rounded-lg transition
            "
            title="Add root page"
          >
            <FilePlus className="w-4 h-4" />
            Page
          </button>

          <button
            onClick={() => addNode(null, 'folder')}
            className="
              flex-1 flex items-center justify-center gap-2
              px-3 py-2 text-sm font-medium text-slate-200
              bg-slate-800 hover:bg-slate-700 rounded-lg transition
            "
            title="Add root folder"
          >
            <FolderPlus className="w-4 h-4" />
            Folder
          </button>
        </div>

        {/* Publish Button */}
        {hasChanges && (
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className={`
              w-full mt-3 flex items-center justify-center gap-2
              px-4 py-2.5 text-sm font-semibold text-white
              rounded-lg transition shadow-lg
              ${
                isSyncing
                  ? 'bg-blue-500/50 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600'
              }
            `}
          >
            {isSyncing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Publishing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Publish Changes ({changeCount})
              </>
            )}
          </button>
        )}
      </div>

      {/* Tree Container */}
      <div className="flex-1 overflow-y-auto py-2">
        {fileTree ? (
          <div>
            {/* Render root node's children */}
            {fileTree.children.map((child) => (
              <SidebarNode
                key={child.id}
                node={child}
                level={0}
                onNodeClick={onPageSelect}
              />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-sm">
            <p>No workspace loaded</p>
            <p className="text-xs mt-2">Click "Page" or "Folder" to start</p>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800 text-xs text-slate-500">
        <div className="flex items-center justify-between">
          <span>{orgId} / {repoId}</span>
          {isSyncing && (
            <span className="flex items-center gap-1 text-blue-400">
              <Loader2 className="w-3 h-3 animate-spin" />
              Syncing...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
