# 🧪 Unified Workspace - Testing Guide

## Quick Start Testing Flow

### 1️⃣ Install Dependencies
```bash
cd pustak
npm install
```

### 2️⃣ Start Frontend
```bash
npm run dev
```
Frontend runs at: **http://localhost:3000**

### 3️⃣ Navigate to Workspace
```
http://localhost:3000/workspace/{org}/{repo}
```

Example:
```
http://localhost:3000/workspace/midnight-testing/midnight
```

---

## 📋 Complete Testing Checklist

### Phase 1: Initial Load
- [ ] **Page loads without errors**
- [ ] **Loading spinner shows** while fetching tree
- [ ] **Sidebar renders** with empty state or existing tree
- [ ] **Editor shows** "No page selected" message

### Phase 2: Create Operations (Local-First)

#### Test 2.1: Add Root Page
**Steps:**
1. Click "Page" button in sidebar header
2. **Expected:**
   - New page appears in tree with "Untitled Page" title
   - Input field is focused (editing mode)
   - Page has "New" badge (temp node)
   - Editor opens with empty content
   - "1 unsaved" badge appears in header
   - "Publish Changes (1)" button appears

#### Test 2.2: Add Root Folder
**Steps:**
1. Click "Folder" button in sidebar header
2. **Expected:**
   - New folder appears with "New Folder" title
   - Input field is focused
   - Folder has collapse icon
   - "New" badge visible

#### Test 2.3: Add Nested Page
**Steps:**
1. Right-click on a folder
2. Select "Add Page Inside"
3. **Expected:**
   - Folder auto-expands
   - New page appears as child
   - Input focused for naming

### Phase 3: Rename Operations

#### Test 3.1: Inline Rename
**Steps:**
1. Double-click any page/folder title
2. Type new name
3. Press Enter
4. **Expected:**
   - Input switches to span
   - Title updates immediately
   - "Publish Changes" button updates count

#### Test 3.2: Rename via Context Menu
**Steps:**
1. Right-click page/folder
2. Select "Rename"
3. Type new name
4. Click outside input
5. **Expected:**
   - Same as inline rename

#### Test 3.3: Rename Cancel
**Steps:**
1. Double-click title
2. Start typing
3. Press Escape
4. **Expected:**
   - Reverts to original title
   - No change tracked

### Phase 4: Delete Operations

#### Test 4.1: Delete Page
**Steps:**
1. Right-click page
2. Select "Delete"
3. Confirm dialog
4. **Expected:**
   - Page removed from tree instantly
   - If it was active, editor shows "No page selected"
   - Content removed from cache
   - Deletion tracked in publish count

#### Test 4.2: Delete Folder
**Steps:**
1. Right-click folder
2. Select "Delete"
3. **Expected:**
   - Folder and all children removed
   - Multiple deletions tracked

### Phase 5: Content Editing

#### Test 5.1: Type in Editor
**Steps:**
1. Click a page in sidebar
2. Type content in editor
3. **Expected:**
   - "Saving..." appears (with clock icon)
   - After 500ms: "Unpublished changes" shows
   - Word count updates in footer
   - Change count increments

#### Test 5.2: Switch Pages Without Losing Content
**Steps:**
1. Click Page A
2. Type "Content A"
3. Click Page B
4. Type "Content B"
5. Click Page A again
6. **Expected:**
   - Page A still shows "Content A"
   - Page B still shows "Content B"
   - No content lost

#### Test 5.3: Rapid Tab Switching
**Steps:**
1. Click between 3+ pages rapidly
2. **Expected:**
   - No lag or flickering
   - Each page shows correct content
   - Debounce prevents excessive saves

### Phase 6: Publish Flow (Backend Sync)

#### Test 6.1: Successful Publish
**Steps:**
1. Make changes (add page, edit content, rename)
2. Click "Publish Changes (3)"
3. **Expected:**
   - Button shows "Publishing..." with spinner
   - Request sent to backend
   - On success:
     - "All changes saved" toast
     - "New" badges removed
     - Unsaved count = 0
     - Temp IDs replaced with real IDs

#### Test 6.2: Publish with Backend Error
**Steps:**
1. Make changes
2. Stop backend server
3. Click "Publish Changes"
4. **Expected:**
   - Error toast appears
   - Changes remain in pending queue
   - Can retry after backend restart

#### Test 6.3: Multiple Publish Cycles
**Steps:**
1. Publish changes
2. Wait for success
3. Make new changes
4. Publish again
5. **Expected:**
   - Each cycle works independently
   - No duplicate requests
   - Temp IDs consistently replaced

### Phase 7: Edge Cases

#### Test 7.1: Empty Title
**Steps:**
1. Rename page to empty string
2. Press Enter
3. **Expected:**
   - Reverts to original title
   - No empty nodes created

#### Test 7.2: Duplicate Names
**Steps:**
1. Create two pages with same name
2. **Expected:**
   - Both allowed (backend will handle path uniqueness)

#### Test 7.3: Deep Nesting
**Steps:**
1. Create folder → subfolder → page
2. Collapse/expand all levels
3. **Expected:**
   - All levels render correctly
   - Indentation increases properly
   - No visual glitches

#### Test 7.4: Simultaneous Edits
**Steps:**
1. Type in editor
2. While "Saving..." shows, switch to another page
3. **Expected:**
   - First page saves successfully
   - No race conditions

---

## 🔧 Manual Testing Script

Run this sequence for comprehensive testing:

```bash
# Terminal 1: Start backend (if needed)
cd /Users/harshsrivastava/Desktop/doc_ai
uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd /Users/harshsrivastava/Desktop/doc_ai/pustak
npm run dev

# Browser: Open
http://localhost:3000/workspace/midnight-testing/midnight
```

### Step-by-Step Test Script

```
1. LOAD TEST
   → Navigate to workspace URL
   ✓ Sidebar loads
   ✓ No console errors

2. CREATE TEST
   → Click "Page" button
   → Type "Getting Started"
   → Press Enter
   ✓ Page appears in tree
   ✓ Editor opens with empty content

3. EDIT TEST
   → Type: "# Welcome\n\nThis is a test page."
   → Wait 1 second
   ✓ "Unpublished changes" shows
   ✓ Word count shows: 5 words

4. MULTI-TAB TEST
   → Click "Page" button again
   → Type "API Reference"
   → Press Enter
   → Type: "API docs here"
   → Click back to "Getting Started"
   ✓ Original content preserved
   ✓ Both pages tracked as dirty

5. FOLDER TEST
   → Click "Folder" button
   → Type "Documentation"
   → Press Enter
   → Right-click "Documentation"
   → Add Page Inside
   → Type "Overview"
   ✓ Nested structure works
   ✓ Folder expands automatically

6. RENAME TEST
   → Double-click "Getting Started"
   → Change to "Introduction"
   → Press Enter
   ✓ Title updates immediately
   ✓ Still marked as dirty

7. DELETE TEST
   → Right-click "API Reference"
   → Delete → Confirm
   ✓ Page removed from tree
   ✓ If active, editor clears

8. PUBLISH TEST
   → Click "Publish Changes"
   ✓ Button shows "Publishing..."
   ✓ On success: "All changes saved"
   ✓ "New" badges removed
   ✓ Unsaved count = 0

9. PERSISTENCE TEST
   → Refresh page (Cmd+R)
   ✓ Tree structure persists (from localStorage)
   ✓ Last active page remembered

10. CONTEXT MENU TEST
    → Right-click various nodes
    ✓ Menu appears at cursor
    ✓ All actions work:
      - Add Page
      - Add Folder
      - Rename
      - Duplicate
      - Delete
```

---

## 🐛 Common Issues & Debug Tips

### Issue 1: "Module not found: zustand"
**Fix:**
```bash
cd pustak
npm install zustand
```

### Issue 2: Tree doesn't load
**Debug:**
```typescript
// Check browser console
// Look for error from:
GET /api/v1/workspace/{org}/{repo}/tree

// If 404, create mock endpoint or initialize empty tree
```

### Issue 3: Publish button doesn't work
**Debug:**
```typescript
// Check Network tab
POST /api/v1/workspace/sync

// Verify payload structure:
{
  org_id: "...",
  repo_id: "...",
  treeStructure: {...},
  modifiedFiles: [...],
  deletedNodes: [...]
}
```

### Issue 4: Content not saving
**Debug:**
```typescript
// Open React DevTools
// Inspect useWorkspaceStore state
// Check:
- contentCache[pageId] exists?
- pendingChanges.has(pageId)?
- Debounce working?
```

### Issue 5: Temp IDs not replaced
**Debug:**
```typescript
// Check backend response
{
  temp_id_mapping: {
    "temp-1234": "real-uuid-5678"  // ✅ Should exist
  }
}

// If missing, backend needs to return this
```

---

## 📊 Expected State Flow

```
INITIAL STATE:
{
  fileTree: null,
  contentCache: {},
  activePageId: null,
  pendingChanges: Set(),
  structureDirty: false
}

↓ User clicks "Add Page"

{
  fileTree: { children: [{ id: "temp-123", title: "Untitled", isTempNode: true }] },
  contentCache: { "temp-123": { content: "", isDirty: true } },
  activePageId: "temp-123",
  pendingChanges: Set(["temp-123"]),
  structureDirty: true
}

↓ User types content

{
  contentCache: { "temp-123": { content: "Hello", isDirty: true } },
  // ... rest unchanged
}

↓ User clicks "Publish"

API Request:
POST /api/v1/workspace/sync
{
  treeStructure: {...},
  modifiedFiles: [{ pageId: "temp-123", content: "Hello", action: "create" }]
}

API Response:
{
  success: true,
  temp_id_mapping: { "temp-123": "real-uuid-abc" }
}

↓ Store updates

{
  fileTree: { children: [{ id: "real-uuid-abc", title: "Untitled", isTempNode: false }] },
  contentCache: { "real-uuid-abc": { content: "Hello", isDirty: false } },
  activePageId: "real-uuid-abc",
  pendingChanges: Set(),
  structureDirty: false
}
```

---

## 🎯 Success Criteria

✅ **All operations instant** (no backend wait)  
✅ **No content loss** when switching tabs  
✅ **Temp IDs replaced** after publish  
✅ **Tree persists** in localStorage  
✅ **Context menu** works on all nodes  
✅ **Debounce prevents** excessive saves  
✅ **Error handling** for failed publishes  
✅ **Visual feedback** for all states (saving, dirty, synced)

---

## 🚀 Next: Automated Tests

Once manual testing passes, create:

```typescript
// __tests__/workspace.test.ts
describe('Unified Workspace', () => {
  it('should create temp node on add page', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    const tempId = result.current.addNode(null, 'page');
    expect(tempId).toMatch(/^temp-/);
    expect(result.current.structureDirty).toBe(true);
  });
  
  // ... more tests
});
```

---

**Ready to test!** Start with Phase 1 and work through each phase sequentially.
