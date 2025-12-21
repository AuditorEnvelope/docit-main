"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  FileText,
  Folder,
  ChevronDown,
  ChevronRight,
  Plus,
  MoreVertical,
  Trash2,
  Edit3,
  FilePlus,
  FolderPlus,
} from "lucide-react";
import { useSidebarStore, SidebarNode } from "@/stores/useSidebarStore";
import { useEditorSession } from "@/contexts/EditorSessionContext";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";

interface NotionSidebarItemProps {
  node: SidebarNode;
  depth: number;
  onFileClick?: (node: SidebarNode) => void;
}

export function NotionSidebarItem({
  node,
  depth,
  onFileClick,
}: NotionSidebarItemProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [editingName, setEditingName] = useState(node.name);
  const inputRef = useRef<HTMLInputElement>(null);
  const {
    toggleExpanded,
    setEditing,
    deleteNode,
    addNode,
    updateNodeName,
  } = useSidebarStore();
  const { openFile } = useEditorSession();

  // Auto-focus input when editing starts
  useEffect(() => {
    if (node.isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [node.isEditing]);

  // Sync editing name with node name
  useEffect(() => {
    if (!node.isEditing) {
      setEditingName(node.name);
    }
  }, [node.name, node.isEditing]);

  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setEditingName(e.target.value);
    },
    []
  );

  const handleNameSubmit = useCallback(() => {
    const trimmedName = editingName.trim();
    if (trimmedName && trimmedName !== node.name) {
      updateNodeName(node.id, trimmedName);
    } else {
      // Cancel editing if empty or unchanged
      setEditing(node.id, false);
      setEditingName(node.name);
    }
  }, [editingName, node.id, node.name, updateNodeName, setEditing]);

  const handleNameKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleNameSubmit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        setEditing(node.id, false);
        setEditingName(node.name);
      }
    },
    [handleNameSubmit, node.id, node.name, setEditing]
  );

  const handleFileClick = useCallback(() => {
    if (node.type === "file" && onFileClick) {
      onFileClick(node);
    } else if (node.type === "folder") {
      toggleExpanded(node.id);
    }
  }, [node, onFileClick, toggleExpanded]);

  const handleAddChild = useCallback(
    (type: "file" | "folder") => {
      const newId = addNode(node.id, type);
      // The new node will be created with isEditing=true, so it will show input
    },
    [node.id, addNode]
  );

  const handleDelete = useCallback(() => {
    if (confirm(`Delete ${node.name}?`)) {
      deleteNode(node.id);
    }
  }, [node.id, node.name, deleteNode]);

  const handleRename = useCallback(() => {
    setEditing(node.id, true);
  }, [node.id, setEditing]);

  const indentStyle = {
    paddingLeft: `${depth * 16 + 8}px`,
  };

  const isFolder = node.type === "folder";
  const isExpanded = isFolder && node.isExpanded;
  const hasChildren = isFolder && node.children && node.children.length > 0;

  return (
    <div>
      <div
        className="group flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm transition-colors hover:bg-slate-800/40"
        style={indentStyle}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Indent guide (optional) */}
        {depth > 0 && (
          <div
            className="absolute left-0 top-0 bottom-0 w-px bg-slate-800/30"
            style={{ left: `${depth * 16}px` }}
          />
        )}

        {/* Expand/Collapse Chevron */}
        {isFolder ? (
          <button
            onClick={() => toggleExpanded(node.id)}
            className="flex-shrink-0 p-0.5 rounded hover:bg-slate-700/50 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
            )}
          </button>
        ) : (
          <div className="w-4" /> // Spacer for alignment
        )}

        {/* Icon */}
        {isFolder ? (
          <Folder className="h-3.5 w-3.5 text-blue-400/80 flex-shrink-0" />
        ) : (
          <FileText className="h-3.5 w-3.5 text-blue-300/70 flex-shrink-0" />
        )}

        {/* Name (or input if editing) */}
        {node.isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editingName}
            onChange={handleNameChange}
            onBlur={handleNameSubmit}
            onKeyDown={handleNameKeyDown}
            className="flex-1 bg-slate-800/60 border border-blue-500/50 rounded px-1.5 py-0.5 text-xs text-slate-100 outline-none focus:border-blue-400"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <button
            onClick={handleFileClick}
            className="flex-1 text-left text-slate-300 hover:text-slate-100 truncate text-sm font-normal"
          >
            {node.name}
          </button>
        )}

        {/* Dirty indicator */}
        {node.isDirty && !node.isEditing && (
          <div className="h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
        )}

        {/* Action buttons (hidden until hover) */}
        <div
          className={`flex items-center gap-0.5 transition-opacity ${
            isHovered ? "opacity-100" : "opacity-0"
          }`}
        >
          {/* Add Child Button */}
          {isFolder && (
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button
                  className="p-1 rounded hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  className="min-w-[180px] rounded-lg border border-slate-700/70 bg-slate-900/95 backdrop-blur-sm p-1 shadow-xl z-50"
                  sideOffset={5}
                  align="start"
                >
                  <DropdownMenu.Item
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white outline-none cursor-pointer"
                    onSelect={() => handleAddChild("file")}
                  >
                    <FilePlus className="h-3.5 w-3.5" />
                    <span>New Page</span>
                  </DropdownMenu.Item>
                  <DropdownMenu.Item
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white outline-none cursor-pointer"
                    onSelect={() => handleAddChild("folder")}
                  >
                    <FolderPlus className="h-3.5 w-3.5" />
                    <span>New Folder</span>
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          )}

          {/* Options Menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                className="p-1 rounded hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreVertical className="h-3.5 w-3.5" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[180px] rounded-lg border border-slate-700/70 bg-slate-900/95 backdrop-blur-sm p-1 shadow-xl z-50"
                sideOffset={5}
                align="start"
              >
                <DropdownMenu.Item
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white outline-none cursor-pointer"
                  onSelect={handleRename}
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  <span>Rename</span>
                </DropdownMenu.Item>
                <DropdownMenu.Separator className="h-px bg-slate-700/70 my-1" />
                <DropdownMenu.Item
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-red-300 hover:bg-red-500/20 hover:text-red-200 outline-none cursor-pointer"
                  onSelect={handleDelete}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Delete</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>

      {/* Children (recursive) */}
      {isFolder && isExpanded && (
        <div className="relative">
          {hasChildren ? (
            node.children!.map((child) => (
              <NotionSidebarItem
                key={child.id}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
              />
            ))
          ) : (
            <div
              className="text-xs text-slate-500 px-1.5 py-1 italic"
              style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}
            >
              Empty folder
            </div>
          )}
        </div>
      )}
    </div>
  );
}

