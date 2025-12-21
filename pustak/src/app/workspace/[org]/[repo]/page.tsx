"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { ProjectStructureProvider, useProjectStructure } from "@/contexts/ProjectStructureContext";
import { EditorSessionProvider } from "@/contexts/EditorSessionContext";
import { NotionSidebar } from "@/components/NotionSidebar";
import { TabbedEditor } from "@/components/TabbedEditor";
import { BulkCommitModal } from "@/components/BulkCommitModal";
import { useEditorSession } from "@/contexts/EditorSessionContext";
import { convertBackendStructureToFileNodes, cleanDocbookFolders } from "@/lib/structureConverter";
import { Save, Loader2 } from "lucide-react";
import { Layout } from "@/components/Layout";
import { useSidebarStore } from "@/stores/useSidebarStore";

function WorkspaceContent() {
  const params = useParams();
  const orgId = params.org as string;
  const repoId = params.repo as string;
  const personaOptions = useMemo(() => ["dev", "internal"], []);
  const [persona, setPersona] = useState("dev");
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { structure, setStructure } = useProjectStructure();
  const { hasUnsavedChanges, renameFile, closeFileByPath } = useEditorSession();
  const { hasUncommittedChanges, commitChanges } = useSidebarStore();

  useEffect(() => {
    const loadStructure = async () => {
      try {
        const token = localStorage.getItem("pustak_access_token");
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Fetch structure from backend
        const response = await fetch(
          `/api/docbook/${orgId}/structure?branch=staging`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          console.error("Failed to load structure:", response.status, response.statusText);
          setIsLoading(false);
          return;
        }

        const data = await response.json();
        console.log("📁 Backend structure data:", JSON.stringify(data, null, 2));
        console.log("📁 Folders array length:", data.folders?.length);
        
        // Clean the structure (same as EnhancedSidebar does)
        const docbookName = `pustak-docbook-${orgId}`;
        const cleanedFolders = cleanDocbookFolders(data.folders || [], docbookName);
        console.log("🧹 Cleaned folders:", cleanedFolders.length);
        
        // repoId from URL is actually the folder name (e.g., "jaishreram")
        // The actual repo name is in data.repo (e.g., "bajrangbalikijai/pustak-docbook-bajrangbalikijai")
        const actualRepoName = data.repo?.split("/")[1] || repoId;
        console.log("🔍 URL repoId (folder name):", repoId);
        console.log("🔍 Actual repo name:", actualRepoName);
        console.log("🔍 Persona:", persona);
        
        const fileNodes = convertBackendStructureToFileNodes(
          cleanedFolders, // Use cleaned folders
          repoId, // Pass the folder name (e.g., "jaishreram")
          persona,
          "", // basePath
          actualRepoName // actual repo name for path construction
        );
        
        console.log("✅ Converted file nodes:", fileNodes);
        console.log("✅ File nodes count:", fileNodes.length);
        if (fileNodes.length > 0) {
          console.log("✅ First file node:", fileNodes[0]);
        }

        setStructure({
          orgId,
          repoId: actualRepoName, // Store actual repo name for API calls
          persona,
          root: fileNodes,
        });

        setIsLoading(false);
      } catch (error) {
        console.error("Error loading structure:", error);
        setIsLoading(false);
      }
    };

    if (orgId && repoId) {
      loadStructure();
    }
  }, [orgId, repoId, persona, setStructure]);

  if (isLoading) {
    return (
      <Layout>
        <div className="flex h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 flex-shrink-0">
          <NotionSidebar
            orgId={orgId}
            repoId={repoId}
            persona={persona}
            onPersonaChange={setPersona}
            initialTree={structure?.root || []}
          />
        </div>

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800/70 bg-slate-900/50 px-4 py-3">
            <div>
              <h1 className="text-lg font-semibold text-white">
                {repoId}
              </h1>
              <p className="text-xs text-slate-400">
                {orgId} • {persona} persona
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 rounded-lg border border-slate-700/70 bg-slate-800/60 px-2 py-1">
                {personaOptions.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPersona(p)}
                    className={`px-2 py-1 text-xs rounded-md transition ${
                      persona === p
                        ? "bg-blue-500/80 text-white"
                        : "text-slate-300 hover:text-white"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <button
                onClick={async () => {
                  try {
                    // Commit sidebar changes first
                    if (hasUncommittedChanges()) {
                      await commitChanges(
                        (oldPath, newPath) => {
                          // Callback when file is renamed
                          renameFile(oldPath, newPath);
                        },
                        (path) => {
                          // Callback when file is deleted
                          closeFileByPath(path);
                        }
                      );
                    }
                    // Then open commit modal for file content changes
                    if (hasUnsavedChanges()) {
                      setIsCommitModalOpen(true);
                    }
                  } catch (error) {
                    console.error("Error saving changes:", error);
                    alert(`Failed to save changes: ${error instanceof Error ? error.message : "Unknown error"}`);
                  }
                }}
                disabled={!hasUnsavedChanges() && !hasUncommittedChanges()}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-500/90 px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </button>
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 overflow-hidden">
            <TabbedEditor />
          </div>
        </div>

        {/* Bulk Commit Modal */}
        <BulkCommitModal
          isOpen={isCommitModalOpen}
          onClose={() => setIsCommitModalOpen(false)}
          orgId={orgId}
          repoId={repoId}
          persona={persona}
        />
      </div>
    </Layout>
  );
}

export default function WorkspacePage() {
  return (
    <ProjectStructureProvider>
      <EditorSessionProvider>
        <WorkspaceContent />
      </EditorSessionProvider>
    </ProjectStructureProvider>
  );
}

