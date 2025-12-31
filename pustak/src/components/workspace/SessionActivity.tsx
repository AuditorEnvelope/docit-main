/**
 * Session Activity Panel - Git-Style Version Control UI
 * 
 * Shows visual diff stats, change indicators, and commit history
 * like VS Code's Source Control panel
 */

'use client';

import { useState, useEffect } from 'react';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { 
  ChevronRight, 
  FileEdit, 
  FilePlus, 
  FileText,
  GitBranch,
  GitCommit,
  Clock,
  Sparkles,
  TrendingUp,
  BarChart3,
  Undo2,
  X
} from 'lucide-react';

interface FileChange {
  id: string;
  title: string;
  type: 'modified' | 'created' | 'deleted';
  additions: number;
  deletions: number;
  timestamp: number;
}

interface SessionActivityProps {
  onPublishClick?: () => void; // Callback to open commit modal
}

export function SessionActivity({ onPublishClick }: SessionActivityProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { pendingChanges, contentCache, getNodeById, setActivePageId, structureDirty, revertChanges, deletedNodes, restoreDeletedNode } = useWorkspaceStore();
  const [animateChanges, setAnimateChanges] = useState<Set<string>>(new Set());
  const [revertConfirmId, setRevertConfirmId] = useState<string | null>(null);
  const [revertFileName, setRevertFileName] = useState<string>('');

  // Build Git-style change list - includes modified, created, AND deleted files
  const modifiedAndCreated: FileChange[] = Array.from(pendingChanges).map(pageId => {
    const node = getNodeById(pageId);
    const cached = contentCache[pageId];
    
    // Simulate diff stats (in real app, calculate actual line changes)
    const contentLength = cached?.content?.length || 0;
    const additions = Math.floor(contentLength / 50);
    const deletions = Math.floor(contentLength / 100);
    
    return {
      id: pageId,
      title: node?.title || 'Untitled',
      type: node?.isTempNode ? 'created' : 'modified',
      additions,
      deletions,
      timestamp: cached?.lastModified || Date.now(),
    };
  });

  // Add deleted files to the change list
  const deletedFiles: FileChange[] = deletedNodes && typeof deletedNodes === 'object' 
    ? Object.values(deletedNodes).map(deletedInfo => ({
        id: deletedInfo.id,
        title: deletedInfo.title,
        type: 'deleted' as const,
        additions: 0,
        deletions: 1, // Show deletion count
        timestamp: deletedInfo.timestamp,
      }))
    : [];

  // Combine and sort all changes
  const fileChanges: FileChange[] = [...modifiedAndCreated, ...deletedFiles].sort((a, b) => b.timestamp - a.timestamp);

  const totalAdditions = fileChanges.reduce((sum, f) => sum + f.additions, 0);
  const totalDeletions = fileChanges.reduce((sum, f) => sum + f.deletions, 0);
  const totalChanges = fileChanges.length;

  // Animate new changes
  useEffect(() => {
    const newIds = new Set(fileChanges.map(f => f.id));
    const changedIds = Array.from(newIds).filter(id => !animateChanges.has(id));
    
    if (changedIds.length > 0) {
      setAnimateChanges(newIds);
      // Remove animation class after 600ms
      const timer = setTimeout(() => {
        setAnimateChanges(new Set());
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [fileChanges.length]);

  const handleRevertFile = (fileId: string, fileTitle: string) => {
    setRevertConfirmId(fileId);
    setRevertFileName(fileTitle);
  };

  const confirmRevert = async () => {
    if (revertConfirmId) {
      await revertChanges(revertConfirmId);
      setRevertConfirmId(null);
    }
  };

  const cancelRevert = () => {
    setRevertConfirmId(null);
    setRevertFileName('');
  };

  const getRelativeTime = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="fixed right-0 top-1/2 -translate-y-1/2 bg-slate-800 border-l border-slate-700 rounded-l-lg p-2 hover:bg-slate-700 transition z-40"
        aria-label="Show session activity"
      >
        <ChevronRight className="w-4 h-4 text-slate-400 rotate-180" />
      </button>
    );
  }

  return (
    <div className="h-full w-[280px] border-l border-slate-800/50 bg-slate-950/80 backdrop-blur-sm overflow-y-auto z-30">
      {/* Header - Git Style */}
      <div className="sticky top-0 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800/50 z-10">
        <div className="px-3 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-semibold text-white">Source Control</h3>
          </div>
          <button
            onClick={() => setIsCollapsed(true)}
            className="hover:bg-slate-700/50 rounded p-1 transition"
            aria-label="Hide session activity"
          >
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>

        {/* Stats Bar - Animated */}
        {totalChanges > 0 && (
          <div className="px-3 py-2 bg-slate-800/30 border-t border-slate-800/50">
            <div className="flex items-center justify-between text-[10px] mb-1.5">
              <span className="text-slate-400">CHANGES</span>
              <span className="text-white font-medium">{totalChanges} file{totalChanges !== 1 ? 's' : ''}</span>
            </div>
            
            {/* Diff Stats Bar */}
            <div className="flex items-center gap-2 text-[10px]">
              <div className="flex items-center gap-1 text-emerald-400">
                <TrendingUp className="w-3 h-3" />
                <span className="font-medium">+{totalAdditions}</span>
              </div>
              <div className="flex-1 h-1 bg-slate-700/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500 ease-out"
                  style={{ width: `${totalAdditions > 0 ? Math.min((totalAdditions / (totalAdditions + totalDeletions)) * 100, 100) : 0}%` }}
                />
              </div>
              <div className="flex items-center gap-1 text-red-400">
                <span className="font-medium">-{totalDeletions}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Changes List - Git Style */}
      <div className="p-2">
        {fileChanges.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-slate-800/50 flex items-center justify-center animate-pulse">
              <Sparkles className="w-5 h-5 text-slate-500" />
            </div>
            <p className="text-xs font-medium text-slate-400 mb-1">No Changes</p>
            <p className="text-[10px] text-slate-600 leading-relaxed">
              Edit documents to track changes
            </p>
            
            {/* Quick Stats */}
            <div className="mt-6 pt-4 border-t border-slate-800/50">
              <div className="flex items-center justify-center gap-4 text-[10px] text-slate-600">
                <div className="flex items-center gap-1">
                  <GitCommit className="w-3 h-3" />
                  <span>0 commits</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>Session started</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold px-2 py-1.5 mb-1">
              Uncommitted Changes
            </div>
            <div className="space-y-0.5">
              {fileChanges.map(file => {
                const isAnimating = animateChanges.has(file.id);
                const isReverting = revertConfirmId === file.id;
                return (
                  <div
                    key={file.id}
                    className={`
                      relative group
                      ${isAnimating ? 'animate-pulse bg-blue-500/10' : ''}
                    `}
                  >
                    {/* File Item - Clickable Area (disabled for deleted files) */}
                    <div
                      onClick={() => {
                        if (file.type !== 'deleted') {
                          setActivePageId(file.id);
                        }
                      }}
                      className={`w-full text-left px-2 py-1.5 rounded transition-all ${
                        file.type === 'deleted' 
                          ? 'opacity-60 cursor-not-allowed' 
                          : 'hover:bg-slate-800/50 cursor-pointer'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {/* Status Indicator */}
                        <div
                          className={`
                            shrink-0 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold
                            ${file.type === 'created' ? 'bg-emerald-500/20 text-emerald-400' : ''}
                            ${file.type === 'modified' ? 'bg-blue-500/20 text-blue-400' : ''}
                            ${file.type === 'deleted' ? 'bg-red-500/20 text-red-400' : ''}
                          `}
                        >
                          {file.type === 'created' ? 'A' : file.type === 'modified' ? 'M' : 'D'}
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className={`text-xs font-medium truncate transition ${
                            file.type === 'deleted' 
                              ? 'text-red-400 line-through' 
                              : 'text-white group-hover:text-blue-400'
                          }`}>
                            {file.title}
                          </p>
                          
                          {/* Inline Diff Stats */}
                          <div className="flex items-center gap-2 mt-0.5">
                            {file.additions > 0 && (
                              <span className="text-[10px] text-emerald-400">+{file.additions}</span>
                            )}
                            {file.deletions > 0 && (
                              <span className="text-[10px] text-red-400">-{file.deletions}</span>
                            )}
                            <span className="text-[10px] text-slate-500">• {getRelativeTime(file.timestamp)}</span>
                          </div>
                        </div>

                        {/* Action Button - Revert for modified/created, Restore for deleted */}
                        {file.type !== 'deleted' ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRevertFile(file.id, file.title);
                            }}
                            className="shrink-0 p-1 rounded hover:bg-red-500/20 transition-all"
                            title="Revert changes"
                          >
                            <Undo2 className="w-3.5 h-3.5 text-red-400 hover:text-red-300 cursor-pointer" />
                          </button>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              restoreDeletedNode(file.id);
                            }}
                            className="shrink-0 p-1 rounded hover:bg-emerald-500/20 transition-all"
                            title="Restore deleted file (like Git restore)"
                          >
                            <Undo2 className="w-3.5 h-3.5 text-emerald-400 hover:text-emerald-300 cursor-pointer rotate-180" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Bottom Action Area */}
      {totalChanges > 0 && (
        <div className="sticky bottom-0 border-t border-slate-800/50 bg-slate-900/95 backdrop-blur-sm p-3">
          <button 
            onClick={onPublishClick}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition-all shadow-lg shadow-blue-500/20 cursor-pointer"
          >
            <GitCommit className="w-3.5 h-3.5" />
            <span>Publish Changes</span>
          </button>
        </div>
      )}

      {/* Centered Revert Confirmation Modal */}
      {revertConfirmId && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            onClick={cancelRevert}
          />
          
          {/* Modal */}
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[101] w-full max-w-md">
            <div className="bg-slate-800 border border-red-500/50 rounded-xl shadow-2xl p-6 mx-4">
              <div className="flex items-start gap-3 mb-4">
                <div className="shrink-0 w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                  <Undo2 className="w-5 h-5 text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-white mb-1">Revert changes?</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    This will discard all changes to <span className="text-white font-medium">{revertFileName}</span>
                  </p>
                </div>
                <button
                  onClick={cancelRevert}
                  className="shrink-0 p-1 hover:bg-slate-700 rounded transition"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={confirmRevert}
                  className="flex-1 px-4 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-red-500/20"
                >
                  Revert
                </button>
                <button
                  onClick={cancelRevert}
                  className="flex-1 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded-lg transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
