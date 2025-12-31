/**
 * Document Sidebar - GitBook/Mintlify Style
 * 
 * Clean, minimal sidebar focused on document navigation
 * Not project structure - just documentation
 */

'use client';

import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { SidebarNode } from './SidebarNode';
import { Search, FilePlus, Loader2 } from 'lucide-react';
import { useState } from 'react';

interface DocumentSidebarProps {
  orgId: string;
  repoId: string;
  onPageSelect?: (pageId: string) => void;
}

export function DocumentSidebar({ orgId, repoId, onPageSelect }: DocumentSidebarProps) {
  const { fileTree, expandedFolders } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');

  // Filter tree based on search
  const filterTree = (node: any): any | null => {
    if (!node) return null;
    
    const matchesSearch = !searchQuery || 
      node.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.children?.some((child: any) => 
        child.title.toLowerCase().includes(searchQuery.toLowerCase())
      );
    
    if (!matchesSearch && node.type === 'folder') {
      return null;
    }
    
    return {
      ...node,
      children: node.children
        ?.map((child: any) => filterTree(child))
        .filter((child: any) => child !== null) || []
    };
  };

  const filteredTree = fileTree ? filterTree(fileTree) : null;

  return (
    <div className="h-full flex flex-col bg-slate-950/50 border-r border-slate-800/50 text-sm">
      {/* Clean Header */}
      <div className="p-3 border-b border-slate-800/50 bg-slate-900/30">
        <h2 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Documentation
        </h2>
      </div>

      {/* Document Tree */}
      <div className="flex-1 overflow-y-auto py-1.5 px-1.5">
        {filteredTree ? (
          <div className="space-y-1">
            {filteredTree.children.map((child: any) => (
              <SidebarNode
                key={child.id}
                node={child}
                level={0}
                onNodeClick={onPageSelect}
              />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-sm">
            <p>No documents found</p>
            {searchQuery && (
              <p className="text-xs mt-2">Try a different search term</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

