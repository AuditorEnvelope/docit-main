"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import DocbookSetupModal from "@/components/DocbookSetupModal";
import {
  OnboardingSplash,
  ONBOARDING_PROGRESS_MESSAGES,
} from "@/components/OnboardingSplash";
import {
  AlertCircle,
  Check,
  ChevronDown,
  Github,
  ArrowRight,
  CheckCircle,
  Loader2,
  ShieldCheck,
  UserCircle2,
  LogOut,
  RefreshCw,
} from "lucide-react";

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

interface OrganizationOption {
  id: string;
  login: string;
  kind: "personal" | "organization";
}

type StepStatus = "complete" | "current" | "upcoming";
type DocbookLinkStatusState = {
  status: "idle" | "linking" | "linked" | "not_found" | "failed";
  error?: string;
};

export default function OnboardingPage() {
  const { user, token, loading, isAuthenticated, markOnboardingComplete } =
    useAuth();
  const router = useRouter();

  const [orgs, setOrgs] = useState<string[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [orgSummaries, setOrgSummaries] = useState<Record<string, OrgSummary>>(
    {},
  );
  const [availableOrganizations, setAvailableOrganizations] = useState<
    OrganizationOption[]
  >([]);
  const [orgSelection, setOrgSelection] = useState("");
  const [orgSelectionError, setOrgSelectionError] = useState("");
  const [orgFetchError, setOrgFetchError] = useState("");
  const [ownerPickerOpen, setOwnerPickerOpen] = useState(false);
  const [orgVerificationLoading, setOrgVerificationLoading] = useState(false);
  const [orgConnectLoading, setOrgConnectLoading] = useState(false);
  const [selectedOrgAppReady, setSelectedOrgAppReady] = useState<
    boolean | null
  >(null);
  const [showDocbookModal, setShowDocbookModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [pollingWriterApp, setPollingWriterApp] = useState(false);
  const [progressIndex, setProgressIndex] = useState(0);
  const [stateLoaded, setStateLoaded] = useState(false);
  const [forceOnboarding, setForceOnboarding] = useState(false);
  const [docbookLinkStatuses, setDocbookLinkStatuses] = useState<
    Record<string, DocbookLinkStatusState>
  >({});
  const docbookPollRefs = useRef<
    Record<string, ReturnType<typeof setInterval> | null>
  >({});
  const docbookPollAttempts = useRef<Record<string, number>>({});
  const writerPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const writerPollAttempts = useRef(0);
  const autoCompletionTriggered = useRef(false);
  const ownerPickerRef = useRef<HTMLDivElement | null>(null);
  const ownerPickerListId = useId();

  const MAX_WRITER_POLL_ATTEMPTS = 12; // roughly 1 minute at 5s interval
  const MAX_DOCBOOK_POLL_ATTEMPTS = 24; // roughly 2 minutes at 5s interval

  const primaryOrg = useMemo(() => orgs[0] || "", [orgs]);
  const shouldBypassOnboarding = Boolean(
    user?.is_onboarding_complete && !forceOnboarding,
  );

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (shouldBypassOnboarding && stateLoaded) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, loading, router, shouldBypassOnboarding, stateLoaded]);

  useEffect(() => {
    if (!(loading || refreshing)) {
      setProgressIndex(0);
      return;
    }

    setProgressIndex(0);
    const interval = setInterval(() => {
      setProgressIndex(
        (prev) => (prev + 1) % ONBOARDING_PROGRESS_MESSAGES.length,
      );
    }, 1800);

    return () => {
      clearInterval(interval);
    };
  }, [loading, refreshing]);

  const loadState = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!token) return;

      try {
        if (!options?.silent) {
          setRefreshing(true);
        }
        setStateLoaded(false);
        const orgsRes = await fetch(`${API_BASE}/user/organizations`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        let orgIds: string[] = [];

        if (orgsRes.ok) {
          const data = await orgsRes.json();
          console.log("[onboarding] orgs response:", data);
          const orgItems: any[] = data.organizations || [];
          const organizationOptions: OrganizationOption[] = orgItems
            .map((org) => {
              if (typeof org === "string") {
                return {
                  id: org,
                  login: org,
                  kind: "organization" as const,
                };
              }
              const login = String(org?.login ?? org?.org ?? org?.name ?? "");
              const id = String(org?.id ?? login);
              return { id, login, kind: "organization" as const };
            })
            .filter((org) => org.id && org.login);
          setAvailableOrganizations(organizationOptions);
          orgIds = orgItems
            .map((org) =>
              typeof org === "string"
                ? org
                : org?.login || org?.org || org?.name || "",
            )
            .filter(Boolean);
          setOrgs(orgIds);
          setOrgFetchError("");

          // Warn if debug shows zero orgs from all sources
          if (data._debug && orgItems.length === 0) {
            const d = data._debug;
            console.warn(
              `[onboarding] orgs empty — sources: direct=${d.direct_count}(${d.direct_debug}) memberships=${d.membership_count}(${d.membership_debug}) public=${d.public_count}(${d.public_debug})`,
            );
          }
        } else {
          const errText = await orgsRes.text().catch(() => "unknown");
          console.error(
            `[onboarding] orgs API failed: ${orgsRes.status} ${errText}`,
          );
          setOrgFetchError(
            `Failed to load organizations (${orgsRes.status}). Try reconnecting GitHub below.`,
          );
        }

        if (orgIds.length > 0) {
          const summaries: Record<string, OrgSummary> = {};
          await Promise.all(
            orgIds.map(async (orgId) => {
              const summary: OrgSummary = { org: orgId };

              const appsRes = await fetch(
                `${API_BASE}/org/${orgId}/verify-apps`,
                {
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                },
              );

              if (appsRes.ok) {
                const appData = await appsRes.json();
                summary.reader_app_installed =
                  appData.reader_app?.installed ?? false;
                summary.writer_app_installed =
                  appData.writer_app?.installed ?? false;
              }

              const docbookRes = await fetch(
                `${API_BASE}/docbook/check-exists?org_id=${orgId}`,
                {
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                },
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
                    summary.docbook_repo,
                  )}`,
                  {
                    headers: {
                      Authorization: `Bearer ${token}`,
                    },
                  },
                );

                if (accessRes.ok) {
                  const accessData = await accessRes.json();
                  summary.writer_app_has_access =
                    accessData.has_access ?? false;
                }
              }

              summaries[orgId] = summary;
            }),
          );

          setOrgSummaries(summaries);

          setDocbookLinkStatuses((prev) => {
            const next: Record<string, DocbookLinkStatusState> = {};
            for (const orgId of orgIds) {
              const summary = summaries[orgId];
              if (summary?.docbook_repo) {
                next[orgId] = { status: "linked" };
              } else if (prev[orgId] && prev[orgId].status !== "linked") {
                next[orgId] = prev[orgId];
              } else {
                next[orgId] = { status: "idle" };
              }
            }
            return next;
          });

          if (user?.is_onboarding_complete) {
            const shouldForce =
              !orgIds.length ||
              orgIds.some((orgId) => {
                const summary = summaries[orgId];
                if (!summary) return true;
                const hasDocbook = Boolean(summary.docbook_repo);
                const writerReady = Boolean(
                  summary.writer_app_installed && summary.writer_app_has_access,
                );
                return !hasDocbook || !writerReady;
              });
            setForceOnboarding(shouldForce);
          } else {
            setForceOnboarding(false);
          }
        }
      } catch (error) {
        console.error("Error loading onboarding state", error);
      } finally {
        if (!options?.silent) {
          setRefreshing(false);
        }
        setStateLoaded(true);
      }
    },
    [token, user?.is_onboarding_complete],
  );

  const verifySelectedOrganization = useCallback(
    async (orgId: string) => {
      if (!token || !orgId) {
        setSelectedOrgAppReady(null);
        return;
      }
      if (
        user?.username &&
        orgId.toLowerCase() === user.username.toLowerCase()
      ) {
        setSelectedOrgAppReady(false);
        return;
      }

      setOrgVerificationLoading(true);
      setOrgSelectionError("");
      try {
        const response = await fetch(`${API_BASE}/org/${orgId}/verify-apps`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          setSelectedOrgAppReady(false);
          return;
        }

        const data = await response.json();
        const readerInstalled = data?.reader_app?.installed === true;
        const writerInstalled = data?.writer_app?.installed === true;
        setSelectedOrgAppReady(readerInstalled && writerInstalled);
      } catch (error) {
        console.error("Failed to verify selected organization", error);
        setSelectedOrgAppReady(false);
      } finally {
        setOrgVerificationLoading(false);
      }
    },
    [token, user?.username],
  );

  const handleConnectOrganizationInline = useCallback(async () => {
    if (!token) return;
    if (!orgSelection) {
      setOrgSelectionError("Please select an organization");
      return;
    }
    if (!selectedOrgAppReady) {
      setOrgSelectionError("Install both Reader and Writer GitHub apps first");
      return;
    }

    setOrgConnectLoading(true);
    setOrgSelectionError("");
    try {
      const response = await fetch(`${API_BASE}/webhook/register`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ org_id: orgSelection }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setOrgSelectionError(data.detail || "Failed to connect organization");
        return;
      }

      await loadState();
      setSelectedOrg((prev) => prev || orgSelection);
      setOrgSelection("");
      setSelectedOrgAppReady(null);
    } catch (error) {
      console.error("Failed to connect organization", error);
      setOrgSelectionError("Error connecting organization");
    } finally {
      setOrgConnectLoading(false);
    }
  }, [API_BASE, loadState, orgSelection, selectedOrgAppReady, token]);

  const handleReconnectGitHub = useCallback(() => {
    // Clear auth and redirect to login so user can re-authorize with fresh scopes
    localStorage.removeItem("DocIt_access_token");
    localStorage.removeItem("DocIt_refresh_token");
    localStorage.removeItem("DocIt_user");
    window.location.href = "/login";
  }, []);

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

  const completeOnboarding = useCallback(
    async (mode: "auto" | "manual" = "manual") => {
      if (!token) return;

      if (mode === "manual") {
        setSaving(true);
      }

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
        } else if (mode === "auto") {
          autoCompletionTriggered.current = false;
        }
      } catch (error) {
        console.error("Failed to complete onboarding", error);
        if (mode === "auto") {
          autoCompletionTriggered.current = false;
        }
      } finally {
        if (mode === "manual") {
          setSaving(false);
        }
      }
    },
    [markOnboardingComplete, router, token],
  );

  useEffect(() => {
    loadState();
  }, [loadState]);

  useEffect(() => {
    if (!orgSelection) {
      setSelectedOrgAppReady(null);
      return;
    }
    void verifySelectedOrganization(orgSelection);
  }, [orgSelection, verifySelectedOrganization]);

  useEffect(() => {
    if (!ownerPickerOpen) return;
    const onClickOutside = (event: MouseEvent) => {
      if (!ownerPickerRef.current) return;
      if (!ownerPickerRef.current.contains(event.target as Node)) {
        setOwnerPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
    };
  }, [ownerPickerOpen]);

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
    currentSummary?.writer_app_installed &&
    currentSummary?.writer_app_has_access;
  const docbookRepoName = currentSummary?.docbook_repo?.split("/").pop() ?? "";
  const suggestedDocbookName = `DocIt-docbook-${(selectedOrg || primaryOrg || "").toLowerCase()}`;

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
  const completedSteps = [step1Status, step2Status, step3Status].filter(
    (status) => status === "complete",
  ).length;
  const progressPercent = (completedSteps / 3) * 100;
  const ownerOptions = useMemo(() => {
    const deduped = new Map<string, OrganizationOption>();
    for (const org of availableOrganizations) {
      deduped.set(org.login.toLowerCase(), org);
    }
    if (user?.username) {
      const key = user.username.toLowerCase();
      if (!deduped.has(key)) {
        deduped.set(key, {
          id: user.username,
          login: user.username,
          kind: "personal",
        });
      }
    }
    return Array.from(deduped.values());
  }, [availableOrganizations, user?.username]);
  const personalOwners = useMemo(
    () => ownerOptions.filter((owner) => owner.kind === "personal"),
    [ownerOptions],
  );
  const organizationOwners = useMemo(
    () => ownerOptions.filter((owner) => owner.kind === "organization"),
    [ownerOptions],
  );
  const selectedOwner = useMemo(
    () => ownerOptions.find((owner) => owner.login === orgSelection),
    [orgSelection, ownerOptions],
  );
  const personalSelection = useMemo(() => {
    if (!orgSelection || !user?.username) return false;
    return orgSelection.toLowerCase() === user.username.toLowerCase();
  }, [orgSelection, user?.username]);
  const activeOrgId = selectedOrg || primaryOrg || "";
  const currentLinkStatus = activeOrgId
    ? docbookLinkStatuses[activeOrgId]
    : undefined;

  useEffect(() => {
    if (!canFinish) {
      autoCompletionTriggered.current = false;
    }
  }, [canFinish]);

  const attemptAutoLinkDocbook = useCallback(
    async (orgId: string): Promise<"linked" | "not_found" | "failed"> => {
      if (!token) {
        return "failed";
      }

      const sanitizedOrg = orgId.toLowerCase().replace(/[^a-z0-9-]/g, "");
      const repoName = `DocIt-docbook-${sanitizedOrg}`;

      setDocbookLinkStatuses((prev) => ({
        ...prev,
        [orgId]: { status: "linking" },
      }));

      try {
        const response = await fetch(`${API_BASE}/docbook/link-repo`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            org_id: orgId,
            docbook_repo_name: repoName,
          }),
        });

        if (response.status === 404) {
          setDocbookLinkStatuses((prev) => ({
            ...prev,
            [orgId]: { status: "not_found" },
          }));
          return "not_found";
        }

        if (!response.ok) {
          const detail = (await response.json().catch(() => ({}))) as {
            detail?: string;
          };
          setDocbookLinkStatuses((prev) => ({
            ...prev,
            [orgId]: {
              status: "failed",
              error: detail.detail || "Failed to link docbook repository",
            },
          }));
          return "failed";
        }

        setDocbookLinkStatuses((prev) => ({
          ...prev,
          [orgId]: { status: "linked" },
        }));
        await loadState({ silent: true });
        return "linked";
      } catch (error) {
        setDocbookLinkStatuses((prev) => ({
          ...prev,
          [orgId]: {
            status: "failed",
            error:
              error instanceof Error
                ? error.message
                : "Unexpected error while linking docbook",
          },
        }));
        return "failed";
      }
      return "failed";
    },
    [API_BASE, loadState, token],
  );

  const stopDocbookPolling = useCallback((orgId: string) => {
    const existing = docbookPollRefs.current[orgId];
    if (existing) {
      clearInterval(existing);
      docbookPollRefs.current[orgId] = null;
    }
    docbookPollAttempts.current[orgId] = 0;
  }, []);

  const startDocbookPolling = useCallback(
    (orgId: string) => {
      if (!orgId) return;
      if (docbookPollRefs.current[orgId]) return;

      docbookPollAttempts.current[orgId] = 0;

      const poll = async () => {
        docbookPollAttempts.current[orgId] =
          (docbookPollAttempts.current[orgId] ?? 0) + 1;

        const result = await attemptAutoLinkDocbook(orgId);

        if (result === "linked") {
          stopDocbookPolling(orgId);
          return;
        }

        if (docbookPollAttempts.current[orgId] >= MAX_DOCBOOK_POLL_ATTEMPTS) {
          stopDocbookPolling(orgId);
        }
      };

      void poll();
      docbookPollRefs.current[orgId] = setInterval(() => {
        void poll();
      }, 5000);
    },
    [attemptAutoLinkDocbook, stopDocbookPolling],
  );

  useEffect(() => {
    if (
      !stateLoaded ||
      refreshing ||
      !hasConnectedOrg ||
      hasLinkedDocbook ||
      !activeOrgId
    ) {
      return;
    }

    const status = docbookLinkStatuses[activeOrgId]?.status;
    if (!status || status === "idle") {
      void attemptAutoLinkDocbook(activeOrgId);
    }
  }, [
    activeOrgId,
    attemptAutoLinkDocbook,
    docbookLinkStatuses,
    hasConnectedOrg,
    hasLinkedDocbook,
    refreshing,
    stateLoaded,
  ]);

  useEffect(() => {
    Object.entries(docbookPollRefs.current).forEach(([orgId]) => {
      const status = docbookLinkStatuses[orgId]?.status;
      if (status === "linked" || status === "failed") {
        stopDocbookPolling(orgId);
      }
    });
  }, [docbookLinkStatuses, stopDocbookPolling]);

  useEffect(() => {
    return () => {
      Object.values(docbookPollRefs.current).forEach((intervalId) => {
        if (intervalId) {
          clearInterval(intervalId);
        }
      });
    };
  }, []);

  useEffect(() => {
    if (
      !user?.is_onboarding_complete &&
      canFinish &&
      !refreshing &&
      !saving &&
      !autoCompletionTriggered.current
    ) {
      autoCompletionTriggered.current = true;
      void completeOnboarding("auto");
    }
  }, [
    canFinish,
    completeOnboarding,
    refreshing,
    saving,
    user?.is_onboarding_complete,
  ]);

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

  const handleFinish = useCallback(async () => {
    await completeOnboarding("manual");
  }, [completeOnboarding]);

  if (shouldBypassOnboarding) {
    return null;
  }

  if ((loading || refreshing) && !shouldBypassOnboarding) {
    return (
      <Layout>
        <OnboardingSplash
          messages={ONBOARDING_PROGRESS_MESSAGES}
          activeIndex={progressIndex}
        />
      </Layout>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Layout>
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/80 shadow-[0_30px_100px_rgba(2,6,23,0.7)] backdrop-blur">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.2),transparent_35%),radial-gradient(circle_at_top_left,rgba(168,85,247,0.25),transparent_45%)]" />
          <div className="relative border-b border-white/10 px-6 py-8 sm:px-10 sm:py-10">
            <div className="grid gap-8 lg:grid-cols-[1.35fr_0.65fr] lg:items-end">
              <div className="space-y-5">
                <div className="inline-flex w-fit items-center gap-2 rounded-full border border-purple-300/25 bg-purple-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-purple-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-purple-300" />
                  Welcome to DocIt
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/10 text-3xl shadow-lg shadow-purple-900/20">
                    ⚡
                  </div>
                  <h1 className="text-3xl font-bold leading-tight text-white sm:text-4xl">
                    Let&apos;s get your organization ready in three quick steps
                  </h1>
                </div>
                <p className="max-w-3xl text-base text-slate-300 sm:text-lg">
                  We&apos;ll connect your GitHub organization, link a Docbook
                  repository, and ensure the Writer app has access so you can
                  start generating living documentation immediately.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 shadow-inner shadow-slate-900/80">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                  Setup Progress
                </p>
                <p className="mt-2 text-3xl font-bold text-white">
                  {completedSteps}
                  <span className="text-lg font-medium text-slate-400">/3</span>
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  Milestones completed
                </p>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400 transition-all duration-700"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Progress updates automatically as each step is verified.
                </p>
              </div>
            </div>
          </div>

          <div className="relative space-y-8 px-6 py-8 sm:px-10 sm:py-10">
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 px-5 py-4">
              <div className="flex flex-wrap items-center gap-4 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
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
              <p className="mt-3 text-xs text-slate-500">
                Complete each milestone in sequence for the fastest setup
                experience.
              </p>
            </div>

            <div className="space-y-6">
              <StepCard
                step={1}
                status={step1Status}
                title="Connect your GitHub organization"
                description="Install the GitHub App and register webhooks so DocIt can listen for commits across your repositories."
              >
                <div className="space-y-5">
                  <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 sm:p-5">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                      Connect Organization
                    </p>
                    <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
                      <div className="relative" ref={ownerPickerRef}>
                        <button
                          type="button"
                          onClick={() => setOwnerPickerOpen((prev) => !prev)}
                          disabled={refreshing || orgConnectLoading}
                          className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-700/70 bg-slate-900 px-4 py-3 text-left text-sm text-white transition hover:border-purple-400/50 focus:outline-none focus:ring-2 focus:ring-purple-400/30 disabled:cursor-not-allowed disabled:opacity-60"
                          aria-expanded={ownerPickerOpen}
                          aria-controls={ownerPickerListId}
                        >
                          <span className="flex items-center gap-2 truncate">
                            <Github className="h-4 w-4 shrink-0 text-slate-300" />
                            {selectedOwner ? (
                              <>
                                <span className="truncate">
                                  {selectedOwner.login}
                                </span>
                                {selectedOwner.kind === "personal" && (
                                  <span className="text-xs text-slate-400">
                                    (personal)
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="text-slate-400">
                                {refreshing
                                  ? "Loading owners..."
                                  : "Select account or organization"}
                              </span>
                            )}
                          </span>
                          <ChevronDown
                            className={`h-4 w-4 shrink-0 text-slate-400 transition ${
                              ownerPickerOpen ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {ownerPickerOpen && (
                          <div
                            id={ownerPickerListId}
                            className="absolute z-30 mt-2 max-h-64 w-full overflow-auto rounded-xl border border-white/10 bg-slate-950 p-2 shadow-2xl shadow-black/40"
                            role="listbox"
                          >
                            {personalOwners.length > 0 && (
                              <div className="mb-2">
                                <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                                  Personal
                                </p>
                                {personalOwners.map((owner) => (
                                  <button
                                    key={owner.id}
                                    type="button"
                                    onClick={() => {
                                      setOrgSelection(owner.login);
                                      setOrgSelectionError("");
                                      setOwnerPickerOpen(false);
                                    }}
                                    className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-2 text-left text-sm text-slate-200 transition hover:bg-white/10"
                                  >
                                    <span className="flex items-center gap-2">
                                      <UserCircle2 className="h-4 w-4 text-slate-300" />
                                      {owner.login}
                                    </span>
                                    {orgSelection === owner.login && (
                                      <Check className="h-4 w-4 text-blue-300" />
                                    )}
                                  </button>
                                ))}
                              </div>
                            )}
                            {organizationOwners.length > 0 && (
                              <div>
                                <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                                  Organizations
                                </p>
                                {organizationOwners.map((owner) => (
                                  <button
                                    key={owner.id}
                                    type="button"
                                    onClick={() => {
                                      setOrgSelection(owner.login);
                                      setOrgSelectionError("");
                                      setOwnerPickerOpen(false);
                                    }}
                                    className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-2 text-left text-sm text-slate-200 transition hover:bg-white/10"
                                  >
                                    <span className="flex items-center gap-2">
                                      <Github className="h-4 w-4 text-slate-300" />
                                      {owner.login}
                                    </span>
                                    {orgSelection === owner.login && (
                                      <Check className="h-4 w-4 text-blue-300" />
                                    )}
                                  </button>
                                ))}
                              </div>
                            )}
                            {!refreshing && ownerOptions.length === 0 && (
                              <div className="px-2 py-2">
                                <p className="text-xs text-slate-400 mb-2">
                                  No organizations found.
                                </p>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleReconnectGitHub();
                                  }}
                                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-blue-300 transition hover:bg-blue-500/10"
                                >
                                  <RefreshCw className="h-3.5 w-3.5" />
                                  Reconnect GitHub to fix permissions
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={handleConnectOrganizationInline}
                        disabled={
                          refreshing ||
                          orgConnectLoading ||
                          !orgSelection ||
                          personalSelection ||
                          selectedOrgAppReady !== true
                        }
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 via-indigo-500 to-blue-500 px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {orgConnectLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            Connect
                            <ArrowRight size={15} />
                          </>
                        )}
                      </button>
                    </div>

                    <div className="mt-3 min-h-5 text-xs">
                      {orgVerificationLoading ? (
                        <p className="flex items-center gap-2 text-blue-300">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Verifying Reader and Writer app installation...
                        </p>
                      ) : personalSelection ? (
                        <p className="text-amber-300">
                          Personal owner selected. Use an organization to
                          connect apps and webhooks.
                        </p>
                      ) : orgSelection ? (
                        selectedOrgAppReady ? (
                          <p className="text-emerald-300">
                            Apps installed. Ready to connect.
                          </p>
                        ) : (
                          <p className="text-amber-300">
                            Install Reader and Writer apps for this organization
                            first.
                          </p>
                        )
                      ) : (
                        <p className="text-slate-500">
                          Select an organization to verify app access.
                        </p>
                      )}
                    </div>

                    {orgSelectionError && (
                      <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>{orgSelectionError}</span>
                      </div>
                    )}

                    {orgFetchError && (
                      <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>{orgFetchError}</span>
                      </div>
                    )}

                    {!refreshing && organizationOwners.length === 0 && (
                      <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                        <p className="text-sm font-medium text-amber-200 mb-1">
                          Only your personal account is visible
                        </p>
                        <p className="text-xs text-slate-400 mb-3">
                          Your GitHub connection may be missing the{" "}
                          <code className="text-amber-300 bg-amber-500/10 px-1 rounded">
                            read:org
                          </code>{" "}
                          permission. This happens when the OAuth token was
                          issued before the app requested organization access.
                        </p>
                        <button
                          onClick={handleReconnectGitHub}
                          className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-700"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          Reconnect GitHub
                        </button>
                        <p className="mt-2 text-[10px] text-slate-500">
                          After clicking, you&apos;ll be asked to authorize
                          DocIt again. Make sure to grant the organization
                          access permission.
                        </p>
                      </div>
                    )}
                  </div>

                  {hasConnectedOrg && (
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm text-slate-300">
                        {orgs.length === 1
                          ? "1 organization connected"
                          : `${orgs.length} organizations connected`}
                      </p>
                      <p className="text-xs text-slate-500">
                        Select one organization below to continue setup.
                      </p>
                    </div>
                  )}

                  {hasConnectedOrg ? (
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
                                <p className="text-xs uppercase tracking-wide text-slate-400">
                                  Organization
                                </p>
                                <p className="text-base font-semibold text-white">
                                  {orgId}
                                </p>
                              </div>
                              {isActive && (
                                <span className="rounded-full bg-purple-500/20 px-3 py-1 text-xs font-semibold text-purple-200">
                                  Selected
                                </span>
                              )}
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <StatusPill
                                label="Reader App"
                                active={summary?.reader_app_installed}
                              />
                              <StatusPill
                                label="Writer App"
                                active={summary?.writer_app_installed}
                              />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      No organizations connected yet. Connect one to unlock step
                      2.
                    </div>
                  )}
                </div>
              </StepCard>

              <StepCard
                step={2}
                status={step2Status}
                title="Create & link your docbook repository"
                description="A dedicated private repository stores the living documentation generated by DocIt."
              >
                {hasConnectedOrg ? (
                  hasLinkedDocbook ? (
                    <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5 text-sm text-slate-200">
                      <div className="flex items-center gap-2 text-emerald-300 text-sm font-semibold">
                        <CheckCircle className="h-5 w-5" />
                        Docbook repository linked
                      </div>
                      <p className="mt-3 text-base text-white">
                        {currentSummary?.docbook_repo}
                      </p>
                      <p className="mt-2 text-slate-400">
                        You can relink or change this docbook anytime from the
                        repository settings.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {currentLinkStatus?.status === "linking" ||
                      currentLinkStatus?.status === "idle" ? (
                        <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-5 text-sm text-blue-100/90 flex items-center gap-3">
                          <Loader2 className="h-5 w-5 animate-spin text-blue-200" />
                          <span>
                            Checking your GitHub organization for an existing
                            docbook repository and linking it automatically...
                          </span>
                        </div>
                      ) : null}

                      {currentLinkStatus?.status === "failed" ? (
                        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-5 text-sm text-red-100 space-y-3">
                          <p className="font-semibold">
                            Failed to verify docbook repository automatically.
                          </p>
                          <p>
                            {currentLinkStatus.error ||
                              "Please try again or link manually."}
                          </p>
                          <div className="flex flex-wrap items-center gap-3">
                            <button
                              onClick={() =>
                                attemptAutoLinkDocbook(activeOrgId)
                              }
                              className="inline-flex items-center gap-2 rounded-full bg-red-500/80 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-500"
                            >
                              Retry automatic link
                            </button>
                            <button
                              onClick={() => setShowDocbookModal(true)}
                              className="inline-flex items-center gap-2 rounded-full border border-slate-600/60 bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:border-red-400/60 hover:bg-slate-900/80"
                            >
                              Link manually
                            </button>
                          </div>
                        </div>
                      ) : null}

                      {currentLinkStatus?.status === "not_found" ? (
                        <div className="space-y-5">
                          <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-5 text-left">
                            <p className="text-sm font-semibold text-blue-200">
                              Manual setup required
                            </p>
                            <p className="mt-2 text-sm text-blue-100/90">
                              Create a private repository named
                              <code className="mx-2 rounded bg-blue-500/20 px-2 py-1 font-mono text-xs text-blue-50">
                                {suggestedDocbookName}
                              </code>
                              inside your organization, then link it to DocIt.
                            </p>
                            <p className="mt-2 text-xs text-blue-200/80">
                              Tip: include a README so the repository is
                              initialized properly.
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center gap-3">
                            <button
                              onClick={() => {
                                if (!activeOrgId) return;
                                startDocbookPolling(activeOrgId);
                                const url = `https://github.com/new?name=${suggestedDocbookName}&private=true&description=DocIt%20Docbook%20Repository`;
                                window.open(
                                  url,
                                  "_blank",
                                  "noopener,noreferrer",
                                );
                              }}
                              disabled={
                                docbookLinkStatuses[activeOrgId]?.status ===
                                "linking"
                              }
                              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-500 via-cyan-500 to-teal-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-70"
                            >
                              Create on GitHub
                              <ArrowRight size={16} />
                            </button>
                            <button
                              onClick={() => setShowDocbookModal(true)}
                              className="inline-flex items-center gap-2 rounded-full border border-slate-600/60 bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:border-blue-400/60 hover:bg-slate-900/80"
                            >
                              Link manually
                            </button>
                            <button
                              onClick={() => {
                                if (!activeOrgId) return;
                                startDocbookPolling(activeOrgId);
                              }}
                              className="inline-flex items-center gap-2 rounded-full border border-blue-400/60 bg-slate-900 px-4 py-2 text-xs font-semibold text-blue-100 transition hover:border-blue-300/80 hover:bg-slate-900/70"
                            >
                              Refresh status
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )
                ) : (
                  <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 text-center text-amber-100">
                    Connect an organization first to unlock docbook
                    configuration.
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
                          Documentation updates will sync automatically whenever
                          we generate docs.
                        </p>
                      </div>
                      <CheckCircle className="h-6 w-6 text-emerald-300" />
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-100">
                        <p className="font-semibold mb-2">
                          Grant access to your docbook repository
                        </p>
                        <p>
                          Install the Writer app from GitHub and grant access
                          only to
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
                                process.env.NEXT_PUBLIC_BACKEND_URL ||
                                "http://localhost:8000";
                              const response = await fetch(
                                `${backendUrl}/auth/install-writer-app`,
                              );
                              if (!response.ok) {
                                throw new Error("Failed to get Writer app URL");
                              }
                              const data = await response.json();
                              window.open(data.url, "_blank");
                            } catch (error) {
                              console.error(
                                "Failed to install Writer App:",
                                error,
                              );
                              stopWriterPolling();
                              alert(
                                "Failed to install Writer App. Please try again.",
                              );
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

            <div className="pt-1">
              <button
                onClick={handleFinish}
                disabled={!canFinish || saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-500 px-6 py-4 text-lg font-semibold text-white shadow-xl shadow-cyan-900/20 transition hover:shadow-2xl hover:shadow-cyan-900/30 disabled:cursor-not-allowed disabled:opacity-60"
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

      {showDocbookModal && currentSummary && (
        <DocbookSetupModal
          isOpen={showDocbookModal}
          onClose={() => setShowDocbookModal(false)}
          orgId={currentSummary.org}
          accessToken={token}
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
      ? "bg-blue-500/20 border-blue-400/60 text-blue-200 shadow-md shadow-blue-900/30"
      : "bg-slate-800/70 border-slate-700/60 text-slate-400";

  const cardBorder = isComplete
    ? "border-emerald-500/35"
    : isCurrent
      ? "border-purple-400/45"
      : "border-slate-700/60";
  const cardBackground = isCurrent
    ? "bg-gradient-to-br from-purple-500/10 via-indigo-500/5 to-transparent"
    : "bg-slate-900/50";

  return (
    <section className="space-y-3">
      <header className="flex items-start gap-3">
        <div
          className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition ${badgeClasses}`}
        >
          {isComplete ? <CheckCircle className="h-5 w-5" /> : step}
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-white sm:text-xl">
            {title}
          </h2>
          <p className="text-sm text-slate-300/80 sm:text-[15px]">
            {description}
          </p>
        </div>
      </header>

      <div
        className={`rounded-2xl border ${cardBorder} ${cardBackground} p-5 shadow-lg shadow-black/10 transition sm:p-6`}
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
