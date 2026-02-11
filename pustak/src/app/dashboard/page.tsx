"use client";

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { GenerateDocsButton } from "@/components/GenerateDocsButton";
import { PublishToLiveButton } from "@/components/PublishToLiveButton";
import PendingReviewsTab from "@/components/PendingReviewsTab";
import { UsageStatsCard } from "@/components/UsageStatsCard";
import { useAuth } from "@/contexts/AuthContext";
import {
  useDashboardData,
  PLAN_CONFIG,
  PlanName,
} from "@/hooks/useDashboardData";
import {
  OnboardingSplash,
  ONBOARDING_PROGRESS_MESSAGES,
} from "@/components/OnboardingSplash";
import { mapDocsRouteToRepoSlug } from "@/lib/docsPathMapper";
import apiClient from "@/lib/apiClient";
import {
  BookOpen,
  Calendar,
  FileText,
  GitBranch,
  Github,
  Loader2,
  LogOut,
  Settings,
  Sparkles,
  X,
} from "lucide-react";

// Onboarding Guard component that checks if all required components are set up
function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, loading: authLoading, token } = useAuth();
  const [checkingOnboarding, setCheckingOnboarding] = useState(true);
  const [progressIndex, setProgressIndex] = useState(0);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  // Track organization and installation status
  const [orgs, setOrgs] = useState<string[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [orgSummaries, setOrgSummaries] = useState<
    Record<
      string,
      {
        org: string;
        reader_app_installed?: boolean;
        writer_app_installed?: boolean;
        docbook_repo?: string;
        writer_app_has_access?: boolean;
      }
    >
  >({});

  // Polling for writer app installation
  const writerPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const writerPollAttempts = useRef(0);
  const MAX_WRITER_POLL_ATTEMPTS = 12; // roughly 1 minute at 5s interval
  const [pollingWriterApp, setPollingWriterApp] = useState(false);

  // Progress message animation
  useEffect(() => {
    if (!checkingOnboarding) return;

    const interval = setInterval(() => {
      setProgressIndex(
        (prev) => (prev + 1) % ONBOARDING_PROGRESS_MESSAGES.length
      );
    }, 1800);

    return () => clearInterval(interval);
  }, [checkingOnboarding]);

  // Stop writer app polling
  const stopWriterPolling = useCallback(() => {
    if (writerPollRef.current) {
      clearInterval(writerPollRef.current);
      writerPollRef.current = null;
    }
    writerPollAttempts.current = 0;
    setPollingWriterApp(false);
  }, []);

  // Load onboarding state
  const loadOnboardingState = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!token) return;

      try {
        if (!options?.silent) {
          setCheckingOnboarding(true);
        }

        // 1. Fetch organizations
        const orgsRes = await apiClient.get<{
          organizations?: any[];
        }>("/user/organizations");

        const orgIds: string[] = (orgsRes.data.organizations || [])
          .map((org: any) =>
            typeof org === "string"
              ? org
              : org?.login || org?.org || org?.name || ""
          )
          .filter(Boolean);

        setOrgs(orgIds);

        // If no orgs, we can't continue onboarding
        if (orgIds.length === 0) {
          setOnboardingComplete(false);
          if (!options?.silent) setCheckingOnboarding(false);
          return;
        }

        // Select first org if none selected
        const primaryOrg = orgIds[0] || "";
        setSelectedOrg((prev) => prev || primaryOrg);

        // 2. Check each organization's setup status
        const summaries: Record<
          string,
          {
            org: string;
            reader_app_installed?: boolean;
            writer_app_installed?: boolean;
            docbook_repo?: string;
            writer_app_has_access?: boolean;
          }
        > = {};
        await Promise.all(
          orgIds.map(async (orgId) => {
            const summary: {
              org: string;
              reader_app_installed?: boolean;
              writer_app_installed?: boolean;
              docbook_repo?: string;
              writer_app_has_access?: boolean;
            } = { org: orgId };

            try {
              // 2.1 Check GitHub Apps installation
              const appsRes = await apiClient.get<{
                reader_app?: { installed?: boolean };
                writer_app?: { installed?: boolean };
              }>(`/org/${orgId}/verify-apps`);

              const appData = appsRes.data;
              summary.reader_app_installed =
                appData?.reader_app?.installed ?? false;
              summary.writer_app_installed =
                appData?.writer_app?.installed ?? false;
            } catch (error) {
              console.error(`Failed to load app status for ${orgId}`, error);
            }

            try {
              // 2.2 Check docbook repository
              const docbookRes = await apiClient.get<{
                exists: boolean;
                docbook_repo?: string;
              }>("/docbook/check-exists", {
                params: { org_id: orgId },
              });

              const docbookData = docbookRes.data;
              if (docbookData.exists) {
                summary.docbook_repo = docbookData.docbook_repo;
              }
            } catch (error) {
              console.error(
                `Failed to load docbook status for ${orgId}`,
                error
              );
            }

            try {
              // 2.3 Check writer app access to docbook repo
              if (summary.docbook_repo) {
                const accessRes = await apiClient.get<{
                  has_access?: boolean;
                }>(`/org/${orgId}/verify-writer-app-access`, {
                  params: {
                    repo: summary.docbook_repo,
                  },
                });

                const accessData = accessRes.data;
                summary.writer_app_has_access = accessData?.has_access ?? false;
              }
            } catch (error) {
              console.error(`Failed to load writer access for ${orgId}`, error);
            }

            summaries[orgId] = summary;
          })
        );

        setOrgSummaries(summaries);

        // 3. Check if primary org has all requirements met
        const primaryOrgSummary = summaries[primaryOrg];
        const hasReaderApp = primaryOrgSummary?.reader_app_installed === true;
        const hasDocbookRepo = !!primaryOrgSummary?.docbook_repo;
        const hasWriterAppAccess =
          primaryOrgSummary?.writer_app_has_access === true;

        const isComplete = hasReaderApp && hasDocbookRepo && hasWriterAppAccess;

        console.log("🔍 Onboarding check results:", {
          org: primaryOrg,
          hasReaderApp,
          hasDocbookRepo,
          hasWriterAppAccess,
          isComplete,
          docbookRepo: primaryOrgSummary?.docbook_repo,
        });

        setOnboardingComplete(isComplete);
      } catch (error) {
        console.error("Error checking onboarding status:", error);
        setOnboardingComplete(false);
      } finally {
        if (!options?.silent) {
          setCheckingOnboarding(false);
        }
      }
    },
    [token]
  );

  // Initial check when component mounts
  useEffect(() => {
    if (user?.is_onboarding_complete) {
      // If user object already has onboarding complete flag, skip checks
      setOnboardingComplete(true);
      setCheckingOnboarding(false);
      return;
    }

    if (token) {
      loadOnboardingState();
    }
  }, [token, user, loadOnboardingState]);

  // Redirect to onboarding if checks fail
  useEffect(() => {
    if (!authLoading && !checkingOnboarding && !onboardingComplete) {
      console.log("🔎 Onboarding incomplete, redirecting to /onboarding", {
        authLoading,
        checkingOnboarding,
        onboardingComplete,
        user: user?.id,
      });
      router.replace("/onboarding");
    }
  }, [authLoading, checkingOnboarding, onboardingComplete, router, user?.id]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopWriterPolling();
    };
  }, [stopWriterPolling]);

  if (authLoading || checkingOnboarding) {
    return (
      <Layout>
        <OnboardingSplash
          messages={ONBOARDING_PROGRESS_MESSAGES}
          activeIndex={progressIndex}
        />
      </Layout>
    );
  }

  if (!onboardingComplete) {
    return null; // Will redirect to onboarding
  }

  console.log("✅ Onboarding complete, showing dashboard");
  return <>{children}</>;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout, isAuthenticated } = useAuth();

  const {
    repositories,
    loadingRepos,
    repoSearchQuery,
    setRepoSearchQuery,
    connectedOrgs,
    loadingOrgs,
    selectedOrg,
    setSelectedOrg,
    errorMessage,
    docbookRepo,
    pendingReviewsDisabled,
    pendingReviewsLoading,
    pendingReviewsError,
    pendingReviewsCount,
    pendingReviewStatusMessage,
    reloadPendingReviews,
    documentedCount,
    loadRepositories,
    actualPlan,
  } = useDashboardData();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  const filteredRepositories = useMemo(() => {
    const query = repoSearchQuery.trim().toLowerCase();
    if (!query) {
      return repositories;
    }

    return repositories.filter((repo) => {
      const fullName = (repo.full_name || repo.name || "").toLowerCase();
      const description = (repo.description || "").toLowerCase();
      return fullName.includes(query) || description.includes(query);
    });
  }, [repoSearchQuery, repositories]);

  const reviewButtonDisabled = pendingReviewsDisabled || !!pendingReviewsError;

  const formatPersona = (persona?: string | null) => {
    if (!persona) return "internal";
    return persona
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  const formatDateTime = (value?: string | null) => {
    if (!value) return "Never";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  if (!user) {
    return null;
  }

  const currentPlanKey = (actualPlan || user.plan) as PlanName;
  const planLabel =
    PLAN_CONFIG[currentPlanKey]?.label ??
    (actualPlan || user.plan || "").toUpperCase();

  return (
    <OnboardingGuard>
      <Layout>
        <div className="min-h-screen bg-slate-950">
          <div className="container mx-auto px-4 py-12 space-y-10">
            <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80 px-8 py-10 shadow-[0_35px_80px_-45px_rgba(59,130,246,0.6)]">
              <div
                className="absolute inset-0 -translate-x-1/3 translate-y-1/4 scale-125 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.35),_transparent_55%)] blur-3xl opacity-70"
                aria-hidden
              />
              <div
                className="absolute inset-0 translate-x-1/3 -translate-y-1/4 scale-125 bg-[radial-gradient(circle_at_bottom_right,_rgba(124,58,237,0.35),_transparent_55%)] blur-3xl opacity-70"
                aria-hidden
              />
              <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
                  <div className="relative shrink-0">
                    {user.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.name || user.username || "User avatar"}
                        className="h-24 w-24 rounded-2xl border-2 border-white/10 object-cover shadow-xl"
                      />
                    ) : (
                      <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 text-3xl font-bold text-white shadow-xl">
                        {(user.name || user.username || "U")[0].toUpperCase()}
                      </div>
                    )}
                    <div className="absolute -bottom-2 -right-2 rounded-full bg-emerald-500 px-2 py-1 text-xs font-semibold text-white shadow-lg">
                      Active
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                        {user.name || user.username || "User"}
                      </h1>
                      <p className="text-sm text-slate-300">
                        {user.email || "No email provided"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/15 px-3 py-1 text-xs font-semibold text-blue-200">
                        <Settings className="h-3 w-3" />
                        {planLabel}
                      </span>
                      {user.username && (
                        <a
                          href={`https://github.com/${user.username}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs font-semibold text-slate-100 hover:border-blue-400 hover:text-white transition"
                        >
                          <Github className="h-3 w-3" />@{user.username}
                        </a>
                      )}
                    </div>
                    <p className="max-w-xl text-sm text-slate-300">
                      Welcome back! Track repository coverage, monitor pending
                      doc reviews, and jump straight into actions tailored to
                      your organization.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
                  <button
                    onClick={() => router.push("/settings")}
                    className="group inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/20 px-5 py-2 text-sm font-semibold text-blue-100 transition hover:bg-blue-500/30"
                  >
                    <Settings className="h-4 w-4" />
                    Workspace settings
                  </button>
                  <button
                    onClick={logout}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-5 py-2 text-sm font-semibold text-slate-100 transition hover:border-rose-400 hover:text-rose-200"
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                </div>
              </div>
            </section>

            {/* ================================================================
             PHASE 5: Usage & Limits Card - TOP PLACEMENT
             ================================================================
             Positioned prominently at the top to give users immediate
             visibility into their usage, limits, and billing cycle.
             ================================================================ */}
            <section className="relative">
              <UsageStatsCard
                onUpgradeClick={() => router.push("/pricing")}
                className="shadow-[0_35px_80px_-45px_rgba(147,51,234,0.6)]"
              />
            </section>

            <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="group relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg transition hover:border-blue-400/60">
                <div
                  className="pointer-events-none absolute inset-0 bg-gradient-to-br from-blue-500/15 via-transparent to-transparent opacity-0 transition group-hover:opacity-100"
                  aria-hidden
                />
                <div className="relative space-y-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
                      <BookOpen className="h-4 w-4" />
                    </div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-400">
                      Repositories
                    </h3>
                  </div>
                  <p className="text-3xl font-semibold text-white">
                    {loadingRepos ? (
                      <Loader2 className="h-6 w-6 animate-spin text-blue-300" />
                    ) : (
                      repositories.length
                    )}
                  </p>
                  <p className="text-sm text-slate-400">
                    Connected via Reader App
                  </p>
                </div>
              </div>

              <div className="group relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-lg transition hover:border-emerald-400/60">
                <div
                  className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-500/15 via-transparent to-transparent opacity-0 transition group-hover:opacity-100"
                  aria-hidden
                />
                <div className="relative space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-300">
                      <FileText className="h-4 w-4" />
                    </div>
                    <h3 className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-400">
                      Documented
                    </h3>
                  </div>
                  <p className="text-3xl font-semibold text-white">
                    {documentedCount}
                  </p>
                  <p className="text-xs text-slate-400">
                    Repositories with generated docs
                  </p>
                </div>
              </div>

              <div className="group relative overflow-hidden rounded-xl border border-purple-500/40 bg-gradient-to-br from-purple-900/70 via-slate-900/70 to-indigo-900/60 p-4 shadow-[0_35px_80px_-55px_rgba(109,40,217,0.75)]">
                <div className="relative space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/30 text-purple-100">
                        <Calendar className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="text-[10px] font-semibold uppercase tracking-[0.3em] text-purple-200">
                          Pending reviews
                        </h3>
                        <p className="text-[9px] text-purple-200/70">
                          Stay on top of docbook approvals
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        if (!reviewButtonDisabled) {
                          router.push("/pending-reviews");
                        }
                      }}
                      className={`inline-flex items-center gap-1.5 rounded-full border border-purple-400/50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest transition ${
                        reviewButtonDisabled
                          ? "cursor-not-allowed bg-purple-500/10 text-purple-200/60"
                          : "bg-purple-500/20 text-purple-50 hover:bg-purple-500/30"
                      }`}
                    >
                      <Sparkles className="h-2.5 w-2.5" />
                      Review docs
                    </button>
                  </div>

                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-semibold text-purple-100">
                      {pendingReviewsDisabled ? (
                        "—"
                      ) : pendingReviewsLoading ? (
                        <Loader2 className="h-6 w-6 animate-spin text-purple-200" />
                      ) : (
                        pendingReviewsCount
                      )}
                    </span>
                    {!pendingReviewsDisabled && !pendingReviewsLoading && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                          pendingReviewsCount === 0
                            ? "bg-emerald-400/20 text-emerald-200"
                            : "bg-purple-400/20 text-purple-100"
                        }`}
                      >
                        {pendingReviewsCount === 0
                          ? "All clear"
                          : `${pendingReviewsCount} waiting`}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-purple-100/80">
                    {pendingReviewStatusMessage}
                  </p>

                  {pendingReviewsError && (
                    <div className="flex items-center justify-between gap-3 text-[10px] text-rose-200">
                      <span>{pendingReviewsError}</span>
                      <button
                        type="button"
                        onClick={reloadPendingReviews}
                        className="font-semibold text-purple-100 hover:underline"
                      >
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/*
          <section className="rounded-3xl border border-purple-500/30 bg-gradient-to-br from-purple-950/70 via-slate-950/70 to-slate-950/50 shadow-[0_40px_90px_-60px_rgba(109,40,217,0.65)] px-8 py-8 space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full bg-purple-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-purple-200">
                  <Sparkles className="w-3 h-3" />
                  Documentation Review Queue
                </div>
                <h2 className="mt-3 text-2xl font-semibold text-white">
                  Pending approvals for {selectedOrg || "your organizations"}
                </h2>
                <p className="text-sm text-slate-300 max-w-2xl">
                  Review the generated documentation diff, approve merges, and
                  keep your docbook main branch up to date.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setShowReviewPanel(false)}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-700/60 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-slate-300 hover:bg-slate-900/60 transition"
                >
                  <X className="w-3 h-3" />
                  Hide panel
                </button>
              </div>
            </div>

            {!selectedOrg ? (
              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-6 py-8 text-center text-slate-300">
                Connect an organization to view documentation reviews.
              </div>
            ) : !token ? (
              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-6 py-8 text-center text-slate-300">
                Sign in again to refresh your session before reviewing
                documentation.
              </div>
            ) : (
              <PendingReviewsTab
                orgId={selectedOrg}
                token={token}
                backendUrl={reviewApiBase}
                onReload={reloadPendingReviews}
                reviewsOverride={pendingReviews}
                isLoadingOverride={pendingReviewsLoading}
                errorOverride={pendingReviewsError}
              />
            )}
          </section>
          */}

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 shadow-[0_25px_60px_-45px_rgba(15,23,42,0.85)]">
              <div className="border-b border-slate-800/80 px-5 py-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/70 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-400">
                    Repository overview
                  </div>
                  <h2 className="mt-2 text-xl font-semibold text-white">
                    {selectedOrg
                      ? `Docs coverage inside ${selectedOrg}`
                      : "Connect an organization to start managing repositories."}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Search, filter, and trigger doc generation directly from
                    these tiles.
                  </p>
                </div>

                <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center lg:w-auto">
                  <div className="relative flex-1 min-w-[200px]">
                    <input
                      type="text"
                      placeholder="Search repositories…"
                      value={repoSearchQuery}
                      onChange={(event) =>
                        setRepoSearchQuery(event.target.value)
                      }
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/80 py-2 pl-9 pr-3 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                      disabled={!repositories.length}
                    />
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-600">
                      <BookOpen className="h-3 w-3" />
                    </span>
                  </div>

                  {connectedOrgs.length > 0 && (
                    <div className="relative">
                      <select
                        value={selectedOrg}
                        onChange={(event) => setSelectedOrg(event.target.value)}
                        className="appearance-none rounded-xl border border-slate-700 bg-slate-900/80 py-2 pl-3 pr-8 text-xs text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500/60"
                      >
                        {connectedOrgs.map((org) => (
                          <option key={org} value={org}>
                            {org}
                          </option>
                        ))}
                      </select>
                      <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-600">
                        <GitBranch className="h-3 w-3" />
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="px-5 py-4">
                {loadingOrgs ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading organizations…</span>
                  </div>
                ) : !connectedOrgs.length ? (
                  <div className="space-y-4 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 px-8 py-12 text-center text-slate-300">
                    <p className="text-lg font-semibold text-white">
                      You haven&apos;t connected any organizations yet.
                    </p>
                    <p className="text-sm text-slate-400 max-w-2xl mx-auto">
                      Launch the onboarding flow to install the GitHub Apps,
                      link your docbook repository, and start documenting your
                      codebase.
                    </p>
                    <button
                      onClick={() => router.push("/onboarding")}
                      className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl"
                    >
                      <Sparkles className="h-4 w-4" />
                      Launch onboarding
                    </button>
                  </div>
                ) : loadingRepos ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Loading repositories…</span>
                  </div>
                ) : errorMessage ? (
                  <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-200">
                    {errorMessage}
                  </div>
                ) : !filteredRepositories.length ? (
                  <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/70 px-6 py-12 text-center text-slate-300">
                    <p className="text-lg font-semibold text-white">
                      No repositories match your search
                    </p>
                    <p className="text-sm text-slate-400">
                      Modify filters or update GitHub permissions to include
                      more repositories.
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                    {filteredRepositories
                      .filter((repo) => {
                        const fullName = (
                          repo.full_name ||
                          repo.name ||
                          ""
                        ).toLowerCase();
                        // Filter out docbook repositories
                        return (
                          !fullName.includes("/pustak-docbook-") &&
                          !fullName.includes("pustak-docbook")
                        );
                      })
                      .map((repo) => {
                        const fullName = repo.full_name || repo.name || "";
                        const displayName =
                          repo.name || fullName.split("/").pop() || fullName;
                        const trackedBranch =
                          repo.tracked_branch ||
                          repo.docbook_tracked_branch ||
                          repo.default_branch ||
                          "main";
                        const pendingReviews = repo.pending_reviews || 0;
                        const hasDocs = Boolean(repo.last_documented_at);
                        const isDocbookRepo = fullName
                          .toLowerCase()
                          .includes("/pustak-docbook-");
                        const docbookNotice =
                          "This is your docbook repository where generated documentation lives. Docs are already stored here.";
                        const repoShortName =
                          fullName.split("/")[1] || displayName;
                        const docsHref = (() => {
                          if (!docbookRepo) {
                            return `/repo/${fullName}`;
                          }

                          const { canonicalSlug } = mapDocsRouteToRepoSlug({
                            org: fullName.split("/")[0] || "",
                            repo: repoShortName,
                            slug: ["introduction"],
                          });

                          const slugPath = canonicalSlug.join("/");
                          return `/docs/${
                            fullName.split("/")[0]
                          }/${repoShortName}/${slugPath}`;
                        })();
                        const viewDocsDisabled = !docbookRepo;

                        // Generate mock activity data for visualization
                        const activityData = Array.from({ length: 14 }, () =>
                          Math.floor(Math.random() * 100)
                        );
                        const maxActivity = Math.max(...activityData, 1);

                        const cardGradient = isDocbookRepo
                          ? "from-blue-500/20 via-slate-900/70 to-slate-900/60"
                          : "from-slate-900/80 via-slate-900/70 to-slate-900/60";

                        return (
                          <div
                            key={fullName}
                            className={`group relative flex min-h-[320px] flex-col overflow-hidden rounded-xl border bg-gradient-to-br shadow-lg transition-all duration-300 ${
                              isDocbookRepo
                                ? "border-blue-500/30 from-blue-950/40 via-slate-900/60 to-slate-900/40 hover:border-blue-500/50 hover:shadow-blue-500/20"
                                : "border-slate-800/60 from-slate-900/70 via-slate-900/60 to-slate-900/50 hover:border-slate-700/70 hover:shadow-slate-700/10"
                            }`}
                          >
                            {/* Ambient glow effects */}
                            <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100">
                              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.15),_transparent_50%)]" />
                              <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_rgba(16,185,129,0.1),_transparent_50%)]" />
                            </div>

                            <div className="relative flex h-full flex-col p-4">
                              {/* Header */}
                              <div className="flex items-start justify-between gap-3 mb-3 pb-3 border-b border-slate-800/50">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h3 className="text-lg font-bold text-white truncate">
                                      {displayName}
                                    </h3>
                                    {hasDocs && (
                                      <div className="flex-shrink-0 flex items-center gap-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                        <span className="text-[9px] text-emerald-400 font-medium">
                                          LIVE
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 truncate">
                                    {fullName}
                                  </p>
                                </div>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <span className="inline-flex items-center gap-1 rounded-full border border-blue-400/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-200">
                                    <GitBranch className="h-2.5 w-2.5" />
                                    {trackedBranch}
                                  </span>
                                  <button
                                    onClick={() => {
                                      const [org, repo] = fullName.split("/");
                                      if (org && repo) {
                                        const hostname =
                                          window.location.hostname;
                                        const isSubdomain =
                                          hostname.split(".").length > 2 &&
                                          !hostname.startsWith("www.") &&
                                          !hostname.startsWith("localhost");

                                        if (isSubdomain) {
                                          const domainParts =
                                            hostname.split(".");
                                          const mainDomain = domainParts
                                            .slice(1)
                                            .join(".");
                                          const protocol =
                                            window.location.protocol;
                                          const settingsUrl = `${protocol}//${mainDomain}/repo/settings/${org}/${repo}`;
                                          window.location.href = settingsUrl;
                                        } else {
                                          router.push(
                                            `/repo/settings/${org}/${repo}`
                                          );
                                        }
                                      }
                                    }}
                                    className="p-1 rounded-md hover:bg-slate-800/60 transition-all cursor-pointer"
                                    title="Repository Settings"
                                  >
                                    <Settings className="h-3.5 w-3.5 text-slate-400 hover:text-white transition-colors" />
                                  </button>
                                </div>
                              </div>

                              {/* Metadata Grid */}
                              <div className="mb-3 grid grid-cols-2 gap-3">
                                <div className="rounded-lg bg-slate-800/30 border border-slate-700/30 px-3 py-2">
                                  <p className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">
                                    Persona
                                  </p>
                                  <p className="text-white font-semibold text-xs">
                                    {formatPersona(repo.doc_persona)}
                                  </p>
                                </div>
                                <div className="rounded-lg bg-slate-800/30 border border-slate-700/30 px-3 py-2">
                                  <p className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">
                                    Last documented
                                  </p>
                                  <p className="text-white font-semibold text-[10px]">
                                    {formatDateTime(repo.last_documented_at)}
                                  </p>
                                </div>
                              </div>

                              {/* Activity Chart */}
                              <div className="mb-4">
                                <p className="text-slate-500 text-[9px] uppercase tracking-wider mb-2">
                                  Activity (14 days)
                                </p>
                                <div className="flex items-end justify-between gap-1 h-12 rounded-lg bg-slate-900/50 border border-slate-800/40 p-2">
                                  {activityData.map((value, idx) => {
                                    const height = Math.max(
                                      (value / maxActivity) * 100,
                                      8
                                    );
                                    const isHighlight = idx === 8;
                                    return (
                                      <div
                                        key={idx}
                                        className={`flex-1 rounded-sm transition-all hover:opacity-80 ${
                                          isHighlight
                                            ? "bg-blue-500 shadow-lg shadow-blue-500/50"
                                            : "bg-slate-700/50 hover:bg-slate-600/50"
                                        }`}
                                        style={{ height: `${height}%` }}
                                        title={`Activity: ${value}`}
                                      />
                                    );
                                  })}
                                </div>
                              </div>

                              {isDocbookRepo && (
                                <div className="rounded-lg border border-blue-400/30 bg-blue-500/10 backdrop-blur-sm px-3 py-2 text-[10px] text-blue-100 mb-3">
                                  <div className="flex items-start gap-2">
                                    <BookOpen className="h-3 w-3 flex-shrink-0 mt-0.5 text-blue-300" />
                                    <span>{docbookNotice}</span>
                                  </div>
                                </div>
                              )}

                              {/* Action Buttons - 3 Buttons in Row */}
                              <div className="mt-auto grid grid-cols-3 gap-1.5">
                                {/* View Docs - Blue Transparent */}
                                <button
                                  onClick={() => {
                                    if (viewDocsDisabled) return;
                                    router.push(docsHref);
                                  }}
                                  disabled={viewDocsDisabled}
                                  className={`group relative col-span-1 inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2.5 text-xs font-semibold transition-all overflow-hidden ${
                                    viewDocsDisabled
                                      ? "cursor-not-allowed bg-slate-800/30 text-slate-500 border border-slate-700/40"
                                      : "cursor-pointer bg-blue-500/15 text-blue-300 border border-blue-500/25 hover:bg-blue-500/25 hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/20"
                                  }`}
                                >
                                  {!viewDocsDisabled && (
                                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400/0 via-blue-400/10 to-blue-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                                  )}
                                  <BookOpen className="h-3.5 w-3.5 relative z-10" />
                                  <span className="hidden xl:inline relative z-10">
                                    View docs
                                  </span>
                                </button>

                                {/* Regenerate Docs - Green Transparent */}
                                <div className="col-span-2">
                                  <GenerateDocsButton
                                    repoName={displayName}
                                    repoFullName={fullName}
                                    hasDocsFolder={hasDocs}
                                    onGenerationComplete={loadRepositories}
                                    disabled={isDocbookRepo}
                                    disabledReason={
                                      isDocbookRepo ? "" : undefined
                                    }
                                    fullWidth
                                  />
                                </div>

                                {/* Publish to Live - Yellow Transparent - Full Width */}
                                {!isDocbookRepo && (
                                  <div className="col-span-3">
                                    <PublishToLiveButton
                                      repoFullName={fullName}
                                      orgId={selectedOrg}
                                      repoId={
                                        fullName.split("/")[1] || displayName
                                      }
                                      hasPublished={false}
                                      lastPublishedAt={null}
                                      onPublishComplete={loadRepositories}
                                      fullWidth
                                      disabled={!hasDocs}
                                    />
                                    {!hasDocs && (
                                      <p className="mt-1 text-[10px] text-amber-400/70 text-center">
                                        Generate docs first to publish
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </Layout>
    </OnboardingGuard>
  );
}
