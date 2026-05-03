"use client";

import {
  commitsToDailyBuckets,
  type RepoCommitLite,
} from "@/hooks/useRepositoriesRecentActivity";
import { formatDistanceToNow } from "date-fns";
import {
  ChevronDown,
  ExternalLink,
  GitBranch,
  GitCommit,
  Loader2,
  Radio,
  Zap,
} from "lucide-react";
import { useId, useState } from "react";

type RepoActivitySectionProps = {
  fullName: string;
  branch: string;
  commits: RepoCommitLite[];
  loading: boolean;
  fetchError: string | null;
  newPush: boolean;
};

function barTone(count: number, max: number, isToday: boolean): string {
  if (count === 0)
    return "bg-slate-800/80 border border-slate-700/40";
  const intensity = max > 0 ? count / max : 0;
  if (intensity > 0.66 || isToday)
    return "bg-gradient-to-t from-cyan-600/90 to-cyan-400/95 shadow-[0_0_14px_rgba(34,211,238,0.35)] border border-cyan-400/50";
  if (intensity > 0.33)
    return "bg-cyan-600/50 border border-cyan-500/35";
  return "bg-slate-600/70 border border-slate-500/30";
}

export function RepoActivitySection({
  fullName,
  branch,
  commits,
  loading,
  fetchError,
  newPush,
}: RepoActivitySectionProps) {
  const [commitsOpen, setCommitsOpen] = useState(false);
  const commitsPanelId = useId();

  const buckets = commitsToDailyBuckets(commits, 14);
  const maxBucket = Math.max(...buckets, 1);

  const todayIdx = buckets.length - 1;

  return (
    <div className="mb-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[9px] uppercase tracking-[0.28em] text-slate-500">
            Branch activity · 14 days
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/80 bg-slate-950/60 px-2 py-0.5 text-[10px] font-medium text-slate-300">
              <GitBranch className="h-3 w-3 text-cyan-400/90" />
              {branch}
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] text-cyan-200/90">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400/40 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
              </span>
              Watching for new commits
            </span>
          </div>
        </div>
        {loading && (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-cyan-400/70" />
        )}
      </div>

      {newPush && (
        <div className="relative overflow-hidden rounded-xl border border-cyan-400/35 bg-gradient-to-r from-cyan-500/15 via-slate-900/40 to-emerald-500/10 px-3 py-2">
          <div className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-cyan-400 via-teal-400 to-emerald-400" />
          <div className="relative flex items-start gap-2 pl-1">
            <Zap className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
            <div>
              <p className="text-[11px] font-semibold text-white">
                New commits on {branch}
              </p>
              <p className="text-[10px] leading-snug text-slate-300">
                DocIt picks these up from GitHub webhooks; manual{" "}
                <span className="text-cyan-200/95">Regenerate</span> still
                pushes fresh staging docs when you need them.
              </p>
            </div>
          </div>
        </div>
      )}

      {fetchError && (
        <p className="text-[10px] text-amber-300/90">
          Activity feed unavailable ({fetchError}). Summary cards still work.
        </p>
      )}

      <div className="rounded-xl border border-slate-800/70 bg-slate-950/45 px-2 pb-2 pt-1">
        <div className="flex h-[2.85rem] items-end justify-between gap-px sm:gap-0.5">
          {buckets.map((count, idx) => {
            const heightPct =
              count === 0 ? 18 : Math.max(32, (count / maxBucket) * 100);
            const isToday = idx === todayIdx;
            return (
              <div
                key={`d-${fullName}-${idx}`}
                className={`flex-1 rounded-sm transition-all duration-300 ${barTone(count, maxBucket, isToday)}`}
                style={{ height: `${Math.min(heightPct, 100)}%` }}
                title={`${count} commit${count === 1 ? "" : "s"} · last ${14 - idx}d`}
              />
            );
          })}
        </div>
      </div>

      {commits.length === 0 && !loading ? (
        <div className="space-y-2">
          <p className="text-[9px] uppercase tracking-[0.28em] text-slate-500">
            Latest commits
          </p>
          <p className="text-[11px] text-slate-500">
            No recent commits on this branch (or GitHub returned an empty
            list).
          </p>
        </div>
      ) : commits.length === 0 && loading ? (
        <div className="flex items-center gap-2 rounded-xl border border-slate-800/70 bg-slate-950/35 px-3 py-2.5">
          <Loader2 className="h-4 w-4 animate-spin text-cyan-400/70" />
          <div>
            <p className="text-[9px] uppercase tracking-[0.28em] text-slate-500">
              Latest commits
            </p>
            <p className="text-[11px] text-slate-400">Loading history…</p>
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800/70 bg-slate-950/35">
          <button
            type="button"
            id={`${commitsPanelId}-trigger`}
            aria-expanded={commitsOpen}
            aria-controls={commitsPanelId}
            onClick={() => setCommitsOpen((o) => !o)}
            className="flex w-full items-center gap-2 px-3 py-2.5 text-left transition hover:bg-slate-800/40"
          >
            <div className="min-w-0 flex-1">
              <p className="text-[9px] uppercase tracking-[0.28em] text-slate-500">
                Latest commits
              </p>
              {!commitsOpen && commits[0] ? (
                <p className="mt-1 line-clamp-1 text-[11px] text-slate-400">
                  <span className="font-mono text-cyan-500/90">
                    {commits[0].short_sha || commits[0].sha.slice(0, 7)}
                  </span>
                  <span className="text-slate-600"> · </span>
                  <span className="text-slate-300">
                    {commits[0].message || "(no message)"}
                  </span>
                </p>
              ) : null}
            </div>
            <span className="shrink-0 rounded-full border border-slate-700/80 bg-slate-900/80 px-2 py-0.5 text-[10px] font-medium tabular-nums text-slate-400">
              {loading ? "…" : commits.length}
            </span>
            <ChevronDown
              className={`h-4 w-4 shrink-0 text-slate-500 transition-transform duration-200 ${
                commitsOpen ? "rotate-180" : ""
              }`}
              aria-hidden
            />
          </button>

          <div
            id={commitsPanelId}
            role="region"
            aria-labelledby={`${commitsPanelId}-trigger`}
            className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
              commitsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="overflow-hidden">
              <ul className="space-y-2 border-t border-slate-800/60 px-2 py-3">
                {commits.map((c) => {
                  const rel = c.committed_at
                    ? formatDistanceToNow(new Date(c.committed_at), {
                        addSuffix: true,
                      })
                    : "";
                  return (
                    <li key={c.sha}>
                      <div className="flex gap-2 rounded-lg border border-slate-800/60 bg-slate-900/35 px-2 py-2 transition hover:border-slate-600/50">
                        <div className="relative mt-0.5 shrink-0">
                          {c.author_avatar_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={c.author_avatar_url}
                              alt=""
                              width={28}
                              height={28}
                              className="h-7 w-7 rounded-full border border-slate-700/60 object-cover"
                            />
                          ) : (
                            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-700/60 bg-slate-800 text-[10px] font-bold text-slate-300">
                              {(c.author_login || c.author_name || "?")
                                .slice(0, 1)
                                .toUpperCase()}
                            </div>
                          )}
                          <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border border-slate-900 bg-cyan-600/90 text-white shadow">
                            <GitCommit className="h-2.5 w-2.5" />
                          </span>
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="line-clamp-2 text-[11px] font-medium leading-snug text-slate-100">
                            {c.message || "(no message)"}
                          </p>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-slate-500">
                            <span className="font-mono text-cyan-600/90 dark:text-cyan-300/90">
                              {c.short_sha || c.sha.slice(0, 7)}
                            </span>
                            <span>
                              {c.author_login || c.author_name}
                              {rel ? ` · ${rel}` : ""}
                            </span>
                          </div>
                        </div>
                        {c.html_url && (
                          <a
                            href={c.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 self-center rounded-lg p-1 text-slate-500 transition hover:bg-slate-800 hover:text-cyan-300"
                            aria-label="View commit on GitHub"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      )}

      <p className="flex items-center gap-1.5 text-[9px] text-slate-600">
        <Radio className="h-3 w-3 text-cyan-600/60" />
        Refreshes automatically so you can leave this open while you ship.
      </p>
    </div>
  );
}
