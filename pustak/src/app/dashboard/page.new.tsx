"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import {
  BookOpen,
  Calendar,
  FileText,
  GitBranch,
  Github,
  Loader2,
  LogOut,
  Settings,
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
        setSelectedOrg((current) => (current && orgs.includes(current) ? current : orgs[0] || ""));
      } catch (error) {
        console.error("Error fetching organizations", error);
        setConnectedOrgs([]);
        setSelectedOrg("");
      } finally {
        setLoadingOrgs(false);
      }
    };

    fetchOrganizations();
  }, [token]);

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

  const totalPendingReviews = useMemo(
    () =>
      repositories.reduce(
        (total, repo) => total + (repo.pending_reviews || 0),
        0
      ),
    [repositories]
  );

  const documentedCount = useMemo(
    () =>
      repositories.filter((repo) => Boolean(repo.last_documented_at)).length,
    [repositories]
  );

  const formatPersona = (persona?: string | null) => {
    if (!persona) return "internal";
    return persona.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
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
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="container mx-auto px-4 py-12 space-y-8">
          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
              <div className="flex items-start gap-4">
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name || user.username || "User avatar"}
                    className="w-20 h-20 rounded-full border-4 border-blue-500"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-blue-500 flex items-center justify-center text-white text-2xl font-bold">
                    {(user.name || user.username || "U")[0].toUpperCase()}
                  </div>
                )}
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                    {user.name || user.username || "User"}
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400">
                    {user.email || "No email provided"}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                      <Settings className="w-3 h-3" />
                      {user.plan.toUpperCase()} PLAN
                    </span>
                    {user.username && (
                      <a
                        href={`https://github.com/${user.username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 transition"
                      >
                        <Github className="w-3 h-3" />@{user.username}
                      </a>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 self-start lg:self-auto">
                <button
                  onClick={() => router.push("/onboarding")}
                  className="px-4 py-2 text-sm font-semibold text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-700 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/40 transition"
                >
                  Review onboarding
                </button>
                <button
                  onClick={logout}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 transition flex items-center gap-2"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-300" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Repositories
                </h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {loadingRepos ? (
                  <Loader2 className="w-7 h-7 animate-spin" />
                ) : (
                  repositories.length
                )}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Connected via Reader App
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Documented
                </h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {documentedCount}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Repositories with generated docs
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Pending Reviews
                </h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {totalPendingReviews}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Awaiting approval across docs
              </p>
            </div>
          </section>

          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700">
            <div className="border-b border-gray-200 dark:border-gray-700 px-8 py-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Repository Overview
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedOrg
                    ? `Showing repositories that Pustak can access in ${selectedOrg}`
                    : "Connect an organization to start managing repositories."}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
                <div className="relative flex-1 min-w-[200px]">
                  <input
                    type="text"
                    placeholder="Search repositories..."
                    value={repoSearchQuery}
                    onChange={(event) => setRepoSearchQuery(event.target.value)}
                    className="w-full pl-4 pr-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={!repositories.length}
                  />
                </div>

                {connectedOrgs.length > 0 && (
                  <select
                    value={selectedOrg}
                    onChange={(event) => setSelectedOrg(event.target.value)}
                    className="pl-3 pr-8 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
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

            <div className="px-8 py-6">
              {loadingOrgs ? (
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Loading organizations…</span>
                </div>
              ) : !connectedOrgs.length ? (
                <div className="text-center py-12 text-gray-600 dark:text-gray-300 space-y-4">
                  <p className="text-lg font-semibold">
                    You haven&apos;t connected any organizations yet.
                  </p>
                  <p className="text-sm max-w-2xl mx-auto">
                    Head over to the onboarding flow to install the GitHub apps, link your docbook repository, and start documenting your codebase.
                  </p>
                  <button
                    onClick={() => router.push("/onboarding")}
                    className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold shadow-lg hover:shadow-xl transition"
                  >
                    Launch onboarding
                  </button>
                </div>
              ) : loadingRepos ? (
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Loading repositories…</span>
                </div>
              ) : errorMessage ? (
                <div className="rounded-xl border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 p-6 text-sm text-red-700 dark:text-red-300">
                  {errorMessage}
                </div>
              ) : !filteredRepositories.length ? (
                <div className="text-center py-12 text-gray-600 dark:text-gray-300">
                  <p className="text-lg font-semibold">No repositories found</p>
                  <p className="text-sm">
                    Adjust your search or update permissions in GitHub to include more repositories.
                  </p>
                </div>
              ) : (
                <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {filteredRepositories.map((repo) => {
                    const fullName = repo.full_name || repo.name || "";
                    const displayName = repo.name || fullName.split("/").pop() || fullName;
                    const trackedBranch =
                      repo.tracked_branch ||
                      repo.docbook_tracked_branch ||
                      repo.default_branch ||
                      "main";
                    const pendingReviews = repo.pending_reviews || 0;

                    return (
                      <div
                        key={fullName}
                        className="border border-gray-200 dark:border-gray-700 rounded-2xl p-6 bg-white dark:bg-gray-900/60 shadow-sm hover:shadow-lg transition-shadow"
                      >
                        <div className="flex items-start justify-between gap-2 mb-4">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                              {displayName}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {fullName}
                            </p>
                          </div>
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-200">
                            <GitBranch className="w-3 h-3" />
                            {trackedBranch}
                          </span>
                        </div>

                        {repo.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-3">
                            {repo.description}
                          </p>
                        )}

                        <div className="space-y-3 text-sm text-gray-600 dark:text-gray-300 mb-6">
                          <div className="flex items-center justify-between">
                            <span className="text-gray-500 dark:text-gray-400">
                              Persona
                            </span>
                            <span className="font-medium text-gray-900 dark:text-white">
                              {formatPersona(repo.doc_persona)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-gray-500 dark:text-gray-400">
                              Last documented
                            </span>
                            <span className="font-medium text-gray-900 dark:text-white">
                              {formatDateTime(repo.last_documented_at)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-gray-500 dark:text-gray-400">
                              Pending reviews
                            </span>
                            <span className="font-medium text-gray-900 dark:text-white">
                              {pendingReviews}
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <Link
                            href={`/repo/${fullName}`}
                            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition"
                          >
                            <BookOpen className="w-4 h-4" />
                            View docs
                          </Link>
                          <button
                            onClick={() => router.push(`/repo/settings/${fullName}`)}
                            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                          >
                            <Settings className="w-4 h-4" />
                            Settings
                          </button>
                          {repo.html_url && (
                            <a
                              href={repo.html_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
                            >
                              <Github className="w-4 h-4" />
                              Code
                            </a>
                          )}
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
