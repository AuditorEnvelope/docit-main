/**
 * Recursive Sidebar Node Component
 * 
 * Renders a single node (folder or page) and all its children recursively.
 * Supports:
 * - Inline renaming (ghost input state)
 * - Drag and drop (placeholder for now)
 * - Context menu actions
 * - Expand/collapse for folders
 */

'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { FileNode, useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { ChevronRight, FileText, Folder, FolderOpen, MoreVertical } from 'lucide-react';

interface SidebarNodeProps {
  node: FileNode;
  level: number; // For indentation
  onNodeClick?: (nodeId: string) => void;
}

export function SidebarNode({ node, level, onNodeClick }: SidebarNodeProps) {
  const {
    activePageId,
    expandedFolders,
    setActivePageId,
    renameNode,
    deleteNode,
    addNode,
    duplicateNode,
    toggleFolder,
    setNodeEditing
  } = useWorkspaceStore();

  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
  const [editingTitle, setEditingTitle] = useState(node.title);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  const isFolder = node.type === 'folder';
  const isExpanded = expandedFolders ? expandedFolders.has(node.id) : false;
  const isActive = activePageId === node.id;
  const isEditing = node.isEditing || false;

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  // Close context menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setShowContextMenu(false);
      }
    };

    if (showContextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showContextMenu]);

  // ========== EVENT HANDLERS ==========

  const handleClick = () => {
    if (isFolder) {
      toggleFolder(node.id);
    } else {
      setActivePageId(node.id);
      onNodeClick?.(node.id);
    }
  };

  const handleDoubleClick = () => {
    if (!isEditing) {
      setNodeEditing(node.id, true);
      setEditingTitle(node.title);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenuPosition({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleRenameSubmit = () => {
    const trimmedTitle = editingTitle.trim();
    if (trimmedTitle && trimmedTitle !== node.title) {
      renameNode(node.id, trimmedTitle);
    } else if (!trimmedTitle) {
      // Empty title, revert to original
      setEditingTitle(node.title);
    }
    setNodeEditing(node.id, false);
  };

  const handleRenameKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setEditingTitle(node.title);
      setNodeEditing(node.id, false);
    }
  };

  const handleAddPage = () => {
    const parentId = isFolder ? node.id : node.parentId;
    addNode(parentId, 'page');
    setShowContextMenu(false);
    
    // Auto-expand parent folder
    if (isFolder) {
      if (!isExpanded) {
        toggleFolder(node.id);
      }
    }
  };

  const handleAddFolder = () => {
    const parentId = isFolder ? node.id : node.parentId;
    addNode(parentId, 'folder');
    setShowContextMenu(false);
    
    // Auto-expand parent folder
    if (isFolder && !isExpanded) {
      toggleFolder(node.id);
    }
  };

  const handleRename = () => {
    setNodeEditing(node.id, true);
    setEditingTitle(node.title);
    setShowContextMenu(false);
  };

  const handleDuplicate = () => {
    duplicateNode(node.id);
    setShowContextMenu(false);
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete "${node.title}"?`)) {
      deleteNode(node.id);
    }
    setShowContextMenu(false);
  };

  // ========== RENDER ==========

  const indentPadding = level * 16; // 16px per level

  return (
    <div className="select-none">
      {/* Node Row */}
      <div
        className={`
          group relative flex items-center gap-2 px-3 py-2 cursor-pointer
          hover:bg-slate-800/60 transition-colors
          ${isActive ? 'bg-blue-500/20 border-l-2 border-blue-400' : ''}
          ${node.isTempNode ? 'opacity-70' : ''}
        `}
        style={{ paddingLeft: `${indentPadding + 12}px` }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Expand/Collapse Icon (Folders Only) */}
        {isFolder && (
          <button
            className="shrink-0 hover:bg-slate-700 rounded p-0.5 transition"
            onClick={(e) => {
              e.stopPropagation();
              toggleFolder(node.id);
            }}
          >
            <ChevronRight
              className={`w-4 h-4 text-slate-400 transition-transform ${
                isExpanded ? 'rotate-90' : ''
              }`}
            />
          </button>
        )}

        {/* Icon */}
        <div className="shrink-0">
          {isFolder ? (
            isExpanded ? (
              <FolderOpen className="w-4 h-4 text-blue-400" />
            ) : (
              <Folder className="w-4 h-4 text-slate-400" />
            )
          ) : (
            <FileText className="w-4 h-4 text-slate-400" />
          )}
        </div>

        {/* Title (Editable) */}
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
                w-full bg-slate-900 border border-blue-400 rounded px-2 py-1
                text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500
              "
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`
                block truncate text-sm
                ${isActive ? 'text-white font-medium' : 'text-slate-300'}
                ${node.isTempNode ? 'italic' : ''}
              `}
            >
              {node.title}
            </span>
          )}
        </div>

        {/* Temp Badge */}
        {node.isTempNode && (
          <span className="shrink-0 text-xs text-amber-400 px-1.5 py-0.5 bg-amber-500/10 rounded">
            New
          </span>
        )}

        {/* Context Menu Button */}
        <button
          className="
            shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
            hover:bg-slate-700 rounded p-1
          "
          onClick={(e) => {
            e.stopPropagation();
            handleContextMenu(e as any);
          }}
        >
          <MoreVertical className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Context Menu */}
      {showContextMenu && (
        <div
          ref={contextMenuRef}
          className="
            fixed z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-xl
            py-1 min-w-[180px]
          "
          style={{
            left: `${contextMenuPosition.x}px`,
            top: `${contextMenuPosition.y}px`
          }}
        >
          <ContextMenuItem onClick={handleAddPage}>
            Add Page {isFolder ? 'Inside' : 'Below'}
          </ContextMenuItem>
          <ContextMenuItem onClick={handleAddFolder}>
            Add Folder {isFolder ? 'Inside' : 'Below'}
          </ContextMenuItem>
          <div className="h-px bg-slate-700 my-1" />
          <ContextMenuItem onClick={handleRename}>Rename</ContextMenuItem>
          <ContextMenuItem onClick={handleDuplicate}>Duplicate</ContextMenuItem>
          <div className="h-px bg-slate-700 my-1" />
          <ContextMenuItem onClick={handleDelete} variant="danger">
            Delete
          </ContextMenuItem>
        </div>
      )}

      {/* Recursive Children (Only if folder and expanded) */}
      {isFolder && isExpanded && node.children.length > 0 && (
        <div>
          {node.children.map((child) => (
            <SidebarNode
              key={child.id}
              node={child}
              level={level + 1}
              onNodeClick={onNodeClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ========== CONTEXT MENU ITEM COMPONENT ==========

interface ContextMenuItemProps {
  onClick: () => void;
  variant?: 'default' | 'danger';
  children: React.ReactNode;
}

function ContextMenuItem({ onClick, variant = 'default', children }: ContextMenuItemProps) {
  return (
    <button
      className={`
        w-full text-left px-3 py-2 text-sm transition-colors
        ${
          variant === 'danger'
            ? 'text-red-400 hover:bg-red-500/10'
            : 'text-slate-200 hover:bg-slate-700'
        }
      `}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
