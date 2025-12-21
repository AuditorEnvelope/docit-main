# Multi-File Workspace Implementation Plan

## Overview
This document outlines the implementation of a GitBook/Mintlify-style multi-file workspace for Pustak, transforming it from a single-page editor to a comprehensive documentation management system.

## Architecture

### Phase 1: Core Contexts & State Management ✅

**Created Files:**
1. `src/contexts/ProjectStructureContext.tsx` - Manages the file tree structure
2. `src/contexts/EditorSessionContext.tsx` - Manages open files and tabs
3. `src/hooks/useDocbookAPI.ts` - API hooks for backend communication

**Key Features:**
- Mutable file tree structure
- Optimistic UI updates
- Dirty state tracking
- File creation, deletion, and movement

### Phase 2: Interactive Sidebar ✅

**Created File:**
- `src/components/InteractiveSidebar.tsx`

**Features:**
- Drag-and-drop reordering (using @dnd-kit)
- Inline file creation (ghost "+ Add Page" buttons)
- Real-time structure updates
- Visual dirty state indicators

### Phase 3: Tabbed Editor Interface ✅

**Created File:**
- `src/components/TabbedEditor.tsx`

**Features:**
- Multi-tab support (VS Code/Notion style)
- Tab switching without losing state
- Dirty state indicators on tabs
- Close tab functionality

### Phase 4: Bulk Commit System ✅

**Created File:**
- `src/components/BulkCommitModal.tsx`

**Features:**
- Lists all modified files
- Single commit for multiple files
- Auto-generated commit messages
- Always commits to staging branch

## Next Steps

### 1. Backend API Endpoints (Required)

Create these endpoints in `app/api/v1/endpoints/docbook.py`:

```python
@router.post("/docbook/create-page")
async def create_page(
    request: CreatePageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new markdown file in the docbook repository."""
    # Implementation: Create file via GitHub API
    pass

@router.put("/docbook/update-structure")
async def update_structure(
    request: UpdateStructureRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the documentation structure (reordering, moving files)."""
    # Implementation: Update SUMMARY.md or docs.json
    pass

@router.put("/docbook/bulk-save")
async def bulk_save(
    request: BulkSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Commit multiple files in a single commit."""
    # Implementation: Create single commit with multiple file changes
    pass
```

### 2. Frontend API Routes (Required)

Create these Next.js API routes in `pustak/src/app/api/docbook/`:

- `create-page/route.ts` - Proxy to backend
- `update-structure/route.ts` - Proxy to backend
- `bulk-save/route.ts` - Proxy to backend

### 3. Integration with Main Page

Update `pustak/src/app/repo/[...slug]/page.tsx` to:
- Wrap with `ProjectStructureProvider` and `EditorSessionProvider`
- Replace `EnhancedSidebar` with `InteractiveSidebar`
- Replace single editor with `TabbedEditor`
- Add `BulkCommitModal` to header

### 4. Structure Initialization

Add logic to:
- Fetch structure from backend on mount
- Convert backend structure format to `FileNode[]`
- Populate `ProjectStructureContext`

### 5. File Content Fetching

Update `EditorSessionContext` to:
- Fetch file content from backend when opening a file
- Cache content to avoid re-fetching
- Sync with `ProjectStructureContext`

## Dependencies Added

```json
{
  "@dnd-kit/core": "^6.1.0",
  "@dnd-kit/sortable": "^8.0.0",
  "@dnd-kit/utilities": "^3.2.2"
}
```

Run: `npm install` to install these packages.

## Usage Example

```tsx
// Wrap your app with providers
<ProjectStructureProvider>
  <EditorSessionProvider>
    <Layout>
      <InteractiveSidebar orgId={orgId} repoId={repoId} persona={persona} />
      <TabbedEditor />
      <BulkCommitModal 
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        orgId={orgId}
        repoId={repoId}
        persona={persona}
      />
    </Layout>
  </EditorSessionProvider>
</ProjectStructureProvider>
```

## Key Design Decisions

1. **Optimistic Updates**: UI updates immediately, then syncs with backend
2. **Context-Based State**: Shared state across components via React Context
3. **Dirty State Tracking**: Files marked as dirty when content changes
4. **Single Commit Flow**: All changes committed together to staging
5. **No Page Reloads**: All navigation happens client-side

## Testing Checklist

- [ ] Create new file via sidebar
- [ ] Drag and drop files to reorder
- [ ] Open multiple files in tabs
- [ ] Edit multiple files
- [ ] Bulk commit all changes
- [ ] Verify structure persists after refresh
- [ ] Test error handling (network failures, etc.)

## Future Enhancements

1. **Folder Creation**: Add ability to create folders inline
2. **File Deletion**: Add delete functionality with confirmation
3. **File Renaming**: Inline rename capability
4. **Search**: Global search across all files
5. **Keyboard Shortcuts**: Cmd+S to save, Cmd+W to close tab, etc.
6. **Undo/Redo**: Per-file undo/redo stack
7. **Collaboration**: Real-time collaborative editing

