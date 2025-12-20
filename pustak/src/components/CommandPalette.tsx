'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, FileText, FolderPlus, Trash, Edit2, Save } from 'lucide-react';
import { useEditor } from '@/contexts/EditorContext';

interface Command {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  shortcut?: string;
  category: 'navigation' | 'file' | 'edit';
}

interface CommandPaletteProps {
  onCreatePage?: () => void;
  onCreateFolder?: () => void;
  onSaveAll?: () => void;
}

export function CommandPalette({ onCreatePage, onCreateFolder, onSaveAll }: CommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const { getDirtyPages } = useEditor();

  const commands: Command[] = [
    {
      id: 'new-page',
      label: 'Create New Page',
      icon: FileText,
      action: () => {
        setIsOpen(false);
        onCreatePage?.();
      },
      shortcut: '⌘N',
      category: 'file',
    },
    {
      id: 'new-folder',
      label: 'Create New Folder',
      icon: FolderPlus,
      action: () => {
        setIsOpen(false);
        onCreateFolder?.();
      },
      category: 'file',
    },
    {
      id: 'save-all',
      label: `Save All Changes (${getDirtyPages().length})`,
      icon: Save,
      action: () => {
        setIsOpen(false);
        onSaveAll?.();
      },
      shortcut: '⌘S',
      category: 'edit',
    },
  ];

  const filteredCommands = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(search.toLowerCase())
  );

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Toggle palette with Cmd/Ctrl + K
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setIsOpen(prev => !prev);
      setSearch('');
      setSelectedIndex(0);
    }

    // Close with Escape
    if (e.key === 'Escape') {
      setIsOpen(false);
      setSearch('');
      setSelectedIndex(0);
    }

    // Navigate with arrow keys
    if (isOpen) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < filteredCommands.length - 1 ? prev + 1 : prev
        );
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : 0);
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        filteredCommands[selectedIndex]?.action();
      }
    }
  }, [isOpen, filteredCommands, selectedIndex]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Reset selected index when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-32"
      onClick={() => setIsOpen(false)}
    >
      <div 
        className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="border-b border-slate-800 p-4">
          <div className="flex items-center gap-3">
            <Search className="h-5 w-5 text-slate-400" />
            <input
              type="text"
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent text-slate-100 outline-none placeholder:text-slate-500"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
            <kbd className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">
              ESC
            </kbd>
          </div>
        </div>

        {/* Commands List */}
        <div className="max-h-96 overflow-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-500">
              No commands found
            </div>
          ) : (
            filteredCommands.map((cmd, index) => {
              const Icon = cmd.icon;
              const isSelected = index === selectedIndex;
              
              return (
                <button
                  key={cmd.id}
                  onClick={cmd.action}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex w-full items-center justify-between rounded-lg px-4 py-3 text-left transition ${
                    isSelected 
                      ? 'bg-blue-500/20 text-blue-200' 
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-5 w-5 ${isSelected ? 'text-blue-400' : 'text-slate-400'}`} />
                    <span>{cmd.label}</span>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">
                      {cmd.shortcut}
                    </kbd>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Help Text */}
        <div className="border-t border-slate-800 px-4 py-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Press ⌘K to toggle command palette</span>
            <div className="flex items-center gap-4">
              <span>↑↓ Navigate</span>
              <span>↵ Select</span>
              <span>ESC Close</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
