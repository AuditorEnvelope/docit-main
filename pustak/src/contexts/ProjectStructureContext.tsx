"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export interface FileNode {
  name: string;
  type: "file" | "folder";
  path: string; // Full path from repo root
  content?: string; // For files
  children?: FileNode[]; // For folders
  isDirty?: boolean; // Track if file has unsaved changes
  lastModified?: Date;
}

export interface ProjectStructure {
  orgId: string;
  repoId: string;
  persona: string;
  root: FileNode[];
}

interface ProjectStructureContextType {
  structure: ProjectStructure | null;
  setStructure: (structure: ProjectStructure | null) => void;
  updateFile: (path: string, content: string, markDirty?: boolean) => void;
  createFile: (parentPath: string, fileName: string, content?: string) => FileNode | null;
  createFolder: (parentPath: string, folderName: string) => FileNode | null;
  deleteNode: (path: string) => boolean;
  moveNode: (sourcePath: string, targetPath: string) => boolean;
  getFile: (path: string) => FileNode | null;
  getDirtyFiles: () => FileNode[];
  markClean: (path: string) => void;
  markAllClean: () => void;
}

const ProjectStructureContext = createContext<ProjectStructureContextType | undefined>(undefined);

export function ProjectStructureProvider({ children }: { children: ReactNode }) {
  const [structure, setStructure] = useState<ProjectStructure | null>(null);

  const findNode = useCallback(
    (path: string, nodes: FileNode[] = structure?.root || []): FileNode | null => {
      for (const node of nodes) {
        if (node.path === path) return node;
        if (node.children) {
          const found = findNode(path, node.children);
          if (found) return found;
        }
      }
      return null;
    },
    [structure]
  );

  const findParent = useCallback(
    (path: string, nodes: FileNode[] = structure?.root || [], parent: FileNode[] = structure?.root || []): FileNode[] | null => {
      for (const node of nodes) {
        if (node.path === path) return parent;
        if (node.children) {
          const found = findParent(path, node.children, node.children);
          if (found) return found;
        }
      }
      return null;
    },
    [structure]
  );

  const updateFile = useCallback(
    (path: string, content: string, markDirty = true) => {
      if (!structure) return;

      const node = findNode(path);
      if (node && node.type === "file") {
        node.content = content;
        if (markDirty) {
          node.isDirty = true;
          node.lastModified = new Date();
        }
        setStructure({ ...structure });
      }
    },
    [structure, findNode]
  );

  const createFile = useCallback(
    (parentPath: string, fileName: string, content = ""): FileNode | null => {
      if (!structure) return null;

      const parent = findNode(parentPath);
      if (!parent || parent.type !== "folder") {
        // If parent not found, try to create at root
        if (parentPath === "" || parentPath === structure.repoId) {
          const filePath = `${structure.repoId}/docs/${structure.persona}/${fileName}`;
          const newFile: FileNode = {
            name: fileName,
            type: "file",
            path: filePath,
            content,
            isDirty: true,
            lastModified: new Date(),
          };
          structure.root.push(newFile);
          setStructure({ ...structure });
          return newFile;
        }
        return null;
      }

      // Build full path
      const filePath = `${parentPath}/${fileName}`;
      const newFile: FileNode = {
        name: fileName,
        type: "file",
        path: filePath,
        content,
        isDirty: true,
        lastModified: new Date(),
      };

      if (!parent.children) parent.children = [];
      parent.children.push(newFile);
      setStructure({ ...structure });
      return newFile;
    },
    [structure, findNode]
  );

  const createFolder = useCallback(
    (parentPath: string, folderName: string): FileNode | null => {
      if (!structure) return null;

      const parent = parentPath === "" ? null : findNode(parentPath);
      const targetArray = parent ? (parent.children ||= []) : structure.root;

      const folderPath = parentPath === "" ? folderName : `${parentPath}/${folderName}`;
      const newFolder: FileNode = {
        name: folderName,
        type: "folder",
        path: folderPath,
        children: [],
      };

      targetArray.push(newFolder);
      setStructure({ ...structure });
      return newFolder;
    },
    [structure, findNode]
  );

  const deleteNode = useCallback(
    (path: string): boolean => {
      if (!structure) return false;

      const parent = findParent(path);
      if (!parent) return false;

      const index = parent.findIndex((node) => node.path === path);
      if (index === -1) return false;

      parent.splice(index, 1);
      setStructure({ ...structure });
      return true;
    },
    [structure, findParent]
  );

  const moveNode = useCallback(
    (sourcePath: string, targetPath: string): boolean => {
      if (!structure) return false;

      const node = findNode(sourcePath);
      const targetParent = findNode(targetPath);
      if (!node || !targetParent || targetParent.type !== "folder") return false;

      const sourceParent = findParent(sourcePath);
      if (!sourceParent) return false;

      const index = sourceParent.findIndex((n) => n.path === sourcePath);
      if (index === -1) return false;

      const movedNode = sourceParent.splice(index, 1)[0];
      movedNode.path = targetPath === "" ? movedNode.name : `${targetPath}/${movedNode.name}`;
      updatePathsRecursive(movedNode, targetPath);

      if (!targetParent.children) targetParent.children = [];
      targetParent.children.push(movedNode);
      setStructure({ ...structure });
      return true;
    },
    [structure, findNode, findParent]
  );

  const updatePathsRecursive = (node: FileNode, newParentPath: string) => {
    node.path = newParentPath === "" ? node.name : `${newParentPath}/${node.name}`;
    if (node.children) {
      node.children.forEach((child) => updatePathsRecursive(child, node.path));
    }
  };

  const getFile = useCallback(
    (path: string): FileNode | null => {
      return findNode(path);
    },
    [findNode]
  );

  const getDirtyFiles = useCallback((): FileNode[] => {
    if (!structure) return [];

    const dirty: FileNode[] = [];
    const traverse = (nodes: FileNode[]) => {
      for (const node of nodes) {
        if (node.type === "file" && node.isDirty) {
          dirty.push(node);
        }
        if (node.children) {
          traverse(node.children);
        }
      }
    };
    traverse(structure.root);
    return dirty;
  }, [structure]);

  const markClean = useCallback(
    (path: string) => {
      const node = findNode(path);
      if (node && node.type === "file") {
        node.isDirty = false;
        setStructure({ ...structure });
      }
    },
    [structure, findNode]
  );

  const markAllClean = useCallback(() => {
    if (!structure) return;

    const traverse = (nodes: FileNode[]) => {
      for (const node of nodes) {
        if (node.type === "file") {
          node.isDirty = false;
        }
        if (node.children) {
          traverse(node.children);
        }
      }
    };
    traverse(structure.root);
    setStructure({ ...structure });
  }, [structure]);

  return (
    <ProjectStructureContext.Provider
      value={{
        structure,
        setStructure,
        updateFile,
        createFile,
        createFolder,
        deleteNode,
        moveNode,
        getFile,
        getDirtyFiles,
        markClean,
        markAllClean,
      }}
    >
      {children}
    </ProjectStructureContext.Provider>
  );
}

export function useProjectStructure() {
  const context = useContext(ProjectStructureContext);
  if (context === undefined) {
    throw new Error("useProjectStructure must be used within a ProjectStructureProvider");
  }
  return context;
}

