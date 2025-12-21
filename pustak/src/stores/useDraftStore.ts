/**
 * Draft Store Implementation
 * A Zustand store for local-first file management with bulk commits
 * Inspired by VS Code and GitBook's architecture
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type {
  DraftStore,
  FileNode,
  OpenFile,
  FileChange,
  PendingChanges,
} from './types';

// Helper: Generate temporary ID
const generateTempId = () => `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Helper: Build file tree map for quick lookups
const buildFileTreeMap = (nodes: FileNode[]): Map<string, FileNode> => {
  const map = new Map<string, FileNode>();
  
  const traverse = (node: FileNode) => {
    map.set(node.id, node);
    if (node.children) {
      node.children.forEach(traverse);
    }
  };
  
  nodes.forEach(traverse);
  return map;
};

// Helper: Calculate full path for a node
const calculatePath = (
  node: FileNode,
  fileTreeMap: Map<string, FileNode>,
  repoId: string,
  persona: string
): string => {
  const parts: string[] = [];
  let currentNode: FileNode | undefined = node;
  
  while (currentNode) {
    parts.unshift(currentNode.name);
    currentNode = currentNode.parentId ? fileTreeMap.get(currentNode.parentId) : undefined;
  }
  
  return `${repoId}/docs/${persona}/${parts.join('/')}`;
};

// Helper: Update paths recursively
const updateNodePaths = (
  node: FileNode,
  fileTreeMap: Map<string, FileNode>,
  repoId: string,
  persona: string
) => {
  node.path = calculatePath(node, fileTreeMap, repoId, persona);
  if (node.children) {
    node.children.forEach(child => updateNodePaths(child, fileTreeMap, repoId, persona));
  }
};

// Initial state
const initialState = {
  fileTree: [],
  fileTreeMap: new Map<string, FileNode>(),
  openFiles: new Map<string, OpenFile>(),
  activeFileId: null,
  pendingChanges: {
    files: new Map<string, FileChange>(),
    structure: [],
    deletedFileIds: new Set<string>(),
  } as PendingChanges,
  orgId: null,
  repoId: null,
  persona: 'dev' as const,
  isLoadingTree: false,
  isSaving: false,
  lastSyncedAt: null,
  unsavedChangesCount: 0,
};

export const useDraftStore = create<DraftStore>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // ============================================
      // INITIALIZATION
      // ============================================
      
      initializeTree: (tree, orgId, repoId, persona) => {
        set((state) => {
          state.fileTree = tree;
          state.fileTreeMap = buildFileTreeMap(tree);
          state.orgId = orgId;
          state.repoId = repoId;
          state.persona = persona;
          state.lastSyncedAt = new Date();
        });
      },

      setPersona: (persona) => {
        set((state) => {
          state.persona = persona;
          // Recalculate all paths with new persona
          state.fileTree.forEach(node => 
            updateNodePaths(node, state.fileTreeMap, state.repoId!, persona)
          );
        });
      },

      // ============================================
      // FILE TREE OPERATIONS (Local Only)
      // ============================================
      
      addFile: (parentId, name) => {
        const tempId = generateTempId();
        const { repoId, persona, fileTreeMap } = get();
        
        set((state) => {
          const newFile: FileNode = {
            id: tempId,
            name: name.endsWith('.md') ? name : `${name}.md`,
            type: 'file',
            path: '', // Will be calculated below
            parentId,
            isTemporary: true,
            content: '',
          };

          // Calculate path
          newFile.path = calculatePath(newFile, fileTreeMap, repoId!, persona);

          // Add to tree
          if (parentId) {
            const parent = state.fileTreeMap.get(parentId);
            if (parent && parent.type === 'folder') {
              parent.children = parent.children || [];
              parent.children.push(newFile);
            }
          } else {
            state.fileTree.push(newFile);
          }

          // Update map
          state.fileTreeMap.set(tempId, newFile);

          // Track as pending change
          state.pendingChanges.files.set(tempId, {
            type: 'create',
            fileId: tempId,
            path: newFile.path,
            content: '',
            parentId,
          });

          state.unsavedChangesCount++;
        });

        return tempId;
      },

      addFolder: (parentId, name) => {
        const tempId = generateTempId();
        const { repoId, persona, fileTreeMap } = get();
        
        set((state) => {
          const newFolder: FileNode = {
            id: tempId,
            name,
            type: 'folder',
            path: '', // Will be calculated below
            parentId,
            children: [],
            isTemporary: true,
          };

          // Calculate path
          newFolder.path = calculatePath(newFolder, fileTreeMap, repoId!, persona);

          // Add to tree
          if (parentId) {
            const parent = state.fileTreeMap.get(parentId);
            if (parent && parent.type === 'folder') {
              parent.children = parent.children || [];
              parent.children.push(newFolder);
            }
          } else {
            state.fileTree.push(newFolder);
          }

          // Update map
          state.fileTreeMap.set(tempId, newFolder);

          // Folders are virtual - no pending change needed
          // They'll be created when files inside them are saved
        });

        return tempId;
      },

      deleteNode: (fileId) => {
        set((state) => {
          const node = state.fileTreeMap.get(fileId);
          if (!node) return;

          // Remove from tree
          const removeFromTree = (nodes: FileNode[]): FileNode[] => {
            return nodes.filter(n => {
              if (n.id === fileId) return false;
              if (n.children) {
                n.children = removeFromTree(n.children);
              }
              return true;
            });
          };

          state.fileTree = removeFromTree(state.fileTree);

          // Remove from map (recursively for folders)
          const removeFromMap = (nodeId: string) => {
            const n = state.fileTreeMap.get(nodeId);
            if (n?.children) {
              n.children.forEach(child => removeFromMap(child.id));
            }
            state.fileTreeMap.delete(nodeId);
          };
          removeFromMap(fileId);

          // Track deletion if not temporary
          if (!node.isTemporary) {
            state.pendingChanges.deletedFileIds.add(fileId);
            state.pendingChanges.files.set(fileId, {
              type: 'delete',
              fileId,
              path: node.path,
              sha: node.sha,
            });
            state.unsavedChangesCount++;
          } else {
            // Remove from pending creates if temporary
            state.pendingChanges.files.delete(fileId);
            state.unsavedChangesCount = Math.max(0, state.unsavedChangesCount - 1);
          }

          // Close file if open
          if (state.openFiles.has(fileId)) {
            state.openFiles.delete(fileId);
            if (state.activeFileId === fileId) {
              state.activeFileId = null;
            }
          }
        });
      },

      renameNode: (fileId, newName) => {
        const { repoId, persona, fileTreeMap } = get();
        
        set((state) => {
          const node = state.fileTreeMap.get(fileId);
          if (!node) return;

          const oldPath = node.path;
          node.name = node.type === 'file' && !newName.endsWith('.md') 
            ? `${newName}.md` 
            : newName;

          // Recalculate path
          updateNodePaths(node, state.fileTreeMap, repoId!, persona);

          // Track rename if not temporary
          if (!node.isTemporary) {
            state.pendingChanges.files.set(fileId, {
              type: 'rename',
              fileId,
              path: node.path,
              oldPath,
              sha: node.sha,
            });
            state.unsavedChangesCount++;
          }

          // Update open file if exists
          const openFile = state.openFiles.get(fileId);
          if (openFile) {
            openFile.name = node.name;
            openFile.path = node.path;
          }
        });
      },

      moveNode: (fileId, newParentId, newIndex) => {
        const { repoId, persona, fileTreeMap } = get();
        
        set((state) => {
          const node = state.fileTreeMap.get(fileId);
          if (!node) return;

          const oldPath = node.path;
          const oldParentId = node.parentId;

          // Remove from old parent
          if (oldParentId) {
            const oldParent = state.fileTreeMap.get(oldParentId);
            if (oldParent?.children) {
              oldParent.children = oldParent.children.filter(c => c.id !== fileId);
            }
          } else {
            state.fileTree = state.fileTree.filter(n => n.id !== fileId);
          }

          // Add to new parent
          node.parentId = newParentId;
          if (newParentId) {
            const newParent = state.fileTreeMap.get(newParentId);
            if (newParent?.children) {
              newParent.children.splice(newIndex, 0, node);
            }
          } else {
            state.fileTree.splice(newIndex, 0, node);
          }

          // Recalculate paths
          updateNodePaths(node, state.fileTreeMap, repoId!, persona);

          // Track move if not temporary
          if (!node.isTemporary) {
            state.pendingChanges.files.set(fileId, {
              type: 'move',
              fileId,
              path: node.path,
              oldPath,
              parentId: newParentId,
              sha: node.sha,
            });
            state.unsavedChangesCount++;
          }
        });
      },

      // ============================================
      // FILE CONTENT OPERATIONS
      // ============================================
      
      openFile: async (fileId) => {
        const { fileTreeMap, openFiles } = get();
        const node = fileTreeMap.get(fileId);
        
        if (!node || node.type !== 'file') return;
        if (openFiles.has(fileId)) {
          // Already open, just activate
          set({ activeFileId: fileId });
          return;
        }

        // TODO: Fetch content from server if not cached
        // For now, use cached content or empty string
        const content = node.content || '';

        set((state) => {
          state.openFiles.set(fileId, {
            id: fileId,
            path: node.path,
            name: node.name,
            content,
            isDirty: false,
          });
          state.activeFileId = fileId;
        });
      },

      closeFile: (fileId) => {
        set((state) => {
          state.openFiles.delete(fileId);
          if (state.activeFileId === fileId) {
            // Set active to first remaining open file or null
            const remainingFiles = Array.from(state.openFiles.keys());
            state.activeFileId = remainingFiles[0] || null;
          }
        });
      },

      updateFileContent: (fileId, content) => {
        set((state) => {
          const openFile = state.openFiles.get(fileId);
          const node = state.fileTreeMap.get(fileId);
          
          if (openFile) {
            const wasClean = !openFile.isDirty;
            openFile.content = content;
            openFile.isDirty = true;
            
            if (wasClean) {
              state.unsavedChangesCount++;
            }
          }

          if (node) {
            node.content = content;
          }

          // Track as pending update
          const existingChange = state.pendingChanges.files.get(fileId);
          if (!existingChange || existingChange.type === 'update') {
            state.pendingChanges.files.set(fileId, {
              type: node?.isTemporary ? 'create' : 'update',
              fileId,
              path: node?.path || '',
              content,
              sha: node?.sha,
            });
          } else {
            // Preserve existing change type but update content
            existingChange.content = content;
          }
        });
      },

      setActiveFile: (fileId) => {
        set({ activeFileId: fileId });
      },

      // ============================================
      // BULK COMMIT
      // ============================================
      
      bulkCommit: async () => {
        const { pendingChanges, orgId, repoId, persona } = get();
        
        set({ isSaving: true });

        try {
          // TODO: Implement actual API calls
          // This is where you'd call your backend bulk-save endpoint
          
          const changes = Array.from(pendingChanges.files.values());
          console.log('🚀 Committing changes:', {
            orgId,
            repoId,
            persona,
            changes,
            deletedFiles: Array.from(pendingChanges.deletedFileIds),
          });

          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 1000));

          // On success: clear pending changes and mark files as saved
          set((state) => {
            state.pendingChanges.files.clear();
            state.pendingChanges.deletedFileIds.clear();
            state.pendingChanges.structure = [];
            state.unsavedChangesCount = 0;
            state.lastSyncedAt = new Date();
            
            // Mark all open files as clean
            state.openFiles.forEach(file => {
              file.isDirty = false;
            });

            // Remove temporary flags from nodes
            state.fileTreeMap.forEach(node => {
              if (node.isTemporary) {
                node.isTemporary = false;
                // TODO: Update with real ID and SHA from server response
              }
            });
          });

          console.log('✅ Changes committed successfully');
        } catch (error) {
          console.error('❌ Failed to commit changes:', error);
          throw error;
        } finally {
          set({ isSaving: false });
        }
      },

      discardChanges: () => {
        set((state) => {
          // Remove temporary nodes
          const removeTemporary = (nodes: FileNode[]): FileNode[] => {
            return nodes
              .filter(n => !n.isTemporary)
              .map(n => ({
                ...n,
                children: n.children ? removeTemporary(n.children) : undefined,
              }));
          };

          state.fileTree = removeTemporary(state.fileTree);
          state.fileTreeMap = buildFileTreeMap(state.fileTree);

          // Close dirty files
          const filesToClose: string[] = [];
          state.openFiles.forEach((file, id) => {
            if (file.isDirty) {
              filesToClose.push(id);
            }
          });
          filesToClose.forEach(id => state.openFiles.delete(id));

          // Clear pending changes
          state.pendingChanges.files.clear();
          state.pendingChanges.deletedFileIds.clear();
          state.pendingChanges.structure = [];
          state.unsavedChangesCount = 0;
        });
      },

      // ============================================
      // UTILITIES
      // ============================================
      
      getUnsavedChanges: () => {
        const { pendingChanges } = get();
        return Array.from(pendingChanges.files.values());
      },

      hasUnsavedChanges: () => {
        const { unsavedChangesCount } = get();
        return unsavedChangesCount > 0;
      },

      getFileById: (fileId) => {
        return get().fileTreeMap.get(fileId);
      },

      getFileByPath: (path) => {
        const { fileTreeMap } = get();
        return Array.from(fileTreeMap.values()).find(node => node.path === path);
      },

      reset: () => {
        set(initialState);
      },
    })),
    { name: 'DraftStore' }
  )
);
