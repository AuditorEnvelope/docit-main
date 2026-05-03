"use client";

import { getBackendApiV1Base } from "@/lib/api";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type RepoCommitLite = {
  sha: string;
  short_sha: string;
  message: string;
  author_login?: string | null;
  author_name?: string;
  author_avatar_url?: string | null;
  committed_at: string;
  html_url?: string | null;
};

export function normalizeRepoLookupKey(fullName: string): string {
  return fullName.trim().toLowerCase();
}

/** Buckets commits into local-calendar days over the last `days` days (oldest → newest). */
export function commitsToDailyBuckets(
  commits: RepoCommitLite[],
  days = 14,
): number[] {
  const buckets = Array.from({ length: days }, () => 0);
  const dayMs = 86400000;
  const now = Date.now();
  const windowStart = new Date(now - (days - 1) * dayMs);
  windowStart.setHours(0, 0, 0, 0);
  const startTs = windowStart.getTime();

  for (const c of commits) {
    const t = new Date(c.committed_at).getTime();
    if (!Number.isFinite(t) || t < startTs) continue;
    const idx = Math.floor((t - startTs) / dayMs);
    if (idx >= 0 && idx < days) buckets[idx] += 1;
  }
  return buckets;
}

type RepoActivityEntry = {
  commits: RepoCommitLite[];
  branch: string;
  error: string | null;
};

export function useRepositoriesRecentActivity(
  token: string | null,
  orgId: string,
  repoTargets: Array<{ full_name: string; branch: string }>,
  options?: { pollMs?: number; disabled?: boolean; perRepoLimit?: number },
) {
  const pollMs = options?.pollMs ?? 30000;
  const disabled = options?.disabled ?? false;
  const perRepoLimit = options?.perRepoLimit ?? 14;

  const [byRepo, setByRepo] = useState<Record<string, RepoActivityEntry>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<string | null>(null);
  const [newPushByRepo, setNewPushByRepo] = useState<Record<string, boolean>>(
    {},
  );

  const prevHeadRef = useRef<Record<string, string>>({});
  const skipCompareRef = useRef(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stableKey = useMemo(
    () =>
      repoTargets
        .map((r) => `${normalizeRepoLookupKey(r.full_name)}:${r.branch}`)
        .sort()
        .join("|"),
    [repoTargets],
  );

  const fetchBatch = useCallback(async () => {
    if (!token || !orgId || disabled || repoTargets.length === 0) {
      setByRepo({});
      setFetchedAt(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const base = getBackendApiV1Base();
      const res = await fetch(
        `${base}/org/${encodeURIComponent(orgId)}/repositories/recent-commits`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            repos: repoTargets.map((r) => ({
              full_name: r.full_name,
              branch: r.branch || "main",
            })),
            per_repo_limit: perRepoLimit,
          }),
        },
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Activity request failed (${res.status})`);
      }

      const data = (await res.json()) as {
        by_repo?: Record<
          string,
          {
            commits?: RepoCommitLite[];
            branch?: string;
            error?: string | null;
          }
        >;
        fetched_at?: string;
      };

      const normalized: Record<string, RepoActivityEntry> = {};
      const detections: Record<string, boolean> = {};

      for (const target of repoTargets) {
        const k = normalizeRepoLookupKey(target.full_name);
        const row = data.by_repo?.[k];
        const commits = Array.isArray(row?.commits) ? row!.commits! : [];
        const branch =
          typeof row?.branch === "string" ? row.branch : target.branch;

        normalized[k] = {
          commits,
          branch,
          error: row?.error ?? null,
        };

        const head = commits[0]?.sha ?? "";
        if (!skipCompareRef.current && head && prevHeadRef.current[k]) {
          if (head !== prevHeadRef.current[k]) {
            detections[k] = true;
          }
        }
        if (head) prevHeadRef.current[k] = head;
      }

      skipCompareRef.current = false;

      setByRepo(normalized);
      setFetchedAt(data.fetched_at ?? new Date().toISOString());

      if (Object.keys(detections).length > 0) {
        setNewPushByRepo((prev) => ({ ...prev, ...detections }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activity");
    } finally {
      setLoading(false);
    }
  }, [disabled, orgId, perRepoLimit, repoTargets, token]);

  useEffect(() => {
    skipCompareRef.current = true;
    prevHeadRef.current = {};
    setNewPushByRepo({});
    void fetchBatch();
  }, [fetchBatch, stableKey, orgId, token]);

  useEffect(() => {
    if (disabled || pollMs <= 0 || repoTargets.length === 0 || !token) {
      return;
    }
    timerRef.current = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void fetchBatch();
    }, pollMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [disabled, fetchBatch, pollMs, repoTargets.length, stableKey, token]);

  useEffect(() => {
    const keys = Object.keys(newPushByRepo).filter((k) => newPushByRepo[k]);
    if (keys.length === 0) return;
    const t = setTimeout(() => {
      setNewPushByRepo((prev) => {
        const next = { ...prev };
        for (const k of keys) delete next[k];
        return next;
      });
    }, 12000);
    return () => clearTimeout(t);
  }, [newPushByRepo]);

  const acknowledgeNewPush = useCallback((fullName: string) => {
    const k = normalizeRepoLookupKey(fullName);
    setNewPushByRepo((prev) => {
      const next = { ...prev };
      delete next[k];
      return next;
    });
  }, []);

  return {
    byRepo,
    loading,
    error,
    fetchedAt,
    refresh: fetchBatch,
    newPushByRepo,
    acknowledgeNewPush,
  };
}
