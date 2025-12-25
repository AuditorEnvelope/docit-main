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
    path: string; // Full file path (e.g., "dev/architecture/current.md")
    content: string;
    action: 'create' | 'update';
  }[];
  deletedNodes: string[]; // File paths to delete
  tempIdMapping?: { [tempId: string]: string }; // Map temp IDs to real IDs after sync
}

export interface WorkspaceState {
  // ========== STATE ==========
  fileTree: FileNode | null;
  contentCache: ContentCache;
  activePageId: string | null;
  pendingChanges: Set<string>; // Page IDs with unsaved content
  structureDirty: boolean; // True if tree was modified (add/delete/move/rename)
  deletedPaths: Set<string>; // File paths to delete on sync
  isSyncing: boolean;
  lastSyncTime: number | null;
  
  // Sidebar state
  expandedFolders: Set<string>; // Folder IDs that are expanded
  
  // ========== ACTIONS ==========
  
  // Tree Structure Actions (Instant, No Backend)
  initializeTree: (tree: FileNode) => void;
  addNode: (parentId: string | null, type: NodeType, afterNodeId?: string) => string; // Returns temp ID
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

/**
 * Get the file path for a node to use in Git operations
 * - For existing nodes: use the stored path field
 * - For new nodes (temp IDs): build path from tree structure
 */
function getNodeFilePath(tree: FileNode, nodeId: string, repoId?: string): string | null {
  // Find the node first
  const node = findNodeRecursive(tree, nodeId);
  if (!node) return null;
  
  // If node has a path already (loaded from backend), use it
  if (node.path) {
    return node.path;
  }
  
  // For new nodes, build the path
  // We need to traverse from root to build: {repoId}/docs/path/to/file.md
  const pathParts: string[] = [];
  let current: FileNode | null = node;
  
  // Traverse up to root, collecting titles
  while (current && current.id !== 'root') {
    if (current.type === 'page') {
      pathParts.unshift(`${current.title}.md`);
    } else {
      pathParts.unshift(current.title);
    }
    
    // Find parent
    if (current.parentId) {
      current = findNodeRecursive(tree, current.parentId);
    } else {
      break;
    }
  }
  
  // For new nodes, we need repoId to build full path
  // Since we don't have it here, return relative path and let sync handle it
  return pathParts.join('/');
}

/**
 * Collect all file paths under a node (for folder deletion)
 * Must build from tree root to get full paths
 */
function collectAllPathsFromTree(tree: FileNode, node: FileNode): string[] {
  const paths: string[] = [];
  
  function collectRecursive(n: FileNode): void {
    if (n.type === 'page') {
      const path = getNodeFilePath(tree, n.id);
      if (path) paths.push(path);
    } else if (n.children.length === 0) {
      // Empty folder - track .gitkeep
      const path = getNodeFilePath(tree, n.id);
      if (path) {
        // Add .gitkeep to folder path
        paths.push(`${path}/.gitkeep`);
      }
    } else {
      // Folder with children
      n.children.forEach(collectRecursive);
    }
  }
  
  collectRecursive(node);
  return paths;
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
  newNode: FileNode,
  afterNodeId?: string
): FileNode {
  if (parentId === null || tree.id === parentId) {
    // Add to root or this node's children
    if (afterNodeId) {
      // Find the position after the specified node
      const afterIndex = tree.children.findIndex(child => child.id === afterNodeId);
      if (afterIndex !== -1) {
        const newChildren = [...tree.children];
        newChildren.splice(afterIndex + 1, 0, newNode);
        return {
          ...tree,
          children: newChildren
        };
      }
    }
    // Default: append to end
    return {
      ...tree,
      children: [...tree.children, newNode]
    };
  }
  
  return {
    ...tree,
    children: tree.children.map(child => insertNodeInTree(child, parentId, newNode, afterNodeId))
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
        deletedPaths: new Set(),
        isSyncing: false,
        lastSyncTime: null,
        expandedFolders: new Set<string>(),
        
        // ========== TREE ACTIONS ==========
        
        initializeTree: (tree) => {
          set({ fileTree: tree, structureDirty: false });
        },
        
        addNode: (parentId, type, afterNodeId) => {
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
            
            const updatedTree = insertNodeInTree(state.fileTree, parentId, newNode, afterNodeId);
            
            // For pages: initialize content cache and mark as pending
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
            
            // For folders: just mark structure as dirty
            // The folder will be represented by .gitkeep or by its children's paths
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
            
            // Get the node before deletion to collect its paths
            const nodeToDelete = findNodeRecursive(state.fileTree, nodeId);
            if (!nodeToDelete) return state;
            
            // Collect all file paths that need to be deleted (with full paths from root)
            const pathsToDelete = collectAllPathsFromTree(state.fileTree, nodeToDelete);
            
            const updatedTree = removeNodeRecursive(state.fileTree, nodeId);
            if (!updatedTree) return state;
            
            // Clean up content cache for deleted pages
            const newContentCache = { ...state.contentCache };
            const newPendingChanges = new Set(state.pendingChanges);
            
            // Remove from cache and pending changes
            if (nodeToDelete.type === 'page') {
              delete newContentCache[nodeId];
              newPendingChanges.delete(nodeId);
            }
            
            // Recursively clean cache for folder children
            function cleanCache(node: FileNode) {
              if (node.type === 'page') {
                delete newContentCache[node.id];
                newPendingChanges.delete(node.id);
              }
              node.children.forEach(cleanCache);
            }
            if (nodeToDelete.type === 'folder') {
              nodeToDelete.children.forEach(cleanCache);
            }
            
            return {
              fileTree: updatedTree,
              structureDirty: true,
              deletedPaths: new Set([...state.deletedPaths, ...pathsToDelete]),
              contentCache: newContentCache,
              pendingChanges: newPendingChanges,
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
            
            const updatedTree = insertNodeInTree(state.fileTree, node.parentId, duplicatedNode, nodeId);
            
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
            // Build list of modified files (pages with content changes)
            const modifiedFiles: { path: string; content: string; action: 'create' | 'update' }[] = [];
            
            // Process pages with content changes
            for (const pageId of state.pendingChanges) {
              const cached = state.contentCache[pageId];
              const node = state.getNodeById(pageId);
              
              if (!node || node.type !== 'page') continue;
              
              // Get file path - will use node.path if exists, or build for new nodes
              let filePath = getNodeFilePath(state.fileTree, pageId);
              if (!filePath) continue;
              
              // For new nodes (temp IDs), prefix with {repoId}/docs/
              if (node.isTempNode && !filePath.startsWith(`${repoId}/docs/`)) {
                filePath = `${repoId}/docs/${filePath}`;
              }
              
              modifiedFiles.push({
                path: filePath,
                content: cached?.content || '',
                action: node.isTempNode ? 'create' : 'update'
              });
            }
            
            // If tree structure changed, collect .gitkeep files for empty folders
            if (state.structureDirty) {
              function collectEmptyFolders(node: FileNode): void {
                if (node.type === 'folder' && node.children.length === 0 && node.id !== 'root') {
                  // Get folder path
                  let folderPath = getNodeFilePath(state.fileTree, node.id);
                  if (!folderPath) return;
                  
                  // For new folders, prefix with {repoId}/docs/
                  if (node.isTempNode && !folderPath.startsWith(`${repoId}/docs/`)) {
                    folderPath = `${repoId}/docs/${folderPath}`;
                  }
                  
                  modifiedFiles.push({
                    path: `${folderPath}/.gitkeep`,
                    content: '',
                    action: node.isTempNode ? 'create' : 'update'
                  });
                }
                
                // Recursively check children
                for (const child of node.children) {
                  collectEmptyFolders(child);
                }
              }
              
              collectEmptyFolders(state.fileTree);
            }
            
            const payload: SyncPayload = {
              treeStructure: state.fileTree,
              modifiedFiles,
              deletedNodes: Array.from(state.deletedPaths)
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
                  deletedPaths: new Set(),
                  isSyncing: false,
                  lastSyncTime: Date.now()
                };
              });
            } else {
              // No temp IDs, just clear dirty flags
              set({
                pendingChanges: new Set(),
                structureDirty: false,
                deletedPaths: new Set(),
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
            deletedPaths: new Set()
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
          return state.pendingChanges.size > 0 || state.structureDirty || state.deletedPaths.size > 0;
        },
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
