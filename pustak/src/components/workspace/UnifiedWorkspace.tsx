/**
 * Unified Workspace - Main Container
 * 
 * Combines Sidebar + Editor into a split-pane layout
 * This is the entry point for the new editor experience
 */

'use client';

import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';
import { useWorkspaceStore } from '@/stores/useWorkspaceStore';
import { DocumentSidebar } from './DocumentSidebar';
import { DocumentEditor } from './DocumentEditor';
import { SessionActivity } from './SessionActivity';
import { CommitModal } from '../CommitModal';
import { BookOpen, Loader2, Search, Sun, Moon, User, LogOut, Settings, Crown } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface UnifiedWorkspaceProps {
  orgId: string;
  repoId: string;
}

export function UnifiedWorkspace({ orgId, repoId }: UnifiedWorkspaceProps) {
  const { fileTree, initializeTree, setActivePageId, activePageId, getNodeById, pendingChanges, structureDirty, syncWorkspace, hasUnsavedChanges } = useWorkspaceStore();
  const { token, user, isAuthenticated, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const { theme, setTheme } = useTheme();
  const router = useRouter();

  const handleCommit = async (message: string) => {
    if (!token) return;
    setIsCommitting(true);
    try {
      await syncWorkspace(orgId, repoId, token, message);
      setIsCommitModalOpen(false);
    } catch (error) {
      console.error('Commit failed:', error);
    } finally {
      setIsCommitting(false);
    }
  };

  const activePage = activePageId ? getNodeById(activePageId) : null;
  const changeCount = pendingChanges.size + (structureDirty ? 1 : 0);
  const hasChanges = hasUnsavedChanges();

  // Get breadcrumb path
  const getBreadcrumb = () => {
    if (!activePage) return [];
    const path = [];
    let current = activePage;
    while (current && current.id !== 'root') {
      path.unshift(current.title);
      if (current.parentId) {
        current = getNodeById(current.parentId);
      } else {
        break;
      }
    }
    return path;
  };

  const breadcrumb = getBreadcrumb();

  // Load workspace tree on mount
  useEffect(() => {
    setMounted(true);
    
    console.log('[UnifiedWorkspace] Effect triggered', { orgId, repoId, hasToken: !!token });
    
    if (!token) {
      console.warn('[UnifiedWorkspace] No auth token available, waiting...');
      return; // Wait for auth
    }
    
    // ALWAYS fetch fresh data from backend, ignore persisted cache
    const loadWorkspace = async () => {
      try {
        const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
        // Don't add /api/v1 if BACKEND_URL already includes it
        const baseUrl = BACKEND_URL.includes('/api/v1') ? BACKEND_URL : `${BACKEND_URL}/api/v1`;
        const url = `${baseUrl}/workspace/${orgId}/${repoId}/tree`;
        
        console.log('[UnifiedWorkspace] Fetching workspace tree from:', url);
        
        const response = await fetch(
          url,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
        
        console.log('[UnifiedWorkspace] Response status:', response.status);

        if (!response.ok) {
          console.error('[UnifiedWorkspace] Failed to load workspace:', response.status, response.statusText);
          throw new Error('Failed to load workspace');
        }

        const data = await response.json();
        console.log('[UnifiedWorkspace] Received tree data:', data);
        initializeTree(data.tree);

        // Auto-select first page if available
        if (data.tree?.children?.length > 0) {
          const firstPage = data.tree.children.find((node: any) => node.type === 'page');
          if (firstPage) {
            setActivePageId(firstPage.id);
          }
        }
      } catch (error) {
        console.error('[UnifiedWorkspace] Error loading workspace:', error);
        // Initialize with empty tree
        initializeTree({
          id: 'root',
          type: 'folder',
          title: 'Root',
          parentId: null,
          position: 0,
          children: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
      }
    };

    console.log('[UnifiedWorkspace] Calling loadWorkspace...');
    loadWorkspace();
  }, [orgId, repoId, initializeTree, setActivePageId, token]);

  if (!fileTree) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (!mounted) {
    return null;
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-slate-950 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="flex-shrink-0 z-50 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800/50">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-6 h-6 text-blue-400" />
              <h1 className="text-xl font-bold text-white">Pustak</h1>
              <span className="text-xs bg-blue-900 text-blue-200 px-2 py-1 rounded-full">
                Beta
              </span>
            </div>

            {/* Breadcrumb */}
            {breadcrumb.length > 0 && (
              <div className="hidden md:flex items-center space-x-2 text-sm text-slate-400">
                <span>/</span>
                {breadcrumb.map((item, index) => (
                  <span key={index} className="flex items-center">
                    <span className={index === breadcrumb.length - 1 ? 'text-white font-medium' : ''}>
                      {item}
                    </span>
                    {index < breadcrumb.length - 1 && <span className="mx-2">/</span>}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* Status Indicator */}
            {hasChanges && (
              <button
                onClick={() => setIsCommitModalOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition"
              >
                <span className="w-2 h-2 bg-orange-400 rounded-full" />
                Publish {changeCount > 0 && `(${changeCount})`}
              </button>
            )}
            {/* Search Button */}
            <button
              className="flex items-center space-x-2 px-3 py-2 text-sm text-slate-400 border border-slate-700 rounded-md hover:bg-slate-800 transition-colors"
            >
              <Search className="w-4 h-4" />
              <span className="hidden sm:inline">Search docs...</span>
              <kbd className="hidden sm:inline text-xs bg-slate-700 px-1 rounded">⌘K</kbd>
            </button>

            {/* Theme Toggle */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {/* User Menu */}
            {isAuthenticated && user ? (
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center space-x-2 p-1 rounded-full hover:bg-slate-800 transition-colors"
                >
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.name || user.username || 'User'}
                      className="w-8 h-8 rounded-full border-2 border-blue-500"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold">
                      {(user.name || user.username || 'U')[0].toUpperCase()}
                    </div>
                  )}
                </button>

                {/* Dropdown Menu */}
                {userMenuOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setUserMenuOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-64 bg-slate-800 rounded-lg shadow-xl border border-slate-700 z-50">
                      {/* User Info */}
                      <div className="p-4 border-b border-slate-700">
                        <p className="font-semibold text-white">
                          {user.name || user.username}
                        </p>
                        <p className="text-sm text-slate-400">
                          {user.email || `@${user.username}`}
                        </p>
                        <div className="mt-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${
                            user.plan === 'free' ? 'bg-slate-700 text-slate-300' :
                            user.plan === 'pro' ? 'bg-blue-900/30 text-blue-400' :
                            user.plan === 'team' ? 'bg-purple-900/30 text-purple-400' :
                            'bg-gradient-to-r from-yellow-400 to-orange-500 text-white'
                          }`}>
                            {user.plan !== 'free' && <Crown className="w-3 h-3" />}
                            {user.plan.toUpperCase()}
                          </span>
                        </div>
                      </div>

                      {/* Menu Items */}
                      <div className="py-2">
                        <button
                          onClick={() => {
                            setUserMenuOpen(false);
                            router.push('/dashboard');
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                          <User className="w-4 h-4" />
                          Dashboard
                        </button>
                        <button
                          onClick={() => {
                            setUserMenuOpen(false);
                            router.push('/pricing');
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                          <Crown className="w-4 h-4" />
                          Upgrade Plan
                        </button>
                        <button
                          onClick={() => {
                            setUserMenuOpen(false);
                            router.push('/settings');
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                          <Settings className="w-4 h-4" />
                          Settings
                        </button>
                      </div>

                      {/* Logout */}
                      <div className="border-t border-slate-700 py-2">
                        <button
                          onClick={() => {
                            setUserMenuOpen(false);
                            logout();
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-red-900/20 transition-colors"
                        >
                          <LogOut className="w-4 h-4" />
                          Logout
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <button
                onClick={() => router.push('/login')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors text-sm"
              >
                Login
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Workspace Content */}
      <div className="flex-1 relative">
        {/* Left Sidebar - Independent Scroll */}
        <div className="fixed left-0 top-[57px] bottom-0 w-[280px] border-r border-slate-800/50 overflow-y-auto">
          <DocumentSidebar
            orgId={orgId}
            repoId={repoId}
            onPageSelect={(pageId) => setActivePageId(pageId)}
          />
        </div>

        {/* Center Editor - Independent Scroll (Leave space for right sidebar) */}
        <div className="fixed left-[280px] right-[280px] top-[57px] bottom-0 overflow-y-auto">
          <DocumentEditor orgId={orgId} repoId={repoId} />
        </div>

        {/* Right Sidebar - Session Activity (fixed to account for navbar) */}
        <div className="fixed right-0 top-[57px] bottom-0">
          <SessionActivity />
        </div>
      </div>

      {/* Commit Modal */}
      <CommitModal
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        onCommit={handleCommit}
        pageTitle={activePage?.title || 'Document'}
        isLoading={isCommitting}
      />
    </div>
  );
}
