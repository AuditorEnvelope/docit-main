"use client";

import { useCallback, useEffect } from "react";
import { X } from "lucide-react";
import { useEditorSession } from "@/contexts/EditorSessionContext";
import { useProjectStructure } from "@/contexts/ProjectStructureContext";
import { BlockNoteEditor } from "./BlockNoteEditor";

interface TabbedEditorProps {
  className?: string;
}

export function TabbedEditor({ className = "" }: TabbedEditorProps) {
  const {
    openFiles,
    activeFileId,
    setActiveFile,
    closeFile,
    updateFileContent,
    getActiveFile,
  } = useEditorSession();

  const activeFile = getActiveFile();

  const { updateFile: updateFileInStructure } = useProjectStructure();

  const handleContentChange = useCallback(
    (markdown: string) => {
      if (activeFileId) {
        updateFileContent(activeFileId, markdown);
        
        // Also update in structure context
        const file = getActiveFile();
        if (file) {
          updateFileInStructure(file.path, markdown, true);
        }
      }
    },
    [activeFileId, updateFileContent, getActiveFile, updateFileInStructure]
  );

  if (openFiles.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        <p>No files open. Click a file in the sidebar to start editing.</p>
      </div>
    );
  }

  return (
    <div className={`flex h-full flex-col ${className}`}>
      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-slate-800/70 bg-slate-900/50 px-2 overflow-x-auto">
        {openFiles.map((file) => (
          <div
            key={file.id}
            className={`group flex items-center gap-2 rounded-t-lg border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              activeFileId === file.id
                ? "border-blue-500 bg-slate-900 text-blue-200"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <button
              onClick={() => setActiveFile(file.id)}
              className="flex items-center gap-2 flex-1 min-w-0"
            >
              <span className="truncate max-w-[200px]">{file.name}</span>
              {file.isDirty && (
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              )}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeFile(file.id);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-slate-700 flex-shrink-0"
              aria-label="Close tab"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Editor Content */}
      <div className="flex-1 overflow-auto">
        {activeFile ? (
          <div className="h-full">
            <div className="mb-2 px-4 pt-4">
              <p className="text-xs text-slate-500">Source: {activeFile.path}</p>
              {activeFile.content && (
                <p className="text-xs text-slate-600 mt-1">
                  Content length: {activeFile.content.length} characters
                </p>
              )}
            </div>
            <div className="px-4 pb-4">
              <BlockNoteEditor
                key={activeFile.id} // Force re-render when switching files
                initialContent={activeFile.content || ""}
                onChange={handleContentChange}
                editable={true}
              />
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            <p>Select a file to edit</p>
          </div>
        )}
      </div>
    </div>
  );
}

