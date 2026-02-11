"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoSearchQuery, setRepoSearchQuery] = useState("");

  const [connectedOrgs, setConnectedOrgs] = useState<string[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [docbookRepo, setDocbookRepo] = useState<string | null>(null);

  const [pendingReviewsLoading, setPendingReviewsLoading] = useState(false);
  const [pendingReviewsError, setPendingReviewsError] = useState<string | null>(
    null
  );
  const [pendingReviewsCount, setPendingReviewsCount] = useState(0);

  const [actualPlan, setActualPlan] = useState<string | null>(null);

  const pendingReviewsDisabled = !selectedOrg || !token;

  const documentedCount = useMemo(
    () =>
      repositories.filter((repo) => Boolean(repo.last_documented_at)).length,
    [repositories]
  );

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

  const loadOrganizations = useCallback(async () => {
    if (!token) {
      setConnectedOrgs([]);
      setSelectedOrg("");
      setDocbookRepo(null);
      return;
    }

    setLoadingOrgs(true);
    try {
      const response = await apiClient.get<{
        organizations?: { login: string }[];
      }>("/user/organizations");
      const orgs =
        response.data.organizations?.map((org) => org.login).filter(Boolean) ??
        [];
      setConnectedOrgs(orgs);
      setSelectedOrg((current) =>
        current && orgs.includes(current) ? current : orgs[0] || ""
      );
    } catch (error) {
      console.error("Error fetching organizations", error);
      setConnectedOrgs([]);
      setSelectedOrg("");
      setDocbookRepo(null);
    } finally {
      setLoadingOrgs(false);
    }
  }, [token]);

  const loadDocbookRepo = useCallback(async () => {
    if (!token || !selectedOrg) {
      setDocbookRepo(null);
      return;
    }

    try {
      const response = await apiClient.get<{
        exists: boolean;
        docbook_repo?: string | null;
      }>("/docbook/check-exists", {
        params: { org_id: selectedOrg },
      });
      setDocbookRepo(
        response.data.exists ? response.data.docbook_repo ?? null : null
      );
    } catch (error) {
      console.error("Error fetching docbook repo", error);
      setDocbookRepo(null);
    }
  }, [selectedOrg, token]);

  const loadRepositories = useCallback(async () => {
    if (!token || !selectedOrg) {
      setRepositories([]);
      return;
    }

    setLoadingRepos(true);
    setErrorMessage(null);

    try {
      const response = await apiClient.get<{
        repositories?: RepositorySummary[];
      }>(`/org/${selectedOrg}/repositories/summary`);

      const repos: RepositorySummary[] = Array.isArray(
        response.data.repositories
      )
        ? response.data.repositories
        : [];
      setRepositories(repos);
    } catch (error: unknown) {
      console.error("Error loading repositories", error);
      setRepositories([]);
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to load repositories"
      );
    } finally {
      setLoadingRepos(false);
    }
  }, [selectedOrg, token]);

  const reloadPendingReviews = useCallback(async () => {
    if (pendingReviewsDisabled) {
      setPendingReviewsLoading(false);
      setPendingReviewsError(null);
      setPendingReviewsCount(0);
      return;
    }

    setPendingReviewsLoading(true);
    setPendingReviewsError(null);

    try {
      const response = await apiClient.get<{ reviews?: unknown[] }>(
        "/docbook/pending-reviews",
        {
          params: { org_id: selectedOrg },
        }
      );
      const reviews = Array.isArray(response.data.reviews)
        ? response.data.reviews
        : [];
      setPendingReviewsCount(reviews.length);
    } catch (error) {
      console.error("Error loading pending reviews", error);
      setPendingReviewsCount(0);
      setPendingReviewsError(
        error instanceof Error
          ? error.message
          : "Unable to load pending reviews"
      );
    } finally {
      setPendingReviewsLoading(false);
    }
  }, [pendingReviewsDisabled, selectedOrg]);

  const loadActualPlan = useCallback(async () => {
    if (!token) return;

    try {
      const response = await apiClient.get<{ plan?: string }>("/usage/me");
      if (response.data.plan) {
        setActualPlan(response.data.plan);
      } else {
        setActualPlan(user?.plan ?? null);
      }
    } catch (error) {
      console.error("Failed to fetch actual plan:", error);
      setActualPlan(user?.plan ?? null);
    }
  }, [token, user?.plan]);

  // Initial loads
  useEffect(() => {
    loadOrganizations();
  }, [loadOrganizations]);

  useEffect(() => {
    loadDocbookRepo();
  }, [loadDocbookRepo]);

  useEffect(() => {
    loadRepositories();
  }, [loadRepositories]);

  useEffect(() => {
    reloadPendingReviews();
  }, [reloadPendingReviews]);

  useEffect(() => {
    loadActualPlan();
  }, [loadActualPlan]);

  // Derived filtered repos live in the consumer to keep hook focused on data

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
