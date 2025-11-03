"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import ConnectOrganizationModal from "@/components/ConnectOrganizationModal";
import DocbookSetupModal from "@/components/DocbookSetupModal";
import PendingReviewsTab from "@/components/PendingReviewsTab";
import {
  Loader2,
  Github,
  BookOpen,
  Zap,
  Settings,
  LogOut,
  Crown,
  CheckCircle,
  Link2,
} from "lucide-react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout, isAuthenticated, token } = useAuth();
  const [repositories, setRepositories] = useState<any[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [generatingDocs, setGeneratingDocs] = useState(false);
  const [showOrgModal, setShowOrgModal] = useState(false);
  const [connectedOrgs, setConnectedOrgs] = useState<string[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [showDocbookModal, setShowDocbookModal] = useState(false);
  const [selectedOrgForDocbook, setSelectedOrgForDocbook] = useState<string>("");
  const [linkedDocbooks, setLinkedDocbooks] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<"getting-started" | "reviews">("getting-started");
  const [selectedOrgForReviews, setSelectedOrgForReviews] = useState<string>("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  // Fetch repositories
  useEffect(() => {
    const fetchRepositories = async () => {
      if (!token) return;

      setLoadingRepos(true);
      try {
        const response = await fetch(`${BACKEND_URL}/auth/repositories`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setRepositories(data.repositories || []);
          console.log(
            `✅ Loaded ${data.repositories?.length || 0} repositories`
          );
        } else {
          console.error("Failed to fetch repositories");
        }
      } catch (error) {
        console.error("Error fetching repositories:", error);
      } finally {
        setLoadingRepos(false);
      }
    };

    fetchRepositories();
  }, [token, user?.id]);

  // Fetch connected organizations
  useEffect(() => {
    const fetchConnectedOrgs = async () => {
      if (!token) return;
      setLoadingOrgs(true);
      try {
        const response = await fetch(`${BACKEND_URL}/auth/user-organizations`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (response.ok) {
          const data = await response.json();
          const orgs = data.organizations?.map((org: any) => org.login) || [];
          setConnectedOrgs(orgs);
        }
      } catch (error) {
        console.error("Error fetching connected orgs:", error);
      } finally {
        setLoadingOrgs(false);
      }
    };
    fetchConnectedOrgs();
  }, [token]);

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

  const getPlanBadge = (plan: string) => {
    const badges = {
      free: {
        color: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
        icon: null,
      },
      pro: {
        color:
          "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
        icon: <Zap className="w-3 h-3" />,
      },
      team: {
        color:
          "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
        icon: <Crown className="w-3 h-3" />,
      },
      enterprise: {
        color: "bg-gradient-to-r from-yellow-400 to-orange-500 text-white",
        icon: <Crown className="w-3 h-3" />,
      },
    };
    return badges[plan as keyof typeof badges] || badges.free;
  };

  const planBadge = getPlanBadge(user.plan);

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="container mx-auto px-4 py-12">
          {/* Header */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 mb-8 border border-gray-200 dark:border-gray-700">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                {/* Avatar */}
                {user.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.name || user.username || "User"}
                    className="w-20 h-20 rounded-full border-4 border-blue-500"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-blue-500 flex items-center justify-center text-white text-2xl font-bold">
                    {(user.name || user.username || "U")[0].toUpperCase()}
                  </div>
                )}

                {/* User Info */}
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                    {user.name || user.username || "User"}
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400 mb-3">
                    {user.email || "No email provided"}
                  </p>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${planBadge.color}`}
                    >
                      {planBadge.icon}
                      {user.plan.toUpperCase()} PLAN
                    </span>
                    <a
                      href={`https://github.com/${user.username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    >
                      <Github className="w-3 h-3" />@{user.username}
                    </a>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <button
                onClick={logout}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Repositories
                </h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {loadingRepos ? (
                  <Loader2 className="w-8 h-8 animate-spin inline" />
                ) : (
                  repositories.length
                )}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {repositories.length === 0
                  ? "No repos connected yet"
                  : `${repositories.length} repositories available`}
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  API Calls
                </h3>
              </div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                0
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                This month
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                  <Settings className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Status
                </h3>
              </div>
              <p className="text-3xl font-bold text-green-600 dark:text-green-400">
                Active
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Account is active
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700 mb-8">
            <div className="flex gap-4 mb-6 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setActiveTab("getting-started")}
                className={`px-4 py-3 font-semibold border-b-2 transition-colors ${
                  activeTab === "getting-started"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-300"
                }`}
              >
                🚀 Getting Started
              </button>
              <button
                onClick={() => {
                  setActiveTab("reviews");
                  if (connectedOrgs.length > 0 && !selectedOrgForReviews) {
                    setSelectedOrgForReviews(connectedOrgs[0]);
                  }
                }}
                className={`px-4 py-3 font-semibold border-b-2 transition-colors ${
                  activeTab === "reviews"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-300"
                }`}
              >
                📋 Pending Reviews
              </button>
            </div>

            {activeTab === "reviews" && connectedOrgs.length > 0 && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Select Organization
                </label>
                <select
                  value={selectedOrgForReviews}
                  onChange={(e) => setSelectedOrgForReviews(e.target.value)}
                  className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  {connectedOrgs.map((org) => (
                    <option key={org} value={org}>
                      {org}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {activeTab === "reviews" && selectedOrgForReviews && (
              <PendingReviewsTab
                orgId={selectedOrgForReviews}
                token={token || ""}
                backendUrl={BACKEND_URL}
              />
            )}

            {activeTab === "reviews" && connectedOrgs.length === 0 && (
              <div className="text-center py-8">
                <p className="text-gray-600 dark:text-gray-400">
                  Connect an organization first to see pending reviews
                </p>
              </div>
            )}
          </div>

          {/* Getting Started */}
          {activeTab === "getting-started" && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
              🚀 Getting Started
            </h2>

            <div className="space-y-4">
              {/* Step 1: Connect Repositories - Show as active only if no repositories */}
              <div
                className={`flex items-start gap-4 p-4 ${
                  repositories.length === 0
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : "bg-gray-50 dark:bg-gray-700/20"
                } rounded-xl ${repositories.length > 0 ? "opacity-70" : ""}`}
              >
                <div
                  className={`w-8 h-8 ${
                    repositories.length === 0 ? "bg-blue-500" : "bg-gray-400"
                  } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                >
                  1
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    Connect Your Repositories
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    Grant access to your GitHub repositories to start generating
                    AI-powered documentation
                  </p>
                  {repositories.length === 0 && (
                    <button
                      onClick={async () => {
                        try {
                          // Get OAuth URL from backend
                          const backendUrl =
                            process.env.NEXT_PUBLIC_BACKEND_URL ||
                            "http://localhost:8000";
                          const redirectUri = `${window.location.origin}/auth/callback`;

                          const response = await fetch(
                            `${backendUrl}/auth/github?redirect_uri=${encodeURIComponent(
                              redirectUri
                            )}&scope=${encodeURIComponent(
                              "user:email read:org repo"
                            )}`
                          );

                          if (!response.ok) {
                            throw new Error("Failed to get OAuth URL");
                          }

                          const data = await response.json();

                          // Redirect to GitHub OAuth page
                          window.location.href = data.url;
                        } catch (error) {
                          console.error(
                            "Failed to connect repositories:",
                            error
                          );
                          alert(
                            "Failed to connect repositories. Please try again."
                          );
                        }
                      }}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors text-sm"
                    >
                      Connect Repositories
                    </button>
                  )}
                  {repositories.length > 0 && (
                    <div className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" />
                      Connected {repositories.length} repositories
                    </div>
                  )}
                </div>
              </div>

              {/* Step 1.5: Connect Organization (Multi-Org Support) */}
              <div className={`flex items-start gap-4 p-4 rounded-xl border-2 ${
                connectedOrgs.length > 0
                  ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700"
                  : "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-700"
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold flex-shrink-0 text-white ${
                  connectedOrgs.length > 0 ? "bg-green-500" : "bg-purple-500"
                }`}>
                  {connectedOrgs.length > 0 ? "✓" : "⚡"}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    🔗 Connect Organization (Multi-Org Support)
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    {connectedOrgs.length > 0
                      ? `${connectedOrgs.length} organization${connectedOrgs.length !== 1 ? "s" : ""} connected`
                      : "Register additional organizations to enable webhook-based automatic documentation generation"}
                  </p>
                  {connectedOrgs.length > 0 && (
                    <div className="mb-3 text-sm">
                      {connectedOrgs.map((org) => (
                        <div key={org} className="text-green-600 dark:text-green-400 flex items-center gap-1">
                          <CheckCircle className="w-4 h-4" />
                          {org}
                        </div>
                      ))}
                    </div>
                  )}
                  <button
                    onClick={() => setShowOrgModal(true)}
                    className={`px-4 py-2 rounded-lg font-semibold transition-colors text-sm flex items-center gap-2 ${
                      connectedOrgs.length > 0
                        ? "bg-green-600 text-white hover:bg-green-700"
                        : "bg-purple-600 text-white hover:bg-purple-700"
                    }`}
                  >
                    <Link2 className="w-4 h-4" />
                    {connectedOrgs.length > 0 ? "Add More Organizations" : "Connect Organization"}
                  </button>
                </div>
              </div>

              {/* Step 2: Setup Docbook Repository */}
              <div className={`flex items-start gap-4 p-4 ${
                connectedOrgs.length > 0
                  ? "bg-orange-50 dark:bg-orange-900/20"
                  : "bg-gray-50 dark:bg-gray-700/50"
              } rounded-xl ${connectedOrgs.length === 0 ? "opacity-50" : ""}`}>
                <div
                  className={`w-8 h-8 ${
                    connectedOrgs.length > 0 ? "bg-orange-500" : "bg-gray-400"
                  } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                >
                  2
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    📚 Setup Docbook Repository
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    Create a dedicated repository for AI-generated documentation
                  </p>
                  {connectedOrgs.length > 0 && (
                    <div className="space-y-2">
                      {connectedOrgs.map((org) => (
                        <button
                          key={org}
                          onClick={() => {
                            setSelectedOrgForDocbook(org);
                            setShowDocbookModal(true);
                          }}
                          className="w-full text-left px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors flex items-center justify-between"
                        >
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {org}
                          </span>
                          {linkedDocbooks[org] ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <span className="text-xs text-gray-500 dark:text-gray-400">Setup</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Step 3: Select Repositories - Show as active if repositories exist */}
              <div
                className={`flex items-start gap-4 p-4 ${
                  repositories.length > 0
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : "bg-gray-50 dark:bg-gray-700/50"
                } rounded-xl ${repositories.length === 0 ? "opacity-50" : ""}`}
              >
                <div
                  className={`w-8 h-8 ${
                    repositories.length > 0 ? "bg-blue-500" : "bg-gray-400"
                  } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                >
                  3
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    Select Repositories
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    Choose which repositories you want to document
                  </p>
                  {repositories.length > 0 && (
                    <div className="mt-2">
                      <select
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        value={selectedRepo}
                        onChange={(e) => setSelectedRepo(e.target.value)}
                      >
                        <option value="" disabled>
                          Select a repository
                        </option>
                        {repositories.map((repo: any) => (
                          <option
                            key={repo.id}
                            value={repo.full_name || repo.name}
                          >
                            {repo.full_name || repo.name}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={async () => {
                          if (!selectedRepo) {
                            alert("Please select a repository first");
                            return;
                          }

                          setGeneratingDocs(true);
                          try {
                            const backendUrl =
                              process.env.NEXT_PUBLIC_BACKEND_URL ||
                              "http://localhost:8000";
                            
                            // Use V4 endpoint (publishes to docbook/staging)
                            const response = await fetch(
                              `${backendUrl}/docs/generate-v4?repo_name=${encodeURIComponent(
                                selectedRepo
                              )}`,
                              {
                                method: "POST",
                                headers: {
                                  Authorization: `Bearer ${token}`,
                                },
                              }
                            );

                            if (response.ok) {
                              const data = await response.json();
                              console.log(
                                "✅ Documentation generated and published to staging"
                              );
                              
                              // Show success modal
                              setSuccessMessage(
                                `✅ Documentation published to staging!\n\nYour docs are now in the staging branch. Check your Pustak dashboard to review and approve.`
                              );
                              setShowSuccessModal(true);
                              
                              // Refresh page after modal is closed
                              setTimeout(() => {
                                window.location.reload();
                              }, 2000);
                            } else {
                              const error = await response.json();
                              setSuccessMessage(
                                `❌ Failed to generate documentation: ${error.detail || 'Unknown error'}`
                              );
                              setShowSuccessModal(true);
                            }
                          } catch (error) {
                            console.error(
                              "Error generating documentation:",
                              error
                            );
                            setSuccessMessage(
                              "❌ Failed to generate documentation. Please try again."
                            );
                            setShowSuccessModal(true);
                          } finally {
                            setGeneratingDocs(false);
                          }
                        }}
                        className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        disabled={!selectedRepo || generatingDocs}
                      >
                        {generatingDocs && (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        )}
                        {generatingDocs
                          ? "Generating & Publishing..."
                          : "Generate Documentation"}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 4: AI Generates Docs */}
              <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl opacity-50">
                <div className="w-8 h-8 bg-gray-400 text-white rounded-full flex items-center justify-center font-bold flex-shrink-0">
                  4
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    AI Generates Docs
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Sit back while AI creates comprehensive documentation
                  </p>
                </div>
              </div>
            </div>
          </div>
          )}

          {/* Upgrade CTA (if on free plan) */}
          {user.plan === "free" && (
            <div className="mt-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-xl p-8 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold mb-2">⚡ Upgrade to Pro</h2>
                  <p className="text-blue-100 mb-4">
                    Unlock unlimited repositories, advanced AI features, and
                    priority support
                  </p>
                  <button
                    onClick={() => router.push("/pricing")}
                    className="px-6 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
                  >
                    View Plans
                  </button>
                </div>
                <Crown className="w-24 h-24 opacity-20" />
              </div>
            </div>
          )}
        </div>

        {/* Connect Organization Modal */}
        <ConnectOrganizationModal
          isOpen={showOrgModal}
          onClose={() => setShowOrgModal(false)}
          backendUrl={BACKEND_URL}
          userToken={token || ''}
          onSuccess={() => {
            // Refresh repositories list
            setLoadingRepos(true);
            fetchRepositories();
          }}
        />

        {/* Docbook Setup Modal */}
        <DocbookSetupModal
          isOpen={showDocbookModal}
          onClose={() => setShowDocbookModal(false)}
          orgId={selectedOrgForDocbook}
          onSuccess={(docbookRepo) => {
            setLinkedDocbooks({
              ...linkedDocbooks,
              [selectedOrgForDocbook]: docbookRepo
            });
          }}
        />

        {/* Success Modal */}
        {showSuccessModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-8 border border-gray-200 dark:border-gray-700 animate-in fade-in zoom-in-95 duration-200">
              <div className="text-center">
                {successMessage.includes("❌") ? (
                  <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-3xl">❌</span>
                  </div>
                ) : (
                  <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-3xl">✅</span>
                  </div>
                )}
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                  {successMessage.includes("❌") ? "Error" : "Success!"}
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6 whitespace-pre-line">
                  {successMessage.replace(/✅|❌/g, "").trim()}
                </p>
                <button
                  onClick={() => setShowSuccessModal(false)}
                  className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                >
                  Got it!
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );

  async function fetchRepositories() {
    if (!token) return;

    setLoadingRepos(true);
    try {
      const response = await fetch(`${BACKEND_URL}/auth/repositories`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRepositories(data.repositories || []);
        console.log(`✅ Loaded ${data.repositories?.length || 0} repositories`);
      } else {
        console.error("Failed to fetch repositories");
      }
    } catch (error) {
      console.error("Error fetching repositories:", error);
    } finally {
      setLoadingRepos(false);
    }
  }
}
