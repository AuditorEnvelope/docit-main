"use client";

import { Package, Folder, Code2, FileCode, File, Box } from "lucide-react";
import Link from "next/link";

interface TreeNode {
  id: string;
  type: "repo" | "sdk" | "module" | "feature" | "function" | "class" | "interface" | "file";
  title: string;
  slug: string;
  path: string;
  depth: number;
  content?: any;
  metadata?: any;
  children?: Array<{
    id: string;
    type: string;
    title: string;
    slug: string;
    path: string;
    position: number;
  }>;
}

interface NodeContentProps {
  node: TreeNode;
}

export function NodeContent({ node }: NodeContentProps) {
  const getTypeIcon = () => {
    const iconClass = "w-8 h-8";
    switch (node.type) {
      case "repo":
        return <Box className={iconClass} />;
      case "sdk":
        return <Package className={iconClass} />;
      case "module":
        return <Folder className={iconClass} />;
      case "function":
        return <Code2 className={iconClass} />;
      case "class":
        return <FileCode className={iconClass} />;
      default:
        return <File className={iconClass} />;
    }
  };

  const getTypeColor = () => {
    switch (node.type) {
      case "repo":
        return "text-blue-600 dark:text-blue-400";
      case "sdk":
        return "text-purple-600 dark:text-purple-400";
      case "module":
        return "text-green-600 dark:text-green-400";
      case "function":
        return "text-orange-600 dark:text-orange-400";
      case "class":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className={`${getTypeColor()}`}>{getTypeIcon()}</div>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {node.title}
            </h1>
            <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
              {node.type}
            </span>
          </div>
          <p className="text-gray-600 dark:text-gray-400">{node.path}</p>
        </div>
      </div>

      {/* Content based on type */}
      {node.type === "repo" && <RepoContent node={node} />}
      {node.type === "sdk" && <SDKContent node={node} />}
      {node.type === "module" && <ModuleContent node={node} />}
      {node.type === "function" && <FunctionContent node={node} />}
      {node.type === "class" && <ClassContent node={node} />}

      {/* Children list */}
      {node.children && node.children.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
            Contents
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {node.children.map((child) => (
              <Link
                key={child.id}
                href={`/repo/${node.path.split("/")[1]}/node/${child.id}`}
                className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-blue-500 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
              >
                <div className="text-gray-400">
                  {child.type === "sdk" && <Package className="w-5 h-5" />}
                  {child.type === "module" && <Folder className="w-5 h-5" />}
                  {child.type === "function" && <Code2 className="w-5 h-5" />}
                  {child.type === "class" && <FileCode className="w-5 h-5" />}
                  {child.type === "file" && <File className="w-5 h-5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                    {child.title}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {child.type}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RepoContent({ node }: { node: TreeNode }) {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <h2>Repository Overview</h2>
      <p>{node.content?.description || "Documentation for this repository."}</p>
      
      {node.metadata && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <h3 className="text-sm font-semibold mb-2">Metadata</h3>
          <dl className="text-sm space-y-1">
            {Object.entries(node.metadata).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <dt className="font-medium text-gray-600 dark:text-gray-400">{key}:</dt>
                <dd className="text-gray-900 dark:text-gray-100">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}

function SDKContent({ node }: { node: TreeNode }) {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <h2>SDK Documentation</h2>
      <p>{node.content?.description || `Documentation for ${node.title} SDK.`}</p>
    </div>
  );
}

function ModuleContent({ node }: { node: TreeNode }) {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <h2>Module Documentation</h2>
      <p>{node.content?.overview || `Documentation for ${node.title} module.`}</p>
      
      {node.content?.exports && (
        <div className="mt-4">
          <h3>Exports</h3>
          <ul>
            {node.content.exports.map((exp: string, i: number) => (
              <li key={i}>{exp}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function FunctionContent({ node }: { node: TreeNode }) {
  return (
    <div className="space-y-6">
      {/* Signature */}
      {node.content?.signature && (
        <div>
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
            Signature
          </h2>
          <pre className="p-4 bg-gray-900 dark:bg-gray-950 text-gray-100 rounded-lg overflow-x-auto">
            <code>{node.content.signature}</code>
          </pre>
        </div>
      )}

      {/* Description */}
      {node.content?.description && (
        <div>
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
            Description
          </h2>
          <p className="text-gray-700 dark:text-gray-300">{node.content.description}</p>
        </div>
      )}

      {/* Parameters */}
      {node.content?.parameters && node.content.parameters.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
            Parameters
          </h2>
          <div className="space-y-3">
            {node.content.parameters.map((param: any, i: number) => (
              <div key={i} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="flex items-baseline gap-2 mb-1">
                  <code className="font-mono text-sm font-semibold text-blue-600 dark:text-blue-400">
                    {param.name}
                  </code>
                  {param.type && (
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {param.type}
                    </span>
                  )}
                </div>
                {param.description && (
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {param.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Returns */}
      {node.content?.returns && (
        <div>
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
            Returns
          </h2>
          <p className="text-gray-700 dark:text-gray-300">{node.content.returns}</p>
        </div>
      )}

      {/* Example */}
      {node.content?.example && (
        <div>
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
            Example
          </h2>
          <pre className="p-4 bg-gray-900 dark:bg-gray-950 text-gray-100 rounded-lg overflow-x-auto">
            <code>{node.content.example}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

function ClassContent({ node }: { node: TreeNode }) {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <h2>Class Documentation</h2>
      <p>{node.content?.description || `Documentation for ${node.title} class.`}</p>
      
      {node.content?.methods && (
        <div className="mt-4">
          <h3>Methods</h3>
          <ul>
            {node.content.methods.map((method: string, i: number) => (
              <li key={i}><code>{method}</code></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
