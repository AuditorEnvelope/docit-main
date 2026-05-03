"use client";

import { useState, useEffect, memo } from "react";
import { useTheme } from "next-themes";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Search,
  Sun,
  Moon,
  Menu,
  X,
  Github,
  GitBranch,
  Clock,
  FileText,
  Building2,
  Code,
  History,
  User,
  LogOut,
  Settings,
  Crown,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
} from "lucide-react";
import { EnhancedSidebar as EnhancedSidebarComponent } from "./EnhancedSidebar";

// Memoize sidebar to prevent re-mounts on parent re-renders
const EnhancedSidebar = memo(EnhancedSidebarComponent);
import { GlobalSearch } from "./GlobalSearch";
import { useAuth } from "@/contexts/AuthContext";
import { startGitHubOAuth } from "@/lib/githubOAuth";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarPinned, setSidebarPinned] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { theme, setTheme } = useTheme();
  const { user, logout, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [githubAuthLoading, setGithubAuthLoading] = useState(false);

  const sidebarHiddenExact = new Set(["/", "/settings", "/pricing", "/login"]);
  const sidebarHiddenPrefixes = [
    "/pending-reviews",
    "/repo/settings",
    "/auth/",
  ];
  const currentPath = pathname ?? "";
  const isAuthRoute = currentPath.startsWith("/auth/");
  const hideNavigation =
    sidebarHiddenExact.has(currentPath) ||
    sidebarHiddenPrefixes.some((prefix) => currentPath.startsWith(prefix));

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const isLanding = currentPath === "/" || currentPath === "";
  const isLandingShell = isLanding || isAuthRoute;

  return (
    <div
      className={
        isLandingShell
          ? "min-h-screen bg-[#030712] text-slate-100 transition-colors"
          : "min-h-screen bg-white dark:bg-gray-900 transition-colors"
      }
    >
      {/* Mobile sidebar overlay */}
      {!hideNavigation && sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      {!hideNavigation && (
        <div
          className={`
          fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
          ${sidebarPinned ? "lg:translate-x-0" : "lg:-translate-x-full"}
        `}
        >
          <EnhancedSidebar
            key="sidebar"
            onClose={() => {
              setSidebarOpen(false);
              setSidebarPinned(false);
            }}
          />
        </div>
      )}

      {/* Main content */}
      <div className={!hideNavigation && sidebarPinned ? "lg:pl-64" : ""}>
        {/* Header */}
        <header
          className={
            isLandingShell
              ? "sticky top-0 z-30 border-b border-cyan-500/10 bg-[#030712]/85 backdrop-blur-xl"
              : "sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700"
          }
        >
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
            <div className="flex items-center space-x-4">
              {!hideNavigation && (
                <>
                  <button
                    onClick={() => setSidebarOpen(true)}
                    className="lg:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
                    aria-label="Open sidebar"
                  >
                    <Menu className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => {
                      if (sidebarPinned) {
                        setSidebarPinned(false);
                      } else {
                        setSidebarPinned(true);
                        setSidebarOpen(false);
                      }
                    }}
                    className="hidden lg:inline-flex items-center justify-center rounded-md border border-transparent bg-gray-100/60 px-2 py-1 text-gray-600 transition hover:bg-gray-200/70 dark:bg-gray-800/60 dark:text-gray-300 dark:hover:bg-gray-700/60"
                    aria-label={
                      sidebarPinned ? "Collapse sidebar" : "Expand sidebar"
                    }
                  >
                    {sidebarPinned ? (
                      <PanelLeftClose className="h-4 w-4" />
                    ) : (
                      <PanelLeftOpen className="h-4 w-4" />
                    )}
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={() => router.push("/")}
                className={
                  isLandingShell
                    ? "flex items-center gap-2 rounded-lg outline-none ring-offset-2 ring-offset-[#030712] focus-visible:ring-2 focus-visible:ring-cyan-400/50"
                    : "flex items-center gap-2 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-blue-400/50"
                }
              >
                {isLandingShell ? (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/logo.png"
                      alt=""
                      width={40}
                      height={40}
                      className="h-[2.1rem] w-[2.1rem] object-cover sm:h-[2.1rem] sm:w-[2.1rem] -mt-1"
                    />
                    <div className="flex items-center gap-2 sm:gap-2.5">
                      <span className="text-lg font-bold tracking-tight text-white sm:text-[1.35rem]">
                        DocIt
                      </span>
                      <span className="inline-flex shrink-0 items-center rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-100">
                        Beta
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="flex items-center space-x-2">
                    {/* <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" /> */}
                    <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      DocIt
                    </h1>
                    <span className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      Beta
                    </span>
                  </div>
                )}
              </button>
              {isLanding && (
                <nav className="ml-4 hidden items-center gap-6 md:flex">
                  <a
                    href="#features"
                    className="text-sm font-medium text-slate-400 transition hover:text-white"
                  >
                    Features
                  </a>
                  <a
                    href="#how-it-works"
                    className="text-sm font-medium text-slate-400 transition hover:text-white"
                  >
                    How it works
                  </a>
                  <a
                    href="#cta"
                    className="text-sm font-medium text-slate-400 transition hover:text-white"
                  >
                    Get started
                  </a>
                </nav>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {!isAuthRoute && (
                <>
                  {/* Search */}
                  {/* <button
                    onClick={() => setSearchOpen(true)}
                    className={
                      isLanding
                        ? "flex items-center space-x-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 transition hover:border-cyan-400/30 hover:bg-white/10"
                        : "flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    }
                  >
                    <Search className="w-4 h-4" />
                    <span className="hidden sm:inline">Search docs...</span>
                    <kbd className="hidden sm:inline text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">
                      ⌘K
                    </kbd>
                  </button> */}

                  {/* Theme toggle */}
                  {/* <button
                    onClick={() =>
                      setTheme(theme === "dark" ? "light" : "dark")
                    }
                    className={
                      isLanding
                        ? "rounded-full border border-white/10 p-2 text-slate-300 transition hover:border-cyan-400/30 hover:bg-white/10 hover:text-white"
                        : "p-2 rounded-md text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    }
                  >
                    {theme === "dark" ? (
                      <Sun className="w-5 h-5" />
                    ) : (
                      <Moon className="w-5 h-5" />
                    )}
                  </button> */}

                  {/* User Menu */}
                  {isAuthenticated && user ? (
                    <div className="relative">
                      <button
                        onClick={() => setUserMenuOpen(!userMenuOpen)}
                        className="flex items-center space-x-2 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                      >
                        {user.avatar_url ? (
                          <img
                            src={user.avatar_url}
                            alt={user.name || user.username || "User"}
                            className="w-8 h-8 rounded-full border-2 border-blue-500"
                          />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold">
                            {(user.name ||
                              user.username ||
                              "U")[0].toUpperCase()}
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
                          <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50">
                            {/* User Info */}
                            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                              <p className="font-semibold text-gray-900 dark:text-white">
                                {user.name || user.username}
                              </p>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {user.email || `@${user.username}`}
                              </p>
                              <div className="mt-2">
                                <span
                                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${
                                    user.plan === "free"
                                      ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                                      : user.plan === "pro"
                                        ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                                        : user.plan === "team"
                                          ? "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
                                          : "bg-gradient-to-r from-yellow-400 to-orange-500 text-white"
                                  }`}
                                >
                                  {user.plan !== "free" && (
                                    <Crown className="w-3 h-3" />
                                  )}
                                  {user.plan.toUpperCase()}
                                </span>
                              </div>
                            </div>

                            {/* Menu Items */}
                            <div className="py-2">
                              <button
                                onClick={() => {
                                  setUserMenuOpen(false);
                                  router.push("/dashboard");
                                }}
                                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                              >
                                <User className="w-4 h-4" />
                                Dashboard
                              </button>
                              <button
                                onClick={() => {
                                  setUserMenuOpen(false);
                                  router.push("/pricing");
                                }}
                                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                              >
                                <Crown className="w-4 h-4" />
                                Upgrade Plan
                              </button>
                              <button
                                onClick={() => {
                                  setUserMenuOpen(false);
                                  router.push("/settings");
                                }}
                                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                              >
                                <Settings className="w-4 h-4" />
                                Settings
                              </button>
                            </div>

                            {/* Logout */}
                            <div className="border-t border-gray-200 dark:border-gray-700 py-2">
                              <button
                                onClick={() => {
                                  setUserMenuOpen(false);
                                  logout();
                                }}
                                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
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
                      type="button"
                      disabled={githubAuthLoading}
                      onClick={async () => {
                        setGithubAuthLoading(true);
                        try {
                          await startGitHubOAuth();
                        } catch (e) {
                          console.error(e);
                          setGithubAuthLoading(false);
                          alert("Failed to start GitHub sign-in. Please try again.");
                        }
                      }}
                      className={
                        isLanding
                          ? "inline-flex cursor-pointer items-center justify-center gap-2 rounded-full border border-white/20 px-4 py-2 text-sm font-semibold text-white transition hover:border-cyan-400/50 hover:bg-cyan-400/10 disabled:cursor-not-allowed disabled:opacity-60"
                          : "inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                      }
                    >
                      {githubAuthLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="hidden sm:inline">Connecting…</span>
                        </>
                      ) : isLanding ? (
                        "Sign in"
                      ) : (
                        "Login"
                      )}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </header>

        {/* Main content area */}
        <main className="flex-1">{children}</main>
      </div>

      {/* Global Search */}
      <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Keyboard shortcuts */}
      <div className="hidden">
        <kbd>⌘K</kbd> - Search
        <kbd>⌘/</kbd> - Toggle sidebar
        <kbd>⌘D</kbd> - Toggle theme
      </div>
    </div>
  );
}
