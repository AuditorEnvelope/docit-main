"use client";

import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

interface BreadcrumbNode {
  id: string;
  title: string;
  path: string;
  type: string;
}

interface BreadcrumbsProps {
  node: BreadcrumbNode;
  repoName: string;
}

export function Breadcrumbs({ node, repoName }: BreadcrumbsProps) {
  // Build path from node.path
  const pathParts = node.path.split("/").filter(Boolean);
  
  const breadcrumbs = [
    { title: repoName, path: `/repo/${repoName}`, id: "root" },
  ];

  // Add intermediate paths
  let currentPath = "";
  pathParts.forEach((part, index) => {
    currentPath += `/${part}`;
    if (index < pathParts.length - 1) {
      breadcrumbs.push({
        title: part,
        path: currentPath,
        id: `path-${index}`,
      });
    }
  });

  // Add current node
  breadcrumbs.push({
    title: node.title,
    path: node.path,
    id: node.id,
  });

  return (
    <nav className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
      <Link
        href={`/repo/${repoName}`}
        className="hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
      >
        <Home className="w-4 h-4" />
      </Link>

      {breadcrumbs.map((crumb, index) => (
        <div key={crumb.id} className="flex items-center space-x-2">
          <ChevronRight className="w-4 h-4 text-gray-400" />
          {index === breadcrumbs.length - 1 ? (
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {crumb.title}
            </span>
          ) : (
            <Link
              href={`/repo/${repoName}/node/${crumb.id}`}
              className="hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
            >
              {crumb.title}
            </Link>
          )}
        </div>
      ))}
    </nav>
  );
}
