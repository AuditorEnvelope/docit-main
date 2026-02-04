# Workspace Refactor: Code Editor → Writer's Room

## Problem Summary
The workspace feels like VS Code (file icons, rigid tree, technical) instead of Notion/GitBook (fluid, typographic, content-focused).

## Critical Bug Fix

### Issue: Editor Loses Focus on Every Keystroke
**Root Cause**: In `BlockNoteEditorClient.tsx` (lines 32-64), the `useEffect` with `initialContent` dependency re-parses and replaces blocks on EVERY content change, destroying editor state.

**Fix Strategy**:
1. Only initialize once when component mounts OR when `initialContent` prop actually changes from parent
2. Use a ref to track if this is user typing vs external content change
3. Skip re-initialization during user typing

### Fixed Code for BlockNoteEditorClient.tsx

```typescript
// Replace lines 24-94 with this:

export default function BlockNoteEditorClient({
  initialContent,
  onChange,
  editable = true,
  className = "",
}: BlockNoteEditorClientProps) {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  
  const [isInitialized, setIsInitialized] = useState(false);
  const lastExternalContentRef = useRef<string>("");
  const isUserTypingRef = useRef(false);

  // Create the editor instance ONCE
  const editor = useCreateBlockNote({});

  // Initialize editor with markdown content ONLY on mount or external content change
  useEffect(() => {
    if (!editor) return;

    // Skip if this is user typing (not external change)
    if (isUserTypingRef.current) {
      return;
    }

    // Skip if content hasn't actually changed from external source
    if (lastExternalContentRef.current === initialContent && isInitialized) {
      return;
    }

    const initializeContent = async () => {
      try {
        const blocks = editor.tryParseMarkdownToBlocks(initialContent || "");
        if (blocks && blocks.length > 0) {
          editor.replaceBlocks(editor.document, blocks);
        } else {
          editor.replaceBlocks(editor.document, []);
        }

        lastExternalContentRef.current = initialContent || "";
        setIsInitialized(true);
      } catch (error) {
        console.error("Error initializing editor:", error);
        setIsInitialized(true);
      }
    };

    initializeContent();
  }, [editor, initialContent, isInitialized]);

  // Handle content changes from user typing
  useEffect(() => {
    if (!onChangeRef.current || !editable || !editor || !isInitialized) return;

    const handleChange = () => {
      isUserTypingRef.current = true;

      try {
        const markdown = editor.blocksToMarkdownLossy(editor.document);
        if (markdown !== lastExternalContentRef.current) {
          onChangeRef.current?.(markdown);
        }
      } catch (error) {
        console.error("Error converting blocks to markdown:", error);
      }

      // Reset user typing flag after short delay
      setTimeout(() => {
        isUserTypingRef.current = false;
      }, 100);
    };

    editor.onChange(handleChange);
  }, [editor, editable, isInitialized]);

  return (
    <div className={`blocknote-editor ${className}`}>
      <BlockNoteView editor={editor} theme="dark" editable={editable} />
      {/* Keep existing styles */}
    </div>
  );
}
```

**Why This Works**:
- `lastExternalContentRef` tracks content from props (not user typing)
- `isUserTypingRef` prevents re-initialization during user edits
- Editor instance is created ONCE (not recreated on each keystroke)
- Re-initialization only happens when switching documents

---

## UI Refactor: Notion/GitBook Style

### Task 2: De-Developerize the Sidebar

**Changes to SidebarNode.tsx**:

1. **Remove all file/folder icons** (lines 196-207)
2. **Use typography hierarchy** instead
3. **Add Reddit/Notion-style guide lines** for depth
4. **Subtle active state** with left border pill

```typescript
// Replace the render section (lines 160-304) with:

export function SidebarNode({ node, level, onNodeClick }: SidebarNodeProps) {
  // ... existing state and handlers ...

  const baseIndent = 12; // Base left padding
  const levelIndent = level * 20; // 20px per level
  const totalIndent = baseIndent + levelIndent;

  return (
    <div className="select-none">
      {/* Node Row - Notion Style */}
      <div
        className={`
          group relative flex items-center gap-2 py-1.5 cursor-pointer
          transition-colors duration-150
          ${isActive 
            ? 'bg-gray-100 dark:bg-slate-800/40' 
            : 'hover:bg-gray-50 dark:hover:bg-slate-800/20'
          }
          ${node.isTempNode ? 'opacity-60' : ''}
        `}
        style={{ paddingLeft: `${totalIndent}px` }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Active Indicator Pill - Left Edge */}
        {isActive && (
          <div className="absolute left-0 top-1 bottom-1 w-1 bg-blue-500 rounded-r-full" />
        )}

        {/* Guide Line for Nested Items */}
        {level > 0 && (
          <div 
            className="absolute left-0 top-0 bottom-0 border-l border-gray-200 dark:border-slate-700/50"
            style={{ left: `${baseIndent + (level - 1) * 20}px` }}
          />
        )}

        {/* Expand/Collapse Button (Folders Only) */}
        {isFolder && (
          <button
            className="shrink-0 w-5 h-5 flex items-center justify-center hover:bg-slate-700/50 rounded transition"
            onClick={(e) => {
              e.stopPropagation();
              toggleFolder(node.id);
            }}
          >
            <ChevronRight
              className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-200 ${
                isExpanded ? 'rotate-90' : ''
              }`}
            />
          </button>
        )}

        {/* Spacer for pages (no chevron) */}
        {!isFolder && <div className="w-5" />}

        {/* Title - Typography Only */}
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <input
              ref={inputRef}
              type="text"
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              onBlur={handleRenameSubmit}
              onKeyDown={handleRenameKeyDown}
              className="
                w-full bg-white dark:bg-slate-800 
                border border-blue-400 rounded px-2 py-1
                text-sm text-gray-900 dark:text-white 
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`
                block truncate text-sm transition-colors
                ${isFolder 
                  ? 'font-semibold text-gray-900 dark:text-slate-100' 
                  : 'font-normal text-gray-700 dark:text-slate-300'
                }
                ${isActive ? 'text-gray-900 dark:text-white' : ''}
                ${level === 0 && isFolder ? 'text-base' : ''}
                ${node.isTempNode ? 'italic' : ''}
              `}
            >
              {node.title}
            </span>
          )}
        </div>

        {/* Context Menu Button - Show on Hover */}
        <button
          className="
            shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
            hover:bg-slate-700/50 rounded p-1
          "
          onClick={(e) => {
            e.stopPropagation();
            handleContextMenu(e as any);
          }}
        >
          <MoreVertical className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Context Menu - Keep as is */}
      {/* Recursive Children - Keep as is */}
    </div>
  );
}
```

---

### Task 3: Layout & Scrolling Architecture

**Replace UnifiedWorkspace.tsx** (lines 103-119):

```typescript
return (
  <div className="h-screen w-screen overflow-hidden bg-slate-950">
    {/* Sidebar - Independent Scroll */}
    <div className="fixed left-0 top-0 bottom-0 w-[280px] border-r border-slate-800/50 overflow-y-auto">
      <DocumentSidebar
        orgId={orgId}
        repoId={repoId}
        onPageSelect={(pageId) => setActivePageId(pageId)}
      />
    </div>

    {/* Main Editor Area - Independent Scroll */}
    <div className="fixed left-[280px] right-0 top-0 bottom-0 overflow-y-auto">
      <DocumentEditor orgId={orgId} repoId={repoId} />
    </div>
  </div>
);
```

**Update DocumentEditor.tsx** (lines 172-234):

```typescript
return (
  <div className="h-full flex flex-col">
    {/* Sticky Header */}
    <div className="sticky top-0 z-50 flex-shrink-0 border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto px-8 py-4 flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-white truncate">
            {activePage.title}
          </h1>
        </div>

        {/* Status Indicator - Right Side */}
        <div className="flex items-center gap-3 ml-4">
          {isSaving && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
              <span>Saving...</span>
            </div>
          )}
          
          {!isSaving && hasChanges && (
            <button
              onClick={() => setIsCommitModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition"
            >
              <span className="w-2 h-2 bg-orange-400 rounded-full" />
              Publish {changeCount > 0 && `(${changeCount})`}
            </button>
          )}

          {!isSaving && !hasChanges && (
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span>Saved</span>
            </div>
          )}
        </div>
      </div>
    </div>

    {/* Editor Content - Centered Paper Style */}
    <div className="flex-1 bg-slate-950">
      {isLoading ? (
        <div className="h-full flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="max-w-3xl mx-auto px-8 py-12">
          <BlockNoteEditor
            key={editorKeyRef.current || activePageId}
            initialContent={editorContent}
            onChange={handleContentChange}
            editable={true}
            className="min-h-screen"
          />
        </div>
      )}
    </div>
  </div>
);
```

---

### Task 4: Session Activity Panel (Right Sidebar)

**Create new file: `SessionActivity.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { Clock, FileEdit, FilePlus, Trash2, ChevronRight } from 'lucide-react';

export function SessionActivity() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { pendingChanges, contentCache, getNodeById } = useWorkspaceStore();

  // Build activity timeline from pending changes
  const activities = Array.from(pendingChanges).map(pageId => {
    const node = getNodeById(pageId);
    const cached = contentCache[pageId];
    
    return {
      id: pageId,
      title: node?.title || 'Untitled',
      type: node?.isTempNode ? 'created' : 'edited',
      timestamp: cached?.lastModified || Date.now(),
    };
  }).sort((a, b) => b.timestamp - a.timestamp);

  const getRelativeTime = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-slate-800 border-l border-slate-700 rounded-l-lg p-2 hover:bg-slate-700 transition"
      >
        <ChevronRight className="w-4 h-4 text-slate-400 rotate-180" />
      </button>
    );
  }

  return (
    <div className="fixed right-0 top-0 bottom-0 w-[280px] border-l border-slate-800/50 bg-slate-900/50 backdrop-blur-sm overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800/50 p-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Session Activity</h3>
        <button
          onClick={() => setIsCollapsed(true)}
          className="hover:bg-slate-700 rounded p-1 transition"
        >
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Timeline */}
      <div className="p-4 space-y-3">
        {activities.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">
            No recent changes
          </p>
        ) : (
          activities.map(activity => (
            <button
              key={activity.id}
              className="w-full text-left p-3 rounded-lg hover:bg-slate-800/50 transition group"
            >
              <div className="flex items-start gap-3">
                <div className={`
                  shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                  ${activity.type === 'created' 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : 'bg-blue-500/20 text-blue-400'
                  }
                `}>
                  {activity.type === 'created' ? (
                    <FilePlus className="w-4 h-4" />
                  ) : (
                    <FileEdit className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate group-hover:text-blue-400 transition">
                    {activity.title}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {activity.type === 'created' ? 'Created' : 'Edited'} • {getRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
```

**Update UnifiedWorkspace.tsx** to include SessionActivity:

```typescript
import { SessionActivity } from './SessionActivity';

return (
  <div className="h-screen w-screen overflow-hidden bg-slate-950">
    {/* Sidebar */}
    <div className="fixed left-0 top-0 bottom-0 w-[280px] ...">
      <DocumentSidebar ... />
    </div>

    {/* Main Editor - Leave space for right sidebar */}
    <div className="fixed left-[280px] right-[280px] top-0 bottom-0 overflow-y-auto">
      <DocumentEditor ... />
    </div>

    {/* Session Activity - Right Sidebar */}
    <SessionActivity />
  </div>
);
```

---

## Summary of Changes

1. ✅ **Fixed focus bug** - Editor no longer re-initializes on typing
2. ✅ **Removed file icons** - Typography-based hierarchy
3. ✅ **Added guide lines** - Visual depth indicators
4. ✅ **Subtle active state** - Left border pill instead of full background
5. ✅ **Fixed scrolling** - Independent scroll containers
6. ✅ **Centered content** - `max-w-3xl mx-auto` for paper feel
7. ✅ **Session activity panel** - Right sidebar with timeline
8. ✅ **Alive state indicator** - Green checkmark, gray spinner, orange dot

The workspace now feels like a "Writer's Room" instead of a code editor!
