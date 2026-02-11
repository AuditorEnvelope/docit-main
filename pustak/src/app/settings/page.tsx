"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  BadgeCheck,
  BookOpen,
  Building2,
  CheckCircle2,
  Crown,
  GitBranch,
  Loader2,
  Plug,
  RefreshCw,
  Settings as SettingsIcon,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Layout } from "@/components/Layout";
import ConnectOrganizationModal from "@/components/ConnectOrganizationModal";
import DocbookSetupModal from "@/components/DocbookSetupModal";
import { useAuth } from "@/contexts/AuthContext";
import apiClient from "@/lib/apiClient";

interface OrgSummary {
  org: string;
  readerInstalled: boolean;
  writerInstalled: boolean;
  writerHasAccess: boolean;
  docbookRepo?: string;
  loading: boolean;
  docbookLinked: boolean;
}

function formatPlanLabel(plan?: string | null) {
  if (!plan) return "FREE";
  return plan.toUpperCase();
}

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const READER_APP_URL = "https://github.com/apps/pustak-analyser-ai-test";
const WRITER_APP_URL = "https://github.com/apps/pustak-publisher-ai-test";

const STATUS_TONE_CLASSES = {
  success:
    "border-emerald-400/60 bg-emerald-500/15 shadow-[0_10px_30px_-15px_rgba(16,185,129,0.45)]",
  warning:
    "border-amber-500/40 bg-amber-500/12 shadow-[0_10px_30px_-15px_rgba(251,191,36,0.35)]",
  neutral: "border-slate-700/70 bg-slate-800/70",
} as const;

const STATUS_VALUE_CLASSES = {
  success: "text-emerald-100",
  warning: "text-amber-100",
  neutral: "text-slate-200",
} as const satisfies Record<StatusTone, string>;

const STATUS_ACTION_DEFAULT_CLASSES = {
  success: "bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30",
  warning: "bg-white/10 text-white hover:bg-white/20",
  neutral: "bg-slate-800/60 text-slate-200 hover:bg-slate-800/80",
} as const satisfies Record<StatusTone, string>;

type StatusTone = keyof typeof STATUS_TONE_CLASSES;

type StatusAction =
  | { type: "link"; label: string; href: string; className?: string }
  | { type: "button"; label: string; onClick: () => void; className?: string };

export default function SettingsPage() {
  const {
    user,
    token,
    loading: authLoading,
    isAuthenticated,
    logout,
  } = useAuth();
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState<string[]>([]);
  const [orgSummaries, setOrgSummaries] = useState<Record<string, OrgSummary>>(
    {}
  );
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [docbookOrg, setDocbookOrg] = useState<string | null>(null);

  const loadSettingsData = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setFetchError(null);

    try {
      const orgsResponse = await apiClient.get<{
        organizations?: { login?: string }[];
      }>("/user/organizations");
      const orgData = orgsResponse.data;
      const orgsArray = Array.isArray(orgData.organizations)
        ? orgData.organizations
        : [];
      const orgIds: string[] = orgsArray
        .map((org: { login?: string }) => org?.login)
        .filter(
          (login): login is string =>
            typeof login === "string" && login.length > 0
        );

      setOrganizations(orgIds);

      if (!orgIds.length) {
        setOrgSummaries({});
        setLoading(false);
        return;
      }

      const summaries: Record<string, OrgSummary> = {};

      await Promise.all(
        orgIds.map(async (orgId) => {
          const summary: OrgSummary = {
            org: orgId,
            readerInstalled: false,
            writerInstalled: false,
            writerHasAccess: false,
            docbookLinked: false,
            loading: true,
          };

          try {
            // Apps installation status
            try {
              const appsRes = await apiClient.get<{
                reader_app?: { installed?: boolean };
                writer_app?: { installed?: boolean };
              }>(`/org/${orgId}/verify-apps`);
              const appData = appsRes.data;
              summary.readerInstalled = appData?.reader_app?.installed ?? false;
              summary.writerInstalled = appData?.writer_app?.installed ?? false;
            } catch (err) {
              console.error(`Failed to load app status for ${orgId}`, err);
            }

            // Docbook and writer access
            try {
              const docbookRes = await apiClient.get<{
                exists: boolean;
                docbook_repo?: string;
              }>("/docbook/check-exists", {
                params: { org_id: orgId },
              });
              const docbookData = docbookRes.data;
              if (docbookData.exists) {
                summary.docbookRepo = docbookData.docbook_repo;
                summary.docbookLinked = true;

                try {
                  const accessRes = await apiClient.get<{
                    has_access?: boolean;
                  }>(`/org/${orgId}/verify-writer-app-access`, {
                    params: {
                      repo: docbookData.docbook_repo,
                    },
                  });
                  const accessData = accessRes.data;
                  summary.writerHasAccess = accessData?.has_access ?? false;
                } catch (err) {
                  console.error(
                    `Failed to load writer access for ${orgId}`,
                    err
                  );
                }
              }
            } catch (err) {
              console.error(`Failed to load docbook status for ${orgId}`, err);
            }
          } catch (err) {
            console.error(`Failed to load status for ${orgId}`, err);
          } finally {
            summary.loading = false;
            summaries[orgId] = summary;
          }
        })
      );

      setOrgSummaries(summaries);
    } catch (error) {
      console.error("Settings load error", error);
      setFetchError(
        error instanceof Error ? error.message : "Unable to fetch settings"
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadSettingsData();
    }
  }, [token, loadSettingsData]);

  const handleDocbookSuccess = (orgId: string, repoName: string) => {
    setOrgSummaries((prev) => ({
      ...prev,
      [orgId]: {
        ...(prev[orgId] || {
          org: orgId,
          readerInstalled: false,
          writerInstalled: false,
          writerHasAccess: false,
          loading: false,
          docbookLinked: true,
        }),
        docbookRepo: repoName,
        docbookLinked: true,
      },
    }));
  };

  if (!isAuthenticated || authLoading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 text-slate-100">
        <div className="max-w-6xl mx-auto px-6 py-12 space-y-10">
          {/* Hero */}
          <section className="rounded-3xl border border-slate-800/80 bg-gradient-to-br from-indigo-900/70 via-blue-900/60 to-slate-900/80 p-10 shadow-2xl">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
              <div className="flex items-start gap-5">
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name || user.username || "User"}
                    className="w-20 h-20 rounded-3xl border-4 border-blue-500/70 shadow-lg"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-3xl bg-blue-500/80 flex items-center justify-center text-2xl font-bold">
                    {(user?.name || user?.username || "U")
                      .slice(0, 1)
                      .toUpperCase()}
                  </div>
                )}
                <div className="space-y-3">
                  <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">
                      {user?.name || user?.username || "Your Account"}
                    </h1>
                    <p className="text-slate-300">
                      {user?.email || `@${user?.username ?? "pustak-user"}`}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full bg-blue-500/20 px-4 py-2 text-xs font-semibold text-blue-200 uppercase tracking-widest">
                      <Crown className="w-3 h-3" />{" "}
                      {formatPlanLabel(user?.plan)} PLAN
                    </span>
                    {token && (
                      <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-200 uppercase tracking-widest">
                        <ShieldCheck className="w-3 h-3" /> Authenticated
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setShowConnectModal(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 hover:bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-900/30 transition"
                >
                  <Plug className="w-4 h-4" /> Connect organization
                </button>
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-700/70 px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-slate-800/60 transition"
                >
                  <Crown className="w-4 h-4" /> View plans
                </Link>
                <button
                  onClick={logout}
                  className="inline-flex items-center gap-2 rounded-xl border border-red-500/50 px-5 py-3 text-sm font-semibold text-red-200 hover:bg-red-500/10 transition"
                >
                  Sign out
                </button>
              </div>
            </div>
          </section>

          {/* Status summary */}
          <section className="grid gap-5 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-lg">
              <div className="flex items-center gap-3 text-indigo-200">
                <SettingsIcon className="w-5 h-5" />
                <span className="text-xs uppercase tracking-widest">
                  Account
                </span>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-white">
                Profile & Billing
              </h3>
              <p className="mt-2 text-sm text-slate-400">
                Update your profile details, manage plan upgrades, and review
                connected services.
              </p>
              <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-indigo-500/15 px-3 py-1 text-xs text-indigo-200">
                <BadgeCheck className="w-3 h-3" /> Account in good standing
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-lg">
              <div className="flex items-center gap-3 text-emerald-200">
                <Building2 className="w-5 h-5" />
                <span className="text-xs uppercase tracking-widest">
                  Organizations
                </span>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-white">
                {organizations.length} connected
              </h3>
              <p className="mt-2 text-sm text-slate-400">
                Manage GitHub organization connections, app access, and webhook
                status.
              </p>
              <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-200">
                <Sparkles className="w-3 h-3" /> Webhooks auto-configured
              </div>
            </div>
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-lg">
              <div className="flex items-center gap-3 text-purple-200">
                <BookOpen className="w-5 h-5" />
                <span className="text-xs uppercase tracking-widest">
                  Docbooks
                </span>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-white">
                {
                  Object.values(orgSummaries).filter((s) => s.docbookLinked)
                    .length
                }{" "}
                linked
              </h3>
              <p className="mt-2 text-sm text-slate-400">
                Keep your generated documentation organized across staging and
                main branches.
              </p>
              <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-purple-500/15 px-3 py-1 text-xs text-purple-200">
                <GitBranch className="w-3 h-3" /> Staging → Main review flow
              </div>
            </div>
          </section>

          {/* Organizations */}
          <section className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-white">
                  Organization Connections
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                  Monitor GitHub app installation, webhook access, and docbook
                  linkage for each organization.
                </p>
              </div>
              <button
                onClick={() => setShowConnectModal(true)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700/70 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800/70 transition"
              >
                <Plug className="w-4 h-4" /> Connect another org
              </button>
            </div>

            {fetchError && (
              <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> {fetchError}
              </div>
            )}

            {loading ? (
              <div className="flex items-center gap-3 rounded-2xl border border-slate-800/70 bg-slate-900/40 p-6 text-slate-300">
                <Loader2 className="w-5 h-5 animate-spin" />
                Loading organization status…
              </div>
            ) : organizations.length === 0 ? (
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-8 text-center space-y-3">
                <ShieldCheck className="mx-auto w-10 h-10 text-slate-400" />
                <h3 className="text-lg font-semibold text-white">
                  No organizations connected yet
                </h3>
                <p className="text-sm text-slate-400">
                  Connect your first GitHub organization to enable automated
                  documentation workflows.
                </p>
                <button
                  onClick={() => setShowConnectModal(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 hover:bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow"
                >
                  <Plug className="w-4 h-4" /> Connect organization
                </button>
              </div>
            ) : (
              <div className="space-y-5">
                {organizations.map((orgId) => {
                  const summary = orgSummaries[orgId];
                  const summaryLoading = !summary || summary.loading;

                  const statusItems: {
                    key: string;
                    label: string;
                    status: string;
                    tone: StatusTone;
                    action?: StatusAction;
                  }[] = summaryLoading
                    ? [
                        {
                          key: "loading",
                          label: "Checking status",
                          status: "Please wait…",
                          tone: "neutral",
                        },
                      ]
                    : [
                        {
                          key: "reader",
                          label: "Reader App",
                          status: summary.readerInstalled
                            ? "Installed"
                            : "Install required",
                          tone: summary.readerInstalled ? "success" : "warning",
                          action: summary.readerInstalled
                            ? undefined
                            : {
                                type: "link",
                                label: "Install",
                                href: READER_APP_URL,
                              },
                        },
                        {
                          key: "docbook",
                          label: "Docbook Repo",
                          status: summary.docbookLinked
                            ? "Linked"
                            : "Create & link",
                          tone: summary.docbookLinked ? "success" : "warning",
                          action: summary.docbookLinked
                            ? undefined
                            : {
                                type: "button",
                                label: "Create & link",
                                onClick: () => setDocbookOrg(orgId),
                              },
                        },
                        {
                          key: "writer",
                          label: "Writer App",
                          status: summary.writerInstalled
                            ? "Installed"
                            : "Install required",
                          tone: summary.writerInstalled ? "success" : "warning",
                          action: summary.writerInstalled
                            ? undefined
                            : {
                                type: "link",
                                label: "Install",
                                href: WRITER_APP_URL,
                              },
                        },
                        {
                          key: "access",
                          label: "Writer Access",
                          status: !summary.docbookLinked
                            ? "Link docbook first"
                            : summary.writerHasAccess
                            ? "Granted"
                            : "Pending",
                          tone: !summary.docbookLinked
                            ? "neutral"
                            : summary.writerHasAccess
                            ? "success"
                            : "warning",
                          action:
                            summary.docbookLinked && !summary.writerHasAccess
                              ? {
                                  type: "link",
                                  label: "Manage access",
                                  href: WRITER_APP_URL,
                                }
                              : undefined,
                        },
                      ];

                  return (
                    <div
                      key={orgId}
                      className="group relative overflow-hidden rounded-3xl border border-slate-800/80 bg-slate-900/60 p-8 shadow-[0_30px_70px_-45px_rgba(30,64,175,0.55)] transition hover:border-indigo-500/40"
                    >
                      <div
                        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(79,70,229,0.28),_transparent_58%)] opacity-70 blur-3xl"
                        aria-hidden
                      />
                      <div
                        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.18),_transparent_55%)] opacity-60 blur-3xl"
                        aria-hidden
                      />

                      <div className="relative space-y-8">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                          <div>
                            <h3 className="text-2xl font-semibold text-white">
                              {orgId}
                            </h3>
                            <p className="mt-1 text-sm text-slate-400">
                              Manage GitHub app access, docbook linkage, and
                              webhook health.
                            </p>
                            {summaryLoading && (
                              <span className="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/70 px-3 py-1 text-xs font-semibold text-slate-300">
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                Syncing status…
                              </span>
                            )}
                          </div>
                          <button
                            onClick={loadSettingsData}
                            className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-slate-200 transition hover:border-indigo-400 hover:text-white"
                          >
                            <RefreshCw className="h-4 w-4" />
                            Refresh
                          </button>
                        </div>

                        <div className="flex flex-col gap-8 xl:flex-row xl:items-start">
                          <div className="flex flex-col gap-6 xl:w-80">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                              <span className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">
                                Docbook repository
                              </span>
                              <div className="mt-3 space-y-2">
                                {summary?.docbookRepo ? (
                                  <>
                                    <p className="break-words text-sm text-slate-200">
                                      {summary.docbookRepo}
                                    </p>
                                    <Link
                                      href={`https://github.com/${summary.docbookRepo}`}
                                      target="_blank"
                                      className="inline-flex items-center gap-2 text-xs font-semibold text-indigo-300 hover:text-indigo-200"
                                    >
                                      Open on GitHub
                                    </Link>
                                  </>
                                ) : (
                                  <p className="text-sm text-amber-200">
                                    No docbook linked yet. Link your docbook
                                    repository to publish docs.
                                  </p>
                                )}
                              </div>
                            </div>

                            <div className="flex flex-wrap gap-3">
                              <button
                                onClick={() => setDocbookOrg(orgId)}
                                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-500/90 px-4 py-2 text-sm font-semibold text-white shadow-lg transition hover:bg-blue-500"
                              >
                                <GitBranch className="h-4 w-4" />
                                {summary?.docbookLinked
                                  ? "Manage docbook"
                                  : "Link docbook"}
                              </button>
                              <a
                                href="https://github.com/apps/pustak-analyser-ai-test"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-indigo-400 hover:text-white"
                              >
                                <ShieldCheck className="h-4 w-4" />
                                Manage GitHub App
                              </a>
                            </div>
                          </div>

                          <div className="flex-1 flex flex-col gap-6 lg:flex-row lg:items-start">
                            <div className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <span className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">
                                  Connection checklist
                                </span>
                                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-200">
                                  <Plug className="h-3.5 w-3.5" />
                                  Status
                                </div>
                              </div>
                              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-2">
                                {statusItems.map(
                                  ({ key, label, status, tone, action }) => (
                                    <div
                                      key={key}
                                      className={`rounded-2xl border px-4 py-3 ${STATUS_TONE_CLASSES[tone]} flex flex-col gap-3`}
                                    >
                                      <div className="space-y-1">
                                        <span className="block text-sm font-semibold text-slate-100">
                                          {label}
                                        </span>
                                        <span
                                          className={`block text-[11px] font-semibold uppercase tracking-[0.35em] ${STATUS_VALUE_CLASSES[tone]}`}
                                        >
                                          {status}
                                        </span>
                                      </div>
                                      {action ? (
                                        action.type === "link" ? (
                                          <a
                                            href={action.href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                              action.className ||
                                              STATUS_ACTION_DEFAULT_CLASSES[
                                                tone
                                              ]
                                            }`}
                                          >
                                            {action.label}
                                          </a>
                                        ) : (
                                          <button
                                            onClick={action.onClick}
                                            className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                              action.className ||
                                              STATUS_ACTION_DEFAULT_CLASSES[
                                                tone
                                              ]
                                            }`}
                                          >
                                            {action.label}
                                          </button>
                                        )
                                      ) : null}
                                    </div>
                                  )
                                )}
                              </div>
                            </div>

                            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 lg:w-72">
                              <span className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">
                                Automation status
                              </span>
                              <ul className="mt-4 space-y-3 text-sm text-slate-300">
                                <li className="flex items-center gap-2">
                                  <CheckCircle2
                                    className={`h-4 w-4 ${
                                      summary?.readerInstalled
                                        ? "text-emerald-400"
                                        : "text-amber-400"
                                    }`}
                                  />
                                  GitHub Reader App{" "}
                                  {summary?.readerInstalled
                                    ? "installed"
                                    : "pending installation"}
                                </li>
                                <li className="flex items-center gap-2">
                                  <CheckCircle2
                                    className={`h-4 w-4 ${
                                      summary?.writerInstalled
                                        ? "text-emerald-400"
                                        : "text-amber-400"
                                    }`}
                                  />
                                  Writer App{" "}
                                  {summary?.writerInstalled
                                    ? "installed"
                                    : "pending installation"}
                                </li>
                                <li className="flex items-center gap-2">
                                  <CheckCircle2
                                    className={`h-4 w-4 ${
                                      summary?.docbookLinked
                                        ? "text-emerald-400"
                                        : "text-amber-400"
                                    }`}
                                  />
                                  Docbook{" "}
                                  {summary?.docbookLinked
                                    ? "linked"
                                    : "not linked"}
                                </li>
                              </ul>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Modals */}
      {token && (
        <ConnectOrganizationModal
          isOpen={showConnectModal}
          onClose={() => {
            setShowConnectModal(false);
            loadSettingsData();
          }}
          backendUrl={BACKEND_URL}
          userToken={token}
          onSuccess={loadSettingsData}
        />
      )}

      {docbookOrg && (
        <DocbookSetupModal
          isOpen={Boolean(docbookOrg)}
          onClose={() => setDocbookOrg(null)}
          orgId={docbookOrg}
          onSuccess={(repo) => {
            if (docbookOrg) {
              handleDocbookSuccess(docbookOrg, repo);
            }
            setDocbookOrg(null);
            loadSettingsData();
          }}
        />
      )}
    </Layout>
  );
}
