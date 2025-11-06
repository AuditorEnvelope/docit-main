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
  Search,
  ChevronDown,
} from "lucide-react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout, isAuthenticated, token } = useAuth();
  const [repositories, setRepositories] = useState<any[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [repoSearchQuery, setRepoSearchQuery] = useState<string>("");
  const [showRepoDropdown, setShowRepoDropdown] = useState(false);
  const [generatingDocs, setGeneratingDocs] = useState(false);
  const [showOrgModal, setShowOrgModal] = useState(false);
  const [connectedOrgs, setConnectedOrgs] = useState<string[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [showDocbookModal, setShowDocbookModal] = useState(false);
  const [selectedOrgForDocbook, setSelectedOrgForDocbook] =
    useState<string>("");
  const [linkedDocbooks, setLinkedDocbooks] = useState<Record<string, string>>(
    {}
  );
  const [activeTab, setActiveTab] = useState<"getting-started" | "reviews">(
    "getting-started"
  );
  const [selectedOrgForReviews, setSelectedOrgForReviews] =
    useState<string>("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [readerAppInstalled, setReaderAppInstalled] = useState(false);
  const [pollingReaderApp, setPollingReaderApp] = useState(false);
  const [docbookRepoName, setDocbookRepoName] = useState<string>("");
  const [docbookRepoExists, setDocbookRepoExists] = useState(false);
  const [pollingDocbookRepo, setPollingDocbookRepo] = useState(false);
  const [docbookLinked, setDocbookLinked] = useState(false);
  const [writerAppInstalled, setWriterAppInstalled] = useState(false);
  const [pollingWriterApp, setPollingWriterApp] = useState(false);
  const [writerAppHasCorrectAccess, setWriterAppHasCorrectAccess] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  // Check Reader App installation status on page load (ONCE)
  useEffect(() => {
    if (!token || !connectedOrgs.length) return;

    const checkReaderAppInstallation = async () => {
      try {
        const org = connectedOrgs[0]; // Check first org

        const response = await fetch(
          `${BACKEND_URL}/api/v1/org/${org}/verify-apps`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.reader_app?.installed) {
            setReaderAppInstalled(true);
          }
        }
      } catch (error) {
        console.error("Error checking Reader App:", error);
      }
    };

    // Check ONCE on page load
    checkReaderAppInstallation();
  }, [token, connectedOrgs]);

  // Poll for Reader App installation after user clicks button
  useEffect(() => {
    if (!pollingReaderApp || !connectedOrgs.length) return;

    const checkReaderAppInstallation = async () => {
      try {
        const org = connectedOrgs[0];

        const response = await fetch(
          `${BACKEND_URL}/api/v1/org/${org}/verify-apps`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.reader_app?.installed) {
            setReaderAppInstalled(true);
            setPollingReaderApp(false); // Stop polling
            console.log("✅ Reader App found!");
          }
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    };

    // Poll every 5 seconds
    const interval = setInterval(checkReaderAppInstallation, 5000);

    // Stop polling after 2 minutes (120 seconds)
    const timeout = setTimeout(() => {
      setPollingReaderApp(false);
      console.log("⏱️ Polling stopped (2 minute timeout)");
    }, 120000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [pollingReaderApp, connectedOrgs, token]);

  // Generate docbook repo name and check if it exists on GitHub (when Reader App is installed)
  useEffect(() => {
    if (!readerAppInstalled || !connectedOrgs.length) return;

    const org = connectedOrgs[0];
    const generatedName = `pustak-docbook-${org}`;
    setDocbookRepoName(generatedName);

    // Check if docbook repo actually exists on GitHub (not in database)
    const checkDocbookRepoOnGitHub = async () => {
      try {
        const backendUrl =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

        console.log(`\n📋 === STEP 2: DOCBOOK REPO CHECK ===`);
        console.log(`📍 Organization: ${org}`);
        console.log(`📝 Generated repo name: ${generatedName}`);

        // Call backend endpoint to check if repo exists on GitHub
        console.log(
          `📡 Calling: ${backendUrl}/docbook/check-github-repo?org_id=${org}&repo_name=${generatedName}`
        );
        const repoCheckResponse = await fetch(
          `${backendUrl}/docbook/check-github-repo?org_id=${org}&repo_name=${generatedName}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        let repoExistsOnGitHub = false;

        if (repoCheckResponse.ok) {
          const data = await repoCheckResponse.json();
          repoExistsOnGitHub = data.exists === true;
          console.log(`📊 GitHub check response:`, data);

          if (repoExistsOnGitHub) {
            console.log(`✅ Docbook repo EXISTS on GitHub: ${generatedName}`);
          } else {
            console.log(
              `❌ Docbook repo NOT FOUND on GitHub: ${generatedName}`
            );
          }
        } else {
          const errorText = await repoCheckResponse.text();
          console.error(
            `❌ Backend error checking repo (${repoCheckResponse.status}):`,
            errorText
          );
          repoExistsOnGitHub = false;
        }

        setDocbookRepoExists(repoExistsOnGitHub);
        console.log(`🔧 Set docbookRepoExists = ${repoExistsOnGitHub}`);

        // Check if it's linked in database
        console.log(
          `\n📡 Calling: ${backendUrl}/docbook/check-exists?org_id=${org}`
        );
        const checkLinkedResponse = await fetch(
          `${backendUrl}/docbook/check-exists?org_id=${org}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        let isLinkedInDatabase = false;
        let linkedRepoFullName = null;

        if (checkLinkedResponse.ok) {
          const data = await checkLinkedResponse.json();
          isLinkedInDatabase = data.exists === true;
          linkedRepoFullName = data.docbook_repo || null;
          console.log(`📊 Database check response:`, data);
          console.log(`🔗 Is linked in database: ${isLinkedInDatabase}`);
          console.log(`📦 Linked repo full name in DB: ${linkedRepoFullName}`);
        } else {
          console.error(
            `❌ Backend error checking database (${checkLinkedResponse.status})`
          );
        }

        // Build expected full name
        const expectedFullName = `${org}/${generatedName}`;
        console.log(`📦 Expected full name: ${expectedFullName}`);

        // ONLY mark as linked if BOTH conditions are true:
        // 1. Repo exists on GitHub
        // 2. It's linked in database with correct full name
        console.log(`\n🔍 DECISION LOGIC:`);
        console.log(`  - Repo exists on GitHub? ${repoExistsOnGitHub}`);
        console.log(`  - Linked in database? ${isLinkedInDatabase}`);
        console.log(
          `  - Linked repo full name matches? ${
            linkedRepoFullName === expectedFullName
          }`
        );

        if (
          repoExistsOnGitHub &&
          isLinkedInDatabase &&
          linkedRepoFullName === expectedFullName
        ) {
          setDocbookLinked(true);
          console.log(
            `✅ RESULT: Docbook repo is PROPERLY LINKED (exists on GitHub + in database with correct full name)`
          );
        } else {
          setDocbookLinked(false);
          console.log(`❌ RESULT: Docbook repo is NOT FULLY LINKED`);

          if (isLinkedInDatabase && !repoExistsOnGitHub) {
            console.warn(
              `⚠️ WARNING: Docbook was linked in database but repo no longer exists on GitHub`
            );
          }
          if (isLinkedInDatabase && linkedRepoFullName !== expectedFullName) {
            console.warn(
              `⚠️ WARNING: Linked repo full name (${linkedRepoFullName}) doesn't match expected (${expectedFullName})`
            );
          }
        }
        console.log(
          `🔧 Set docbookLinked = ${
            repoExistsOnGitHub &&
            isLinkedInDatabase &&
            linkedRepoFullName === expectedFullName
          }`
        );
        console.log(`\n`);
      } catch (error) {
        console.error("❌ Error checking docbook status:", error);
        setDocbookRepoExists(false);
        setDocbookLinked(false);
      }
    };

    checkDocbookRepoOnGitHub();
  }, [readerAppInstalled, connectedOrgs, token]);

  // Check Writer App installation status on page load (ONCE)
  useEffect(() => {
    if (!token || !connectedOrgs.length || !docbookLinked) return;

    const checkWriterAppInstallation = async () => {
      try {
        const org = connectedOrgs[0];

        const response = await fetch(
          `${BACKEND_URL}/api/v1/org/${org}/verify-apps`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.writer_app?.installed) {
            // Check if it has access to the correct docbook repo
            const hasCorrectAccess = await checkWriterAppAccess(org, docbookRepoName);
            setWriterAppInstalled(true);
            setWriterAppHasCorrectAccess(hasCorrectAccess);
          }
        }
      } catch (error) {
        console.error("Error checking Writer App:", error);
      }
    };

    checkWriterAppInstallation();
  }, [token, connectedOrgs, docbookLinked, docbookRepoName]);

  // Helper function to check if Writer App has access to the docbook repo
  const checkWriterAppAccess = async (org: string, docbookRepo: string) => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/v1/org/${org}/verify-writer-app-access?repo=${docbookRepo}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        return data.has_access === true;
      }
      return false;
    } catch (error) {
      console.error("Error checking Writer App access:", error);
      return false;
    }
  };

  // Poll for Writer App installation after user clicks button
  useEffect(() => {
    if (!pollingWriterApp || !connectedOrgs.length || !docbookRepoName) return;

    const checkWriterAppInstallation = async () => {
      try {
        const org = connectedOrgs[0];

        console.log(`⏱️ [POLLING] Checking if Writer App is installed...`);

        const response = await fetch(
          `${BACKEND_URL}/api/v1/org/${org}/verify-apps`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.writer_app?.installed) {
            // Check if it has access to the correct docbook repo
            const hasCorrectAccess = await checkWriterAppAccess(org, docbookRepoName);
            if (hasCorrectAccess) {
              setWriterAppInstalled(true);
              setWriterAppHasCorrectAccess(true);
              setPollingWriterApp(false); // Stop polling
              console.log("✅ Writer App found with correct access!");
            } else {
              console.log(
                "⚠️ Writer App found but doesn't have access to docbook repo"
              );
            }
          }
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    };

    // Poll every 5 seconds
    const interval = setInterval(checkWriterAppInstallation, 5000);

    // Stop polling after 2 minutes (120 seconds)
    const timeout = setTimeout(() => {
      setPollingWriterApp(false);
      console.log("⏱️ Polling stopped (2 minute timeout)");
    }, 120000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [pollingWriterApp, connectedOrgs, token, docbookRepoName]);

  // Poll for docbook repo creation after user clicks button
  useEffect(() => {
    if (!pollingDocbookRepo || !connectedOrgs.length || !docbookRepoName)
      return;

    const checkDocbookRepoExists = async () => {
      try {
        const org = connectedOrgs[0];
        const backendUrl =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

        console.log(
          `⏱️ [POLLING] Checking if docbook repo exists: ${docbookRepoName}`
        );

        // Call backend endpoint to check if repo exists on GitHub
        const repoCheckResponse = await fetch(
          `${backendUrl}/docbook/check-github-repo?org_id=${org}&repo_name=${docbookRepoName}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (repoCheckResponse.ok) {
          const data = await repoCheckResponse.json();
          console.log(`⏱️ [POLLING] Response:`, data);

          if (data.exists === true) {
            // Repo found on GitHub!
            setDocbookRepoExists(true);
            setPollingDocbookRepo(false); // Stop polling
            console.log(
              `✅ [POLLING] Docbook repo FOUND on GitHub! Stopping polling.`
            );
          } else {
            console.log(
              `⏳ [POLLING] Repo not found yet, will check again in 5 seconds...`
            );
          }
        } else {
          console.error(
            `⏱️ [POLLING] Backend error (${repoCheckResponse.status})`
          );
        }
      } catch (error) {
        console.error("❌ [POLLING] Error:", error);
      }
    };

    // Poll every 5 seconds
    const interval = setInterval(checkDocbookRepoExists, 5000);

    // Stop polling after 2 minutes (120 seconds)
    const timeout = setTimeout(() => {
      setPollingDocbookRepo(false);
      console.log("⏱️ Docbook polling stopped (2 minute timeout)");
    }, 120000);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [pollingDocbookRepo, connectedOrgs, token, docbookRepoName]);

  // Fetch repositories that Reader App can access (ONLY if Reader App is installed)
  useEffect(() => {
    const fetchRepositories = async () => {
      // STEP 3: Only fetch repos if Reader App is installed
      if (!token || !connectedOrgs.length || !readerAppInstalled) {
        console.log(
          `⏭️  Skipping repo fetch: token=${!!token}, orgs=${connectedOrgs.length}, readerAppInstalled=${readerAppInstalled}`
        );
        return;
      }

      setLoadingRepos(true);
      try {
        const org = connectedOrgs[0];
        const endpoint = `${BACKEND_URL}/api/v1/org/${org}/reader/repositories`;

        console.log(`\n📚 === STEP 3: FETCHING READER APP REPOSITORIES ===`);
        console.log(`📍 Organization: ${org}`);
        console.log(`📡 Calling: ${endpoint}`);

        const response = await fetch(endpoint, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          const repos = data.repositories || [];

          console.log(`✅ Response received:`, data);
          console.log(`📦 Repositories the Reader App can access:`);
          repos.forEach((repo: any) => {
            console.log(`   - ${repo.full_name}`);
          });
          console.log(`📊 Total: ${repos.length} repositories`);

          setRepositories(repos);
        } else {
          const errorText = await response.text();
          console.error(
            `❌ Failed to fetch repositories (${response.status}):`,
            errorText
          );
          setRepositories([]);
        }
      } catch (error) {
        console.error("❌ Error fetching repositories:", error);
        setRepositories([]);
      } finally {
        setLoadingRepos(false);
      }
    };

    fetchRepositories();
  }, [token, connectedOrgs, readerAppInstalled]);

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
                {/* Step 1: Install Reader App - Show button until Reader App is actually installed */}
                <div
                  className={`flex items-start gap-4 p-4 ${
                    !readerAppInstalled
                      ? "bg-blue-50 dark:bg-blue-900/20"
                      : "bg-green-50 dark:bg-green-900/20"
                  } rounded-xl`}
                >
                  <div
                    className={`w-8 h-8 ${
                      !readerAppInstalled ? "bg-blue-500" : "bg-green-500"
                    } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                  >
                    {!readerAppInstalled ? "1" : "✓"}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      📖 Install Reader App
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Install Pustak Analyser AI to grant read-only access to
                      your source code repositories
                    </p>
                    {!readerAppInstalled ? (
                      <button
                        onClick={async () => {
                          try {
                            const backendUrl =
                              process.env.NEXT_PUBLIC_BACKEND_URL ||
                              "http://localhost:8000";

                            // Get GitHub App installation URL from backend
                            const response = await fetch(
                              `${backendUrl}/auth/install-reader-app`
                            );

                            if (!response.ok) {
                              throw new Error(
                                "Failed to get app installation URL"
                              );
                            }

                            const data = await response.json();

                            // Start polling for app installation
                            setPollingReaderApp(true);

                            // Redirect to GitHub App installation page (opens in new tab)
                            window.open(data.url, "_blank");
                          } catch (error) {
                            console.error(
                              "Failed to install Reader App:",
                              error
                            );
                            alert(
                              "Failed to install Reader App. Please try again."
                            );
                          }
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors text-sm"
                      >
                        Install Reader App
                      </button>
                    ) : (
                      <div className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" />
                        Reader App installed in{" "}
                        {connectedOrgs[0] || "organization"}
                      </div>
                    )}
                    {pollingReaderApp && (
                      <div className="mt-2 text-sm text-blue-600 dark:text-blue-400 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Checking for app installation... (will stop after 2
                        minutes)
                      </div>
                    )}
                  </div>
                </div>

                {/* Step 2: Create & Link Docbook Repository (Two-step process) */}
                <div
                  className={`flex items-start gap-4 p-4 rounded-xl ${
                    readerAppInstalled
                      ? docbookLinked
                        ? "bg-green-50 dark:bg-green-900/20"
                        : "bg-purple-50 dark:bg-purple-900/20"
                      : "bg-gray-50 dark:bg-gray-700/50 opacity-50"
                  }`}
                >
                  <div
                    className={`w-8 h-8 ${
                      readerAppInstalled
                        ? docbookLinked
                          ? "bg-green-500"
                          : "bg-purple-500"
                        : "bg-gray-400"
                    } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                  >
                    {docbookLinked ? "✓" : "2"}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      📑 Create & Link Docbook Repository
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Create a dedicated private repository to store your
                      AI-generated documentation
                    </p>

                    {readerAppInstalled && (
                      <>
                        {/* Step 2a: Create Repo - Show if repo doesn't exist */}
                        {!docbookRepoExists ? (
                          <>
                            <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3 mb-3">
                              <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                                <strong>📝 Step 1: Create Repository</strong>
                              </p>
                              <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
                                Create a new private repository with this name:
                              </p>
                              <code className="bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded text-sm font-mono text-blue-900 dark:text-blue-100">
                                {docbookRepoName}
                              </code>
                            </div>
                            <a
                              href={`https://github.com/new?name=${docbookRepoName}&private=true`}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={() => setPollingDocbookRepo(true)}
                              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors text-sm"
                            >
                              <Github className="w-4 h-4" />
                              Create on GitHub
                            </a>
                            {pollingDocbookRepo && (
                              <div className="mt-2 text-sm text-blue-600 dark:text-blue-400 flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Checking for repo... (will stop after 2 minutes)
                              </div>
                            )}
                          </>
                        ) : !docbookLinked ? (
                          <>
                            {/* Step 2b: Link Repo - Show if repo exists but NOT linked */}
                            <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg p-3 mb-3">
                              <p className="text-sm text-green-800 dark:text-green-200 mb-2 flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" />
                                <strong>✅ Repository Created!</strong>
                              </p>
                              <p className="text-sm text-green-700 dark:text-green-300">
                                Now link it to your organization
                              </p>
                            </div>
                            <button
                              onClick={async () => {
                                try {
                                  const backendUrl =
                                    process.env.NEXT_PUBLIC_BACKEND_URL ||
                                    "http://localhost:8000";

                                  console.log(
                                    `\n🔗 === LINKING DOCBOOK REPO ===`
                                  );
                                  console.log(
                                    `📍 Organization: ${connectedOrgs[0]}`
                                  );
                                  console.log(
                                    `📦 Repo name: ${docbookRepoName}`
                                  );
                                  console.log(
                                    `📡 Calling: POST ${backendUrl}/docbook/link-repo`
                                  );

                                  const response = await fetch(
                                    `${backendUrl}/docbook/link-repo`,
                                    {
                                      method: "POST",
                                      headers: {
                                        "Content-Type": "application/json",
                                        Authorization: `Bearer ${token}`,
                                      },
                                      body: JSON.stringify({
                                        org_id: connectedOrgs[0],
                                        docbook_repo_name: docbookRepoName,
                                      }),
                                    }
                                  );

                                  if (response.ok) {
                                    const data = await response.json();
                                    console.log(`✅ Link response:`, data);
                                    setDocbookLinked(true);
                                    console.log(
                                      `✅ Docbook repo LINKED successfully!`
                                    );
                                    console.log(`🔧 Set docbookLinked = true`);
                                  } else {
                                    const error = await response.json();
                                    console.error(
                                      `❌ Link failed (${response.status}):`,
                                      error
                                    );
                                    alert(`Failed to link: ${error.detail}`);
                                  }
                                } catch (error) {
                                  console.error(
                                    "❌ Error linking repo:",
                                    error
                                  );
                                  alert("Failed to link repository");
                                }
                              }}
                              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors text-sm"
                            >
                              <Link2 className="w-4 h-4" />
                              Link Repository
                            </button>
                          </>
                        ) : (
                          <>
                            {/* Step 2 Complete - Show if repo exists AND linked */}
                            <div className="text-sm text-green-600 dark:text-green-400 flex items-center gap-2">
                              <CheckCircle className="w-4 h-4" />
                              Docbook repository linked: {docbookRepoName}
                            </div>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Step 3: Select Repositories to Document */}
                <div
                  className={`flex items-start gap-4 p-4 rounded-xl ${
                    docbookLinked && repositories.length > 0
                      ? "bg-blue-50 dark:bg-blue-900/20"
                      : "bg-gray-50 dark:bg-gray-700/50 opacity-50"
                  }`}
                >
                  <div
                    className={`w-8 h-8 ${
                      docbookLinked && repositories.length > 0
                        ? "bg-blue-500"
                        : "bg-gray-400"
                    } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                  >
                    3
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      📚 Select Repositories to Document
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Choose which repositories you want to generate
                      documentation for
                    </p>
                    {docbookLinked && repositories.length > 0 && (
                      <>
                        <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-700 rounded-lg p-3 mb-3">
                          <p className="text-sm text-yellow-800 dark:text-yellow-200">
                            <strong>🎯 Free Plan:</strong> You can document 1
                            repository. Upgrade to Pro to document unlimited
                            repositories.
                          </p>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                          Showing {repositories.length} repositories that Reader
                          App can access:
                        </p>

                        {/* Custom Searchable Dropdown */}
                        <div className="relative mb-3">
                          {/* Dropdown Button */}
                          <button
                            onClick={() =>
                              setShowRepoDropdown(!showRepoDropdown)
                            }
                            className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 hover:border-blue-400 dark:hover:border-blue-500 transition-colors"
                          >
                            <span className="flex items-center gap-2">
                              {selectedRepo ? (
                                <>
                                  <BookOpen className="w-4 h-4 text-blue-500" />
                                  <span className="font-medium">
                                    {selectedRepo.split("/").pop()}
                                  </span>
                                </>
                              ) : (
                                <>
                                  <BookOpen className="w-4 h-4 text-gray-400" />
                                  <span className="text-gray-500">
                                    Select a repository
                                  </span>
                                </>
                              )}
                            </span>
                            <ChevronDown
                              className={`w-5 h-5 text-gray-400 transition-transform ${
                                showRepoDropdown ? "rotate-180" : ""
                              }`}
                            />
                          </button>

                          {/* Dropdown Menu */}
                          {showRepoDropdown && (
                            <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-50">
                              {/* Search Bar */}
                              <div className="p-3 border-b border-gray-200 dark:border-gray-600">
                                <div className="relative">
                                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                                  <input
                                    type="text"
                                    placeholder="Search repositories..."
                                    value={repoSearchQuery}
                                    onChange={(e) =>
                                      setRepoSearchQuery(e.target.value)
                                    }
                                    className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-600 border border-gray-200 dark:border-gray-500 rounded-md text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    autoFocus
                                  />
                                </div>
                              </div>

                              {/* Scrollable Repo List */}
                              <div className="max-h-64 overflow-y-auto">
                                {repositories.filter((repo) =>
                                  (repo.full_name || repo.name)
                                    .toLowerCase()
                                    .includes(repoSearchQuery.toLowerCase())
                                ).length === 0 ? (
                                  <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                                    No repositories found
                                  </div>
                                ) : (
                                  repositories
                                    .filter((repo) =>
                                      (repo.full_name || repo.name)
                                        .toLowerCase()
                                        .includes(repoSearchQuery.toLowerCase())
                                    )
                                    .map((repo: any) => {
                                      const repoName =
                                        repo.full_name || repo.name;
                                      const isSelected =
                                        selectedRepo === repoName;
                                      return (
                                        <button
                                          key={repo.id}
                                          onClick={() => {
                                            setSelectedRepo(repoName);
                                            setShowRepoDropdown(false);
                                            setRepoSearchQuery("");
                                          }}
                                          className={`w-full text-left px-4 py-3 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors flex items-center gap-3 ${
                                            isSelected
                                              ? "bg-blue-50 dark:bg-blue-900/30 border-l-4 border-blue-500"
                                              : ""
                                          }`}
                                        >
                                          <BookOpen
                                            className={`w-4 h-4 flex-shrink-0 ${
                                              isSelected
                                                ? "text-blue-500"
                                                : "text-gray-400"
                                            }`}
                                          />
                                          <div className="flex-1 min-w-0">
                                            <p
                                              className={`text-sm font-medium truncate ${
                                                isSelected
                                                  ? "text-blue-600 dark:text-blue-400"
                                                  : "text-gray-900 dark:text-gray-100"
                                              }`}
                                            >
                                              {repoName.split("/").pop()}
                                            </p>
                                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                              {repoName}
                                            </p>
                                          </div>
                                          {isSelected && (
                                            <CheckCircle className="w-5 h-5 text-blue-500 flex-shrink-0" />
                                          )}
                                        </button>
                                      );
                                    })
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Step 4: Install Writer App */}
                <div
                  className={`flex items-start gap-4 p-4 rounded-xl ${
                    docbookLinked && !writerAppHasCorrectAccess
                      ? "bg-red-50 dark:bg-red-900/20"
                      : writerAppHasCorrectAccess
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-gray-50 dark:bg-gray-700/50 opacity-50"
                  }`}
                >
                  <div
                    className={`w-8 h-8 ${
                      writerAppHasCorrectAccess
                        ? "bg-green-500"
                        : docbookLinked && !writerAppHasCorrectAccess
                        ? "bg-red-500"
                        : "bg-gray-400"
                    } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                  >
                    {writerAppHasCorrectAccess ? "✓" : "4"}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      🚀 Grant Write Access (Install Writer App)
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Install Pustak Publisher AI to grant write-only access to
                      your docbook repository
                    </p>

                    {writerAppHasCorrectAccess ? (
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                        <CheckCircle size={18} />
                        <span className="text-sm font-semibold">
                          Writer App installed with correct access
                        </span>
                      </div>
                    ) : docbookLinked ? (
                      <>
                        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg p-3 mb-3">
                          <p className="text-sm text-red-800 dark:text-red-200 font-semibold mb-2">
                            ⚠️ IMPORTANT: Only select your{" "}
                            <code className="bg-red-100 dark:bg-red-800 px-1 rounded">
                              {docbookRepoName}
                            </code>{" "}
                            repository!
                          </p>
                          <p className="text-sm text-red-700 dark:text-red-300">
                            On the next screen, grant access ONLY to your
                            docbook repository. Do NOT select your source code
                            repositories.
                          </p>
                        </div>
                        <button
                          onClick={async () => {
                            try {
                              setPollingWriterApp(true);
                              const backendUrl =
                                process.env.NEXT_PUBLIC_BACKEND_URL ||
                                "http://localhost:8000";

                              const response = await fetch(
                                `${backendUrl}/auth/install-writer-app`
                              );

                              if (!response.ok) {
                                throw new Error("Failed to get Writer app URL");
                              }

                              const data = await response.json();
                              window.open(data.url, "_blank");
                            } catch (error) {
                              console.error(
                                "Failed to install Writer App:",
                                error
                              );
                              setPollingWriterApp(false);
                              alert(
                                "Failed to install Writer App. Please try again."
                              );
                            }
                          }}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors text-sm"
                        >
                          Install Writer App
                        </button>
                        {pollingWriterApp && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                            ⏳ Waiting for Writer App installation...
                          </p>
                        )}
                      </>
                    ) : null}
                  </div>
                </div>

                {/* Step 5: Generate Documentation */}
                <div
                  className={`flex items-start gap-4 p-4 rounded-xl ${
                    repositories.length > 0 && selectedRepo
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-gray-50 dark:bg-gray-700/50 opacity-50"
                  }`}
                >
                  <div
                    className={`w-8 h-8 ${
                      repositories.length > 0 && selectedRepo
                        ? "bg-green-500"
                        : "bg-gray-400"
                    } text-white rounded-full flex items-center justify-center font-bold flex-shrink-0`}
                  >
                    5
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                      ✨ Generate Documentation
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Ready to generate AI-powered documentation for your
                      repository
                    </p>
                    {repositories.length > 0 && selectedRepo && (
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
                                `❌ Failed to generate documentation: ${
                                  error.detail || "Unknown error"
                                }`
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
                        className="px-4 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        disabled={!selectedRepo || generatingDocs}
                      >
                        {generatingDocs && (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        )}
                        {generatingDocs
                          ? "Generating & Publishing..."
                          : "Generate Documentation"}
                      </button>
                    )}
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
          userToken={token || ""}
          onSuccess={() => {
            // Repositories will auto-refresh via useEffect when connectedOrgs changes
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
              [selectedOrgForDocbook]: docbookRepo,
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
}
