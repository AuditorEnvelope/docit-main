"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Layout } from "@/components/Layout";
import PendingReviewsTab from "@/components/PendingReviewsTab";
import { useAuth } from "@/contexts/AuthContext";
import { usePendingReviews } from "@/hooks/usePendingReviews";
import { Building2, ChevronLeft, Loader2, TriangleAlert } from "lucide-react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function PendingReviewsPage() {
  const router = useRouter();
  const { user, loading, isAuthenticated, token } = useAuth();

  const [connectedOrgs, setConnectedOrgs] = useState<string[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const reviewApiBase = useMemo(() => {
    const normalized = BACKEND_URL.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(normalized);
    return hasApiSuffix ? normalized : `${normalized}/api/v1`;
  }, []);

  const reviewsDisabled = !selectedOrg || !token;

  const {
    reviews,
    isLoading: pendingReviewsLoading,
    error: pendingReviewsError,
    count: pendingCount,
    reload: reloadPendingReviews,
  } = usePendingReviews({
    orgId: reviewsDisabled ? null : selectedOrg,
    token: token ?? null,
    backendUrl: reviewApiBase,
    disabled: reviewsDisabled,
  });

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    if (!token) {
      setConnectedOrgs([]);
      setSelectedOrg("");
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
        setErrorMessage(
          error instanceof Error ? error.message : "Unable to load organizations"
        );
      } finally {
        setLoadingOrgs(false);
      }
    };

    fetchOrganizations();
  }, [token]);

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
        </div>
      </Layout>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900">
        <div className="container mx-auto px-4 py-10 space-y-10">
          <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-violet-200">
                <Building2 className="w-3 h-3" />
                Documentation Review Desk
              </div>
              <h1 className="text-3xl font-bold text-white">Pending Reviews</h1>
              <p className="max-w-2xl text-sm text-slate-300">
                Track and approve documentation updates staged for your organizations. Select an org to dive into the review queue, compare diffs, and merge once everything looks good.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-300 hover:bg-slate-900 transition"
              >
                <ChevronLeft className="w-3 h-3" /> Back to dashboard
              </Link>
            </div>
          </header>

          <section className="rounded-3xl border border-slate-800/60 bg-slate-950/60 p-6">
            <div className="grid gap-6 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-5 py-6">
                <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
                  Pending reviews
                </p>
                <p className="mt-2 text-4xl font-semibold text-white">
                  {reviewsDisabled ? (
                    "—"
                  ) : pendingReviewsLoading ? (
                    <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
                  ) : (
                    pendingCount
                  )}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  {reviewsDisabled
                    ? "Select an organization to view its pending documentation reviews."
                    : "Awaiting approval across the selected organization"}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-5 py-6">
                <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
                  Active organizations
                </p>
                <p className="mt-2 text-4xl font-semibold text-white">
                  {connectedOrgs.length}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Linked with docbook repositories
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-5 py-6">
                <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
                  Reviewer
                </p>
                <p className="mt-2 text-lg font-semibold text-white">
                  {user.name || user.username || "Your team"}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  {user.email || "Signed in via GitHub"}
                </p>
              </div>
            </div>
          </section>

          <section className="space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="space-y-1">
                <h2 className="text-xl font-semibold text-white">Review queues</h2>
                <p className="text-sm text-slate-400">
                  Switch organizations to focus on one docbook queue at a time.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
                {connectedOrgs.length > 0 && (
                  <select
                    value={selectedOrg}
                    onChange={(event) => setSelectedOrg(event.target.value)}
                    className="min-w-[220px] rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    {connectedOrgs.map((org) => (
                      <option key={org} value={org}>
                        {org}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {loadingOrgs ? (
              <div className="flex items-center gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/60 px-6 py-5 text-slate-300">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Loading organizations…</span>
              </div>
            ) : errorMessage ? (
              <div className="flex items-center gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 px-6 py-5 text-red-200">
                <TriangleAlert className="h-5 w-5" />
                <span>{errorMessage}</span>
              </div>
            ) : !connectedOrgs.length ? (
              <div className="rounded-3xl border border-slate-800/60 bg-slate-900/60 px-6 py-10 text-center text-slate-300 space-y-3">
                <TriangleAlert className="w-6 h-6 mx-auto text-violet-400" />
                <h3 className="text-lg font-semibold text-white">No organizations connected</h3>
                <p className="text-sm text-slate-400">
                  Install the GitHub apps for your organizations and link their docbook repositories from the dashboard to start reviewing documentation.
                </p>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-full border border-violet-500/40 bg-violet-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-violet-200 hover:bg-violet-500/20 transition"
                >
                  Go to dashboard
                </Link>
              </div>
            ) : !selectedOrg ? (
              <div className="flex items-center gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/60 px-6 py-5 text-slate-300">
                <TriangleAlert className="h-5 w-5 text-violet-400" />
                <span>Select an organization to view its review queue.</span>
              </div>
            ) : !token ? (
              <div className="flex items-center gap-3 rounded-2xl border border-slate-800/60 bg-slate-900/60 px-6 py-5 text-slate-300">
                <TriangleAlert className="h-5 w-5 text-violet-400" />
                <span>Sign in again to refresh your session before reviewing documentation.</span>
              </div>
            ) : (
              <PendingReviewsTab
                orgId={selectedOrg}
                token={token}
                backendUrl={reviewApiBase}
                onReload={reloadPendingReviews}
                reviewsOverride={reviews}
                isLoadingOverride={pendingReviewsLoading}
                errorOverride={pendingReviewsError}
              />
            )}
          </section>
        </div>
      </div>
    </Layout>
  );
}
