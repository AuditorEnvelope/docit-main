"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Layout } from "@/components/Layout";
import {
  Github,
  Loader2,
  Sparkles,
  Zap,
  ShieldCheck,
  Globe2,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { startGitHubOAuth } from "@/lib/githubOAuth";

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, loading } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const highlightPills = [
    {
      icon: Sparkles,
      label: "AI doc orchestration",
    },
    {
      icon: ShieldCheck,
      label: "Secure by design",
    },
    {
      icon: Globe2,
      label: "Multi-org ready",
    },
  ];

  const benefitItems = [
    {
      icon: Zap,
      title: "Instant documentation",
      description:
        "Generate architecture, workflow, and changelog docs right after every push.",
      accent: "from-blue-500/25",
    },
    {
      icon: Github,
      title: "Native GitHub integration",
      description:
        "Connect once to sync installations, docbooks, and approvals across orgs.",
      accent: "from-purple-500/25",
    },
    {
      icon: ShieldCheck,
      title: "Secure & transparent",
      description:
        "We respect repository boundaries—your commits stay authored by you.",
      accent: "from-emerald-500/30",
    },
  ];

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, loading, router]);

  const handleGitHubLogin = async () => {
    setIsLoggingIn(true);

    try {
      await startGitHubOAuth();
    } catch (error) {
      console.error("Login error:", error);
      setIsLoggingIn(false);
      alert("Failed to start login. Please try again.");
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
        <div className="absolute inset-0">
          <div
            className="absolute left-[-10%] top-[10%] h-[380px] w-[380px] rounded-full bg-blue-600/35 blur-[160px]"
            aria-hidden
          />
          <div
            className="absolute right-[-5%] top-[25%] h-[320px] w-[320px] rounded-full bg-purple-500/30 blur-[160px]"
            aria-hidden
          />
          <div
            className="absolute inset-x-0 bottom-[-25%] h-[420px] bg-gradient-to-b from-transparent via-blue-500/10 to-blue-500/5"
            aria-hidden
          />
        </div>

        <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 py-16">
          <div className="w-full max-w-3xl text-center">
            <div className="mx-auto flex w-fit items-center gap-2 rounded-full border border-blue-400/40 bg-blue-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.4em] text-blue-100">
              DocIt
            </div>
            <h1 className="mt-6 text-4xl font-semibold leading-tight sm:text-5xl">
              Welcome to the docbook automation hub
            </h1>
            <p className="mt-4 text-sm text-slate-300 sm:text-base">
              Connect GitHub, ship docs with confidence. DocIt brings AI-powered
              documentation flows, review gates, and publishing automation into
              one staging pipeline.
            </p>

            <div className="mt-8 flex flex-wrap justify-center gap-3">
              {highlightPills.map((pill) => {
                const PillIcon = pill.icon;
                return (
                  <span
                    key={pill.label}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-slate-900/70 px-4 py-2 text-[12px] uppercase tracking-[0.24em] text-slate-300"
                  >
                    <PillIcon className="h-3.5 w-3.5 text-blue-300" />
                    {pill.label}
                  </span>
                );
              })}
            </div>
          </div>

          <div className="mt-14 w-full max-w-3xl rounded-3xl border border-slate-900/60 bg-slate-900/70 p-10 shadow-xl shadow-blue-950/40">
            <div className="grid gap-6 sm:grid-cols-3">
              {benefitItems.map((benefit) => {
                const BenefitIcon = benefit.icon;
                return (
                  <div
                    key={benefit.title}
                    className="group relative overflow-hidden rounded-2xl border border-slate-800/60 bg-slate-950/60 p-5 text-left transition hover:border-blue-500/40 hover:bg-slate-950/80"
                  >
                    <div
                      className={`absolute inset-0 bg-gradient-to-br ${benefit.accent} via-transparent to-transparent opacity-0 transition duration-300 group-hover:opacity-90`}
                      aria-hidden
                    />
                    <div className="relative flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900/80 text-blue-200">
                        <BenefitIcon className="h-5 w-5" />
                      </span>
                      <h3 className="text-sm font-semibold text-slate-100">
                        {benefit.title}
                      </h3>
                    </div>
                    <p className="relative mt-3 text-sm text-slate-400">
                      {benefit.description}
                    </p>
                  </div>
                );
              })}
            </div>

            <div className="mt-10 flex flex-col items-center gap-4">
              <button
                onClick={handleGitHubLogin}
                disabled={isLoggingIn}
                className="group inline-flex w-full items-center justify-center gap-3 rounded-2xl bg-blue-500 px-6 py-4 text-sm font-semibold text-white shadow-lg transition hover:bg-blue-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
              >
                {isLoggingIn ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Connecting to GitHub...
                  </>
                ) : (
                  <>
                    <Github className="h-5 w-5" />
                    Continue with GitHub
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1 cursor-pointer" />
                  </>
                )}
              </button>

              <p className="text-xs text-slate-500">
                By continuing you agree to our{" "}
                <a
                  href="/terms"
                  className="underline decoration-dotted underline-offset-4 hover:text-slate-300"
                >
                  Terms of Service
                </a>{" "}
                and{" "}
                <a
                  href="/privacy"
                  className="underline decoration-dotted underline-offset-4 hover:text-slate-300"
                >
                  Privacy Policy
                </a>
                .
              </p>
            </div>
          </div>

          <div className="mt-10 text-center text-sm text-slate-400">
            🎉 Start with our{" "}
            <span className="font-semibold text-blue-300">Free plan</span> — no
            credit card required
          </div>
        </div>
      </div>
    </Layout>
  );
}
