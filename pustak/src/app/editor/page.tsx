'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Layout } from '@/components/Layout';
import { EnhancedSidebar } from '@/components/EnhancedSidebar';
import { MultiPageEditor } from '@/components/MultiPageEditor';
import { CommandPalette } from '@/components/CommandPalette';
import { useEditor } from '@/contexts/EditorContext';

export default function EditorPage() {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentRepo, setCurrentRepo] = useState<string>('');
  const { getDirtyPages } = useEditor();

  useEffect(() => {
    // Get user token to verify authentication
    const token = localStorage.getItem('pustak_access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Load user's organizations to get docbook repo
    const loadUserOrgs = async () => {
      try {
        const response = await fetch('/api/user/organizations', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.organizations && data.organizations.length > 0) {
            const firstOrg = data.organizations[0];
            const orgLogin = typeof firstOrg === 'string' ? firstOrg : firstOrg.login;
            setCurrentRepo(`${orgLogin}/pustak-docbook-${orgLogin}`);
          }
        }
      } catch (error) {
        console.error('Failed to load organizations:', error);
      }
    };

    loadUserOrgs();
  }, [router]);

  // Warn before leaving if there are unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      const dirtyPages = getDirtyPages();
      if (dirtyPages.length > 0) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [getDirtyPages]);

  const handleSaveAll = () => {
    // Trigger save all from the MultiPageEditor
    const saveAllButton = document.querySelector('[data-save-all]') as HTMLButtonElement;
    saveAllButton?.click();
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-80 flex-shrink-0 overflow-y-auto border-r border-slate-800">
          <EnhancedSidebar onClose={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Main Editor Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="border-b border-slate-800 bg-slate-900/50 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-700"
                >
                  Show Sidebar
                </button>
              )}
              <h1 className="text-xl font-semibold text-slate-100">
                Documentation Editor
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-sm text-slate-400">
                Press <kbd className="rounded bg-slate-800 px-2 py-1 text-xs">⌘K</kbd> for commands
              </div>
            </div>
          </div>
        </div>

        {/* Editor */}
        <div className="flex-1 overflow-hidden">
          {currentRepo ? (
            <MultiPageEditor repo={currentRepo} />
          ) : (
            <div className="flex h-full items-center justify-center text-slate-400">
              <p>Loading...</p>
            </div>
          )}
        </div>
      </div>

      {/* Command Palette */}
      <CommandPalette onSaveAll={handleSaveAll} />
    </div>
  );
}
