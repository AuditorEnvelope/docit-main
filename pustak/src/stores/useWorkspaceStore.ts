/**
 * Unified Workspace Store - Local-First Architecture
 * 
 * This store manages the entire documentation workspace state using Zustand.
 * Key principles:
 * - All UI operations are instant (optimistic updates)
 * - Backend sync happens only on explicit "Publish" action
 * - Supports temp IDs for ghost states
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type NodeType = 'folder' | 'page';

export interface FileNode {
  id: string; // Can be temp-uuid or real server ID
  type: NodeType;
  title: string;
  parentId: string | null;
  position: number; // Order within parent
  children: FileNode[];
  
  // Ghost state management
  isEditing?: boolean; // True when showing input field
  isTempNode?: boolean; // True for client-only nodes not yet synced
  
  // Metadata
  createdAt: string;
  updatedAt: string;
  path?: string; // File path in docbook repo (e.g., "docs/dev/api.md")
}

export interface ContentCache {
  [pageId: string]: {
    content: string; // Markdown content
    lastModified: number; // Timestamp
    isDirty: boolean; // Has unsaved changes
  };
}

export interface SyncPayload {
  treeStructure: FileNode;
  modifiedFiles: {
    pageId: string;
    path: string;
    content: string;
    action: 'create' | 'update' | 'delete';
  }[];
  deletedNodes: string[]; // IDs of deleted pages/folders
  tempIdMapping?: { [tempId: string]: string }; // Map temp IDs to real IDs after sync
}

export interface WorkspaceState {
  // ========== STATE ==========
  fileTree: FileNode | null;
  contentCache: ContentCache;
  activePageId: string | null;
  pendingChanges: Set<string>; // Page IDs with unsaved content
  structureDirty: boolean; // True if tree was modified
  deletedQueue: Set<string>; // IDs to delete on sync
  isSyncing: boolean;
  lastSyncTime: number | null;
  
  // Sidebar state
  expandedFolders: Set<string>; // Folder IDs that are expanded
  
  // ========== ACTIONS ==========
  
  // Tree Structure Actions (Instant, No Backend)
  initializeTree: (tree: FileNode) => void;
  addNode: (parentId: string | null, type: NodeType) => string; // Returns temp ID
  deleteNode: (nodeId: string) => void;
  moveNode: (dragId: string, dropId: string, position: 'before' | 'after' | 'inside') => void;
  renameNode: (nodeId: string, newTitle: string) => void;
  duplicateNode: (nodeId: string) => string; // Returns new node ID
  
  // Content Actions (Instant, Debounced Store Update)
  setActivePageId: (pageId: string | null) => void;
  updateContent: (pageId: string, content: string) => void;
  loadPageContent: (pageId: string, content: string) => void; // Load from server
  
  // Editing State
  setNodeEditing: (nodeId: string, isEditing: boolean) => void;
  toggleFolder: (folderId: string) => void;
  
  // Sync Actions
  syncWorkspace: (orgId: string, repoId: string, token: string, commitMessage?: string) => Promise<void>;
  clearPendingChanges: () => void;
  
  // Utility
  getNodeById: (nodeId: string) => FileNode | null;
  getNodePath: (nodeId: string) => FileNode[]; // Breadcrumb path
  hasUnsavedChanges: () => boolean;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function generateTempId(): string {
  return `temp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function findNodeRecursive(node: FileNode | null, targetId: string): FileNode | null {
  if (!node) return null;
  if (node.id === targetId) return node;
  
  for (const child of node.children) {
    const found = findNodeRecursive(child, targetId);
    if (found) return found;
  }
  
  return null;
}

function updateNodeRecursive(
  node: FileNode,
  targetId: string,
  updater: (node: FileNode) => FileNode
): FileNode {
  if (node.id === targetId) {
    return updater(node);
  }
  
  return {
    ...node,
    children: node.children.map(child => updateNodeRecursive(child, targetId, updater))
  };
}

function removeNodeRecursive(node: FileNode, targetId: string): FileNode | null {
  if (node.id === targetId) {
    return null;
  }
  
  return {
    ...node,
    children: node.children
      .map(child => removeNodeRecursive(child, targetId))
      .filter((child): child is FileNode => child !== null)
  };
}

function insertNodeInTree(
  tree: FileNode,
  parentId: string | null,
  newNode: FileNode
): FileNode {
  if (parentId === null || tree.id === parentId) {
    // Add to root or this node's children
    return {
      ...tree,
      children: [...tree.children, newNode]
    };
  }
  
  return {
    ...tree,
    children: tree.children.map(child => insertNodeInTree(child, parentId, newNode))
  };
}

// ============================================================================
// ZUSTAND STORE
// ============================================================================

export const useWorkspaceStore = create<WorkspaceState>()(
  devtools(
    persist(
      (set, get) => ({
        // ========== INITIAL STATE ==========
        fileTree: null,
        contentCache: {},
        activePageId: null,
        pendingChanges: new Set(),
        structureDirty: false,
        deletedQueue: new Set(),
        isSyncing: false,
        lastSyncTime: null,
        expandedFolders: new Set<string>(),
        
        // ========== TREE ACTIONS ==========
        
        initializeTree: (tree) => {
          set({ fileTree: tree, structureDirty: false });
        },
        
        addNode: (parentId, type) => {
          const tempId = generateTempId();
          const newNode: FileNode = {
            id: tempId,
            type,
            title: type === 'folder' ? 'New Folder' : 'Untitled Page',
            parentId,
            position: 0, // Will be recalculated
            children: [],
            isEditing: true,
            isTempNode: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
          
          set((state) => {
            if (!state.fileTree) return state;
            
            const updatedTree = insertNodeInTree(state.fileTree, parentId, newNode);
            
            // If it's a page, initialize content cache
            if (type === 'page') {
              return {
                fileTree: updatedTree,
                structureDirty: true,
                contentCache: {
                  ...state.contentCache,
                  [tempId]: {
                    content: '',
                    lastModified: Date.now(),
                    isDirty: true
                  }
                },
                pendingChanges: new Set([...state.pendingChanges, tempId]),
                activePageId: tempId
              };
            }
            
            return {
              fileTree: updatedTree,
              structureDirty: true,
              expandedFolders: parentId 
                ? new Set([...state.expandedFolders, parentId])
                : state.expandedFolders
            };
          });
          
          return tempId;
        },
        
        deleteNode: (nodeId) => {
          set((state) => {
            if (!state.fileTree) return state;
            
            const updatedTree = removeNodeRecursive(state.fileTree, nodeId);
            if (!updatedTree) return state;
            
            // Clean up content cache for deleted pages
            const newContentCache = { ...state.contentCache };
            delete newContentCache[nodeId];
            
            return {
              fileTree: updatedTree,
              structureDirty: true,
              deletedQueue: new Set([...state.deletedQueue, nodeId]),
              contentCache: newContentCache,
              activePageId: state.activePageId === nodeId ? null : state.activePageId
            };
          });
        },
        
        moveNode: (dragId, dropId, position) => {
          set((state) => {
            if (!state.fileTree) return state;
            
            // This is a simplified version - full implementation would need:
            // 1. Remove node from old position
            // 2. Insert at new position based on 'before'|'after'|'inside'
            // 3. Recalculate position numbers for all affected nodes
            
            // For now, just mark structure as dirty
            return {
              structureDirty: true
            };
          });
        },
        
        renameNode: (nodeId, newTitle) => {
          set((state) => {
            if (!state.fileTree) return state;
            
            const updatedTree = updateNodeRecursive(state.fileTree, nodeId, (node) => ({
              ...node,
              title: newTitle,
              updatedAt: new Date().toISOString(),
              isEditing: false
            }));
            
            return {
              fileTree: updatedTree,
              structureDirty: true
            };
          });
        },
        
        duplicateNode: (nodeId) => {
          const node = get().getNodeById(nodeId);
          if (!node) return '';
          
          const tempId = generateTempId();
          const duplicatedNode: FileNode = {
            ...node,
            id: tempId,
            title: `${node.title} (Copy)`,
            isTempNode: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            children: [] // Don't duplicate children for simplicity
          };
          
          set((state) => {
            if (!state.fileTree) return state;
            
            const updatedTree = insertNodeInTree(state.fileTree, node.parentId, duplicatedNode);
            
            // Copy content if it's a page
            if (node.type === 'page' && state.contentCache[nodeId]) {
              return {
                fileTree: updatedTree,
                structureDirty: true,
                contentCache: {
                  ...state.contentCache,
                  [tempId]: {
                    ...state.contentCache[nodeId],
                    isDirty: true
                  }
                },
                pendingChanges: new Set([...state.pendingChanges, tempId])
              };
            }
            
            return {
              fileTree: updatedTree,
              structureDirty: true
            };
          });
          
          return tempId;
        },
        
        // ========== CONTENT ACTIONS ==========
        
        setActivePageId: (pageId) => {
          set({ activePageId: pageId });
        },
        
        updateContent: (pageId, content) => {
          set((state) => ({
            contentCache: {
              ...state.contentCache,
              [pageId]: {
                content,
                lastModified: Date.now(),
                isDirty: true
              }
            },
            pendingChanges: new Set([...state.pendingChanges, pageId])
          }));
        },
        
        loadPageContent: (pageId, content) => {
          set((state) => ({
            contentCache: {
              ...state.contentCache,
              [pageId]: {
                content,
                lastModified: Date.now(),
                isDirty: false
              }
            }
          }));
        },
        
        // ========== EDITING STATE ==========
        
        setNodeEditing: (nodeId, isEditing) => {
          set((state) => {
            if (!state.fileTree) return state;
            
            const updatedTree = updateNodeRecursive(state.fileTree, nodeId, (node) => ({
              ...node,
              isEditing
            }));
            
            return { fileTree: updatedTree };
          });
        },
        
        toggleFolder: (folderId) => {
          set((state) => {
            const newExpanded = new Set(state.expandedFolders);
            if (newExpanded.has(folderId)) {
              newExpanded.delete(folderId);
            } else {
              newExpanded.add(folderId);
            }
            return { expandedFolders: newExpanded };
          });
        },
        
        // ========== SYNC ACTIONS ==========
        
        syncWorkspace: async (orgId, repoId, token, commitMessage) => {
          const state = get();
          
          if (!state.fileTree || state.isSyncing) {
            return;
          }
          
          set({ isSyncing: true });
          
          try {
            // Build sync payload
            const modifiedFiles = Array.from(state.pendingChanges).map(pageId => {
              const cached = state.contentCache[pageId];
              const node = state.getNodeById(pageId);
              
              return {
                pageId,
                path: node?.path || `docs/${node?.title || 'untitled'}.md`,
                content: cached?.content || '',
                action: node?.isTempNode ? 'create' : 'update' as const
              };
            });
            
            const payload: SyncPayload = {
              treeStructure: state.fileTree,
              modifiedFiles,
              deletedNodes: Array.from(state.deletedQueue)
            };
            
            // Default commit message
            const defaultCommitMessage = commitMessage || `docs: Update ${modifiedFiles.length} file(s)`;
            
            // Call backend API with commit message as query parameter
            const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const baseUrl = BACKEND_URL.includes('/api/v1') ? BACKEND_URL : `${BACKEND_URL}/api/v1`;
            const url = new URL(`${baseUrl}/workspace/sync`);
            url.searchParams.set('commit_message', defaultCommitMessage);
            
            const response = await fetch(url.toString(), {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
              },
              body: JSON.stringify({
                org_id: orgId,
                repo_id: repoId,
                ...payload
              })
            });
            
            if (!response.ok) {
              throw new Error('Sync failed');
            }
            
            const result = await response.json();
            
            // Update temp IDs with real IDs from server
            if (result.temp_id_mapping) {
              set((state) => {
                let updatedTree = state.fileTree;
                let updatedCache = { ...state.contentCache };
                
                Object.entries(result.temp_id_mapping).forEach(([tempId, realId]) => {
                  if (updatedTree) {
                    updatedTree = updateNodeRecursive(updatedTree, tempId, (node) => ({
                      ...node,
                      id: realId as string,
                      isTempNode: false
                    }));
                  }
                  
                  // Update content cache
                  if (updatedCache[tempId]) {
                    updatedCache[realId as string] = {
                      ...updatedCache[tempId],
                      isDirty: false
                    };
                    delete updatedCache[tempId];
                  }
                });
                
                return {
                  fileTree: updatedTree,
                  contentCache: updatedCache,
                  pendingChanges: new Set(),
                  structureDirty: false,
                  deletedQueue: new Set(),
                  isSyncing: false,
                  lastSyncTime: Date.now()
                };
              });
            } else {
              // No temp IDs, just clear dirty flags
              set({
                pendingChanges: new Set(),
                structureDirty: false,
                deletedQueue: new Set(),
                isSyncing: false,
                lastSyncTime: Date.now()
              });
            }
            
          } catch (error) {
            console.error('Sync failed:', error);
            set({ isSyncing: false });
            throw error;
          }
        },
        
        clearPendingChanges: () => {
          set({
            pendingChanges: new Set(),
            structureDirty: false,
            deletedQueue: new Set()
          });
        },
        
        // ========== UTILITY ==========
        
        getNodeById: (nodeId) => {
          const state = get();
          return findNodeRecursive(state.fileTree, nodeId);
        },
        
        getNodePath: (nodeId) => {
          const path: FileNode[] = [];
          const state = get();
          
          function buildPath(node: FileNode | null, targetId: string): boolean {
            if (!node) return false;
            
            if (node.id === targetId) {
              path.unshift(node);
              return true;
            }
            
            for (const child of node.children) {
              if (buildPath(child, targetId)) {
                path.unshift(node);
                return true;
              }
            }
            
            return false;
          }
          
          buildPath(state.fileTree, nodeId);
          return path;
        },
        
        hasUnsavedChanges: () => {
          const state = get();
          return state.pendingChanges.size > 0 || state.structureDirty || state.deletedQueue.size > 0;
        }
      }),
      {
        name: 'workspace-storage',
        partialize: (state) => ({
          fileTree: state.fileTree,
          contentCache: state.contentCache,
          expandedFolders: state.expandedFolders instanceof Set 
            ? Array.from(state.expandedFolders)
            : []
        }),
        merge: (persistedState: any, currentState: any) => ({
          ...currentState,
          ...persistedState,
          expandedFolders: new Set(persistedState.expandedFolders || [])
        })
      }
    )
  )
);
