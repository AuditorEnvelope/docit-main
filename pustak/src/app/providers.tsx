"use client";

import { ThemeProvider } from "next-themes";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { EditorProvider } from "@/contexts/EditorContext";
import {
  OnboardingSplash,
  ONBOARDING_PROGRESS_MESSAGES,
} from "@/components/OnboardingSplash";

const RAW_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const API_BASE = RAW_BACKEND_URL.endsWith("/api/v1")
  ? RAW_BACKEND_URL
  : `${RAW_BACKEND_URL.replace(/\/$/, "")}/api/v1`;

async function fetchJson<T>(url: string, token: string): Promise<T | null> {
  try {
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Failed to fetch onboarding prerequisite", error);
    return null;
  }
}

async function checkOnboardingCompletion(token: string): Promise<boolean> {
  const orgsData = await fetchJson<{
    organizations?: Array<string | { login?: string; org?: string; name?: string }>;
  }>(`${API_BASE}/user/organizations`, token);

  const orgIds = orgsData?.organizations
    ?.map((org) =>
      typeof org === "string"
        ? org
        : org?.login || org?.org || org?.name || ""
    )
    .filter(Boolean);

  if (!orgIds || orgIds.length === 0) {
    return false;
  }

  for (const orgId of orgIds) {
    const appsData = await fetchJson<{
      reader_app?: { installed?: boolean };
      writer_app?: { installed?: boolean };
    }>(`${API_BASE}/org/${orgId}/verify-apps`, token);

    const readerInstalled = appsData?.reader_app?.installed ?? false;
    const writerInstalled = appsData?.writer_app?.installed ?? false;

    if (!readerInstalled || !writerInstalled) {
      continue;
    }

    const docbookData = await fetchJson<{
      exists?: boolean;
      docbook_repo?: string;
    }>(`${API_BASE}/docbook/check-exists?org_id=${encodeURIComponent(orgId)}`, token);

    if (!docbookData?.exists || !docbookData.docbook_repo) {
      continue;
    }

    const accessData = await fetchJson<{
      has_access?: boolean;
    }>(
      `${API_BASE}/org/${orgId}/verify-writer-app-access?repo=${encodeURIComponent(
        docbookData.docbook_repo
      )}`,
      token
    );

    if (accessData?.has_access) {
      return true;
    }
  }

  return false;
}

async function markOnboardingCompleteRemotely(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/onboarding-complete`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.ok;
  } catch (error) {
    console.error("Failed to mark onboarding complete", error);
    return false;
  }
}

function OnboardingRedirect({
  children,
  isDocbookHost,
}: {
  children: ReactNode;
  isDocbookHost: boolean;
}) {
  const { loading, isAuthenticated, user, token, markOnboardingComplete } =
    useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [status, setStatus] = useState<"checking" | "redirecting" | "ready">(
    () => (isDocbookHost ? "ready" : "checking")
  );
  const [progressIndex, setProgressIndex] = useState(0);
  const completionAttemptedRef = useRef(false);

  const { isOnboardingRoute, isPublicRoute, isDocsRoute, isNotFoundRoute } =
    useMemo(() => {
      const current = pathname || "";
      const normalized = current.replace(/\/+$|^$/, (match) =>
        match === "" ? "/" : ""
      );
      const docsRoute =
        normalized === "/docs" || normalized.startsWith("/docs/");
      const notFoundRoute = normalized === "/404";
      return {
        isOnboardingRoute: normalized.startsWith("/onboarding"),
        isPublicRoute:
          normalized === "" ||
          normalized === "/" ||
          normalized.startsWith("/auth/") ||
          normalized === "/login" ||
          docsRoute ||
          notFoundRoute,
        isDocsRoute: docsRoute,
        isNotFoundRoute: notFoundRoute,
      };
    }, [pathname]);

  useEffect(() => {
    if (isDocbookHost) {
      setStatus("ready");
      return;
    }

    if (isDocsRoute || isNotFoundRoute) {
      setStatus("ready");
      return;
    }

    if (loading) {
      setStatus(isPublicRoute && !isAuthenticated ? "ready" : "checking");
      return;
    }

    if (!isAuthenticated) {
      completionAttemptedRef.current = false;
      setStatus("ready");
      return;
    }

    let cancelled = false;

    const decideRoute = async () => {
      if (user?.is_onboarding_complete) {
        if (isOnboardingRoute) {
          setStatus("redirecting");
          router.replace("/dashboard");
        } else {
          setStatus("ready");
        }
        return;
      }

      if (!token) {
        if (!isOnboardingRoute && !isPublicRoute) {
          setStatus("redirecting");
          router.replace("/onboarding");
        } else {
          setStatus("ready");
        }
        return;
      }

      setStatus("checking");
      const prerequisitesSatisfied = await checkOnboardingCompletion(token);

      if (cancelled) return;

      if (prerequisitesSatisfied) {
        if (!completionAttemptedRef.current) {
          completionAttemptedRef.current = true;
          const success = await markOnboardingCompleteRemotely(token);
          if (success) {
            markOnboardingComplete();
          } else {
            completionAttemptedRef.current = false;
          }
        }

        if (isOnboardingRoute) {
          setStatus("redirecting");
          router.replace("/dashboard");
        } else {
          setStatus("ready");
        }
        return;
      }

      completionAttemptedRef.current = false;

      if (!isOnboardingRoute && !isPublicRoute) {
        setStatus("redirecting");
        router.replace("/onboarding");
        return;
      }

      setStatus("ready");
    };

    void decideRoute();

    return () => {
      cancelled = true;
    };
  }, [
    isDocbookHost,
    isAuthenticated,
    isOnboardingRoute,
    isPublicRoute,
    loading,
    router,
    token,
    user?.is_onboarding_complete,
    markOnboardingComplete,
  ]);

  const showSplash =
    status !== "ready" &&
    !isOnboardingRoute &&
    !isDocsRoute &&
    !isNotFoundRoute &&
    !isDocbookHost;

  useEffect(() => {
    if (!showSplash) return;
    const interval = setInterval(() => {
      setProgressIndex((prev) =>
        (prev + 1) % ONBOARDING_PROGRESS_MESSAGES.length
      );
    }, 1800);
    return () => clearInterval(interval);
  }, [showSplash]);

  if (showSplash) {
    return (
      <OnboardingSplash
        messages={ONBOARDING_PROGRESS_MESSAGES}
        activeIndex={progressIndex}
      />
    );
  }

  return <>{children}</>;
}

export function Providers({
  children,
  isDocbookHost = false,
}: {
  children: ReactNode;
  isDocbookHost?: boolean;
}) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <AuthProvider>
        <EditorProvider>
          <OnboardingRedirect isDocbookHost={isDocbookHost}>
            {children}
          </OnboardingRedirect>
        </EditorProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
