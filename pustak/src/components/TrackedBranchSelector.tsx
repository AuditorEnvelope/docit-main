"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  GitBranch,
  Loader2,
  RefreshCw,
  Save,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";
import apiClient from "@/lib/apiClient";

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

  // Extract actual repo name if it contains org/repo format
  const normalizedRepoId = useMemo(() => {
    console.log('🔍 TrackedBranchSelector received repoId:', repoId);
    
    // If repoId is in the format "org/repo", use it directly
    if (repoId && repoId.includes('/')) {
      return repoId;
    }
    
    // If repoId has multiple segments (like org/repo/settings), extract org/repo
    const segments = repoId.split('/');
    if (segments.length >= 2) {
      const result = `${segments[0]}/${segments[1]}`;
      console.log('🔍 Normalized repoId to:', result);
      return result;
    }
    
    return repoId;
  }, [repoId]);
  
  const encodedRepoId = useMemo(() => encodeURIComponent(normalizedRepoId), [normalizedRepoId]);

  useEffect(() => {
    if (!userToken) return;

    const fetchTrackedInfo = async () => {
      setLoadingInfo(true);
      setError(null);
      try {
        const response = await apiClient.get<TrackedBranchResponse>(
          `/repositories/${encodedRepoId}/tracked-branch`
        );

        const data = response.data;
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
        const response = await apiClient.get<{
          branches?: string[];
        }>(`/repositories/${encodedRepoId}/branches`);

        const data = response.data;
        const fetchedBranches: string[] = Array.isArray(data?.branches)
          ? data.branches
          : [];

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
      const response = await apiClient.post<TrackedBranchResponse>(
        `/repositories/${encodedRepoId}/tracked-branch`,
        { tracked_branch: branchValue }
      );

      const data = response.data;
      setTrackedInfo(data);
      setSelectedBranch(data.tracked_branch || branchValue);
      setSuccess(true);
      onSave?.(data.tracked_branch);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        (err instanceof Error ? err.message : undefined);
      setError(detail || "Failed to update tracked branch");
    } finally {
      setSaving(false);
    }
  };

  if (!userToken) {
    return (
      <div className="relative overflow-hidden rounded-3xl border border-slate-900/60 bg-slate-950/70 p-8">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10 opacity-40" aria-hidden />
        <div className="relative space-y-3">
          <div className="flex items-center gap-3 text-purple-200">
            <GitBranch className="h-5 w-5" />
            <h3 className="text-lg font-semibold">Tracked branch</h3>
          </div>
          <p className="text-sm text-slate-400">Sign in again to manage tracked branches.</p>
        </div>
      </div>
    );
  }

  const CUSTOM_OPTION_VALUE = "__custom_branch__";
  const hasFetchedBranches = branches.length > 0;
  const branchInList = selectedBranch && branches.includes(selectedBranch);

  return (
    <div className="relative overflow-hidden rounded-3xl border border-slate-900/60 bg-slate-950/70 p-8 shadow-lg shadow-purple-950/30">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10 opacity-40" aria-hidden />
      <div className="relative space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.32em] text-purple-200">
              Branch flow
            </div>
            <h3 className="mt-3 text-xl font-semibold text-slate-100">Tracked branch</h3>
            <p className="mt-2 text-sm text-slate-400">
              Choose which branch DocAI should monitor for documentation updates.
            </p>
          </div>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-purple-500/40 bg-purple-500/10 text-purple-200">
            <GitBranch className="h-5 w-5" />
          </span>
        </div>

        {loadingInfo ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-800/80 bg-slate-950/70 px-4 py-3 text-sm text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading current branch…
          </div>
        ) : (
          <div className="space-y-4">
            {hasFetchedBranches && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
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
                    className="w-full appearance-none rounded-2xl border border-slate-800/70 bg-slate-950/80 px-4 py-3 pr-12 text-sm text-slate-100 outline-none transition focus:border-purple-400/70 focus:ring-2 focus:ring-purple-400/40"
                  >
                    {branches.map((branch) => (
                      <option key={branch} value={branch}>
                        {branch}
                      </option>
                    ))}
                    <option value={CUSTOM_OPTION_VALUE}>Custom branch…</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                </div>
                <p className="flex items-center gap-2 text-xs text-slate-500">
                  <RefreshCw className="h-3 w-3" />
                  {loadingBranches ? "Fetching branches from GitHub…" : `${branches.length} branches fetched from GitHub.`}
                </p>
              </div>
            )}

            {(useCustomBranch || !hasFetchedBranches) && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
                  {hasFetchedBranches ? "Custom branch" : "Tracked branch"}
                </label>
                <input
                  type="text"
                  value={selectedBranch}
                  onChange={(event) => setSelectedBranch(event.target.value)}
                  placeholder="e.g. main"
                  className="w-full rounded-2xl border border-slate-800/70 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-purple-400/70 focus:ring-2 focus:ring-purple-400/40"
                />
                {hasFetchedBranches && (
                  <p className="text-xs text-slate-500">
                    Can't find the branch above? Enter it manually here.
                  </p>
                )}
              </div>
            )}

            {trackedInfo && (
              <div className="rounded-2xl border border-purple-500/40 bg-purple-500/10 p-4 text-xs text-purple-100">
                <div className="flex items-center gap-2">
                  <GitBranch className="h-3.5 w-3.5" />
                  <span>
                    Current source: <span className="font-semibold text-purple-50">{trackedInfo.source}</span>
                  </span>
                </div>
                {trackedInfo.fallback_branch && (
                  <div className="mt-1">
                    Fallback (docbook): <code>{trackedInfo.fallback_branch}</code>
                  </div>
                )}
                {trackedInfo.default_branch && (
                  <div className="mt-1">
                    Default branch: <code>{trackedInfo.default_branch}</code>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="flex items-start gap-2 rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="flex items-center gap-2 rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                <CheckCircle2 className="h-4 w-4" />
                <span>Tracked branch updated</span>
              </div>
            )}

            <button
              onClick={handleSave}
              disabled={saving}
              className="group inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-purple-500/50 bg-purple-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-purple-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save tracked branch
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default TrackedBranchSelector;
