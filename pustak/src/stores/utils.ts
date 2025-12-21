/**
 * Utility functions for Draft Store
 * Handles conversions between old structure and new FileNode format
 */

import type { FileNode } from './types';
import type { FileNode as OldFileNode } from '@/contexts/ProjectStructureContext';

/**
 * Convert old ProjectStructure format to new FileNode format
 */
export function convertOldStructureToFileNodes(
  oldNodes: OldFileNode[],
  repoId: string,
  persona: string,
  parentId: string | null = null
): FileNode[] {
  return oldNodes.map(oldNode => {
    const newNode: FileNode = {
      id: oldNode.path, // Use path as ID for server-synced files
      name: oldNode.name,
      type: oldNode.type,
      path: oldNode.path,
      parentId,
      sha: oldNode.sha,
      isTemporary: false,
    };

    if (oldNode.children && oldNode.children.length > 0) {
      newNode.children = convertOldStructureToFileNodes(
        oldNode.children,
        repoId,
        persona,
        newNode.id
      );
    }

    return newNode;
  });
}

/**
 * Convert new FileNode format back to old ProjectStructure format
 * (for backward compatibility during migration)
 */
export function convertFileNodesToOldStructure(
  nodes: FileNode[]
): OldFileNode[] {
  return nodes.map(node => {
    const oldNode: OldFileNode = {
      name: node.name,
      path: node.path,
      type: node.type,
      sha: node.sha,
    };

    if (node.children && node.children.length > 0) {
      oldNode.children = convertFileNodesToOldStructure(node.children);
    }

    return oldNode;
  });
}

/**
 * Flatten tree into a list (depth-first)
 */
export function flattenFileTree(nodes: FileNode[]): FileNode[] {
  const result: FileNode[] = [];
  
  const traverse = (node: FileNode) => {
    result.push(node);
    if (node.children) {
      node.children.forEach(traverse);
    }
  };
  
  nodes.forEach(traverse);
  return result;
}

/**
 * Find a node by predicate
 */
export function findNode(
  nodes: FileNode[],
  predicate: (node: FileNode) => boolean
): FileNode | undefined {
  for (const node of nodes) {
    if (predicate(node)) return node;
    if (node.children) {
      const found = findNode(node.children, predicate);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * Count files in tree
 */
export function countFiles(nodes: FileNode[]): number {
  return nodes.reduce((count, node) => {
    if (node.type === 'file') return count + 1;
    if (node.children) return count + countFiles(node.children);
    return count;
  }, 0);
}

/**
 * Get all parent IDs for a node
 */
export function getParentChain(
  nodeId: string,
  fileTreeMap: Map<string, FileNode>
): string[] {
  const chain: string[] = [];
  let currentNode = fileTreeMap.get(nodeId);
  
  while (currentNode?.parentId) {
    chain.unshift(currentNode.parentId);
    currentNode = fileTreeMap.get(currentNode.parentId);
  }
  
  return chain;
}

/**
 * Check if a node is ancestor of another
 */
export function isAncestor(
  ancestorId: string,
  descendantId: string,
  fileTreeMap: Map<string, FileNode>
): boolean {
  const parentChain = getParentChain(descendantId, fileTreeMap);
  return parentChain.includes(ancestorId);
}
