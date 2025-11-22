"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import ConnectOrganizationModal from "@/components/ConnectOrganizationModal";
import DocbookSetupModal from "@/components/DocbookSetupModal";
import { ArrowRight, CheckCircle, Loader2, ShieldCheck } from "lucide-react";

const RAW_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const API_BASE = RAW_BACKEND_URL.endsWith("/api/v1")
  ? RAW_BACKEND_URL
  : `${RAW_BACKEND_URL.replace(/\/$/, "")}/api/v1`;

interface OrgSummary {
  org: string;
  docbook_repo?: string;
  writer_app_installed?: boolean;
  reader_app_installed?: boolean;
  writer_app_has_access?: boolean;
}

type StepStatus = "complete" | "current" | "upcoming";

export default function OnboardingPage() {
  const { user, token, loading, isAuthenticated, markOnboardingComplete } =
    useAuth();
  const router = useRouter();

  const [orgs, setOrgs] = useState<string[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [orgSummaries, setOrgSummaries] = useState<Record<string, OrgSummary>>({});
  const [showOrgModal, setShowOrgModal] = useState(false);
  const [showDocbookModal, setShowDocbookModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pollingWriterApp, setPollingWriterApp] = useState(false);
  const writerPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const writerPollAttempts = useRef(0);

  const MAX_WRITER_POLL_ATTEMPTS = 12; // roughly 1 minute at 5s interval

  const primaryOrg = useMemo(() => orgs[0] || "", [orgs]);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (user?.is_onboarding_complete) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, loading, router, user?.is_onboarding_complete]);

  const loadState = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!token) return;

      try {
        if (!options?.silent) {
          setRefreshing(true);
        }
        const orgsRes = await fetch(`${API_BASE}/user/organizations`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

      if (orgsRes.ok) {
        const data = await orgsRes.json();
        const orgItems: any[] = data.organizations || [];
        const orgIds: string[] = orgItems
          .map((org) =>
            typeof org === "string"
              ? org
              : org?.login || org?.org || org?.name || ""
          )
          .filter(Boolean);
        setOrgs(orgIds);

        const summaries: Record<string, OrgSummary> = {};
        await Promise.all(
          orgIds.map(async (orgId) => {
            const summary: OrgSummary = { org: orgId };

            const appsRes = await fetch(`${API_BASE}/org/${orgId}/verify-apps`, {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });

            if (appsRes.ok) {
              const appData = await appsRes.json();
              summary.reader_app_installed = appData.reader_app?.installed ?? false;
              summary.writer_app_installed = appData.writer_app?.installed ?? false;
            }

            const docbookRes = await fetch(
              `${API_BASE}/docbook/check-exists?org_id=${orgId}`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            if (docbookRes.ok) {
              const docbookData = await docbookRes.json();
              if (docbookData.exists) {
                summary.docbook_repo = docbookData.docbook_repo;
              }
            }

            if (summary.docbook_repo) {
              const accessRes = await fetch(
                `${API_BASE}/org/${orgId}/verify-writer-app-access?repo=${encodeURIComponent(
                  summary.docbook_repo
                )}`,
                {
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                }
              );

              if (accessRes.ok) {
                const accessData = await accessRes.json();
                summary.writer_app_has_access = accessData.has_access ?? false;
              }
            }

            summaries[orgId] = summary;
          })
        );

        setOrgSummaries(summaries);
      }
      } catch (error) {
        console.error("Error loading onboarding state", error);
      } finally {
        if (!options?.silent) {
          setRefreshing(false);
        }
      }
    },
    [token]
  );

  const stopWriterPolling = useCallback(() => {
    if (writerPollRef.current) {
      clearInterval(writerPollRef.current);
      writerPollRef.current = null;
    }
    writerPollAttempts.current = 0;
    setPollingWriterApp(false);
  }, []);

  const startWriterPolling = useCallback(() => {
    if (writerPollRef.current) return;

    setPollingWriterApp(true);
    writerPollAttempts.current = 0;

    const poll = async () => {
      writerPollAttempts.current += 1;
      await loadState({ silent: true });

      if (writerPollAttempts.current >= MAX_WRITER_POLL_ATTEMPTS) {
        stopWriterPolling();
      }
    };

    void poll();
    writerPollRef.current = setInterval(() => {
      void poll();
    }, 5000);
  }, [loadState, stopWriterPolling]);

  useEffect(() => {
    loadState();
  }, [loadState]);

  useEffect(() => {
    if (!orgs.length) {
      setSelectedOrg("");
      return;
    }

    setSelectedOrg((prev) => {
      if (prev && orgs.includes(prev)) {
        return prev;
      }
      return orgs[0];
    });
  }, [orgs]);

  const currentSummary = selectedOrg
    ? orgSummaries[selectedOrg]
    : primaryOrg
    ? orgSummaries[primaryOrg]
    : undefined;

  const hasConnectedOrg = orgs.length > 0;
  const hasLinkedDocbook = !!currentSummary?.docbook_repo;
  const writerAppReady =
    currentSummary?.writer_app_installed && currentSummary?.writer_app_has_access;
  const docbookRepoName = currentSummary?.docbook_repo?.split("/").pop() ?? "";
  const suggestedDocbookName = `pustak-docbook-${(selectedOrg || primaryOrg || "").toLowerCase()}`;

  const step1Status: StepStatus = hasConnectedOrg ? "complete" : "current";
  const step2Status: StepStatus = hasLinkedDocbook
    ? "complete"
    : hasConnectedOrg
    ? "current"
    : "upcoming";
  const step3Status: StepStatus = writerAppReady
    ? "complete"
    : hasLinkedDocbook
    ? "current"
    : "upcoming";

  const canFinish = hasConnectedOrg && hasLinkedDocbook && writerAppReady;

  useEffect(() => {
    if (writerAppReady) {
      stopWriterPolling();
    }
  }, [writerAppReady, stopWriterPolling]);

  useEffect(() => {
    if (!hasLinkedDocbook) {
      stopWriterPolling();
    }
  }, [hasLinkedDocbook, stopWriterPolling]);

  useEffect(() => {
    return () => {
      stopWriterPolling();
    };
  }, [stopWriterPolling]);

  const handleOrgConnected = async () => {
    setShowOrgModal(false);
    await loadState();
  };

  const handleDocbookLinked = async (docbookRepo: string) => {
    setShowDocbookModal(false);
    if (!selectedOrg && !primaryOrg) return;
    const targetOrg = selectedOrg || primaryOrg;

    setOrgSummaries((prev) => ({
      ...prev,
      [targetOrg]: {
        ...(prev[targetOrg] || { org: targetOrg }),
        docbook_repo: `${targetOrg}/${docbookRepo}`,
      },
    }));

    await loadState();
  };

  const handleFinish = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/auth/onboarding-complete`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        markOnboardingComplete();
        router.replace("/dashboard");
      }
    } catch (error) {
      console.error("Failed to complete onboarding", error);
    } finally {
      setSaving(false);
    }
  };

  if (loading || refreshing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-slate-200 bg-slate-950">
        <Loader2 className="h-10 w-10 animate-spin" />
        <p className="text-lg">Preparing your onboarding experience...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto py-12 px-6">
        <div className="bg-slate-900 rounded-3xl border border-slate-800 shadow-2xl overflow-hidden">
          <div className="bg-gradient-to-br from-purple-900 via-indigo-900 to-slate-900 px-10 py-12 flex flex-col gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center text-3xl">
                ⚡
              </div>
              <div>
                <p className="text-sm uppercase tracking-widest text-purple-200/70">
                  Welcome to Pustak
                </p>
                <h1 className="text-3xl sm:text-4xl font-bold text-white">
                  Let’s get your organization ready in three quick steps
                </h1>
              </div>
            </div>
            <p className="text-slate-200/80 text-lg max-w-2xl">
              We’ll connect your GitHub organization, link a Docbook repository,
              and ensure the Writer app has access so you can start generating
              living documentation immediately.
            </p>
          </div>

          <div className="px-10 py-12 space-y-10">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3 text-sm uppercase tracking-widest text-slate-500">
                <span className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      step1Status === "complete"
                        ? "bg-emerald-400"
                        : step1Status === "current"
                        ? "bg-blue-400 animate-pulse"
                        : "bg-slate-600"
                    }`}
                  />
                  Step 1
                </span>
                <span className="hidden sm:inline text-slate-600">•</span>
                <span className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      step2Status === "complete"
                        ? "bg-emerald-400"
                        : step2Status === "current"
                        ? "bg-blue-400 animate-pulse"
                        : "bg-slate-600"
                    }`}
                  />
                  Step 2
                </span>
                <span className="hidden sm:inline text-slate-600">•</span>
                <span className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      step3Status === "complete"
                        ? "bg-emerald-400"
                        : step3Status === "current"
                        ? "bg-blue-400 animate-pulse"
                        : "bg-slate-600"
                    }`}
                  />
                  Step 3
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Progress updates automatically as you complete each milestone.
              </p>
            </div>

            <div className="space-y-8">
              <StepCard
                step={1}
                status={step1Status}
                title="Connect your GitHub organization"
                description="Install the GitHub App and register webhooks so Pustak can listen for commits across your repositories."
              >
                {hasConnectedOrg ? (
                  <div className="space-y-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm text-slate-300">
                        {orgs.length === 1
                          ? "1 organization connected"
                          : `${orgs.length} organizations connected`}
                      </p>
                      <button
                        onClick={() => setShowOrgModal(true)}
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-600/60 bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:border-purple-400/70 hover:bg-slate-800/80"
                      >
                        Manage organizations
                        <ArrowRight size={16} />
                      </button>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      {orgs.map((orgId) => {
                        const summary = orgSummaries[orgId];
                        const isActive = (selectedOrg || primaryOrg) === orgId;
                        return (
                          <button
                            key={orgId}
                            onClick={() => setSelectedOrg(orgId)}
                            className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                              isActive
                                ? "border-purple-400/60 bg-purple-500/10 shadow-lg shadow-purple-950/20"
                                : "border-slate-700/60 bg-slate-900/40 hover:border-purple-400/40 hover:bg-purple-500/10"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <p className="text-xs uppercase tracking-wide text-slate-400">Organization</p>
                                <p className="text-base font-semibold text-white">{orgId}</p>
                              </div>
                              {isActive && (
                                <span className="rounded-full bg-purple-500/20 px-3 py-1 text-xs font-semibold text-purple-200">
                                  Selected
                                </span>
                              )}
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <StatusPill label="Reader App" active={summary?.reader_app_installed} />
                              <StatusPill label="Writer App" active={summary?.writer_app_installed} />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-4 text-center">
                    <ShieldCheck className="h-12 w-12 text-purple-300" />
                    <div className="space-y-1">
                      <p className="text-lg font-semibold text-white">No organizations connected yet</p>
                      <p className="text-sm text-slate-400">
                        Choose the GitHub organization where you want to install the Pustak apps.
                      </p>
                    </div>
                    <button
                      onClick={() => setShowOrgModal(true)}
                      className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-purple-500 via-indigo-500 to-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl"
                    >
                      Connect organization
                      <ArrowRight size={16} />
                    </button>
                  </div>
                )}
              </StepCard>

              <StepCard
                step={2}
                status={step2Status}
                title="Create & link your docbook repository"
                description="A dedicated private repository stores the living documentation generated by Pustak."
              >
                {hasConnectedOrg ? (
                  hasLinkedDocbook ? (
                    <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5 text-sm text-slate-200">
                      <div className="flex items-center gap-2 text-emerald-300 text-sm font-semibold">
                        <CheckCircle className="h-5 w-5" />
                        Docbook repository linked
                      </div>
                      <p className="mt-3 text-base text-white">{currentSummary?.docbook_repo}</p>
                      <p className="mt-2 text-slate-400">
                        You can relink or change this docbook anytime from the repository settings.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-5 text-left">
                        <p className="text-sm font-semibold text-blue-200">Manual setup required</p>
                        <p className="mt-2 text-sm text-blue-100/90">
                          Create a private repository named
                          <code className="mx-2 rounded bg-blue-500/20 px-2 py-1 font-mono text-xs text-blue-50">
                            {suggestedDocbookName}
                          </code>
                          inside your organization, then link it to Pustak.
                        </p>
                        <p className="mt-2 text-xs text-blue-200/80">
                          Tip: include a README so the repository is initialized properly.
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3">
                        <a
                          href={`https://github.com/new?name=${suggestedDocbookName}&private=true&description=Pustak%20Docbook%20Repository`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-500 via-cyan-500 to-teal-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl"
                        >
                          Create on GitHub
                          <ArrowRight size={16} />
                        </a>
                        <button
                          onClick={() => setShowDocbookModal(true)}
                          className="inline-flex items-center gap-2 rounded-full border border-slate-600/60 bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:border-blue-400/60 hover:bg-slate-900/80"
                        >
                          Link existing docbook
                        </button>
                      </div>
                    </div>
                  )
                ) : (
                  <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 text-center text-amber-100">
                    Connect an organization first to unlock docbook configuration.
                  </div>
                )}
              </StepCard>

              <StepCard
                step={3}
                status={step3Status}
                title="Grant Writer App publish access"
                description="The Writer GitHub App needs access to your docbook repository to publish documentation updates."
              >
                {hasLinkedDocbook ? (
                  writerAppReady ? (
                    <div className="flex items-center justify-between gap-4 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-5 py-4">
                      <div>
                        <p className="text-sm font-semibold text-emerald-200">
                          Writer app installed with repository access
                        </p>
                        <p className="text-xs text-emerald-100/80">
                          Documentation updates will sync automatically whenever we generate docs.
                        </p>
                      </div>
                      <CheckCircle className="h-6 w-6 text-emerald-300" />
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-100">
                        <p className="font-semibold mb-2">Grant access to your docbook repository</p>
                        <p>
                          Install the Writer app from GitHub and grant access only to
                          <code className="mx-2 rounded bg-red-500/20 px-2 py-1 font-mono text-xs text-red-50">
                            {docbookRepoName || suggestedDocbookName}
                          </code>
                          . Afterwards, refresh the status below.
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          onClick={async () => {
                            try {
                              startWriterPolling();
                              const backendUrl =
                                process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
                              const response = await fetch(`${backendUrl}/auth/install-writer-app`);
                              if (!response.ok) {
                                throw new Error("Failed to get Writer app URL");
                              }
                              const data = await response.json();
                              window.open(data.url, "_blank");
                            } catch (error) {
                              console.error("Failed to install Writer App:", error);
                              stopWriterPolling();
                              alert("Failed to install Writer App. Please try again.");
                            }
                          }}
                          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-red-500 via-pink-500 to-purple-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl"
                        >
                          Install Writer App
                          <ArrowRight size={16} />
                        </button>
                        <button
                          onClick={async () => {
                            await loadState();
                            stopWriterPolling();
                          }}
                          className="inline-flex items-center gap-2 rounded-full border border-slate-600/60 bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:border-emerald-400/70 hover:bg-slate-900/80"
                        >
                          Refresh status
                        </button>
                      </div>
                      {pollingWriterApp && (
                        <p className="flex items-center gap-2 text-xs text-slate-400">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Waiting for Writer app installation...
                        </p>
                      )}
                    </div>
                  )
                ) : (
                  <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 text-center text-amber-100">
                    Link a docbook repository before granting Writer app access.
                  </div>
                )}
              </StepCard>
            </div>

            <div className="pt-2">
              <button
                onClick={handleFinish}
                disabled={!canFinish || saving}
                className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-500 px-6 py-4 text-lg font-semibold text-white shadow-xl transition hover:shadow-2xl disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-6 w-6 animate-spin" />
                    Finishing setup...
                  </>
                ) : (
                  <>
                    Complete onboarding
                    <ArrowRight size={22} />
                  </>
                )}
              </button>
              <p className="mt-3 text-center text-xs text-slate-500">
                You can revisit these steps later from the dashboard settings.
              </p>
            </div>
          </div>
        </div>
      </div>

      {showOrgModal && token && (
        <ConnectOrganizationModal
          isOpen={showOrgModal}
          onClose={() => setShowOrgModal(false)}
          backendUrl={API_BASE}
          userToken={token || ""}
          onSuccess={handleOrgConnected}
        />
      )}

      {showDocbookModal && currentSummary && (
        <DocbookSetupModal
          isOpen={showDocbookModal}
          onClose={() => setShowDocbookModal(false)}
          orgId={currentSummary.org}
          onSuccess={handleDocbookLinked}
        />
      )}
    </Layout>
  );
}

function StepCard({
  step,
  status,
  title,
  description,
  children,
}: {
  step: number;
  status: StepStatus;
  title: string;
  description: string;
  children: ReactNode;
}) {
  const isComplete = status === "complete";
  const isCurrent = status === "current";

  const badgeClasses = isComplete
    ? "bg-emerald-500/20 border-emerald-400/60 text-emerald-200"
    : isCurrent
    ? "bg-blue-500/20 border-blue-400/60 text-blue-200"
    : "bg-slate-800/60 border-slate-700/60 text-slate-400";

  const cardBorder = isComplete
    ? "border-emerald-500/40"
    : isCurrent
    ? "border-purple-500/50"
    : "border-slate-700/60";
  const cardBackground = isCurrent ? "bg-purple-950/20" : "bg-slate-900/40";

  return (
    <section className="space-y-4">
      <header className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-full border text-sm font-semibold transition ${badgeClasses}`}
        >
          {isComplete ? <CheckCircle className="h-5 w-5" /> : step}
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-white">{title}</h2>
          <p className="text-sm text-slate-300/80">{description}</p>
        </div>
      </header>

      <div
        className={`rounded-2xl border ${cardBorder} ${cardBackground} p-6 shadow-lg shadow-black/10 transition`}
      >
        {children}
      </div>
    </section>
  );
}

function StatusPill({
  label,
  active,
}: {
  label: string;
  active: boolean | undefined;
}) {
  const pillClasses = active
    ? "bg-emerald-500/15 text-emerald-200 border border-emerald-400/40"
    : "bg-slate-800/80 text-slate-400 border border-slate-700/60";

  const dotClasses = active ? "bg-emerald-300" : "bg-slate-500";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${pillClasses}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotClasses}`} />
      {label}
    </span>
  );
}
