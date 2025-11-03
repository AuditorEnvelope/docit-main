"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  File,
  Package,
  Box,
  Code2,
  FileCode,
  Loader2,
} from "lucide-react";

// Tree node types matching backend
interface TreeNode {
  id: string;
  type: "repo" | "sdk" | "module" | "feature" | "function" | "class" | "interface" | "file";
  title: string;
  slug: string;
  path: string;
  depth: number;
  position: number;
  children?: TreeNode[];
  content?: any;
  metadata?: any;
}

interface TreeSidebarProps {
  repoName: string;
  currentPath?: string;
}

export function TreeSidebar({ repoName, currentPath }: TreeSidebarProps) {
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    loadTree();
  }, [repoName]);

  const loadTree = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `http://localhost:8000/api/repos/${encodeURIComponent(repoName)}/tree`
      );

      if (!response.ok) {
        throw new Error(`Failed to load tree: ${response.statusText}`);
      }

      const data = await response.json();
      setTree(data);

      // Auto-expand root and first level
      const autoExpand = new Set<string>();
      autoExpand.add(data.id);
      if (data.children) {
        data.children.forEach((child: TreeNode) => autoExpand.add(child.id));
      }
      setExpanded(autoExpand);
    } catch (err) {
      console.error("Error loading tree:", err);
      setError(err instanceof Error ? err.message : "Failed to load tree");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (nodeId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleNodeClick = (node: TreeNode) => {
    // If has children, toggle expand
    if (node.children && node.children.length > 0) {
      toggleExpand(node.id);
    }

    // Navigate to node page
    router.push(`/repo/${repoName}/node/${node.id}`);
  };

  const getNodeIcon = (node: TreeNode, isExpanded: boolean) => {
    const iconClass = "w-4 h-4 flex-shrink-0";

    switch (node.type) {
      case "repo":
        return <Box className={iconClass} />;
      case "sdk":
        return <Package className={iconClass} />;
      case "module":
        return isExpanded ? (
          <FolderOpen className={iconClass} />
        ) : (
          <Folder className={iconClass} />
        );
      case "feature":
        return <Folder className={iconClass} />;
      case "function":
        return <Code2 className={iconClass} />;
      case "class":
        return <FileCode className={iconClass} />;
      case "file":
        return <File className={iconClass} />;
      default:
        return <File className={iconClass} />;
    }
  };

  const renderNode = (node: TreeNode, level: number = 0) => {
    const isExpanded = expanded.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const isActive = currentPath === node.path;

    return (
      <div key={node.id} className="select-none">
        <div
          className={`
            flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer
            hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors
            ${isActive ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400" : ""}
          `}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => handleNodeClick(node)}
        >
          {/* Expand/collapse chevron */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.id);
              }}
              className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          ) : (
            <div className="w-4" /> // Spacer for alignment
          )}

          {/* Icon */}
          {getNodeIcon(node, isExpanded)}

          {/* Title */}
          <span className="text-sm truncate flex-1">{node.title}</span>

          {/* Type badge */}
          {node.type !== "repo" && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {node.type}
            </span>
          )}
        </div>

        {/* Children */}
        {hasChildren && isExpanded && (
          <div>
            {node.children!.map((child) => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-red-600 dark:text-red-400">
        <p className="font-semibold mb-2">Failed to load tree</p>
        <p className="text-xs">{error}</p>
        <button
          onClick={loadTree}
          className="mt-2 text-xs underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!tree) {
    return (
      <div className="p-4 text-sm text-gray-500 dark:text-gray-400">
        No documentation structure found
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-2">
        <div className="mb-4">
          <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Documentation Tree
          </h2>
        </div>
        {renderNode(tree)}
      </div>
    </div>
  );
}
