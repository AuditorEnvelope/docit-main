/**
 * Session Activity Panel - Right Sidebar
 * 
 * Shows a timeline of recent changes during the current editing session
 * Replaces raw Git diff with user-friendly activity feed
 */

'use client';

import { useState } from 'react';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { ChevronRight, FileEdit, FilePlus, Sparkles } from 'lucide-react';

export function SessionActivity() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { pendingChanges, contentCache, getNodeById, setActivePageId } = useWorkspaceStore();

  // Build activity timeline from pending changes
  const activities = Array.from(pendingChanges).map(pageId => {
    const node = getNodeById(pageId);
    const cached = contentCache[pageId];
    
    return {
      id: pageId,
      title: node?.title || 'Untitled',
      type: node?.isTempNode ? 'created' : 'edited',
      timestamp: cached?.lastModified || Date.now(),
    };
  }).sort((a, b) => b.timestamp - a.timestamp);

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
    <div className="h-full w-[280px] border-l border-slate-800/50 bg-slate-900/50 backdrop-blur-sm overflow-y-auto z-30">
      {/* Header */}
      <div className="sticky top-0 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800/50 p-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Session Activity</h3>
        <button
          onClick={() => setIsCollapsed(true)}
          className="hover:bg-slate-700 rounded p-1 transition"
          aria-label="Hide session activity"
        >
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Timeline */}
      <div className="p-4 space-y-3">
        {activities.length === 0 ? (
          <div className="text-center py-16 px-6">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-slate-800/50 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-slate-500" />
            </div>
            <p className="text-sm font-medium text-slate-400 mb-2">No recent changes</p>
            <p className="text-xs text-slate-600 leading-relaxed">
              Start editing documents to see your activity timeline here
            </p>
            <div className="mt-6 pt-6 border-t border-slate-800/50">
              <p className="text-xs text-slate-600 mb-2">💡 Tip:</p>
              <p className="text-xs text-slate-500">
                Press <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">⌘K</kbd> to search docs
              </p>
            </div>
          </div>
        ) : (
          activities.map(activity => (
            <button
              key={activity.id}
              onClick={() => setActivePageId(activity.id)}
              className="w-full text-left p-3 rounded-lg hover:bg-slate-800/50 transition group"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`
                    shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                    ${
                      activity.type === 'created'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-blue-500/20 text-blue-400'
                    }
                  `}
                >
                  {activity.type === 'created' ? (
                    <FilePlus className="w-4 h-4" />
                  ) : (
                    <FileEdit className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate group-hover:text-blue-400 transition">
                    {activity.title}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {activity.type === 'created' ? 'Created' : 'Edited'} •{' '}
                    {getRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
