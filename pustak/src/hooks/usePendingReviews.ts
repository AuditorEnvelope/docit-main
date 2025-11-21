"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

export interface PendingReviewItem {
  id: number;
  source_repo_name: string;
  docbook_full_name: string;
  status: string;
  commit_message: string;
  created_at: string | null;
}

interface UsePendingReviewsOptions {
  orgId: string | null;
  token: string | null;
  backendUrl: string;
  disabled?: boolean;
}

export interface UsePendingReviewsResult {
  reviews: PendingReviewItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  count: number;
  hasData: boolean;
}

export function usePendingReviews({
  orgId,
  token,
  backendUrl,
  disabled = false,
}: UsePendingReviewsOptions): UsePendingReviewsResult {
  const [reviews, setReviews] = useState<PendingReviewItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedBase = useMemo(() => {
    const trimmed = backendUrl.replace(/\/$/, "");
    const hasApiSuffix = /\/api(\/v\d+)?$/i.test(trimmed);
    return hasApiSuffix ? trimmed : `${trimmed}/api/v1`;
  }, [backendUrl]);

  const fetchReviews = useCallback(async () => {
    if (disabled) {
      setIsLoading(false);
      return;
    }

    if (!orgId || !token) {
      setReviews([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${normalizedBase}/docbook/pending-reviews?org_id=${encodeURIComponent(
          orgId
        )}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Failed to load pending reviews");
      }

      const data = await response.json();
      const payload: PendingReviewItem[] = Array.isArray(data.reviews)
        ? data.reviews
        : [];
      setReviews(payload);
    } catch (fetchError) {
      console.error("Error loading pending reviews", fetchError);
      setReviews([]);
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : "Unable to load pending reviews"
      );
    } finally {
      setIsLoading(false);
    }
  }, [normalizedBase, orgId, token]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews, disabled]);

  const count = reviews.length;

  return {
    reviews,
    isLoading,
    error,
    reload: fetchReviews,
    count,
    hasData: count > 0,
  };
}
