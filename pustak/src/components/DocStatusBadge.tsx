"use client";

import { CheckCircle, AlertCircle, Clock } from "lucide-react";

interface DocStatusBadgeProps {
  hasDocsFolder: boolean;
  isGenerating?: boolean;
}

export function DocStatusBadge({
  hasDocsFolder,
  isGenerating = false,
}: DocStatusBadgeProps) {
  if (isGenerating) {
    return (
      <div className="flex items-center space-x-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 rounded text-xs font-medium text-blue-700 dark:text-blue-300">
        <Clock className="w-3 h-3 animate-spin" />
        <span>Generating</span>
      </div>
    );
  }

  if (hasDocsFolder) {
    return (
      <div className="flex items-center space-x-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 rounded text-xs font-medium text-green-700 dark:text-green-300">
        <CheckCircle className="w-3 h-3" />
        <span>Docs Ready</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-1 px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 rounded text-xs font-medium text-yellow-700 dark:text-yellow-300">
      <AlertCircle className="w-3 h-3" />
      <span>No Docs</span>
    </div>
  );
}
