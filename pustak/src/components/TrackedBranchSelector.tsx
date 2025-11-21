"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { GitBranch, Loader2, RefreshCw, Save, AlertCircle, CheckCircle2, ChevronDown } from "lucide-react";

interface TrackedBranchSelectorProps {
  repoId: string;
  backendUrl?: string;
  userToken?: string;
  onSave?: (branch: string) => void;
}

interface TrackedBranchResponse {
  repo_id: string;
  tracked_branch: string;
  source: string;
  fallback_branch?: string | null;
  default_branch?: string | null;
}

export function TrackedBranchSelector({
  repoId,
  backendUrl = "http://localhost:8000",
  userToken,
  onSave,
}: TrackedBranchSelectorProps) {
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [trackedInfo, setTrackedInfo] = useState<TrackedBranchResponse | null>(null);
  const [branches, setBranches] = useState<string[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [useCustomBranch, setUseCustomBranch] = useState(false);

  const encodedRepoId = useMemo(() => encodeURIComponent(repoId), [repoId]);

  const apiBase = useMemo(() => {
    const normalized = backendUrl.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(normalized);
    return hasApiSuffix ? normalized : `${normalized}/api/v1`;
  }, [backendUrl]);

  const authedFetch = useCallback(
    async (path: string, init?: RequestInit) => {
      if (!userToken) {
        throw new Error("Missing authentication token");
      }

      const response = await fetch(`${apiBase}${path}`, {
        ...init,
        headers: {
          Authorization: `Bearer ${userToken}`,
          ...(init?.headers ?? {}),
        },
      });

      return response;
    },
    [apiBase, userToken]
  );

  useEffect(() => {
    if (!userToken) return;

    const fetchTrackedInfo = async () => {
      setLoadingInfo(true);
      setError(null);
      try {
        const response = await authedFetch(`/repositories/${encodedRepoId}/tracked-branch`);

        if (!response.ok) {
          throw new Error("Failed to fetch tracked branch");
        }

        const data: TrackedBranchResponse = await response.json();
        setTrackedInfo(data);
        setSelectedBranch(data.tracked_branch || "");
        setUseCustomBranch(false);
      } catch (err) {
        console.error("Error fetching tracked branch:", err);
        setError(err instanceof Error ? err.message : "Failed to load tracked branch");
      } finally {
        setLoadingInfo(false);
      }
    };

    fetchTrackedInfo();
  }, [authedFetch, encodedRepoId, userToken]);

  useEffect(() => {
    if (!userToken) return;

    const fetchBranches = async () => {
      setLoadingBranches(true);
      try {
        const response = await authedFetch(`/repositories/${encodedRepoId}/branches`);

        if (!response.ok) {
          throw new Error("Failed to fetch branches");
        }

        const data = await response.json();
        const fetchedBranches: string[] = Array.isArray(data?.branches) ? data.branches : [];

        const unique = Array.from(new Set(fetchedBranches.filter(Boolean)));
        unique.sort((a, b) => a.localeCompare(b));

        setBranches(unique);
        if (selectedBranch) {
          setUseCustomBranch(!unique.includes(selectedBranch));
        } else {
          setUseCustomBranch(unique.length === 0);
        }
      } catch (err) {
        console.error("Error fetching branches:", err);
        setError(err instanceof Error ? err.message : "Failed to load branches");
      } finally {
        setLoadingBranches(false);
      }
    };

    fetchBranches();
  }, [authedFetch, encodedRepoId, userToken]);

  const handleSave = async () => {
    if (!userToken) {
      setError("Not authenticated");
      return;
    }

    const branchValue = selectedBranch.trim();
    if (!branchValue) {
      setError("Branch name cannot be empty");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await authedFetch(`/repositories/${encodedRepoId}/tracked-branch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ tracked_branch: branchValue }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update tracked branch");
      }

      const data: TrackedBranchResponse = await response.json();
      setTrackedInfo(data);
      setSelectedBranch(data.tracked_branch || branchValue);
      setSuccess(true);
      onSave?.(data.tracked_branch);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update tracked branch");
    } finally {
      setSaving(false);
    }
  };

  if (!userToken) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Tracked Branch</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Sign in again to manage tracked branches.
        </p>
      </div>
    );
  }

  const CUSTOM_OPTION_VALUE = "__custom_branch__";
  const hasFetchedBranches = branches.length > 0;
  const branchInList = selectedBranch && branches.includes(selectedBranch);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch className="w-5 h-5 text-purple-500" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Tracked Branch</h3>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Choose which branch DocAI should monitor for documentation updates.
      </p>

      {loadingInfo ? (
        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Loading current branch…</span>
        </div>
      ) : (
        <div className="space-y-4">
          {hasFetchedBranches && (
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-500 dark:text-gray-400 mb-2">
                Select tracked branch
              </label>
              <div className="relative">
                <select
                  value={!useCustomBranch && branchInList ? selectedBranch : CUSTOM_OPTION_VALUE}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (value === CUSTOM_OPTION_VALUE) {
                      setUseCustomBranch(true);
                      if (!branchInList) {
                        setSelectedBranch("");
                      }
                    } else {
                      setUseCustomBranch(false);
                      setSelectedBranch(value);
                    }
                  }}
                  className="w-full appearance-none px-3 py-2 pr-10 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {branches.map((branch) => (
                    <option key={branch} value={branch}>
                      {branch}
                    </option>
                  ))}
                  <option value={CUSTOM_OPTION_VALUE}>Custom branch…</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              </div>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                <RefreshCw className="w-3 h-3" />
                {loadingBranches ? "Fetching branches from GitHub…" : `${branches.length} branches fetched from GitHub.`}
              </p>
            </div>
          )}

          {(useCustomBranch || !hasFetchedBranches) && (
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-500 dark:text-gray-400 mb-2">
                {hasFetchedBranches ? "Custom branch" : "Tracked branch"}
              </label>
              <input
                type="text"
                value={selectedBranch}
                onChange={(event) => setSelectedBranch(event.target.value)}
                placeholder="e.g. main"
                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              {hasFetchedBranches && (
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Can't find the branch above? Enter it manually here.
                </p>
              )}
            </div>
          )}

          {trackedInfo && (
            <div className="rounded-md bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 p-3 text-xs text-purple-800 dark:text-purple-200 space-y-1">
              <div className="flex items-center gap-2">
                <GitBranch className="w-3 h-3" />
                <span>
                  Current source: <strong>{trackedInfo.source}</strong>
                </span>
              </div>
              {trackedInfo.fallback_branch && (
                <div>
                  Fallback (docbook): <code>{trackedInfo.fallback_branch}</code>
                </div>
              )}
              {trackedInfo.default_branch && (
                <div>
                  Default branch: <code>{trackedInfo.default_branch}</code>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-sm text-red-700 dark:text-red-300 p-3">
              <AlertCircle className="w-4 h-4 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 rounded-md border border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-sm text-green-700 dark:text-green-300 p-3">
              <CheckCircle2 className="w-4 h-4" />
              <span>Tracked branch updated</span>
            </div>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Tracked Branch
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default TrackedBranchSelector;
