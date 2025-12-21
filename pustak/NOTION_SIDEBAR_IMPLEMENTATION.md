# Notion-Style Sidebar Implementation

## Overview

This document describes the complete refactor of the File Explorer to replicate Notion's sidebar behavior with optimistic UI updates, clean aesthetics, and infinite nesting support.

## Architecture

### 1. Zustand Store (`useSidebarStore.ts`)

**Location**: `pustak/src/stores/useSidebarStore.ts`

The store manages all sidebar state with optimistic updates:

- **State**:
  - `tree`: Current local tree structure (with optimistic changes)
  - `serverTree`: Last known server state (for diff detection)
  - `deletedIds`: Set of deleted node IDs (for commit)
  - `renamedNodes`: Map of oldPath -> newPath (for commit)
  - `orgId`, `repoId`, `persona`: Metadata

- **Key Actions**:
  - `initialize()`: Load initial tree from server
  - `addNode()`: Instantly add node to tree (optimistic)
  - `deleteNode()`: Instantly remove node (optimistic)
  - `updateNodeName()`: Update node name locally
  - `toggleExpanded()`: Expand/collapse folders
  - `moveNode()`: Move nodes (for drag & drop)
  - `commitChanges()`: Save all changes to server
  - `resetToServerState()`: Discard local changes
  - `hasUncommittedChanges()`: Check if there are pending changes

### 2. NotionSidebarItem Component

**Location**: `pustak/src/components/NotionSidebarItem.tsx`

Recursive component that renders each file/folder row:

**Features**:
- **Hover States**: Add/Delete buttons only visible on hover (`opacity-0` → `opacity-100`)
- **Inline Editing**: Click to rename, input appears with auto-focus
- **Context Menu**: Radix UI dropdown with Rename/Delete options
- **Infinite Nesting**: Recursively renders children
- **Indent Guides**: Subtle vertical lines showing hierarchy depth

**Props**:
- `node`: SidebarNode to render
- `depth`: Current nesting depth (for indentation)
- `onFileClick`: Callback when file is clicked

### 3. NotionSidebar Component

**Location**: `pustak/src/components/NotionSidebar.tsx`

Main wrapper component that:
- Initializes the Zustand store with FileNode data
- Renders the tree using NotionSidebarItem
- Provides header with persona switcher
- Shows uncommitted changes indicator

### 4. Converter Utilities

**Location**: `pustak/src/lib/sidebarNodeConverter.ts`

Converts between `FileNode` (from ProjectStructureContext) and `SidebarNode` (for Zustand store):

- `convertFileNodeToSidebarNode()`: FileNode → SidebarNode
- `convertSidebarNodeToFileNode()`: SidebarNode → FileNode

## Usage

### Integration in Workspace Page

The workspace page (`pustak/src/app/workspace/[org]/[repo]/page.tsx`) now uses `NotionSidebar`:

```tsx
<NotionSidebar
  orgId={orgId}
  repoId={repoId}
  persona={persona}
  onPersonaChange={setPersona}
  initialTree={structure?.root || []}
/>
```

### Save Changes Flow

1. User makes changes (add/delete/rename) → Updates happen instantly in Zustand store
2. "Save Changes" button lights up when `hasUncommittedChanges()` returns true
3. On click:
   - `commitChanges()` is called (currently just syncs serverTree)
   - Then opens BulkCommitModal for file content changes

## Styling (Tailwind)

- **Spacing**: Compact, dense (Notion style)
- **Typography**: Subtle font weight, `text-sm`
- **Selected State**: `bg-slate-100/10` or `hover:bg-slate-800/40`
- **Indent Guides**: `bg-slate-800/30` vertical lines
- **Hover Controls**: `opacity-0 group-hover:opacity-100`

## Next Steps

1. **Implement `commitChanges()` API call**: Currently it just syncs `serverTree`. Need to:
   - Send deleted IDs to backend
   - Send renamed nodes to backend
   - Send new nodes to backend
   - Update structure via `/api/docbook/update-structure`

2. **Drag & Drop**: The `moveNode()` function exists but needs DnD integration

3. **File Content Sync**: When files are renamed/deleted, update EditorSessionContext

4. **Error Handling**: Add error states and rollback for failed commits

## Key Differences from Old Implementation

| Old (InteractiveSidebar) | New (NotionSidebar) |
|--------------------------|---------------------|
| Direct API calls on every action | Optimistic updates, batch commit |
| Permanent "+ Add Page" buttons | Hidden until hover |
| No inline renaming | Inline editing with input |
| Context menu via custom div | Radix UI DropdownMenu |
| React Context for state | Zustand store |
| No uncommitted changes tracking | Full diff tracking |

## Files Created

1. `pustak/src/stores/useSidebarStore.ts` - Zustand store
2. `pustak/src/components/NotionSidebarItem.tsx` - Recursive row component
3. `pustak/src/components/NotionSidebar.tsx` - Main sidebar wrapper
4. `pustak/src/lib/sidebarNodeConverter.ts` - Conversion utilities

## Files Modified

1. `pustak/src/app/workspace/[org]/[repo]/page.tsx` - Uses NotionSidebar instead of InteractiveSidebar

