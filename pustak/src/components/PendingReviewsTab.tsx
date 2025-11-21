"use client";

import { useState, useEffect } from "react";
import { CheckCircle, AlertCircle, ExternalLink, Loader2 } from "lucide-react";

interface PendingReview {
  id: number;
  source_repo_name: string;
  docbook_full_name: string;
  status: string;
  commit_message: string;
  created_at: string;
}

interface PendingReviewsTabProps {
  orgId: string;
  token: string;
  backendUrl: string;
}

export default function PendingReviewsTab({
  orgId,
  token,
  backendUrl,
}: PendingReviewsTabProps) {
  const [reviews, setReviews] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingReviews();
  }, [orgId, token]);

  const fetchPendingReviews = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${backendUrl}/docbook/pending-reviews?org_id=${orgId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setReviews(data.reviews || []);
      } else {
        console.error("Failed to fetch pending reviews");
      }
    } catch (error) {
      console.error("Error fetching pending reviews:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (sourceRepoName: string) => {
    setApproving(sourceRepoName);
    try {
      const response = await fetch(
        `${backendUrl}/docbook/approve-and-merge`,
        {
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
        }
      );

      if (response.ok) {
        alert(`✅ Documentation approved and merged for ${sourceRepoName}`);
        fetchPendingReviews();
      } else {
        const error = await response.json();
        alert(`Failed to approve: ${error.detail}`);
      }
    } catch (error) {
      console.error("Error approving documentation:", error);
      alert("Failed to approve documentation");
    } finally {
      setApproving(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-300">
        <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-800/50 bg-gradient-to-br from-slate-900/70 via-indigo-950/60 to-slate-900/80 px-10 py-12 text-center shadow-inner">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
          <CheckCircle className="h-8 w-8 text-emerald-300" />
        </div>
        <h3 className="text-2xl font-semibold text-white mb-2">All caught up!</h3>
        <p className="text-sm text-slate-300 max-w-md mx-auto">
          There are no pending documentation reviews right now. Generate docs from your repositories to send fresh updates for review.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {reviews.map((review) => (
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
                  {new Date(review.created_at).toLocaleDateString()} · {new Date(review.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
