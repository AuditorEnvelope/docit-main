# Draft Store Architecture Documentation

## Overview

This is a **local-first state management system** for documentation editing, inspired by VS Code and GitBook. It implements a "draft with bulk commits" pattern that prevents UI race conditions and provides a smooth editing experience.

## Architecture Principles

### 1. **Local-First Operations**
- All user interactions (create, delete, rename, move) happen **instantly** in local state
- No waiting for server responses
- UI updates are immediate and optimistic

### 2. **Bulk Commits**
- Changes are tracked in a `pendingChanges` object
- A single "Save Changes" button commits all modifications at once
- Reduces API calls and prevents race conditions

### 3. **Temporary IDs**
- New files/folders get temporary IDs (e.g., `temp_1234567890_abc123`)
- After successful commit, these are replaced with real server IDs
- Allows instant UI updates without server round-trips

## Core Data Structures

### FileNode
```typescript
interface FileNode {
  id: string;              // Unique ID (temporary or real)
  name: string;            // File/folder name
  type: "file" | "folder"; // Node type
  path: string;            // Full path (e.g., "repo/docs/dev/api.md")
  parentId: string | null; // Parent node ID
  children?: FileNode[];   // Child nodes (for folders)
  content?: string;        // Cached content (for open files)
  isTemporary?: boolean;   // True for unsaved nodes
  sha?: string;            // GitHub SHA (for existing files)
}
```

### PendingChanges
```typescript
interface PendingChanges {
  files: Map<string, FileChange>;  // All file modifications
  structure: StructureChange[];    // Tree reordering
  deletedFileIds: Set<string>;     // Deleted nodes
}
```

### FileChange
```typescript
interface FileChange {
  type: "create" | "update" | "delete" | "rename" | "move";
  fileId: string;
  path: string;
  oldPath?: string;   // For rename/move
  content?: string;   // For create/update
  parentId?: string;  // For create/move
  sha?: string;       // For update/delete
}
```

## Store API

### Initialization
```typescript
// Initialize the store with server data
initializeTree(tree: FileNode[], orgId: string, repoId: string, persona: "dev" | "internal"): void

// Switch persona (dev/internal)
setPersona(persona: "dev" | "internal"): void
```

### File Tree Operations (All Local)
```typescript
// Add new file - returns temporary ID
addFile(parentId: string | null, name: string): string

// Add new folder - returns temporary ID
addFolder(parentId: string | null, name: string): string

// Delete node (moves to deletedFileIds)
deleteNode(fileId: string): void

// Rename node (tracks in pendingChanges)
renameNode(fileId: string, newName: string): void

// Move node to new parent/position
moveNode(fileId: string, newParentId: string | null, newIndex: number): void
```

### File Content Operations
```typescript
// Open file in editor (fetches content if needed)
openFile(fileId: string): Promise<void>

// Close file tab
closeFile(fileId: string): void

// Update file content (marks as dirty)
updateFileContent(fileId: string, content: string): void

// Set active tab
setActiveFile(fileId: string | null): void
```

### Bulk Commit
```typescript
// Save all pending changes to server
bulkCommit(): Promise<void>

// Discard all local changes
discardChanges(): void
```

### Utilities
```typescript
// Get list of all unsaved changes
getUnsavedChanges(): FileChange[]

// Check if there are unsaved changes
hasUnsavedChanges(): boolean

// Get node by ID
getFileById(fileId: string): FileNode | undefined

// Get node by path
getFileByPath(path: string): FileNode | undefined
```

## State Structure

```typescript
{
  // File tree (hierarchical)
  fileTree: FileNode[],
  
  // Quick lookup map
  fileTreeMap: Map<string, FileNode>,
  
  // Open files (tabs)
  openFiles: Map<string, OpenFile>,
  activeFileId: string | null,
  
  // Pending changes (to be committed)
  pendingChanges: {
    files: Map<string, FileChange>,
    structure: StructureChange[],
    deletedFileIds: Set<string>
  },
  
  // Metadata
  orgId: string | null,
  repoId: string | null,
  persona: "dev" | "internal",
  
  // Loading states
  isLoadingTree: boolean,
  isSaving: boolean,
  lastSyncedAt: Date | null,
  
  // Unsaved changes counter
  unsavedChangesCount: number
}
```

## Usage Example

### 1. Initialize on Page Load
```typescript
import { useDraftStore } from '@/stores';

function WorkspacePage() {
  const initializeTree = useDraftStore(s => s.initializeTree);
  
  useEffect(() => {
    // Fetch tree from server
    const tree = await fetchTreeFromServer(orgId, repoId, persona);
    
    // Initialize store
    initializeTree(tree, orgId, repoId, persona);
  }, []);
}
```

### 2. Add File (Instant UI Update)
```typescript
function Sidebar() {
  const addFile = useDraftStore(s => s.addFile);
  const unsavedCount = useDraftStore(s => s.unsavedChangesCount);
  
  const handleAddPage = (parentId: string | null) => {
    // This is INSTANT - no API call
    const newFileId = addFile(parentId, 'new-page.md');
    console.log('Created file with temp ID:', newFileId);
    // UI updates immediately!
  };
  
  return (
    <div>
      <button onClick={() => handleAddPage(null)}>
        + Add Page
      </button>
      {unsavedCount > 0 && (
        <span>({unsavedCount} unsaved changes)</span>
      )}
    </div>
  );
}
```

### 3. Delete File (Instant Removal)
```typescript
function FileItem({ fileId }) {
  const deleteNode = useDraftStore(s => s.deleteNode);
  
  const handleDelete = () => {
    // Removes from tree instantly
    deleteNode(fileId);
    // UI updates immediately!
  };
  
  return (
    <button onClick={handleDelete}>
      Delete
    </button>
  );
}
```

### 4. Edit File Content
```typescript
function Editor() {
  const activeFileId = useDraftStore(s => s.activeFileId);
  const openFiles = useDraftStore(s => s.openFiles);
  const updateFileContent = useDraftStore(s => s.updateFileContent);
  
  const activeFile = activeFileId ? openFiles.get(activeFileId) : null;
  
  const handleChange = (newContent: string) => {
    if (activeFileId) {
      // Marks file as dirty, tracks in pendingChanges
      updateFileContent(activeFileId, newContent);
    }
  };
  
  return (
    <textarea
      value={activeFile?.content || ''}
      onChange={(e) => handleChange(e.target.value)}
    />
  );
}
```

### 5. Bulk Commit (Save All Changes)
```typescript
function SaveButton() {
  const bulkCommit = useDraftStore(s => s.bulkCommit);
  const isSaving = useDraftStore(s => s.isSaving);
  const unsavedCount = useDraftStore(s => s.unsavedChangesCount);
  const hasChanges = unsavedCount > 0;
  
  const handleSave = async () => {
    try {
      await bulkCommit();
      toast.success('All changes saved!');
    } catch (error) {
      toast.error('Failed to save changes');
    }
  };
  
  return (
    <button
      onClick={handleSave}
      disabled={!hasChanges || isSaving}
    >
      {isSaving ? 'Saving...' : `Save Changes (${unsavedCount})`}
    </button>
  );
}
```

## Migration Path

### Phase 1: Dual Mode (Current + New)
- Keep existing `ProjectStructureContext` working
- Initialize `useDraftStore` in parallel
- Use conversion utilities to sync between them
- Test thoroughly

### Phase 2: Component Migration
- Migrate Sidebar to use `useDraftStore`
- Migrate Editor to use `useDraftStore`
- Remove dependencies on old context

### Phase 3: Cleanup
- Remove `ProjectStructureContext`
- Remove `EditorSessionContext` (replaced by store)
- Remove old API hooks

## Benefits

### ✅ **No More Race Conditions**
- All operations are synchronous (local state updates)
- Server calls only happen on bulk commit
- No "stale state" issues

### ✅ **Instant UI Updates**
- Add file? Instant.
- Delete file? Instant.
- Rename file? Instant.
- Users see changes immediately

### ✅ **Better UX**
- "Save Changes" button shows pending work
- Users control when to sync
- Can work offline, commit later

### ✅ **Fewer API Calls**
- One bulk commit instead of N individual calls
- Reduces server load
- Faster overall experience

### ✅ **Undo/Redo Ready**
- All changes tracked in pendingChanges
- Easy to implement undo/redo
- Can discard all changes at once

## Next Steps

1. **Update Sidebar Component** to use the new store
2. **Update Editor Component** to use the new store
3. **Implement Bulk Commit API** in backend
4. **Add Visual Indicators** for unsaved changes
5. **Add Confirmation Dialog** for discard changes
6. **Add Keyboard Shortcuts** (Cmd+S for save)
7. **Add Auto-Save** (optional, every N minutes)

## Files Created

- `pustak/src/stores/types.ts` - TypeScript interfaces
- `pustak/src/stores/useDraftStore.ts` - Zustand store implementation
- `pustak/src/stores/utils.ts` - Helper utilities
- `pustak/src/stores/index.ts` - Public exports

## Dependencies Added

- `zustand` - State management
- `immer` - Immutable updates (Zustand middleware)
