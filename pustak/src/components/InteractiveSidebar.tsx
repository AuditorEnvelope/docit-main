"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  FileText,
  Folder,
  ChevronDown,
  ChevronRight,
  Plus,
  X,
  MoreVertical,
  Trash2,
  Edit3,
  Copy,
  ArrowUp,
  ArrowDown,
  FilePlus,
  FolderPlus,
} from "lucide-react";
import { useProjectStructure, FileNode } from "@/contexts/ProjectStructureContext";
import { useEditorSession } from "@/contexts/EditorSessionContext";
import { useDocbookAPI } from "@/hooks/useDocbookAPI";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface InteractiveSidebarProps {
  orgId: string;
  repoId: string;
  persona: string;
  onPersonaChange?: (persona: string) => void;
  onClose?: () => void;
}

interface SortableItemProps {
  node: FileNode;
  depth: number;
  onFileClick: (file: FileNode) => void;
  onCreateChild: (parentPath: string, type: "file" | "folder", name: string) => void;
  onDelete: (path: string) => void;
  onRename: (path: string, newName: string) => void;
  onInsertAfter: (path: string, type: "file" | "folder", name: string) => void;
}

function SortableItem({
  node,
  depth,
  onFileClick,
  onCreateChild,
  onDelete,
  onRename,
  onInsertAfter,
}: SortableItemProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 1); // expand root-level by default
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showMenu, setShowMenu] = useState(false);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(node.name);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { createPage, createFolder } = useDocbookAPI();
  const { structure, createFile: createFileInContext, createFolder: createFolderInContext } = useProjectStructure();

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: node.path });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  useEffect(() => {
    if (isCreating && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isCreating]);

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus();
      // Select the text without extension for files
      if (node.type === "file" && inputRef.current.value.includes(".")) {
        const dotIndex = inputRef.current.value.lastIndexOf(".");
        inputRef.current.setSelectionRange(0, dotIndex);
      }
    }
  }, [isRenaming, node.type]);

  // Keyboard handler for input fields
  const handleKeyDown = (e: React.KeyboardEvent, action: "file" | "folder" | "rename") => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (action === "rename") {
        handleRename();
      } else {
        handleCreate(action);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (action === "rename") {
        setIsRenaming(false);
        setRenameValue(node.name);
      } else {
        setIsCreating(false);
        setNewName("");
      }
    }
  };

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowContextMenu(false);
      }
    };

    if (showContextMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showContextMenu]);

  const handleCreate = async (type: "file" | "folder") => {
    if (!newName.trim() || !structure) {
      setIsCreating(false);
      setNewName("");
      return;
    }

    onCreateChild(node.path, type, newName.trim());

    setIsCreating(false);
    setNewName("");
    if (node.type === "folder" && !isExpanded) {
      setIsExpanded(true);
    }
  };

  const handleRename = async () => {
    if (!renameValue.trim() || !structure) {
      setIsRenaming(false);
      setRenameValue(node.name);
      return;
    }

    // If it's a file, preserve the .md extension
    let finalName = renameValue.trim();
    if (node.type === "file" && !finalName.endsWith(".md")) {
      finalName = `${finalName}.md`;
    }

    onRename(node.path, finalName);
    setIsRenaming(false);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Close any existing context menus
    document.querySelectorAll('.context-menu').forEach(el => el.remove());
    
    // Get click position
    const x = e.clientX;
    const y = e.clientY;
    
    setContextMenuPosition({ x, y });
    setShowContextMenu(true);
  };

  const handleDeleteWithConfirmation = () => {
    if (window.confirm(`Are you sure you want to delete "${node.name}"? This action cannot be undone.`)) {
      onDelete(node.path);
    }
    setShowContextMenu(false);
  };

  const handleInsertAfter = (type: "file" | "folder") => {
    const name = type === "file" ? "New Page" : "New Folder";
    onInsertAfter(node.path, type, name);
    setShowContextMenu(false);
  };

  const handleStartRename = () => {
    setIsRenaming(true);
    setRenameValue(node.name);
    setShowContextMenu(false);
  };

  const handleDuplicate = () => {
    // TODO: Implement duplicate functionality
    console.log("Duplicate not yet implemented");
    setShowContextMenu(false);
  };

  if (isRenaming) {
    return (
      <div
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-all duration-150 hover:bg-slate-800/60"
      >
        <div className="flex items-center gap-2 flex-1">
          {node.type === "file" ? (
            <FileText className="h-3 w-3 text-blue-300/80 flex-shrink-0" />
          ) : (
            <Folder className="h-3 w-3 text-blue-300 flex-shrink-0" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => handleKeyDown(e, "rename")}
            onBlur={handleRename}
            className="flex-1 bg-transparent text-xs text-slate-200 placeholder:text-slate-500 outline-none border-b border-blue-500/50 py-1"
          />
        </div>
      </div>
    );
  }

  if (node.type === "file") {
    return (
      <div className="relative">
        <div
          ref={setNodeRef}
          style={{ ...style, paddingLeft: `${depth * 16 + 8}px` }}
          className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-all duration-150 hover:bg-slate-800/60"
        >
          <FileText className="h-3 w-3 text-blue-300/80 flex-shrink-0" />
          <button
            onClick={() => onFileClick(node)}
            className="flex-1 text-left text-slate-400 hover:text-slate-100 truncate transition-colors"
          >
            {node.name}
          </button>
          {node.isDirty && (
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" title="Unsaved changes" />
          )}
          {/* Hover Actions */}
          <button
            onClick={handleContextMenu}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-700/80 transition-opacity"
            title="More actions"
          >
            <MoreVertical className="h-3 w-3 text-slate-400" />
          </button>
        </div>
        {showContextMenu && (
          <div
            ref={menuRef}
            className="context-menu fixed z-50 min-w-[200px] rounded-lg border border-slate-700 bg-slate-800 py-2 shadow-xl"
            style={{
              left: contextMenuPosition.x,
              top: contextMenuPosition.y,
            }}
          >
            <button
              onClick={handleStartRename}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
            >
              <Edit3 className="h-3 w-3" />
              <span>Rename</span>
            </button>
            <button
              onClick={() => handleInsertAfter("file")}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
            >
              <FilePlus className="h-3 w-3" />
              <span>Insert page after</span>
            </button>
            <button
              onClick={() => handleInsertAfter("folder")}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
            >
              <FolderPlus className="h-3 w-3" />
              <span>Insert folder after</span>
            </button>
            <button
              onClick={handleDuplicate}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
            >
              <Copy className="h-3 w-3" />
              <span>Duplicate</span>
            </button>
            <hr className="my-2 border-slate-700" />
            <button
              onClick={handleDeleteWithConfirmation}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-red-400 hover:bg-red-500/20"
            >
              <Trash2 className="h-3 w-3" />
              <span>Delete</span>
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        ref={setNodeRef}
        style={{ ...style, paddingLeft: `${depth * 16 + 8}px` }}
        className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-all duration-150 hover:bg-slate-800/60"
        onContextMenu={handleContextMenu}
      >
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1"
          {...attributes}
          {...listeners}
        >
          {isExpanded ? (
            <ChevronDown className="h-3 w-3 text-slate-400" />
          ) : (
            <ChevronRight className="h-3 w-3 text-slate-400" />
          )}
          <Folder className="h-3 w-3 text-blue-300 flex-shrink-0" />
        </button>
        <span className="flex-1 font-medium text-slate-100">{node.name}</span>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsCreating(true);
            }}
            className="p-0.5 rounded text-slate-500 hover:text-slate-300"
            title="Add page"
          >
            <Plus className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleContextMenu(e);
            }}
            className="p-0.5 rounded text-slate-500 hover:text-slate-300"
            title="More actions"
          >
            <MoreVertical className="h-3 w-3" />
          </button>
        </div>
      </div>

      {isCreating && (
        <div className="ml-4 mt-1" style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}>
          <div className="flex items-center gap-2 rounded-lg bg-slate-800/60 px-2 py-1">
            <input
              ref={inputRef}
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, "file")}
              onBlur={() => {
                if (newName.trim()) handleCreate("file");
                else setIsCreating(false);
              }}
              placeholder="Page name..."
              className="flex-1 bg-transparent text-xs text-slate-200 placeholder:text-slate-500 outline-none"
            />
            <button
              onClick={() => handleCreate("file")}
              className="text-blue-400 hover:text-blue-300"
            >
              <Plus className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}

      {isExpanded && node.children && (
        <div className="ml-3 border-l border-slate-800/60 pl-2">
          <SortableContext
            items={node.children.map((c) => c.path)}
            strategy={verticalListSortingStrategy}
          >
            {node.children.map((child) => (
              <SortableItem
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
                onCreateChild={onCreateChild}
                onDelete={onDelete}
                onRename={onRename}
                onInsertAfter={onInsertAfter}
              />
            ))}
          </SortableContext>
          {/* Ghost "Add Page" button at bottom of folder */}
          <button
            onClick={() => setIsCreating(true)}
            className="mt-2 flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:text-blue-300 hover:bg-blue-500/10 transition-all"
            style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}
          >
            <Plus className="h-3 w-3" />
            <span>Add Page</span>
          </button>
        </div>
      )}
      {showContextMenu && (
        <div
          ref={menuRef}
          className="context-menu fixed z-50 min-w-[200px] rounded-lg border border-slate-700 bg-slate-800 py-2 shadow-xl"
          style={{
            left: contextMenuPosition.x,
            top: contextMenuPosition.y,
          }}
        >
          <button
            onClick={handleStartRename}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
          >
            <Edit3 className="h-3 w-3" />
            <span>Rename</span>
          </button>
          <button
            onClick={() => handleInsertAfter("file")}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
          >
            <FilePlus className="h-3 w-3" />
            <span>Insert page after</span>
          </button>
          <button
            onClick={() => handleInsertAfter("folder")}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
          >
            <FolderPlus className="h-3 w-3" />
            <span>Insert folder after</span>
          </button>
          <button
            onClick={() => setIsCreating(true)}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-slate-300 hover:bg-slate-700/80"
          >
            <Plus className="h-3 w-3" />
            <span>Add page inside</span>
          </button>
          <hr className="my-2 border-slate-700" />
          <button
            onClick={handleDeleteWithConfirmation}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-red-400 hover:bg-red-500/20"
          >
            <Trash2 className="h-3 w-3" />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
}

export function InteractiveSidebar({
  orgId,
  repoId,
  persona,
  onPersonaChange,
  onClose,
}: InteractiveSidebarProps) {
  const {
    structure,
    setStructure,
    moveNode: moveNodeInContext,
    deleteNode,
    createFile: createFileInContext,
    createFolder: createFolderInContext,
  } = useProjectStructure();
  const { openFile } = useEditorSession();
  const { createPage, updateStructure: updateStructureApi, deletePage } = useDocbookAPI();
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const sourcePath = active.id as string;
    const targetPath = over.id as string;

    // Move node in context
    moveNodeInContext(sourcePath, targetPath);
    // API call to update structure would go here
  };

  const handleFileClick = useCallback(
    async (file: FileNode) => {
      try {
        await openFile(file, structure ? { orgId: structure.orgId, repoId: structure.repoId } : null);
      } catch (error) {
        console.error('Failed to open file:', error);
        // If file was just created, it might not exist on server yet
        // Open it with empty content
        if (file.path && structure) {
          const emptyFile = {
            ...file,
            content: '',
          };
          await openFile(emptyFile, { orgId: structure.orgId, repoId: structure.repoId });
        }
      }
    },
    [openFile, structure]
  );

  const handleDelete = useCallback(
    async (path: string) => {
      if (!structure || !deleteNode) return;
      
      // First delete from GitHub
      try {
        await deletePage({
          orgId: structure.orgId,
          repoId: structure.repoId,
          persona: structure.persona,
          filePath: path,
        });
        
        // Then update local structure
        const success = deleteNode(path);
        if (success) {
          setStructure({ ...structure });
          try {
            await updateStructureApi({
              orgId: structure.orgId,
              repoId: structure.repoId,
              persona: structure.persona,
              structure: structure.root,
            });
          } catch (err) {
            console.error("Failed to persist delete:", err);
          }
        }
      } catch (err) {
        console.error("Failed to delete page:", err);
        alert("Failed to delete page: " + (err instanceof Error ? err.message : "Unknown error"));
      }
    },
    [structure, setStructure, deleteNode, updateStructureApi, deletePage]
  );

  const handleRename = useCallback(
    async (path: string, newName: string) => {
      if (!structure) return;
      
      // TODO: Implement rename functionality with API call
      console.log("Rename not yet implemented", path, newName);
      
      // For now, just reload the structure
      setStructure({ ...structure });
    },
    [structure, setStructure]
  );

  const handleInsertAfter = useCallback(
    async (path: string, type: "file" | "folder", name: string) => {
      if (!structure) return;
      
      // TODO: Implement insert after functionality
      console.log("Insert after not yet implemented", path, type, name);
      
      // For now, just reload the structure
      setStructure({ ...structure });
    },
    [structure, setStructure]
  );

  const handleAddPageRoot = useCallback(async () => {
    if (!structure || !createFileInContext) return;
    const fileName = prompt("Page name (without extension):");
    if (!fileName) return;
    const finalName = fileName.endsWith(".md") ? fileName : `${fileName}.md`;
    const rootPath = `${structure.repoId}/docs/${structure.persona}`;
    
    console.log('🔧 Creating root file:', {
      fileName: finalName,
      rootPath,
      willSendToAPI: {
        org_id: structure.orgId,
        repo_id: structure.repoId,
        persona: structure.persona,
        parent_path: "",  // Empty for root
        fileName: finalName
      }
    });
    
    createFileInContext(rootPath, finalName);
    setStructure({ ...structure });
    try {
      await createPage({
        orgId: structure.orgId,
        repoId: structure.repoId,
        persona: structure.persona,
        parentPath: "",  // Empty string for root
        fileName: finalName,
        content: "",
      });
      await updateStructureApi({
        orgId: structure.orgId,
        repoId: structure.repoId,
        persona: structure.persona,
        structure: structure.root,
      });
    } catch (err) {
      console.error("Failed to create page:", err);
    }
  }, [structure, setStructure, createFileInContext, createPage, updateStructureApi]);

  const handleCreateChild = useCallback(
    async (parentPath: string, type: "file" | "folder", name: string) => {
      if (!structure) return;
      const fileName = type === "file" ? (name.endsWith(".md") ? name : `${name}.md`) : name;
      if (type === "file") {
        // CRITICAL FIX: Remove repo name from parent path
        // Parent path format: "repoId/docs/persona/folder/subfolder"
        // We need: "folder/subfolder" (relative to docs/persona)
        let relativeParentPath = "";
        
        if (parentPath) {
          // Remove the prefix: repoId/docs/persona/
          const prefix = `${structure.repoId}/docs/${structure.persona}`;
          if (parentPath.startsWith(prefix)) {
            relativeParentPath = parentPath.slice(prefix.length);
            // Remove leading slash
            if (relativeParentPath.startsWith("/")) {
              relativeParentPath = relativeParentPath.slice(1);
            }
          }
        }
        
        console.log('🔧 Creating file:', {
          fileName,
          parentPath,
          relativeParentPath,
          willSendToAPI: {
            org_id: structure.orgId,
            repo_id: structure.repoId,
            persona: structure.persona,
            parent_path: relativeParentPath,
            fileName
          }
        });
        
        createFileInContext?.(parentPath, fileName);
        setStructure({ ...structure });
        
        try {
          await createPage({
            orgId: structure.orgId,
            repoId: structure.repoId,
            persona: structure.persona,
            parentPath: relativeParentPath,
            fileName,
            content: "",
          });
          await updateStructureApi({
            orgId: structure.orgId,
            repoId: structure.repoId,
            persona: structure.persona,
            structure: structure.root,
          });
        } catch (err) {
          console.error("Failed to create page:", err);
        }
      } else {
        createFolderInContext?.(parentPath, fileName);
        setStructure({ ...structure });
      }
    },
    [structure, setStructure, createFileInContext, createFolderInContext, createPage, updateStructureApi]
  );

  if (!structure) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        <p>Loading structure...</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-r border-slate-800/70 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <div className="relative overflow-hidden border-b border-slate-800/70 px-5 py-6">
        <div
          className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.35),_transparent_55%)]"
          aria-hidden
        />
        <div
          className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.25),_transparent_60%)]"
          aria-hidden
        />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-blue-500/20 p-2.5 ring-1 ring-inset ring-blue-400/40">
              <Folder className="h-6 w-6 text-blue-300" />
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">
                File Explorer
              </p>
              <h2 className="text-lg font-semibold text-white sm:text-xl">
                {repoId}
              </h2>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="rounded-full border border-slate-700/70 bg-slate-900/70 p-2 text-slate-400 transition hover:border-slate-500/70 hover:text-white"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        {/* Persona Switcher */}
        {onPersonaChange && (
          <div className="relative mt-4 flex items-center gap-2 rounded-2xl border border-slate-800/70 bg-slate-950/70 p-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 px-2">Persona</span>
            <div className="flex items-center gap-1 flex-1">
              {["dev", "internal"].map((p) => (
                <button
                  key={p}
                  onClick={() => onPersonaChange?.(p)}
                  className={`flex-1 px-3 py-1.5 text-xs rounded-lg font-medium transition-all ${
                    persona === p
                      ? "bg-blue-500/80 text-white shadow-lg shadow-blue-500/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700/70">
          <SortableContext
            items={structure.root.map((n) => n.path)}
            strategy={verticalListSortingStrategy}
          >
            {structure.root.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/40 p-6 text-center">
                <p className="text-sm font-medium text-slate-200">No files yet</p>
                <p className="mt-2 text-xs text-slate-500">Click + to create a page</p>
              </div>
            ) : (
              structure.root.map((node) => (
                <SortableItem
                  key={node.path}
                  node={node}
                  depth={0}
                  onFileClick={handleFileClick}
                  onCreateChild={handleCreateChild}
                  onDelete={handleDelete}
                  onRename={handleRename}
                  onInsertAfter={handleInsertAfter}
                />
              ))
            )}
          </SortableContext>
          {/* Root level "Add Page" button */}
          {structure.root.length > 0 && (
            <button
              onClick={handleAddPageRoot}
              className="mt-4 flex items-center gap-2 rounded-2xl border border-slate-800/70 bg-slate-900/60 px-4 py-2.5 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900/80 hover:border-blue-500/40 transition-all w-full group"
            >
              <div className="rounded-lg bg-blue-500/20 p-1 group-hover:bg-blue-500/30 transition">
                <Plus className="h-3.5 w-3.5 text-blue-300" />
              </div>
              <span>Add Page</span>
            </button>
          )}
        </div>
      </DndContext>
    </div>
  );
}

