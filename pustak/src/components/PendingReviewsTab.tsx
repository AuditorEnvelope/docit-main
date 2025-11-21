"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle, AlertCircle, ExternalLink, Loader2 } from "lucide-react";

import {
  usePendingReviews,
  PendingReviewItem,
} from "@/hooks/usePendingReviews";

interface PendingReviewsTabProps {
  orgId: string;
  token: string;
  backendUrl: string;
  onCountChange?: (count: number) => void;
  onReload?: () => Promise<void> | void;
  reviewsOverride?: PendingReviewItem[];
  isLoadingOverride?: boolean;
  errorOverride?: string | null;
}

export default function PendingReviewsTab({
  orgId,
  token,
  backendUrl,
  onCountChange,
  onReload,
  reviewsOverride,
  isLoadingOverride,
  errorOverride,
}: PendingReviewsTabProps) {
  const [approving, setApproving] = useState<string | null>(null);

  const overrideProvided =
    reviewsOverride !== undefined ||
    isLoadingOverride !== undefined ||
    errorOverride !== undefined;

  const normalizedBase = useMemo(() => {
    const trimmed = backendUrl.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(trimmed);
    return hasApiSuffix ? trimmed : `${trimmed}/api/v1`;
  }, [backendUrl]);

  const {
    reviews,
    isLoading,
    error,
    reload,
    count,
  } = usePendingReviews({ orgId, token, backendUrl, disabled: overrideProvided });

  const effectiveReviews = overrideProvided ? reviewsOverride ?? [] : reviews;
  const effectiveLoading = overrideProvided ? isLoadingOverride ?? false : isLoading;
  const effectiveError = overrideProvided ? errorOverride ?? null : error;
  const effectiveCount = overrideProvided
    ? (reviewsOverride ? reviewsOverride.length : 0)
    : count;

  useEffect(() => {
    onCountChange?.(effectiveCount);
  }, [effectiveCount, onCountChange]);

  const handleApprove = async (sourceRepoName: string) => {
    setApproving(sourceRepoName);
    try {
      const response = await fetch(`${normalizedBase}/docbook/approve-and-merge`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          org_id: orgId,
          repo_name: sourceRepoName,
          message: "docs: Approve and merge documentation",
        }),
      });

      if (response.ok) {
        alert(`✅ Documentation approved and merged for ${sourceRepoName}`);
        if (!overrideProvided) {
          await reload();
        }
        if (onReload) {
          await onReload();
        }
      } else {
        const errorPayload = await response.json();
        alert(`Failed to approve: ${errorPayload.detail ?? "Unknown error"}`);
      }
    } catch (approveError) {
      console.error("Error approving documentation:", approveError);
      alert("Failed to approve documentation");
    } finally {
      setApproving(null);
    }
  };

  const formatDate = (timestamp: string | null) => {
    if (!timestamp) return "Unknown";
    try {
      return new Date(timestamp).toLocaleString();
    } catch (error) {
      console.error("Failed to format timestamp", error);
      return timestamp;
    }
  };

  if (effectiveLoading) {
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-purple-500/30 bg-purple-500/10 px-6 py-5 text-purple-200">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading pending reviews…</span>
      </div>
    );
  }

  if (effectiveError) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-6 py-5 text-red-200">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5" />
          <span>{effectiveError}</span>
        </div>
      </div>
    );
  }

  if (!effectiveReviews.length) {
    return (
      <div className="rounded-2xl border border-purple-500/20 bg-purple-500/5 px-6 py-5 text-purple-100">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5" />
          <span>No pending documentation reviews at the moment.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {effectiveReviews.map((review: PendingReviewItem) => (
        <div
          key={review.id}
          className="relative overflow-hidden rounded-3xl border border-slate-800/60 bg-slate-950/60 px-6 py-6 shadow-[0_30px_60px_-40px_rgba(30,64,175,0.45)] backdrop-blur"
        >
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/60 to-transparent" aria-hidden />
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-2 rounded-full bg-indigo-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-200">
                  Pending review
                </span>
                <span className="text-xs font-mono text-slate-400">
                  {formatDate(review.created_at)}
                </span>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white tracking-tight">
                  {review.source_repo_name}
                </h3>
                <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                  {review.commit_message || "Documentation update pending approval."}
                </p>
              </div>
              <div className="rounded-2xl border border-slate-800/60 bg-slate-900/60 px-4 py-3">
                <p className="text-xs uppercase tracking-widest text-slate-400">Docbook repository</p>
                <p className="mt-1 font-mono text-sm text-slate-100">
                  {review.docbook_full_name}
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-3 lg:w-60">
              <a
                href={`https://github.com/${review.docbook_full_name}/compare/main...staging`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-indigo-500/40 bg-indigo-500/10 px-4 py-3 text-sm font-semibold text-indigo-200 hover:bg-indigo-500/20 transition"
              >
                <ExternalLink className="w-4 h-4" />
                Review diff on GitHub
              </a>
              <button
                onClick={() => handleApprove(review.source_repo_name)}
                disabled={approving === review.source_repo_name}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500/90 px-4 py-3 text-sm font-semibold text-emerald-950 shadow-lg shadow-emerald-900/40 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {approving === review.source_repo_name ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Approving…
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" /> Approve & merge
                  </>
                )}
              </button>
              <p className="text-xs text-slate-400 text-center">
                Approves and merges <code className="font-mono">staging</code> into <code className="font-mono">main</code> for this docbook.
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
