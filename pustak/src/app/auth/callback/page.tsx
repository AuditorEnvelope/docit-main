"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Layout } from "@/components/Layout";
import {
  Loader2,
  CheckCircle,
  XCircle,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState("");
  const hasRun = useRef(false);

  const statusContent = {
    loading: {
      title: "Authenticating",
      description:
        "We're securing your GitHub connection and setting up your session.",
      icon: Loader2,
      accent: "from-blue-500/30",
      badge: "Connecting to GitHub",
    },
    success: {
      title: "Authenticated",
      description:
        "You're all set! Redirecting you to the docbook dashboard in a moment.",
      icon: CheckCircle,
      accent: "from-emerald-500/30",
      badge: "Ready to go",
    },
    error: {
      title: "Authentication Failed",
      description:
        "We couldn't complete your login. You can retry below or review the details.",
      icon: XCircle,
      accent: "from-rose-500/30",
      badge: "Needs attention",
    },
  } satisfies Record<
    "loading" | "success" | "error",
    {
      title: string;
      description: string;
      icon: typeof Loader2;
      accent: string;
      badge: string;
    }
  >;

  useEffect(() => {
    // Prevent multiple runs in React Strict Mode
    if (hasRun.current) return;
    hasRun.current = true;

    const handleCallback = async () => {
      try {
        // Get code from URL
        const code = searchParams.get("code");
        const error = searchParams.get("error");

        if (error) {
          throw new Error(`GitHub OAuth error: ${error}`);
        }

        if (!code) {
          throw new Error("No authorization code received");
        }

        // Exchange code for tokens
        const response = await fetch(
          `${BACKEND_URL}/auth/callback?code=${encodeURIComponent(code)}`,
          { credentials: "include" },
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Authentication failed");
        }

        const data = await response.json();

        // Store tokens and user data
        login(data.access_token, data.refresh_token, data.user);

        // Store GitHub token in cookie for server-side API calls
        if (data.github_token) {
          document.cookie = `github_token=${encodeURIComponent(
            data.github_token,
          )}; path=/; max-age=2592000; SameSite=Lax`;
        }

        setStatus("success");

        // Redirect to dashboard after 1 second
        setTimeout(() => {
          router.push("/dashboard");
        }, 1000);
      } catch (error: any) {
        console.error("Auth callback error:", error);
        setStatus("error");
        setErrorMessage(error.message || "Authentication failed");
      }
    };

    handleCallback();
  }, [searchParams, login, router]);

  const currentContent = statusContent[status];

  return (
    <Layout>
      <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
        <div className="absolute inset-0">
          <div
            className="absolute left-[-10%] top-[15%] h-[360px] w-[360px] rounded-full bg-blue-600/35 blur-[160px]"
            aria-hidden
          />
          <div
            className="absolute right-[-5%] top-[35%] h-[320px] w-[320px] rounded-full bg-purple-500/30 blur-[160px]"
            aria-hidden
          />
          <div
            className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-blue-500/10 via-transparent to-transparent"
            aria-hidden
          />
          <div
            className="absolute inset-x-0 bottom-[-35%] h-[420px] bg-gradient-to-t from-slate-950 via-slate-900/40 to-transparent"
            aria-hidden
          />
        </div>

        <div className="relative mx-auto flex min-h-screen max-w-4xl flex-col items-center justify-center px-6 py-16">
          <div className="flex flex-col items-center gap-4 text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-800/60 bg-slate-900/70 px-4 py-1.5 text-[11px] uppercase tracking-[0.36em] text-slate-400">
              <Sparkles className="h-3.5 w-3.5 text-blue-300" />
              Secure OAuth handshake
            </span>
            <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
              Finalizing your DocIt session
            </h1>
            <p className="max-w-2xl text-sm text-slate-400 sm:text-base">
              We’re syncing your GitHub identity, refreshing docbook access, and
              preparing your personalized dashboard.
            </p>
          </div>

          <div className="mt-12 w-full max-w-2xl rounded-3xl border border-slate-900/60 bg-slate-900/70 p-10 shadow-2xl shadow-blue-950/40">
            <div className="flex flex-col items-center gap-6 text-center">
              <div className="relative">
                <div
                  className={`absolute inset-0 rounded-full bg-gradient-to-br ${currentContent.accent} via-transparent to-transparent blur-xl opacity-70`}
                  aria-hidden
                />
                <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-slate-800/60 bg-slate-950/80">
                  {status === "loading" ? (
                    <currentContent.icon className="h-7 w-7 animate-spin text-blue-200" />
                  ) : (
                    <currentContent.icon className="h-7 w-7 text-blue-200" />
                  )}
                </div>
              </div>

              <div className="flex flex-col items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-slate-950/60 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-slate-500">
                  <ShieldCheck className="h-3.5 w-3.5 text-blue-300" />
                  {currentContent.badge}
                </span>
                <h2 className="text-2xl font-semibold text-slate-100 sm:text-3xl">
                  {currentContent.title}
                </h2>
                <p className="max-w-xl text-sm text-slate-400 sm:text-base">
                  {status === "error" && errorMessage
                    ? errorMessage
                    : currentContent.description}
                </p>
              </div>

              {status === "error" && (
                <div className="w-full rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4" />
                    <p>{errorMessage || "Something unexpected happened"}</p>
                  </div>
                </div>
              )}

              <div className="flex flex-col items-center gap-4">
                {status === "error" ? (
                  <button
                    onClick={() => router.push("/login")}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-blue-500/50 bg-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-blue-400"
                  >
                    Try sign-in again
                  </button>
                ) : (
                  <p className="text-xs text-slate-500">
                    This should take just a moment. We'll auto-redirect once
                    everything is ready.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <AuthCallbackContent />
    </Suspense>
  );
}

function LoadingFallback() {
  return (
    <Layout>
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full mb-4">
                <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Loading...
              </h2>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
