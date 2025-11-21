"use client";

import { Layout } from "@/components/Layout";
import { useState, useEffect } from "react";
import {
  BookOpen,
  GitBranch,
  Clock,
  FileText,
  Building2,
  Code,
  History,
  TrendingUp,
  Users,
  Zap,
  Search,
  Sparkles,
  ShieldCheck,
  Globe2,
} from "lucide-react";

export default function HomePage() {
  const [stats, setStats] = useState({
    repositories: 0,
    documents: 0,
    updates: 0,
    lastUpdate: "Loading...",
  });
  const [loading, setLoading] = useState(true);

  const heroHighlights = [
    {
      icon: Sparkles,
      title: "AI doc orchestration",
      description:
        "Let Pustak draft architecture, workflow, and changelog docs in minutes.",
    },
    {
      icon: Globe2,
      title: "Multi-org aware",
      description: "Seamlessly route staging updates across every org you manage.",
    },
    {
      icon: ShieldCheck,
      title: "Transparent & secure",
      description:
        "Ship docs with your GitHub identity—tokens stay scoped and auditable.",
    },
  ];

  const capabilityTiles = [
    {
      icon: Zap,
      title: "AI-Powered",
      description:
        "Generate release-ready documentation from code changes with contextual AI.",
      accent: "from-blue-500/20 via-blue-500/10 to-transparent",
    },
    {
      icon: TrendingUp,
      title: "Always Updated",
      description:
        "Keep staging docbooks in lockstep with commits—no more stale Confluence pages.",
      accent: "from-emerald-500/25 via-emerald-500/10 to-transparent",
    },
    {
      icon: Users,
      title: "Team Ready",
      description:
        "Review, approve, and publish docs together with built-in workflows.",
      accent: "from-purple-500/25 via-purple-500/10 to-transparent",
    },
  ];

  const welcomeTiles = [
    {
      title: "🚀 AI-Powered",
      description:
        "Automatically generates documentation from your code changes using advanced AI.",
      bg: "bg-blue-500/10",
    },
    {
      title: "🔄 Real-time Updates",
      description:
        "Automatic synchronization with repository changes keeps staging branches fresh.",
      bg: "bg-emerald-500/10",
    },
    {
      title: "📚 Multi-Repository",
      description:
        "Organize documentation across multiple repositories with automatic discovery.",
      bg: "bg-purple-500/10",
    },
    {
      title: "🎨 Beautiful Interface",
      description:
        "Enjoy a GitBook-inspired reading experience with dark mode and smooth transitions.",
      bg: "bg-amber-500/10",
    },
  ];

  useEffect(() => {
    async function loadStats() {
      try {
        // Get JWT token from localStorage
        const userToken = localStorage.getItem('pustak_access_token');
        
        if (!userToken) {
          console.log('No user token available - skipping stats');
          setLoading(false);
          return;
        }

        const response = await fetch('/api/repositories', {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch repositories');
        }
        const repos = await response.json();
        const repoCount = repos.length;
        
        // Calculate total documents (6 doc types per repo)
        const docCount = repoCount * 6;
        
        // Get the most recent update time
        const mostRecent = repos.reduce((latest: Date, repo: any) => {
          const repoDate = new Date(repo.lastUpdated);
          return repoDate > latest ? repoDate : latest;
        }, new Date(0));
        
        const now = new Date();
        const diffMs = now.getTime() - mostRecent.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);
        
        let lastUpdateStr = "Just now";
        if (diffDays > 0) {
          lastUpdateStr = `${diffDays}d ago`;
        } else if (diffHours > 0) {
          lastUpdateStr = `${diffHours}h ago`;
        }
        
        setStats({
          repositories: repoCount,
          documents: docCount,
          updates: repoCount * 8, // Approximate updates
          lastUpdate: lastUpdateStr,
        });
        setLoading(false);
      } catch (error) {
        console.error("Failed to load stats:", error);
        setLoading(false);
      }
    }
    
    loadStats();
  }, []);

  return (
    <Layout>
      <div className="min-h-screen bg-slate-950 text-slate-100">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-20">
          <div className="absolute left-1/2 top-[-20%] h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-blue-600/40 blur-[180px]" aria-hidden />
          <div className="absolute right-[8%] top-[10%] h-40 w-40 rounded-full bg-emerald-400/30 blur-3xl animate-pulse" aria-hidden />
          <div className="absolute left-[10%] bottom-[12%] h-36 w-36 rounded-full bg-purple-500/30 blur-3xl animate-pulse" aria-hidden />

          <div className="relative mx-auto flex max-w-6xl flex-col gap-16 px-6">
            <div className="text-center">
              <div className="mx-auto flex w-fit items-center gap-3 rounded-full border border-blue-500/40 bg-blue-500/10 px-5 py-2 text-sm font-semibold uppercase tracking-[0.28em] text-blue-200">
                <BookOpen className="h-5 w-5" /> Pustak
              </div>
              <h1 className="mt-6 text-4xl font-semibold leading-snug sm:text-5xl">
                Ship documentation with the same velocity as your code.
              </h1>
              <p className="mt-4 text-base text-slate-300 sm:text-lg">
                Pustak turns GitHub activity into beautiful docbooks—architecture, workflows, and changelogs stay review-ready without manual toil.
              </p>

              {/* Highlights */}
              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {heroHighlights.map((highlight) => {
                  const HighlightIcon = highlight.icon;
                  return (
                    <div
                      key={highlight.title}
                      className="group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-900/60 p-4 transition hover:border-blue-400/50 hover:bg-slate-900/80"
                    >
                      <div className="absolute inset-0 translate-y-10 bg-gradient-to-br from-blue-500/20 via-transparent to-transparent opacity-0 transition duration-500 group-hover:translate-y-0 group-hover:opacity-100" aria-hidden />
                      <div className="relative flex items-start gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-500/10 text-blue-200">
                          <HighlightIcon className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-100">{highlight.title}</p>
                          <p className="mt-1 text-xs text-slate-400">{highlight.description}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Command Bar */}
              <div className="mx-auto mt-12 max-w-xl">
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const event = new KeyboardEvent("keydown", {
                      key: "k",
                      metaKey: true,
                      bubbles: true,
                      cancelable: true,
                    });
                    document.dispatchEvent(event);
                  }}
                  className="group flex w-full items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-900/70 px-5 py-4 text-left text-sm transition hover:border-blue-500/60 hover:bg-slate-900/90"
                >
                  <Search className="h-5 w-5 text-slate-500 transition group-hover:text-blue-400" />
                  <span className="flex-1 text-slate-400 transition group-hover:text-slate-200">Search documentation…</span>
                  <kbd className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-400">⌘K</kbd>
                </button>
              </div>
            </div>

          </div>
        </section>

        {/* Capability Section */}
        <section className="border-t border-slate-900/60 bg-slate-950/95 py-20">
          <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6">
            <div className="flex flex-col gap-4 text-center">
              <span className="text-xs uppercase tracking-[0.32em] text-slate-500">Why teams choose Pustak</span>
              <h2 className="text-3xl font-semibold text-slate-100 sm:text-4xl">Everything you expect from modern documentation</h2>
              <p className="text-sm text-slate-400 sm:text-base">
                Automate docbook pipelines from webhook to review. Purpose-built for product squads that ship continuously.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {capabilityTiles.map((tile) => {
                const CapabilityIcon = tile.icon;
                return (
                  <div
                    key={tile.title}
                    className="group relative overflow-hidden rounded-3xl border border-slate-900/60 bg-slate-900/70 p-6 transition duration-300 hover:-translate-y-1 hover:border-blue-500/50 hover:bg-slate-900/85"
                  >
                    <div className={`absolute inset-0 bg-gradient-to-br ${tile.accent} via-transparent to-transparent opacity-0 transition duration-500 group-hover:opacity-90`} aria-hidden />
                    <div className="relative flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950/80 text-blue-100">
                        <CapabilityIcon className="h-6 w-6" />
                      </div>
                      <h3 className="text-lg font-semibold text-slate-100">{tile.title}</h3>
                    </div>
                    <p className="relative mt-3 text-sm text-slate-300">{tile.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Welcome Section */}
        <section className="border-t border-slate-900/60 bg-slate-950 py-20">
          <div className="mx-auto max-w-5xl px-6">
            <div className="rounded-3xl border border-slate-900/60 bg-slate-900/75 p-10 shadow-inner shadow-blue-950/40">
              <div className="flex flex-col gap-4 text-center sm:text-left">
                <span className="text-xs uppercase tracking-[0.32em] text-blue-300">Welcome aboard</span>
                <h2 className="text-3xl font-semibold text-slate-100 sm:text-4xl">Your docbook co-pilot</h2>
                <p className="text-sm text-slate-400 sm:text-base">
                  Pustak (पुस्तक) connects to your GitHub workflow, drafts documentation automatically, and keeps every stakeholder in sync.
                </p>
              </div>

              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {welcomeTiles.map((tile) => (
                  <div
                    key={tile.title}
                    className={`rounded-2xl border border-slate-800/70 ${tile.bg} p-5 text-left transition hover:border-blue-400/40`}
                  >
                    <h3 className="text-base font-semibold text-slate-100">{tile.title}</h3>
                    <p className="mt-2 text-sm text-slate-300">{tile.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
