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
import { createPortal } from 'react-dom';
import { FileNode, useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { ChevronRight, MoreVertical } from 'lucide-react';

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
    if (isFolder) {
      // Adding inside folder - no afterNodeId
      addNode(node.id, 'page');
      // Auto-expand parent folder
      if (!isExpanded) {
        toggleFolder(node.id);
      }
    } else {
      // Adding below a page - pass current node ID as afterNodeId
      addNode(node.parentId, 'page', node.id);
    }
    setShowContextMenu(false);
  };

  const handleAddFolder = () => {
    if (isFolder) {
      // Adding inside folder - no afterNodeId
      addNode(node.id, 'folder');
      // Auto-expand parent folder
      if (!isExpanded) {
        toggleFolder(node.id);
      }
    } else {
      // Adding below a page - pass current node ID as afterNodeId
      addNode(node.parentId, 'folder', node.id);
    }
    setShowContextMenu(false);
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

  const baseIndent = 8; // Base left padding (reduced)
  const levelIndent = level * 16; // 16px per nesting level (reduced)
  const totalIndent = baseIndent + levelIndent;

  return (
    <div className="select-none">
      {/* Node Row - Notion Style (Typography over Icons) */}
      <div
        className={`
          group relative flex items-center gap-1.5 py-1 cursor-pointer
          transition-colors duration-150
          ${
            isActive
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
        {/* Active Indicator Pill - Absolute Left Edge */}
        {isActive && (
          <div className="absolute left-0 top-1 bottom-1 w-1 bg-blue-500 rounded-r-full" />
        )}

        {/* Guide Line for Nested Items */}
        {level > 0 && (
          <div
            className="absolute top-0 bottom-0 border-l border-gray-200 dark:border-slate-700/50 pointer-events-none z-0"
            style={{ left: `${baseIndent + (level - 1) * 16}px` }}
          />
        )}

        {/* Expand/Collapse Button (Folders Only) */}
        {isFolder && (
          <button
            className="shrink-0 w-4 h-4 flex items-center justify-center hover:bg-slate-700/50 rounded transition"
            onClick={(e) => {
              e.stopPropagation();
              toggleFolder(node.id);
            }}
          >
            <ChevronRight
              className={`w-3 h-3 text-slate-500 transition-transform duration-200 ${
                isExpanded ? 'rotate-90' : ''
              }`}
            />
          </button>
        )}

        {/* Spacer for pages (no chevron) */}
        {!isFolder && <div className="w-4" />}

        {/* Title - Typography Hierarchy (NO ICONS) */}
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
                border border-blue-400 rounded px-1.5 py-0.5
                text-xs text-gray-900 dark:text-white
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`
                block truncate text-xs transition-colors
                ${
                  isFolder
                    ? 'font-semibold text-gray-900 dark:text-slate-100'
                    : 'font-normal text-gray-700 dark:text-slate-300'
                }
                ${isActive ? 'text-gray-900 dark:text-white' : ''}
                ${level === 0 && isFolder ? 'text-sm' : ''}
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
            hover:bg-slate-700/50 rounded p-0.5
          "
          onClick={(e) => {
            e.stopPropagation();
            handleContextMenu(e as any);
          }}
        >
          <MoreVertical className="w-3.5 h-3.5 text-slate-400" />
        </button>
      </div>

      {/* Context Menu - Rendered via Portal */}
      {showContextMenu && createPortal(
        <div
          ref={contextMenuRef}
          className="
            fixed z-[100] bg-slate-800 border border-slate-700 rounded-lg shadow-2xl
            py-2 min-w-[200px] overflow-hidden
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
        </div>,
        document.body
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
        w-full text-left px-2.5 py-1.5 text-xs transition-colors
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
