# Unified Workspace Architecture - Implementation Guide

## 📋 Overview

This document outlines the **Local-First, Optimistic UI Architecture** for the Pustak Unified Canvas Editor. The system is designed to provide instant feedback for all editing operations while syncing to the backend only on explicit user action.

---

## 🏗️ Architecture Principles

### 1. **Local-First Editing**
- All operations (add, delete, move, rename) happen **instantly** in the client
- No backend calls during editing
- Changes accumulate in a "pending changes" queue

### 2. **Optimistic UI**
- UI updates immediately on user action
- Backend sync happens asynchronously
- Temporary IDs (e.g., `temp-1234`) are replaced with real IDs after sync

### 3. **Single Source of Truth**
- Global Zustand store (`useWorkspaceStore`) manages all state
- No individual `useState` hooks in components
- Components are pure renderers of store state

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COMPONENT (UI Layer)                          │
│  • SidebarNode: Handles clicks, drags, context menu             │
│  • CanvasEditor: Debounces keystrokes                           │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ dispatch(action)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ZUSTAND STORE (State Manager)                  │
│  • fileTree: Recursive JSON structure                           │
│  • contentCache: { pageId → markdown content }                  │
│  • pendingChanges: Set<pageId>                                  │
│  • structureDirty: Boolean                                      │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ (Immediate re-render)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        UI RE-RENDERS                             │
│  • Tree updates instantly                                        │
│  • Editor content persists across tab switches                  │
└─────────────────────────────────────────────────────────────────┘

             (User clicks "Publish Changes")
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SYNC TO BACKEND (One-Shot)                     │
│  POST /api/v1/workspace/sync                                     │
│  Payload: { treeStructure, modifiedFiles[], deletedNodes[] }    │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ 200 OK + temp_id_mapping
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   UPDATE STORE WITH REAL IDS                     │
│  • Replace temp-1234 → real-uuid-5678                           │
│  • Clear pendingChanges                                          │
│  • Mark structureDirty = false                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ File Structure

```
pustak/
├── src/
│   ├── stores/
│   │   └── useWorkspaceStore.ts          # Global state manager
│   ├── components/
│   │   └── workspace/
│   │       ├── UnifiedWorkspace.tsx      # Main container
│   │       ├── WorkspaceSidebar.tsx      # Sidebar wrapper
│   │       ├── SidebarNode.tsx           # Recursive tree node
│   │       └── CanvasEditor.tsx          # Markdown editor
│   └── lib/
│       └── utils.ts                      # Debounce, throttle utilities
```

---

## 📦 Core Components

### 1. **useWorkspaceStore** (Zustand Store)

**Location:** `src/stores/useWorkspaceStore.ts`

**Key State:**
```typescript
{
  fileTree: FileNode | null,           // Recursive tree structure
  contentCache: { [pageId]: { content, isDirty, lastModified } },
  activePageId: string | null,
  pendingChanges: Set<string>,         // Page IDs with unsaved content
  structureDirty: boolean,             // Tree was modified
  deletedQueue: Set<string>,           // IDs to delete on sync
  isSyncing: boolean,
  expandedFolders: Set<string>
}
```

**Key Actions:**
```typescript
// Tree operations
addNode(parentId, type) → tempId
deleteNode(nodeId)
moveNode(dragId, dropId, position)
renameNode(nodeId, newTitle)

// Content operations
updateContent(pageId, content)       // Marks as dirty
loadPageContent(pageId, content)     // From backend

// Sync
syncWorkspace(orgId, repoId)         // POST to backend
```

---

### 2. **SidebarNode** (Recursive Component)

**Location:** `src/components/workspace/SidebarNode.tsx`

**Features:**
- Renders itself + all children recursively
- **Ghost Input State:** Switches between `<span>` and `<input>` for renaming
- **Context Menu:** Right-click to add/rename/duplicate/delete
- **Expand/Collapse:** For folders

**Props:**
```typescript
{
  node: FileNode,        // Current node
  level: number,         // Indentation depth
  onNodeClick?: (id) => void
}
```

**Key Logic:**
```typescript
// Inline Editing
const [isEditing, setIsEditing] = useState(node.isEditing);

{isEditing ? (
  <input 
    value={editingTitle}
    onBlur={() => renameNode(node.id, editingTitle)}
    onKeyDown={(e) => e.key === 'Enter' && handleRenameSubmit()}
  />
) : (
  <span onDoubleClick={() => setIsEditing(true)}>
    {node.title}
  </span>
)}
```

---

### 3. **CanvasEditor** (Markdown Editor)

**Location:** `src/components/workspace/CanvasEditor.tsx`

**Features:**
- Multi-file aware (content persists when switching tabs)
- Debounced auto-save to store (500ms)
- Shows save status (Saving... / Unpublished changes / All saved)

**Key Logic:**
```typescript
const debouncedSave = useCallback(
  debounce((pageId, content) => {
    updateContent(pageId, content);
  }, 500),
  []
);

// On content change
<textarea 
  value={localContent}
  onChange={(e) => {
    setLocalContent(e.target.value);
    debouncedSave(activePageId, e.target.value);
  }}
/>
```

---

### 4. **WorkspaceSidebar** (Container)

**Location:** `src/components/workspace/WorkspaceSidebar.tsx`

**Features:**
- Renders all root-level nodes via `<SidebarNode>`
- "Add Page" / "Add Folder" buttons
- "Publish Changes" button (only shows when dirty)

---

### 5. **UnifiedWorkspace** (Main Entry Point)

**Location:** `src/components/workspace/UnifiedWorkspace.tsx`

**Features:**
- Loads initial tree from backend on mount
- Split-pane layout: Sidebar (280px) + Editor (flex)

**Usage:**
```tsx
<UnifiedWorkspace orgId="myorg" repoId="myrepo" />
```

---

## 🔄 Sync Flow

### When User Clicks "Publish Changes"

**1. Gather Dirty State**
```typescript
const modifiedFiles = Array.from(pendingChanges).map(pageId => ({
  pageId,
  path: getNodeById(pageId)?.path || 'untitled.md',
  content: contentCache[pageId].content,
  action: node.isTempNode ? 'create' : 'update'
}));

const payload = {
  treeStructure: fileTree,
  modifiedFiles,
  deletedNodes: Array.from(deletedQueue)
};
```

**2. POST to Backend**
```typescript
const response = await fetch('/api/v1/workspace/sync', {
  method: 'POST',
  body: JSON.stringify({ org_id, repo_id, ...payload })
});

const { temp_id_mapping } = await response.json();
// Example: { "temp-1234": "real-uuid-5678" }
```

**3. Update Store with Real IDs**
```typescript
Object.entries(temp_id_mapping).forEach(([tempId, realId]) => {
  // Recursively replace tempId with realId in fileTree
  fileTree = updateNodeRecursive(fileTree, tempId, node => ({
    ...node,
    id: realId,
    isTempNode: false
  }));
  
  // Update contentCache keys
  contentCache[realId] = contentCache[tempId];
  delete contentCache[tempId];
});

// Clear dirty flags
pendingChanges.clear();
structureDirty = false;
deletedQueue.clear();
```

---

## 🎯 Key Implementation Details

### Handling Temp IDs

**Problem:** When a user creates a new page, we need a local ID before the backend assigns a real one.

**Solution:**
```typescript
function generateTempId() {
  return `temp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// Mark as temp
const newNode: FileNode = {
  id: generateTempId(),
  isTempNode: true,  // Visual indicator
  ...
};

// After sync, replace with real ID
const realId = tempIdMapping[tempId];
updateNodeRecursive(tree, tempId, node => ({ ...node, id: realId, isTempNode: false }));
```

---

### Ghost Input State

**Problem:** Inline renaming should feel like Notion (double-click to edit, Enter to save).

**Solution:**
```typescript
const [isEditing, setIsEditing] = useState(node.isEditing);
const inputRef = useRef<HTMLInputElement>(null);

useEffect(() => {
  if (isEditing) {
    inputRef.current?.focus();
    inputRef.current?.select();
  }
}, [isEditing]);

// Render
{isEditing ? (
  <input
    ref={inputRef}
    value={editingTitle}
    onBlur={() => handleRenameSubmit()}
    onKeyDown={(e) => {
      if (e.key === 'Enter') handleRenameSubmit();
      if (e.key === 'Escape') setIsEditing(false);
    }}
  />
) : (
  <span onDoubleClick={() => setIsEditing(true)}>
    {node.title}
  </span>
)}
```

---

### Content Cache Persistence

**Problem:** Switching tabs should not lose unsaved content.

**Solution:**
```typescript
// In CanvasEditor
const [localContent, setLocalContent] = useState('');

useEffect(() => {
  // When activePageId changes, load from cache
  const cached = contentCache[activePageId];
  if (cached) {
    setLocalContent(cached.content);
  }
}, [activePageId]);

// On content change
const handleContentChange = (newContent) => {
  setLocalContent(newContent);  // Update UI immediately
  debouncedSave(activePageId, newContent);  // Save to store after 500ms
};
```

---

## 🚀 Next Steps

### 1. Backend API Endpoint

Create the sync endpoint in FastAPI:

```python
@router.post("/workspace/sync")
async def sync_workspace(
    org_id: str,
    repo_id: str,
    tree_structure: dict,
    modified_files: List[dict],
    deleted_nodes: List[str],
    db: AsyncSession = Depends(get_db)
):
    # 1. Update docbook repo with new files
    # 2. Delete removed files
    # 3. Update tree structure in database
    # 4. Return temp_id_mapping
    
    return {
        "success": True,
        "temp_id_mapping": {
            "temp-1234": "real-uuid-5678"
        }
    }
```

### 2. Drag & Drop

Implement `moveNode` properly using libraries like `react-dnd` or `@dnd-kit/core`.

### 3. Real-Time Collaboration (Optional)

Add WebSocket support for multi-user editing:
- Broadcast tree changes via WebSocket
- Merge conflicts resolution
- Show other users' cursors

### 4. Undo/Redo

Track state history in Zustand:
```typescript
{
  past: FileNode[],
  future: FileNode[],
  undo: () => void,
  redo: () => void
}
```

---

## 📚 Dependencies

```json
{
  "dependencies": {
    "zustand": "^4.5.0",
    "lucide-react": "^0.545.0",
    "react": "^18.0.0"
  }
}
```

**Install:**
```bash
npm install zustand
```

---

## ✅ Testing Checklist

- [ ] Create new page → Shows in tree immediately
- [ ] Type in editor → Debounces to store
- [ ] Switch tabs → Previous content persists
- [ ] Rename node → Inline editing works
- [ ] Delete node → Removed instantly
- [ ] Publish → Backend receives correct payload
- [ ] Temp IDs → Replaced with real IDs after sync
- [ ] Expand/collapse folders → State persists
- [ ] Context menu → All actions work

---

## 🎨 Future Enhancements

1. **Rich Text Editor:** Replace `<textarea>` with BlockNote or TipTap
2. **Live Preview:** Split-pane markdown preview
3. **Search:** Global search across all pages
4. **Version History:** Track document revisions
5. **Templates:** Pre-built page templates
6. **Keyboard Shortcuts:** Cmd+K command palette

---

## 📞 Support

For questions or issues, refer to:
- Zustand docs: https://zustand-demo.pmnd.rs/
- Pustak backend API docs: http://localhost:8000/docs

---

**Architecture Status:** ✅ Complete  
**Implementation Status:** 🚧 Ready for Integration  
**Last Updated:** December 24, 2025
