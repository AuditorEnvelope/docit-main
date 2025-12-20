'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface PageContent {
  path: string;
  content: string;
  originalContent: string;
  isDirty: boolean;
  lastSaved?: Date;
}

interface EditorState {
  openPages: Map<string, PageContent>;
  activePagePath: string | null;
  sidebarMode: 'view' | 'edit';
}

interface EditorContextType {
  state: EditorState;
  openPage: (path: string, content: string) => void;
  closePage: (path: string) => void;
  setActivePagePath: (path: string | null) => void;
  updatePageContent: (path: string, content: string) => void;
  markPageSaved: (path: string) => void;
  getActivePage: () => PageContent | null;
  getDirtyPages: () => PageContent[];
  setSidebarMode: (mode: 'view' | 'edit') => void;
  hasUnsavedChanges: (path: string) => boolean;
  closeAllPages: () => void;
}

const EditorContext = createContext<EditorContextType | undefined>(undefined);

export function EditorProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<EditorState>({
    openPages: new Map(),
    activePagePath: null,
    sidebarMode: 'view',
  });

  const openPage = useCallback((path: string, content: string) => {
    setState(prev => {
      const newPages = new Map(prev.openPages);
      if (!newPages.has(path)) {
        newPages.set(path, {
          path,
          content,
          originalContent: content,
          isDirty: false,
        });
      }
      return {
        ...prev,
        openPages: newPages,
        activePagePath: path,
      };
    });
  }, []);

  const closePage = useCallback((path: string) => {
    setState(prev => {
      const newPages = new Map(prev.openPages);
      newPages.delete(path);
      const newActivePath = prev.activePagePath === path
        ? (newPages.size > 0 ? Array.from(newPages.keys())[0] : null)
        : prev.activePagePath;
      return {
        ...prev,
        openPages: newPages,
        activePagePath: newActivePath,
      };
    });
  }, []);

  const closeAllPages = useCallback(() => {
    setState(prev => ({
      ...prev,
      openPages: new Map(),
      activePagePath: null,
    }));
  }, []);

  const setActivePagePath = useCallback((path: string | null) => {
    setState(prev => ({ ...prev, activePagePath: path }));
  }, []);

  const updatePageContent = useCallback((path: string, content: string) => {
    setState(prev => {
      const newPages = new Map(prev.openPages);
      const page = newPages.get(path);
      if (page) {
        newPages.set(path, {
          ...page,
          content,
          isDirty: content !== page.originalContent,
        });
      }
      return { ...prev, openPages: newPages };
    });
  }, []);

  const markPageSaved = useCallback((path: string) => {
    setState(prev => {
      const newPages = new Map(prev.openPages);
      const page = newPages.get(path);
      if (page) {
        newPages.set(path, {
          ...page,
          originalContent: page.content,
          isDirty: false,
          lastSaved: new Date(),
        });
      }
      return { ...prev, openPages: newPages };
    });
  }, []);

  const getActivePage = useCallback(() => {
    if (!state.activePagePath) return null;
    return state.openPages.get(state.activePagePath) || null;
  }, [state.activePagePath, state.openPages]);

  const getDirtyPages = useCallback(() => {
    return Array.from(state.openPages.values()).filter(page => page.isDirty);
  }, [state.openPages]);

  const hasUnsavedChanges = useCallback((path: string) => {
    const page = state.openPages.get(path);
    return page?.isDirty || false;
  }, [state.openPages]);

  const setSidebarMode = useCallback((mode: 'view' | 'edit') => {
    setState(prev => ({ ...prev, sidebarMode: mode }));
  }, []);

  return (
    <EditorContext.Provider
      value={{
        state,
        openPage,
        closePage,
        closeAllPages,
        setActivePagePath,
        updatePageContent,
        markPageSaved,
        getActivePage,
        getDirtyPages,
        setSidebarMode,
        hasUnsavedChanges,
      }}
    >
      {children}
    </EditorContext.Provider>
  );
}

export function useEditor() {
  const context = useContext(EditorContext);
  if (!context) {
    throw new Error('useEditor must be used within EditorProvider');
  }
  return context;
}
