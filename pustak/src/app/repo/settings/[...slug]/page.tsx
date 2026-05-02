"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import DocPersonaSelector from "@/components/DocPersonaSelector";
import TrackedBranchSelector from "@/components/TrackedBranchSelector";
import {
  ArrowLeft,
  Settings,
  Loader2,
  Sparkles,
  ShieldCheck,
  HelpCircle,
} from "lucide-react";
import Link from "next/link";

interface SettingsPageProps {
  params: Promise<{
    slug: string[];
  }>;
}

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function RepositorySettingsPage({ params }: SettingsPageProps) {
  const router = useRouter();
  const [repoName, setRepoName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [userToken, setUserToken] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      try {
        const resolvedParams = await params;
        const slug = resolvedParams.slug;

        console.log("🔍 Settings page received slug:", slug);

        // Extract repo name from slug
        const repoPath = slug.join("/");
        console.log("🔍 Constructed repo path:", repoPath);

        if (!isMounted) return;

        setRepoName(repoPath);

        // Get user token from localStorage
        const token = localStorage.getItem("DocIt_access_token");
        if (token) {
          setUserToken(token);
        }

        setLoading(false);
      } catch (error) {
        console.error("Error loading settings page:", error);
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPage();

    return () => {
      isMounted = false;
    };
  }, [params]);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
        <div className="absolute inset-0">
          <div
            className="absolute left-[-12%] top-[10%] h-[420px] w-[420px] rounded-full bg-blue-600/35 blur-[180px]"
            aria-hidden
          />
          <div
            className="absolute right-[-8%] top-[35%] h-[360px] w-[360px] rounded-full bg-purple-500/30 blur-[180px]"
            aria-hidden
          />
          <div
            className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-blue-500/15 via-transparent to-transparent"
            aria-hidden
          />
          <div
            className="absolute inset-x-0 bottom-[-30%] h-[420px] bg-gradient-to-t from-slate-950 via-slate-900/40 to-transparent"
            aria-hidden
          />
        </div>

        <div className="relative mx-auto flex max-w-6xl flex-col gap-10 px-6 py-14">
          {/* Header */}
          <div className="space-y-6">
            <Link
              href={`/dashboard`}
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-300 transition hover:text-blue-200"
            >
              <ArrowLeft className="h-4 w-4" /> Back to dashboard
            </Link>

            <div className="rounded-3xl border border-slate-900/60 bg-slate-900/70 p-8 shadow-lg shadow-blue-950/40">
              <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                <div className="flex items-start gap-4">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-500/50 bg-blue-500/10 text-blue-200">
                    <Settings className="h-6 w-6" />
                  </span>
                  <div>
                    <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-slate-950/60 px-3 py-1 text-[11px] uppercase tracking-[0.32em] text-slate-400">
                      Repository settings
                    </div>
                    <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">
                      {repoName}
                    </h1>
                    <p className="mt-2 text-sm text-slate-400 sm:text-base">
                      Choose personas, tracked branches, and upcoming controls
                      to keep docbooks aligned with your release flow.
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800/60 bg-slate-950/60 px-4 py-3 text-left text-sm text-slate-400">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Sparkles className="h-4 w-4 text-blue-300" /> Tips
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Persona controls influence AI tone, and tracked branches
                    steer your staging cadence.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Settings Grid */}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            {/* Main Content */}
            <div className="space-y-8">
              <div className="rounded-3xl border border-slate-900/60 bg-slate-900/70 p-6 shadow-lg shadow-blue-950/30">
                <DocPersonaSelector
                  repoId={repoName}
                  backendUrl={BACKEND_URL}
                  userToken={userToken}
                  onSave={(persona) => {
                    console.log(`✅ Saved doc_persona: ${persona}`);
                  }}
                />
              </div>

              <div className="rounded-3xl border border-slate-900/60 bg-slate-900/70 p-6 shadow-lg shadow-blue-950/30">
                <TrackedBranchSelector
                  repoId={repoName}
                  backendUrl={BACKEND_URL}
                  userToken={userToken}
                  onSave={(branch) => {
                    console.log(`✅ Saved tracked_branch: ${branch}`);
                  }}
                />
              </div>

              <div className="rounded-3xl border border-dashed border-slate-800/80 bg-slate-950/50 p-6 text-sm text-slate-400">
                <h3 className="text-lg font-semibold text-slate-100">
                  More controls coming soon
                </h3>
                <p className="mt-2">
                  We're building automation toggles for publishing cadence,
                  review routing, and docbook labeling. Stay tuned!
                </p>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              <div className="rounded-3xl border border-blue-500/20 bg-blue-500/10 p-6 text-sm text-blue-100">
                <div className="flex items-center gap-2 text-blue-200">
                  <ShieldCheck className="h-5 w-5" /> Persona quickstart
                </div>
                <div className="mt-4 space-y-4">
                  <div>
                    <p className="text-sm font-semibold text-blue-100">
                      Internal
                    </p>
                    <p className="mt-1 text-xs text-blue-200/80">
                      Deep dive for staff engineers—architecture, implementation
                      detail, and workflow nuance.
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-blue-100">
                      Developer
                    </p>
                    <p className="mt-1 text-xs text-blue-200/80">
                      External-friendly docs highlighting APIs, usage stories,
                      and integration paths.
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-900/60 bg-slate-900/70 p-6 text-sm text-slate-400">
                <div className="flex items-center gap-2 text-slate-200">
                  <HelpCircle className="h-5 w-5 text-blue-300" /> Need help?
                </div>
                <p className="mt-3">
                  Personas guide AI phrasing while tracked branches decide which
                  commits feed docbook staging.
                </p>
                <a
                  href="#"
                  className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-300 transition hover:text-blue-200"
                >
                  Learn more
                  <ArrowLeft className="rotate-180 h-3.5 w-3.5" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
