"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import apiClient from "@/lib/apiClient";

export interface RepositorySummary {
  full_name?: string;
  name?: string;
  description?: string | null;
  default_branch?: string | null;
  tracked_branch?: string | null;
  tracked_branch_source?: string | null;
  docbook_tracked_branch?: string | null;
  doc_persona?: string | null;
  last_documented_at?: string | null;
  pending_reviews?: number | null;
  html_url?: string | null;
}

export const PLAN_CONFIG = {
  free: {
    label: "FREE PLAN",
  },
  pro: {
    label: "PRO PLAN",
  },
  team: {
    label: "TEAM PLAN",
  },
  enterprise: {
    label: "ENTERPRISE PLAN",
  },
} as const;

export type PlanName = keyof typeof PLAN_CONFIG;

interface UseDashboardDataResult {
  repositories: RepositorySummary[];
  loadingRepos: boolean;
  repoSearchQuery: string;
  setRepoSearchQuery: (value: string) => void;

  connectedOrgs: string[];
  loadingOrgs: boolean;
  selectedOrg: string;
  setSelectedOrg: (org: string) => void;
  errorMessage: string | null;
  docbookRepo: string | null;

  pendingReviewsDisabled: boolean;
  pendingReviewsLoading: boolean;
  pendingReviewsError: string | null;
  pendingReviewsCount: number;
  pendingReviewStatusMessage: string;
  reloadPendingReviews: () => Promise<void>;

  documentedCount: number;
  loadRepositories: () => Promise<void>;

  actualPlan: string | null;
}

export function useDashboardData(): UseDashboardDataResult {
  const { token, user } = useAuth();
  const [repoSearchQuery, setRepoSearchQuery] = useState("");

  // 1. User organizations
  const {
    data: orgsData,
    isLoading: loadingOrgs,
  } = useQuery({
    queryKey: ["user", "organizations"],
    queryFn: async () => {
      const response = await apiClient.get<{
        organizations?: { login: string }[];
      }>("/user/organizations");
      const orgs =
        response.data.organizations?.map((org) => org.login).filter(Boolean) ??
        [];
      return { organizations: orgs };
    },
    enabled: Boolean(token),
  });

  const connectedOrgs = orgsData?.organizations ?? [];
  const [selectedOrg, setSelectedOrgState] = useState<string>("");

  // Sync selectedOrg when orgs load: keep current if still in list, else first org
  useEffect(() => {
    if (connectedOrgs.length === 0) return;
    setSelectedOrgState((current) =>
      current && connectedOrgs.includes(current) ? current : connectedOrgs[0] ?? ""
    );
  }, [connectedOrgs]);

  const setSelectedOrg = useCallback((org: string) => {
    setSelectedOrgState(org);
  }, []);

  // 2. Repo summary for selected org
  const {
    data: reposData,
    isLoading: loadingRepos,
    isError: reposError,
    error: reposErrorObj,
    refetch: refetchRepositories,
  } = useQuery({
    queryKey: ["repo", "summary", selectedOrg],
    queryFn: async () => {
      const response = await apiClient.get<{
        repositories?: RepositorySummary[];
      }>(`/org/${selectedOrg}/repositories/summary`);
      const repos: RepositorySummary[] = Array.isArray(
        response.data.repositories
      )
        ? response.data.repositories
        : [];
      return { repositories: repos };
    },
    enabled: Boolean(token && selectedOrg),
  });

  const repositories = reposData?.repositories ?? [];
  const errorMessage = reposError
    ? (reposErrorObj instanceof Error
        ? reposErrorObj.message
        : "Unable to load repositories")
    : null;

  // 3. Usage / plan
  const { data: usageData } = useQuery({
    queryKey: ["usage", "plan"],
    queryFn: async () => {
      const response = await apiClient.get<{ plan?: string }>("/usage/me");
      return { plan: response.data.plan ?? null };
    },
    enabled: Boolean(token),
    retry: (failureCount, error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 404) return false;
      return failureCount < 1;
    },
  });

  const actualPlan = usageData?.plan ?? user?.plan ?? null;

  // 4. Docbook check-exists for selected org
  const { data: docbookData } = useQuery({
    queryKey: ["docbook", "check-exists", selectedOrg],
    queryFn: async () => {
      const response = await apiClient.get<{
        exists: boolean;
        docbook_repo?: string | null;
      }>("/docbook/check-exists", { params: { org_id: selectedOrg } });
      return {
        docbookRepo:
          response.data.exists ? response.data.docbook_repo ?? null : null,
      };
    },
    enabled: Boolean(token && selectedOrg),
  });

  const docbookRepo = docbookData?.docbookRepo ?? null;

  // 5. Pending reviews for selected org
  const {
    data: pendingData,
    isLoading: pendingReviewsLoading,
    isError: pendingReviewsIsError,
    error: pendingReviewsErrorObj,
    refetch: refetchPendingReviews,
  } = useQuery({
    queryKey: ["docbook", "pending-reviews", selectedOrg],
    queryFn: async () => {
      const response = await apiClient.get<{ reviews?: unknown[] }>(
        "/docbook/pending-reviews",
        { params: { org_id: selectedOrg } }
      );
      const reviews = Array.isArray(response.data.reviews)
        ? response.data.reviews
        : [];
      return { reviews, count: reviews.length };
    },
    enabled: Boolean(token && selectedOrg),
  });

  const pendingReviewsCount = pendingData?.count ?? 0;
  const pendingReviewsDisabled = !selectedOrg || !token;
  const pendingReviewsError = pendingReviewsIsError
    ? (pendingReviewsErrorObj instanceof Error
        ? pendingReviewsErrorObj.message
        : "Unable to load pending reviews")
    : null;

  const pendingReviewStatusMessage = useMemo(() => {
    if (pendingReviewsDisabled) {
      return "Connect an organization to start tracking documentation reviews.";
    }
    if (pendingReviewsLoading) {
      return "Syncing review queue…";
    }
    if (pendingReviewsError) {
      return "Unable to fetch the latest review status.";
    }
    if (pendingReviewsCount === 0) {
      return "All caught up! Nothing waiting for approval.";
    }
    return "Awaiting approval across docs";
  }, [
    pendingReviewsDisabled,
    pendingReviewsLoading,
    pendingReviewsError,
    pendingReviewsCount,
  ]);

  const loadRepositories = useCallback(async () => {
    await refetchRepositories();
  }, [refetchRepositories]);

  const reloadPendingReviews = useCallback(async () => {
    await refetchPendingReviews();
  }, [refetchPendingReviews]);

  const documentedCount = useMemo(
    () =>
      repositories.filter((repo) => Boolean(repo.last_documented_at)).length,
    [repositories]
  );

  return {
    repositories,
    loadingRepos,
    repoSearchQuery,
    setRepoSearchQuery,

    connectedOrgs,
    loadingOrgs,
    selectedOrg,
    setSelectedOrg,

    errorMessage,
    docbookRepo,

    pendingReviewsDisabled,
    pendingReviewsLoading,
    pendingReviewsError,
    pendingReviewsCount,
    pendingReviewStatusMessage,
    reloadPendingReviews,

    documentedCount,
    loadRepositories,

    actualPlan,
  };
}
