import { FileNode } from "@/contexts/ProjectStructureContext";
import { SidebarNode } from "@/stores/useSidebarStore";

/**
 * Convert FileNode to SidebarNode format
 */
export function convertFileNodeToSidebarNode(fileNode: FileNode): SidebarNode {
  const sidebarNode: SidebarNode = {
    id: fileNode.path, // Use path as ID
    name: fileNode.name,
    type: fileNode.type,
    path: fileNode.path,
    content: fileNode.content,
    isDirty: fileNode.isDirty,
    isExpanded: fileNode.type === "folder" ? true : undefined, // Default expand folders
  };

  if (fileNode.children && fileNode.children.length > 0) {
    sidebarNode.children = fileNode.children.map(convertFileNodeToSidebarNode);
  }

  return sidebarNode;
}

/**
 * Convert SidebarNode back to FileNode format
 */
export function convertSidebarNodeToFileNode(sidebarNode: SidebarNode): FileNode {
  const fileNode: FileNode = {
    name: sidebarNode.name,
    type: sidebarNode.type,
    path: sidebarNode.path,
    content: sidebarNode.content,
    isDirty: sidebarNode.isDirty,
  };

  if (sidebarNode.children && sidebarNode.children.length > 0) {
    fileNode.children = sidebarNode.children.map(convertSidebarNodeToFileNode);
  }

  return fileNode;
}

