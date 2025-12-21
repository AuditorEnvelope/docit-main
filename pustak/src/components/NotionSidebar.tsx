"use client";

import { useEffect, useCallback } from "react";
import { Plus, Folder } from "lucide-react";
import { useSidebarStore } from "@/stores/useSidebarStore";
import { NotionSidebarItem } from "./NotionSidebarItem";
import { convertFileNodeToSidebarNode } from "@/lib/sidebarNodeConverter";
import { FileNode } from "@/contexts/ProjectStructureContext";
import { useEditorSession } from "@/contexts/EditorSessionContext";

interface NotionSidebarProps {
  orgId: string;
  repoId: string;
  persona: string;
  onPersonaChange?: (persona: string) => void;
  onClose?: () => void;
  // Initial tree from ProjectStructureContext
  initialTree?: FileNode[];
}

export function NotionSidebar({
  orgId,
  repoId,
  persona,
  onPersonaChange,
  onClose,
  initialTree = [],
}: NotionSidebarProps) {
  const { tree, initialize, addNode, hasUncommittedChanges } = useSidebarStore();
  const { openFile } = useEditorSession();

  // Initialize store when tree changes
  useEffect(() => {
    const sidebarNodes = initialTree.map(convertFileNodeToSidebarNode);
    initialize(sidebarNodes, orgId, repoId, persona);
  }, [initialTree, orgId, repoId, persona, initialize]);

  const handleFileClick = useCallback(
    async (node: { path: string; name: string; content?: string }) => {
      // Convert SidebarNode to FileNode format for openFile
      const fileNode: FileNode = {
        name: node.name,
        type: "file",
        path: node.path,
        content: node.content,
      };
      await openFile(fileNode, { orgId, repoId });
    },
    [openFile, orgId, repoId]
  );

  const handleAddRootPage = useCallback(() => {
    addNode(null, "file");
  }, [addNode]);

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
              <Plus className="h-4 w-4 rotate-45" />
            </button>
          )}
        </div>
        {/* Persona Switcher */}
        {onPersonaChange && (
          <div className="relative mt-4 flex items-center gap-2 rounded-2xl border border-slate-800/70 bg-slate-950/70 p-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500 px-2">
              Persona
            </span>
            <div className="flex items-center gap-1 flex-1">
              {["dev", "internal"].map((p) => (
                <button
                  key={p}
                  onClick={() => onPersonaChange(p)}
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

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto px-3 py-3 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700/70">
        {tree.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700/70 bg-slate-900/40 p-6 text-center">
            <p className="text-sm font-medium text-slate-200">No files yet</p>
            <p className="mt-2 text-xs text-slate-500">
              Click + to create a page
            </p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {tree.map((node) => (
              <NotionSidebarItem
                key={node.id}
                node={node}
                depth={0}
                onFileClick={handleFileClick}
              />
            ))}
          </div>
        )}

        {/* Root level Add Page button */}
        {tree.length > 0 && (
          <button
            onClick={handleAddRootPage}
            className="mt-3 flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition-all w-full group"
          >
            <div className="rounded bg-blue-500/20 p-0.5 group-hover:bg-blue-500/30 transition">
              <Plus className="h-3 w-3 text-blue-300" />
            </div>
            <span>New Page</span>
          </button>
        )}
      </div>

      {/* Footer - Uncommitted Changes Indicator */}
      {hasUncommittedChanges() && (
        <div className="border-t border-slate-800/70 px-5 py-3 bg-amber-500/10">
          <p className="text-xs text-amber-300">
            You have uncommitted changes
          </p>
        </div>
      )}
    </div>
  );
}

