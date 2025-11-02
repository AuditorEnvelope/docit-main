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
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="bg-gray-50 dark:bg-gray-700/20 rounded-lg p-8 text-center">
        <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          All caught up!
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          No pending documentation reviews. Generate docs to see them here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {reviews.map((review) => (
        <div
          key={review.id}
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {review.source_repo_name}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {review.commit_message}
              </p>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
              <AlertCircle className="w-3 h-3" />
              Pending Review
            </span>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700/30 rounded p-3 mb-3">
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              Docbook Repository:
            </p>
            <p className="text-sm font-mono text-gray-900 dark:text-white">
              {review.docbook_full_name}
            </p>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 dark:text-gray-500">
              {new Date(review.created_at).toLocaleDateString()} at{" "}
              {new Date(review.created_at).toLocaleTimeString()}
            </p>
            <div className="flex gap-2">
              <a
                href={`https://github.com/${review.docbook_full_name}/compare/main...staging`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                Review on GitHub
              </a>
              <button
                onClick={() => handleApprove(review.source_repo_name)}
                disabled={approving === review.source_repo_name}
                className="inline-flex items-center gap-1 px-3 py-1 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {approving === review.source_repo_name && (
                  <Loader2 className="w-3 h-3 animate-spin" />
                )}
                {approving === review.source_repo_name
                  ? "Approving..."
                  : "Approve & Merge"}
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
