import { FileNode } from "@/contexts/ProjectStructureContext";

/**
 * Cleans the docbook folder structure by removing the docbook repo folder
 * This matches the logic in EnhancedSidebar
 */
export function cleanDocbookFolders(
  items: any[] | undefined,
  docbookName: string
): any[] {
  if (!items || !Array.isArray(items)) return [];
  return items
    .filter((item) => item.name !== docbookName)
    .map((item) =>
      item.type === "folder"
        ? {
            ...item,
            files: cleanDocbookFolders(item.files, docbookName),
          }
        : item
    );
}

/**
 * Navigates through the backend structure to find the persona folder
 * Backend structure from logs: jaishreram -> docs -> dev -> files
 * The repoId in URL is "jaishreram" (a folder name), not the actual repo name
 */
function findPersonaFolder(
  items: any[],
  persona: string,
  repoId: string
): any[] | null {
  console.log("🔍 findPersonaFolder - items:", items?.length, "persona:", persona, "repoId:", repoId);
  console.log("📋 Top level items:", items.map((i: any) => ({ name: i.name, type: i.type })));
  
  // Step 1: Find the folder matching repoId (e.g., "jaishreram")
  // This is the root folder in the repo that contains the docs structure
  let targetFolder = null;
  
  for (const item of items) {
    if (item.type === "folder" && item.name === repoId) {
      targetFolder = item;
      console.log("✅ Found repoId folder:", repoId);
      break;
    }
  }
  
  // If repoId folder not found, try finding any folder that contains docs
  if (!targetFolder) {
    console.log("⚠️ repoId folder not found, searching for docs folder...");
    for (const item of items) {
      if (item.type === "folder" && item.files) {
        // Check if this folder contains docs
        for (const child of item.files) {
          if (child.name === "docs" && child.type === "folder") {
            targetFolder = item;
            console.log("✅ Found folder containing docs:", item.name);
            break;
          }
        }
        if (targetFolder) break;
      }
    }
  }
  
  if (!targetFolder || !targetFolder.files) {
    console.log("❌ Target folder not found or has no files");
    return null;
  }
  
  // Step 2: Find docs folder inside targetFolder
  let docsFolder = null;
  for (const child of targetFolder.files) {
    if (child.name === "docs" && child.type === "folder" && child.files) {
      docsFolder = child;
      console.log("✅ Found docs folder");
      break;
    }
  }
  
  if (!docsFolder) {
    console.log("❌ Docs folder not found");
    return null;
  }
  
  // Step 3: Find persona folder inside docs
  console.log("📚 Checking personas in docs:", docsFolder.files.map((f: any) => f.name));
  for (const personaItem of docsFolder.files) {
    if (personaItem.name === persona && personaItem.type === "folder") {
      console.log("✅ Found persona folder:", persona, "with", personaItem.files?.length || 0, "items");
      return personaItem.files || [];
    }
  }

  // Fallback: if persona folder not found, return all items under docs so UI still shows something
  console.log("⚠️ Persona folder", persona, "not found; falling back to all docs contents");
  return docsFolder.files || [];
}

export function convertBackendStructureToFileNodes(
  backendFolders: any[],
  folderName: string, // This is the folder name like "jaishreram", not the repo name
  persona: string,
  basePath: string = "",
  actualRepoName?: string // The actual repo name for path construction
): FileNode[] {
  // If basePath is empty, we're at the root - need to navigate to persona folder
  if (basePath === "") {
    const personaFiles = findPersonaFolder(backendFolders, persona, folderName);
    if (personaFiles && personaFiles.length > 0) {
      // Now convert the files inside the persona folder
      // Pass a special marker to indicate we're processing persona files
      return convertPersonaFilesToFileNodes(personaFiles, folderName, persona, actualRepoName || folderName);
    }
    // If persona folder not found, return empty
    console.warn(`Persona folder "${persona}" not found in structure`);
    return [];
  }

  // We're processing files/folders within a subdirectory of the persona folder
  const nodes: FileNode[] = [];
  const repoForPath = actualRepoName || folderName;

  for (const item of backendFolders) {
    const itemPath = `${basePath}/${item.name}`;
    // Path format: {folderName}/docs/{persona}/{itemPath}
    // e.g., "jaishreram/docs/dev/architecture/current.md"
    const fullPath = `${folderName}/docs/${persona}/${itemPath}`;

    if (item.type === "file") {
      nodes.push({
        name: item.name,
        type: "file",
        path: fullPath,
        content: item.content || "",
        isDirty: false,
      });
    } else if (item.type === "folder" && item.files) {
      const children = convertBackendStructureToFileNodes(
        item.files,
        folderName,
        persona,
        itemPath,
        actualRepoName
      );

      nodes.push({
        name: item.name,
        type: "folder",
        path: fullPath,
        children,
      });
    }
  }

  return nodes;
}

/**
 * Converts files directly inside the persona folder (root level of persona)
 */
function convertPersonaFilesToFileNodes(
  personaFiles: any[],
  folderName: string,
  persona: string,
  repoForPath: string
): FileNode[] {
  const nodes: FileNode[] = [];

  for (const item of personaFiles) {
    // For root level files in persona folder, path is just the filename
    // e.g., "jaishreram/docs/dev/SUMMARY.md"
    const fullPath = `${folderName}/docs/${persona}/${item.name}`;

    if (item.type === "file") {
      nodes.push({
        name: item.name,
        type: "file",
        path: fullPath,
        content: item.content || "",
        isDirty: false,
      });
    } else if (item.type === "folder" && item.files) {
      // For folders, recursively convert with basePath set to folder name
      const children = convertBackendStructureToFileNodes(
        item.files,
        folderName,
        persona,
        item.name, // basePath is now the folder name
        repoForPath
      );

      nodes.push({
        name: item.name,
        type: "folder",
        path: fullPath,
        children,
      });
    }
  }

  return nodes;
}

/**
 * Converts FileNode format to backend structure format
 */
export function convertFileNodesToBackendStructure(
  nodes: FileNode[],
  repoId: string,
  persona: string
): any[] {
  return nodes.map((node) => {
    // Extract relative path (remove repoId/docs/persona prefix)
    const prefix = `${repoId}/docs/${persona}/`;
    const relativePath = node.path.startsWith(prefix)
      ? node.path.slice(prefix.length)
      : node.path;

    if (node.type === "file") {
      return {
        name: node.name,
        type: "file",
        path: relativePath,
        content: node.content || "",
      };
    } else {
      return {
        name: node.name,
        type: "folder",
        files: node.children
          ? convertFileNodesToBackendStructure(node.children, repoId, persona)
          : [],
      };
    }
  });
}

