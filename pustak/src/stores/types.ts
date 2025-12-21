/**
 * Draft Store Types
 * Defines the shape of our local-first state management system
 */

export type FileNodeType = "file" | "folder";

export interface FileNode {
  id: string; // Unique ID - can be temporary for new files (e.g., "temp_123")
  name: string;
  type: FileNodeType;
  path: string; // Full path from root (e.g., "docs/dev/architecture/current.md")
  parentId: string | null;
  children?: FileNode[];
  content?: string; // Cached content for open files
  isTemporary?: boolean; // True for newly created items not yet saved to server
  sha?: string; // GitHub SHA for existing files
}

export interface OpenFile {
  id: string;
  path: string;
  name: string;
  content: string;
  isDirty: boolean; // Has unsaved changes
  cursorPosition?: number;
  scrollPosition?: number;
}

export interface FileChange {
  type: "create" | "update" | "delete" | "rename" | "move";
  fileId: string;
  path: string;
  oldPath?: string; // For rename/move operations
  content?: string; // For create/update
  parentId?: string; // For create/move
  sha?: string; // For update/delete (GitHub requires this)
}

export interface StructureChange {
  type: "reorder" | "nest" | "unnest";
  nodeId: string;
  newParentId: string | null;
  newIndex: number;
}

export interface PendingChanges {
  files: Map<string, FileChange>; // Key is fileId
  structure: StructureChange[];
  deletedFileIds: Set<string>;
}

export interface DraftState {
  // File Tree
  fileTree: FileNode[];
  fileTreeMap: Map<string, FileNode>; // Quick lookup by ID
  
  // Open Files & Tabs
  openFiles: Map<string, OpenFile>; // Key is fileId
  activeFileId: string | null;
  
  // Pending Changes
  pendingChanges: PendingChanges;
  
  // Metadata
  orgId: string | null;
  repoId: string | null;
  persona: "dev" | "internal";
  
  // Loading States
  isLoadingTree: boolean;
  isSaving: boolean;
  lastSyncedAt: Date | null;
  
  // Sync status
  unsavedChangesCount: number;
}

export interface DraftActions {
  // Initialization
  initializeTree: (tree: FileNode[], orgId: string, repoId: string, persona: "dev" | "internal") => void;
  setPersona: (persona: "dev" | "internal") => void;
  
  // File Tree Operations (Local Only)
  addFile: (parentId: string | null, name: string) => string; // Returns new file ID
  addFolder: (parentId: string | null, name: string) => string;
  deleteNode: (fileId: string) => void;
  renameNode: (fileId: string, newName: string) => void;
  moveNode: (fileId: string, newParentId: string | null, newIndex: number) => void;
  
  // File Content Operations
  openFile: (fileId: string) => Promise<void>;
  closeFile: (fileId: string) => void;
  updateFileContent: (fileId: string, content: string) => void;
  setActiveFile: (fileId: string | null) => void;
  
  // Bulk Save
  bulkCommit: () => Promise<void>;
  discardChanges: () => void;
  
  // Utilities
  getUnsavedChanges: () => FileChange[];
  hasUnsavedChanges: () => boolean;
  getFileById: (fileId: string) => FileNode | undefined;
  getFileByPath: (path: string) => FileNode | undefined;
  
  // Reset
  reset: () => void;
}

export type DraftStore = DraftState & DraftActions;
