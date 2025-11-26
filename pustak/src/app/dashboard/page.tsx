"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { GenerateDocsButton } from "@/components/GenerateDocsButton";
import { PublishToLiveButton } from "@/components/PublishToLiveButton";
import PendingReviewsTab from "@/components/PendingReviewsTab";
import { useAuth } from "@/contexts/AuthContext";
import { usePendingReviews } from "@/hooks/usePendingReviews";
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

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface RepositorySummary {
  full_name?: string;
  name?: string;
  description?: string | null;
  default_branch?: string | null;
  tracked_branch?: string | null;
  tracked_branch_source?: string | null;
  docbook_tracked_branch?: string | null;
  doc_persona?: string | null;
  last_documented_at?: string | null;
  pending_reviews?: number | null;
  html_url?: string | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout, isAuthenticated, token } = useAuth();

  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearchQuery, setRepoSearchQuery] = useState("");
  const [connectedOrgs, setConnectedOrgs] = useState<string[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [docbookRepo, setDocbookRepo] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    if (!token) {
      setConnectedOrgs([]);
      setSelectedOrg("");
      setDocbookRepo(null);
      return;
    }

    const fetchOrganizations = async () => {
      setLoadingOrgs(true);
      try {
        const response = await fetch(`${BACKEND_URL}/user/organizations`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error("Failed to load organizations");
        }

        const data = await response.json();
        const orgs: string[] = (data.organizations || []).map(
          (org: { login: string }) => org.login
        );
        setConnectedOrgs(orgs);
        setSelectedOrg((current) =>
          current && orgs.includes(current) ? current : orgs[0] || ""
        );
      } catch (error) {
        console.error("Error fetching organizations", error);
        setConnectedOrgs([]);
        setSelectedOrg("");
        setDocbookRepo(null);
      } finally {
        setLoadingOrgs(false);
      }
    };

    fetchOrganizations();
  }, [token]);

  const fetchDocbookRepo = useCallback(async () => {
    if (!token || !selectedOrg) {
      setDocbookRepo(null);
      return;
    }

    try {
      const response = await fetch(
        `${BACKEND_URL}/docbook/check-exists?org_id=${encodeURIComponent(selectedOrg)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      if (!response.ok) {
        setDocbookRepo(null);
        return;
      }

      const data = await response.json();
      setDocbookRepo(data.exists ? data.docbook_repo ?? null : null);
    } catch (error) {
      console.error("Error fetching docbook repo", error);
      setDocbookRepo(null);
    }
  }, [selectedOrg, token]);

  const reviewApiBase = useMemo(() => {
    const normalized = BACKEND_URL.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(normalized);
    return hasApiSuffix ? normalized : `${normalized}/api/v1`;
  }, []);

  const pendingReviewsDisabled = !selectedOrg || !token;

  const {
    reviews: pendingReviews,
    isLoading: pendingReviewsLoading,
    error: pendingReviewsError,
    count: pendingReviewsCount,
    reload: reloadPendingReviews,
  } = usePendingReviews({
    orgId: pendingReviewsDisabled ? null : selectedOrg,
    token: token ?? null,
    backendUrl: reviewApiBase,
    disabled: pendingReviewsDisabled,
  });

  const loadRepositories = useCallback(async () => {
    if (!token || !selectedOrg) {
      setRepositories([]);
      return;
    }

    setLoadingRepos(true);
    setErrorMessage(null);

    try {
      const response = await fetch(
        `${BACKEND_URL}/org/${selectedOrg}/repositories/summary`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Failed to load repositories");
      }

      const data = await response.json();
      const repos: RepositorySummary[] = Array.isArray(data.repositories)
        ? data.repositories
        : [];
      setRepositories(repos);
    } catch (error) {
      console.error("Error loading repositories", error);
      setRepositories([]);
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to load repositories"
      );
    } finally {
      setLoadingRepos(false);
    }
  }, [selectedOrg, token]);

  useEffect(() => {
    loadRepositories();
  }, [loadRepositories]);

  useEffect(() => {
    fetchDocbookRepo();
  }, [fetchDocbookRepo]);

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

  const pendingReviewStatusMessage = useMemo(() => {
    if (pendingReviewsDisabled) {
      return "Connect an organization to start tracking documentation reviews.";
    }
    if (pendingReviewsLoading) {
      return "Syncing review queue…";
    }
    if (pendingReviewsError) {
      return "Unable to fetch the latest review status.";
    }
    if (pendingReviewsCount === 0) {
      return "All caught up! Nothing waiting for approval.";
    }
    return "Awaiting approval across docs";
  }, [
    pendingReviewsDisabled,
    pendingReviewsLoading,
    pendingReviewsError,
    pendingReviewsCount,
  ]);

  const reviewButtonDisabled = pendingReviewsDisabled || !!pendingReviewsError;

  const documentedCount = useMemo(
    () =>
      repositories.filter((repo) => Boolean(repo.last_documented_at)).length,
    [repositories]
  );

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

  return (
    <Layout>
      <div className="min-h-screen bg-slate-950">
        <div className="container mx-auto px-4 py-12 space-y-10">
          <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/80 px-8 py-10 shadow-[0_35px_80px_-45px_rgba(59,130,246,0.6)]">
            <div className="absolute inset-0 -translate-x-1/3 translate-y-1/4 scale-125 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.35),_transparent_55%)] blur-3xl opacity-70" aria-hidden />
            <div className="absolute inset-0 translate-x-1/3 -translate-y-1/4 scale-125 bg-[radial-gradient(circle_at_bottom_right,_rgba(124,58,237,0.35),_transparent_55%)] blur-3xl opacity-70" aria-hidden />
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
                      {user.plan.toUpperCase()} PLAN
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
                    Welcome back! Track repository coverage, monitor pending doc reviews, and jump straight into actions tailored to your organization.
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

          <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg transition hover:border-blue-400/60">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-blue-500/15 via-transparent to-transparent opacity-0 transition group-hover:opacity-100" aria-hidden />
              <div className="relative space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-400">
                    Repositories
                  </h3>
                </div>
                <p className="text-4xl font-semibold text-white">
                  {loadingRepos ? (
                    <Loader2 className="h-7 w-7 animate-spin text-blue-300" />
                  ) : (
                    repositories.length
                  )}
                </p>
                <p className="text-sm text-slate-400">
                  Connected via Reader App
                </p>
              </div>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg transition hover:border-emerald-400/60">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-emerald-500/15 via-transparent to-transparent opacity-0 transition group-hover:opacity-100" aria-hidden />
              <div className="relative space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-300">
                    <FileText className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-400">
                    Documented
                  </h3>
                </div>
                <p className="text-4xl font-semibold text-white">{documentedCount}</p>
                <p className="text-sm text-slate-400">
                  Repositories with generated docs
                </p>
              </div>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-purple-500/40 bg-gradient-to-br from-purple-900/70 via-slate-900/70 to-indigo-900/60 p-6 shadow-[0_40px_90px_-60px_rgba(109,40,217,0.8)]">
              <div className="relative space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-500/30 text-purple-100">
                      <Calendar className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-[0.35em] text-purple-200">
                        Pending reviews
                      </h3>
                      <p className="text-xs text-purple-200/70">
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
                    className={`inline-flex items-center gap-2 rounded-full border border-purple-400/50 px-4 py-2 text-xs font-semibold uppercase tracking-widest transition ${
                      reviewButtonDisabled
                        ? "cursor-not-allowed bg-purple-500/10 text-purple-200/60"
                        : "bg-purple-500/20 text-purple-50 hover:bg-purple-500/30"
                    }`}
                  >
                    <Sparkles className="h-3 w-3" />
                    Review docs
                  </button>
                </div>

                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-semibold text-purple-100">
                    {pendingReviewsDisabled ? (
                      "—"
                    ) : pendingReviewsLoading ? (
                      <Loader2 className="h-7 w-7 animate-spin text-purple-200" />
                    ) : (
                      pendingReviewsCount
                    )}
                  </span>
                  {!pendingReviewsDisabled && !pendingReviewsLoading && (
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${
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

                <p className="text-sm text-purple-100/80">
                  {pendingReviewStatusMessage}
                </p>

                {pendingReviewsError && (
                  <div className="flex items-center justify-between gap-3 text-xs text-rose-200">
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

          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 shadow-[0_30px_70px_-50px_rgba(15,23,42,0.9)]">
            <div className="border-b border-slate-800/80 px-8 py-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">
                  Repository overview
                </div>
                <h2 className="mt-3 text-2xl font-semibold text-white">
                  {selectedOrg
                    ? `Docs coverage inside ${selectedOrg}`
                    : "Connect an organization to start managing repositories."}
                </h2>
                <p className="text-sm text-slate-400">
                  Search, filter, and trigger doc generation directly from these tiles.
                </p>
              </div>

              <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center lg:w-auto">
                <div className="relative flex-1 min-w-[220px]">
                  <input
                    type="text"
                    placeholder="Search repositories…"
                    value={repoSearchQuery}
                    onChange={(event) => setRepoSearchQuery(event.target.value)}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-900/80 py-2.5 pl-11 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                    disabled={!repositories.length}
                  />
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-600">
                    <BookOpen className="h-4 w-4" />
                  </span>
                </div>

                {connectedOrgs.length > 0 && (
                  <div className="relative">
                    <select
                      value={selectedOrg}
                      onChange={(event) => setSelectedOrg(event.target.value)}
                      className="appearance-none rounded-2xl border border-slate-700 bg-slate-900/80 py-2.5 pl-4 pr-10 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500/60"
                    >
                      {connectedOrgs.map((org) => (
                        <option key={org} value={org}>
                          {org}
                        </option>
                      ))}
                    </select>
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-600">
                      <GitBranch className="h-4 w-4" />
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="px-8 py-6">
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
                    Launch the onboarding flow to install the GitHub Apps, link your docbook repository, and start documenting your codebase.
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
                  <p className="text-lg font-semibold text-white">No repositories match your search</p>
                  <p className="text-sm text-slate-400">
                    Modify filters or update GitHub permissions to include more repositories.
                  </p>
                </div>
              ) : (
                <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {filteredRepositories.map((repo) => {
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
                    const repoShortName = fullName.split("/")[1] || displayName;
                    const docsHref = docbookRepo
                      ? `/repo/${docbookRepo}/${repoShortName}/architecture/current.md`
                      : `/repo/${fullName}`;
                    const viewDocsDisabled = !docbookRepo;

                    const cardGradient = isDocbookRepo
                      ? "from-blue-500/20 via-slate-900/70 to-slate-900/60"
                      : "from-slate-900/80 via-slate-900/70 to-slate-900/60";

                    return (
                      <div
                        key={fullName}
                        className={`group relative flex min-h-[360px] flex-col overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br ${cardGradient} p-6 shadow-[0_25px_60px_-40px_rgba(15,23,42,0.7)] transition hover:border-blue-400/50`}
                      >
                        <div className="pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.25),_transparent_55%)]" aria-hidden />
                        <div className="pointer-events-none absolute inset-y-0 left-0 w-1/2 -translate-x-1/4 opacity-0 transition group-hover:opacity-60 bg-[radial-gradient(circle_at_bottom_left,_rgba(45,212,191,0.18),_transparent_55%)]" aria-hidden />
                        <div className="relative flex h-full flex-col">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h3 className="text-lg font-semibold text-white">
                                {displayName}
                              </h3>
                              <p className="text-xs uppercase tracking-[0.35em] text-slate-400">
                                {fullName}
                              </p>
                            </div>
                            <span className="inline-flex items-center gap-1 rounded-full border border-blue-400/40 bg-blue-500/15 px-2.5 py-1 text-xs font-semibold text-blue-100">
                              <GitBranch className="h-3 w-3" />
                              {trackedBranch}
                            </span>
                          </div>

                          {repo.description && (
                            <p className="mt-4 line-clamp-3 text-sm text-slate-300">
                              {repo.description}
                            </p>
                          )}

                          <div className="mt-6 space-y-3 text-sm text-slate-300">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400">Persona</span>
                              <span className="font-medium text-white">
                                {formatPersona(repo.doc_persona)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400">Last documented</span>
                              <span className="font-medium text-white">
                                {formatDateTime(repo.last_documented_at)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400">Pending reviews</span>
                              <span className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-2 py-0.5 text-xs font-semibold text-slate-200">
                                {pendingReviews}
                              </span>
                            </div>
                            {isDocbookRepo && (
                              <div className="rounded-xl border border-blue-400/30 bg-blue-500/10 px-3 py-3 text-xs text-blue-100">
                                {docbookNotice}
                              </div>
                            )}
                          </div>

                          <div className="mt-auto space-y-4 pt-6">
                            {!isDocbookRepo && (
                              <div className="flex flex-wrap gap-3">
                                <button
                                  onClick={() => {
                                    if (viewDocsDisabled) return;
                                    router.push(docsHref);
                                  }}
                                  disabled={viewDocsDisabled}
                                  className={`inline-flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold shadow-lg transition ${
                                    viewDocsDisabled
                                      ? "cursor-not-allowed bg-blue-500/40 text-blue-100 opacity-70"
                                      : "cursor-pointer bg-blue-500/90 text-white hover:bg-blue-500"
                                  }`}
                                >
                                  <BookOpen className="h-4 w-4" />
                                  View docs
                                </button>
                                <button
                                  onClick={() => router.push(`/repo/settings/${fullName}`)}
                                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-blue-400 hover:text-white cursor-pointer"
                                >
                                  <Settings className="h-4 w-4" />
                                  Settings
                                </button>
                                {repo.html_url && (
                                  <a
                                    href={repo.html_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-blue-400 hover:text-white cursor-pointer"
                                  >
                                    <Github className="h-4 w-4" />
                                    Code
                                  </a>
                                )}
                                {viewDocsDisabled && (
                                  <p className="w-full text-xs text-amber-300">
                                    Link your docbook repository to browse generated docs.
                                  </p>
                                )}
                              </div>
                            )}

                            <GenerateDocsButton
                              repoName={displayName}
                              repoFullName={fullName}
                              hasDocsFolder={hasDocs}
                              onGenerationComplete={loadRepositories}
                              disabled={isDocbookRepo}
                              disabledReason={isDocbookRepo ? "" : undefined}
                              fullWidth
                            />

                            {!isDocbookRepo && (
                              <div className="relative">
                                <PublishToLiveButton
                                  repoFullName={fullName}
                                  orgId={selectedOrg}
                                  repoId={fullName.split("/")[1] || displayName}
                                  hasPublished={false}
                                  lastPublishedAt={null}
                                  onPublishComplete={loadRepositories}
                                  fullWidth
                                  disabled={!hasDocs}
                                />
                                {!hasDocs && (
                                  <p className="mt-2 text-xs text-amber-400">
                                    Generate docs first to enable publishing
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
  );
}
