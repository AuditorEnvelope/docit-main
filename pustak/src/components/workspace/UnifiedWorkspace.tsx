/**
 * Unified Workspace - Main Container
 * 
 * Combines Sidebar + Editor into a split-pane layout
 * This is the entry point for the new editor experience
 */

'use client';

import { useEffect } from 'react';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { DocumentSidebar } from './DocumentSidebar';
import { DocumentEditor } from './DocumentEditor';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface UnifiedWorkspaceProps {
  orgId: string;
  repoId: string;
}

export function UnifiedWorkspace({ orgId, repoId }: UnifiedWorkspaceProps) {
  const { fileTree, initializeTree, setActivePageId } = useWorkspaceStore();
  const { token } = useAuth();

  // Load workspace tree on mount
  useEffect(() => {
    console.log('[UnifiedWorkspace] Effect triggered', { orgId, repoId, hasToken: !!token });
    
    if (!token) {
      console.warn('[UnifiedWorkspace] No auth token available, waiting...');
      return; // Wait for auth
    }
    
    // ALWAYS fetch fresh data from backend, ignore persisted cache
    const loadWorkspace = async () => {
      try {
        const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        // Don't add /api/v1 if BACKEND_URL already includes it
        const baseUrl = BACKEND_URL.includes('/api/v1') ? BACKEND_URL : `${BACKEND_URL}/api/v1`;
        const url = `${baseUrl}/workspace/${orgId}/${repoId}/tree`;
        
        console.log('[UnifiedWorkspace] Fetching workspace tree from:', url);
        
        const response = await fetch(
          url,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
        
        console.log('[UnifiedWorkspace] Response status:', response.status);

        if (!response.ok) {
          console.error('[UnifiedWorkspace] Failed to load workspace:', response.status, response.statusText);
          throw new Error('Failed to load workspace');
        }

        const data = await response.json();
        console.log('[UnifiedWorkspace] Received tree data:', data);
        initializeTree(data.tree);

        // Auto-select first page if available
        if (data.tree?.children?.length > 0) {
          const firstPage = data.tree.children.find((node: any) => node.type === 'page');
          if (firstPage) {
            setActivePageId(firstPage.id);
          }
        }
      } catch (error) {
        console.error('[UnifiedWorkspace] Error loading workspace:', error);
        // Initialize with empty tree
        initializeTree({
          id: 'root',
          type: 'folder',
          title: 'Root',
          parentId: null,
          position: 0,
          children: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }
    };

    console.log('[UnifiedWorkspace] Calling loadWorkspace...');
    loadWorkspace();
  }, [orgId, repoId, initializeTree, setActivePageId, token]);

  if (!fileTree) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden bg-slate-950">
      {/* Sidebar - Fixed Width (GitBook Style) */}
      <div className="w-64 flex-shrink-0">
        <DocumentSidebar
          orgId={orgId}
          repoId={repoId}
          onPageSelect={(pageId) => setActivePageId(pageId)}
        />
      </div>

      {/* Editor - Flexible Width */}
      <div className="flex-1 overflow-hidden">
        <DocumentEditor orgId={orgId} repoId={repoId} />
      </div>
    </div>
  );
}
