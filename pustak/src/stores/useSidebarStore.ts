import { create } from "zustand";
import { produce } from "immer";

export interface SidebarNode {
  id: string; // Unique ID (path-based or temp ID)
  name: string;
  type: "file" | "folder";
  path: string; // Full path from repo root
  content?: string; // For files
  children?: SidebarNode[]; // For folders
  isEditing?: boolean; // For inline renaming
  isExpanded?: boolean; // For folders
  isDirty?: boolean; // Track if file has unsaved changes
  isNew?: boolean; // Track if this is a newly created node (not yet saved)
}

interface SidebarState {
  // Tree structure
  tree: SidebarNode[];
  
  // Server state (for diff detection)
  serverTree: SidebarNode[];
  
  // Track deleted IDs (for commit) - using array instead of Set for Immer compatibility
  deletedIds: string[];
  
  // Track renamed nodes (oldPath -> newPath) - using object instead of Map for Immer compatibility
  renamedNodes: Record<string, string>;
  
  // Metadata
  orgId: string;
  repoId: string;
  persona: string;
  
  // Actions
  initialize: (tree: SidebarNode[], orgId: string, repoId: string, persona: string) => void;
  addNode: (parentId: string | null, type: "file" | "folder") => string; // Returns new node ID
  deleteNode: (nodeId: string) => void;
  updateNodeName: (nodeId: string, newName: string) => void;
  toggleExpanded: (nodeId: string) => void;
  moveNode: (nodeId: string, targetParentId: string | null, index?: number) => void;
  setEditing: (nodeId: string, isEditing: boolean) => void;
  updateFileContent: (nodeId: string, content: string) => void;
  markDirty: (nodeId: string, isDirty: boolean) => void;
  
  // Sync actions
  commitChanges: (onFileRenamed?: (oldPath: string, newPath: string) => void, onFileDeleted?: (path: string) => void) => Promise<void>; // Save to server
  resetToServerState: () => void; // Discard local changes
  hasUncommittedChanges: () => boolean;
  
  // Helpers
  findNode: (nodeId: string, nodes?: SidebarNode[]) => SidebarNode | null;
  findNodeParent: (nodeId: string, nodes?: SidebarNode[], parent?: SidebarNode) => { node: SidebarNode; parent: SidebarNode | null; siblings: SidebarNode[] } | null;
}

// Helper functions that work with draft state (inside produce)
function findNodeInDraft(nodeId: string, nodes: SidebarNode[]): SidebarNode | null {
  for (const node of nodes) {
    if (node.id === nodeId) return node;
    if (node.children) {
      const found = findNodeInDraft(nodeId, node.children);
      if (found) return found;
    }
  }
  return null;
}

function findNodeParentInDraft(
  nodeId: string,
  nodes: SidebarNode[],
  parent: SidebarNode | null = null
): { node: SidebarNode; parent: SidebarNode | null; siblings: SidebarNode[] } | null {
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    if (node.id === nodeId) {
      return {
        node,
        parent,
        siblings: nodes,
      };
    }
    if (node.children) {
      const found = findNodeParentInDraft(nodeId, node.children, node);
      if (found) return found;
    }
  }
  return null;
}

export const useSidebarStore = create<SidebarState>()((set, get) => ({
    tree: [],
    serverTree: [],
    deletedIds: [],
    renamedNodes: {},
    orgId: "",
    repoId: "",
    persona: "",

    initialize: (tree, orgId, repoId, persona) => {
      set(
        produce((state: SidebarState) => {
          state.tree = tree;
          state.serverTree = JSON.parse(JSON.stringify(tree)); // Deep clone
          state.orgId = orgId;
          state.repoId = repoId;
          state.persona = persona;
          state.deletedIds = [];
          state.renamedNodes = {};
        })
      );
    },

    findNode: (nodeId, nodes) => {
      const searchNodes = nodes || get().tree;
      for (const node of searchNodes) {
        if (node.id === nodeId) return node;
        if (node.children) {
          const found = get().findNode(nodeId, node.children);
          if (found) return found;
        }
      }
      return null;
    },

    findNodeParent: (nodeId, nodes, parent) => {
      const searchNodes = nodes || get().tree;
      for (let i = 0; i < searchNodes.length; i++) {
        const node = searchNodes[i];
        if (node.id === nodeId) {
          return {
            node,
            parent: parent || null,
            siblings: searchNodes,
          };
        }
        if (node.children) {
          const found = get().findNodeParent(nodeId, node.children, node);
          if (found) return found;
        }
      }
      return null;
    },

    addNode: (parentId, type) => {
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const defaultName = type === "file" ? "Untitled.md" : "Untitled";
      
      set(
        produce((state: SidebarState) => {
          const newNode: SidebarNode = {
            id: tempId,
            name: defaultName,
            type,
            path: "", // Will be set when saved
            isEditing: true,
            isNew: true,
            isExpanded: type === "folder",
            children: type === "folder" ? [] : undefined,
          };

          if (parentId === null) {
            // Add to root
            state.tree.push(newNode);
          } else {
            // Find parent in draft state
            const parent = findNodeInDraft(parentId, state.tree);
            if (parent && parent.type === "folder") {
              if (!parent.children) {
                parent.children = [];
              }
              parent.children.push(newNode);
              parent.isExpanded = true; // Auto-expand parent when adding child
            }
          }
        })
      );

      return tempId;
    },

    deleteNode: (nodeId) => {
      set(
        produce((state: SidebarState) => {
          const result = findNodeParentInDraft(nodeId, state.tree);
          if (!result) return;

          const { siblings } = result;
          const index = siblings.findIndex((n) => n.id === nodeId);
          if (index !== -1) {
            siblings.splice(index, 1);
            if (!state.deletedIds.includes(nodeId)) {
              state.deletedIds.push(nodeId);
            }
          }
        })
      );
    },

    updateNodeName: (nodeId, newName) => {
      set(
        produce((state: SidebarState) => {
          const node = findNodeInDraft(nodeId, state.tree);
          if (!node) return;

          const oldPath = node.path;
          node.name = newName;
          node.isEditing = false;

          // Update path if it exists
          if (oldPath) {
            const pathParts = oldPath.split("/");
            pathParts[pathParts.length - 1] = newName;
            const newPath = pathParts.join("/");
            node.path = newPath;
            state.renamedNodes[oldPath] = newPath;
          }
        })
      );
    },

    toggleExpanded: (nodeId) => {
      set(
        produce((state: SidebarState) => {
          const node = findNodeInDraft(nodeId, state.tree);
          if (node && node.type === "folder") {
            node.isExpanded = !node.isExpanded;
          }
        })
      );
    },

    moveNode: (nodeId, targetParentId, index) => {
      set(
        produce((state: SidebarState) => {
          const result = findNodeParentInDraft(nodeId, state.tree);
          if (!result) return;

          const { node, siblings } = result;
          const nodeIndex = siblings.findIndex((n) => n.id === nodeId);
          if (nodeIndex === -1) return;

          // Remove from current location
          siblings.splice(nodeIndex, 1);

          // Add to target location
          if (targetParentId === null) {
            // Move to root
            if (index !== undefined) {
              state.tree.splice(index, 0, node);
            } else {
              state.tree.push(node);
            }
          } else {
            const targetParent = findNodeInDraft(targetParentId, state.tree);
            if (targetParent && targetParent.type === "folder") {
              if (!targetParent.children) {
                targetParent.children = [];
              }
              if (index !== undefined) {
                targetParent.children.splice(index, 0, node);
              } else {
                targetParent.children.push(node);
              }
              targetParent.isExpanded = true;
            }
          }
        })
      );
    },

    setEditing: (nodeId, isEditing) => {
      set(
        produce((state: SidebarState) => {
          const node = findNodeInDraft(nodeId, state.tree);
          if (node) {
            node.isEditing = isEditing;
          }
        })
      );
    },

    updateFileContent: (nodeId, content) => {
      set(
        produce((state: SidebarState) => {
          const node = findNodeInDraft(nodeId, state.tree);
          if (node && node.type === "file") {
            node.content = content;
          }
        })
      );
    },

    markDirty: (nodeId, isDirty) => {
      set(
        produce((state: SidebarState) => {
          const node = findNodeInDraft(nodeId, state.tree);
          if (node) {
            node.isDirty = isDirty;
          }
        })
      );
    },

    hasUncommittedChanges: () => {
      const state = get();
      return (
        state.deletedIds.length > 0 ||
        Object.keys(state.renamedNodes).length > 0 ||
        JSON.stringify(state.tree) !== JSON.stringify(state.serverTree)
      );
    },

    commitChanges: async (onFileRenamed, onFileDeleted) => {
      const state = get();
      const token = localStorage.getItem("pustak_access_token");
      if (!token) throw new Error("Not authenticated");

      const rollbackActions: Array<() => void> = [];
      const savedNodeData = new Map<string, SidebarNode>(); // For rollback

      try {
        // Helper to normalize paths (remove repo prefix)
        const normalizePath = (path: string): string => {
          if (!path) return "";
          // Remove repoId prefix if present
          if (path.startsWith(`${state.repoId}/`)) {
            return path.slice(state.repoId.length + 1);
          }
          // Remove first segment if it's not "docs"
          const segments = path.split("/");
          if (segments.length > 1 && segments[0] && !segments[0].startsWith("docs")) {
            return segments.slice(1).join("/");
          }
          return path;
        };

        // 1. Collect all new nodes (isNew: true)
        const newNodes: SidebarNode[] = [];
        const collectNewNodes = (nodes: SidebarNode[]) => {
          for (const node of nodes) {
            if (node.isNew && node.type === "file") {
              newNodes.push(node);
            }
            if (node.children) {
              collectNewNodes(node.children);
            }
          }
        };
        collectNewNodes(state.tree);

        // 2. Create new nodes
        for (const node of newNodes) {
          const savedNode = JSON.parse(JSON.stringify(node));
          savedNodeData.set(node.id, savedNode);

          // Find parent node to get the correct parent path
          const parentResult = get().findNodeParent(node.id);
          let relativeParentPath = "";
          
          if (parentResult && parentResult.parent) {
            // Parent exists - extract path relative to docs/persona
            const parentPath = parentResult.parent.path || "";
            // Remove repoId/docs/persona prefix
            const prefix = `${state.repoId}/docs/${state.persona}`;
            if (parentPath.startsWith(prefix)) {
              relativeParentPath = parentPath.slice(prefix.length);
              if (relativeParentPath.startsWith("/")) {
                relativeParentPath = relativeParentPath.slice(1);
              }
            } else {
              // Try alternative: remove first segment (repo name)
              const segments = parentPath.split("/");
              const personaIndex = segments.findIndex(s => s === state.persona);
              if (personaIndex >= 0 && personaIndex < segments.length - 1) {
                relativeParentPath = segments.slice(personaIndex + 1).join("/");
              }
            }
          }

          const response = await fetch("/api/docbook/create-page", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              org_id: state.orgId,
              repo_id: state.repoId,
              persona: state.persona,
              parent_path: relativeParentPath,
              fileName: node.name,
              content: node.content || "",
            }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || `Failed to create page: ${node.name}`);
          }

          const createdNode = await response.json();
          
          // Rollback action
          rollbackActions.push(() => {
            set(
              produce((draft: SidebarState) => {
                const found = findNodeInDraft(createdNode.path || node.id, draft.tree);
                if (found && savedNode) {
                  Object.assign(found, savedNode);
                }
              })
            );
          });

          // Update node with server response
          set(
            produce((draft: SidebarState) => {
              const found = findNodeInDraft(node.id, draft.tree);
              if (found && createdNode.path) {
                found.path = createdNode.path;
                found.id = createdNode.path;
                found.isNew = false;
              }
            })
          );
        }

        // 3. Delete nodes
        for (const deletedId of [...state.deletedIds]) {
          const node = state.findNode(deletedId);
          if (!node || !node.path || node.type !== "file") continue;

          const savedNode = JSON.parse(JSON.stringify(node));
          const normalizedPath = normalizePath(node.path);

          const response = await fetch("/api/docbook/delete-page", {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              org_id: state.orgId,
              repo_id: state.repoId,
              persona: state.persona,
              file_path: normalizedPath,
            }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || `Failed to delete page: ${node.name}`);
          }

          // Notify EditorSessionContext
          if (onFileDeleted) {
            onFileDeleted(node.path);
          }

          // Rollback: re-add the node
          rollbackActions.push(() => {
            set(
              produce((draft: SidebarState) => {
                const result = findNodeParentInDraft(deletedId, draft.tree);
                if (result && savedNode) {
                  result.siblings.push(savedNode);
                }
              })
            );
          });
        }

        // 4. Rename nodes
        for (const [oldPath, newPath] of Object.entries(state.renamedNodes)) {
          const node = state.findNode(newPath);
          if (!node || node.type !== "file") continue;

          const savedNode = JSON.parse(JSON.stringify(node));
          savedNode.path = oldPath;
          savedNode.id = oldPath;

          const normalizedOldPath = normalizePath(oldPath);
          const normalizedNewPath = normalizePath(newPath);

          const response = await fetch("/api/docbook/rename-page", {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              org_id: state.orgId,
              repo_id: state.repoId,
              persona: state.persona,
              old_path: normalizedOldPath,
              new_path: normalizedNewPath,
            }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || `Failed to rename page: ${oldPath}`);
          }

          // Notify EditorSessionContext
          if (onFileRenamed) {
            onFileRenamed(oldPath, newPath);
          }

          // Rollback: restore old path
          rollbackActions.push(() => {
            set(
              produce((draft: SidebarState) => {
                const found = findNodeInDraft(newPath, draft.tree);
                if (found) {
                  found.path = oldPath;
                  found.id = oldPath;
                  found.name = oldPath.split("/").pop() || found.name;
                }
              })
            );
          });
        }

        // 5. Update structure (for reordering/moving)
        const convertToFileNode = (node: SidebarNode): any => {
          const fileNode: any = {
            name: node.name,
            type: node.type,
            path: node.path,
          };
          if (node.children) {
            fileNode.children = node.children.map(convertToFileNode);
          }
          return fileNode;
        };

        const structure = state.tree.map(convertToFileNode);
        const structureResponse = await fetch("/api/docbook/update-structure", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            org_id: state.orgId,
            repo_id: state.repoId,
            persona: state.persona,
            structure,
          }),
        });

        if (!structureResponse.ok) {
          const error = await structureResponse.json().catch(() => ({}));
          throw new Error(error.detail || error.message || "Failed to update structure");
        }

        // All successful - update serverTree and clear change tracking
        set(
          produce((draft: SidebarState) => {
            draft.serverTree = JSON.parse(JSON.stringify(draft.tree));
            draft.deletedIds = [];
            draft.renamedNodes = {};
          })
        );
      } catch (error) {
        // Rollback all changes
        console.error("Error committing changes, rolling back:", error);
        for (const rollback of rollbackActions.reverse()) {
          try {
            rollback();
          } catch (rollbackError) {
            console.error("Error during rollback:", rollbackError);
          }
        }
        throw error;
      }
    },

    resetToServerState: () => {
      set(
        produce((state: SidebarState) => {
          state.tree = JSON.parse(JSON.stringify(state.serverTree));
          state.deletedIds = [];
          state.renamedNodes = {};
        })
      );
    },
  }));
