"use client";

import { ThemeProvider } from "next-themes";
import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";

function OnboardingRedirect({ children }: { children: ReactNode }) {
  const { loading, isAuthenticated, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) return;

    const isOnboardingRoute = pathname?.startsWith("/onboarding");
    const isPublicRoute =
      pathname === "/" || pathname?.startsWith("/auth/") || pathname === "/login";

    if (!user?.is_onboarding_complete && !isOnboardingRoute && !isPublicRoute) {
      router.replace("/onboarding");
      return;
    }

    if (user?.is_onboarding_complete && isOnboardingRoute) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, loading, pathname, router, user?.is_onboarding_complete]);

  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <AuthProvider>
        <OnboardingRedirect>{children}</OnboardingRedirect>
      </AuthProvider>
    </ThemeProvider>
  );
}
