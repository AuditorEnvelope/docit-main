"use client";

import { Layout } from "@/components/Layout";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { startGitHubOAuth } from "@/lib/githubOAuth";
import {
  ArrowRight,
  BookOpen,
  GitBranch,
  Github,
  Link2,
  Rocket,
  Shield,
  Sparkles,
  Zap,
  Layers,
  Search,
  CircleDot,
  Mail,
} from "lucide-react";

export function HomePageClient() {
  const router = useRouter();

  const goApp = async () => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("DocIt_access_token")
        : null;
    if (token) {
      router.push("/dashboard");
      return;
    }
    try {
      await startGitHubOAuth();
    } catch (e) {
      console.error(e);
      alert("Failed to start GitHub sign-in. Please try again.");
    }
  };

  const features = [
    {
      icon: BookOpen,
      title: 'The "self-healing" docbook',
      description:
        "Architecture, runbooks, and API docs draft themselves from merges—review once, ship everywhere.",
    },
    {
      icon: Layers,
      title: "Zero-drift synchronization",
      description:
        "Webhooks keep staging aligned with GitHub. No phantom sections or stale screenshots.",
    },
    {
      icon: Shield,
      title: "Secure & GitHub-native",
      description:
        "Scoped installs, auditable flows, and permissions that mirror how your org already ships.",
    },
  ] as const;

  const steps = [
    {
      step: "01",
      icon: Link2,
      title: "Connect your repo",
      description:
        "Authorize DocIt once. We mirror structure and persona boundaries automatically.",
    },
    {
      step: "02",
      icon: Zap,
      title: "Ship commits like usual",
      description:
        "Every meaningful merge trains context-aware summaries—intent preserved, noise trimmed.",
    },
    {
      step: "03",
      icon: Rocket,
      title: "AI maintains momentum",
      description:
        "Draft changelog deltas and depth-first explanations into review queues you already trust.",
    },
  ] as const;

  return (
    <Layout>
      <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-[#030712] text-slate-100">
        {/* Ambient layers */}
        <div
          className="pointer-events-none absolute inset-0 landing-grid-bg landing-grid-drift opacity-[0.4]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute left-1/2 top-[-18%] h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.22)_0%,rgba(59,130,246,0.08)_45%,transparent_70%)] landing-animate-glow"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute right-[-8%] top-[35%] h-[340px] w-[340px] rounded-full bg-purple-500/15 blur-[100px]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-0 left-[-10%] h-[280px] w-[420px] rounded-full bg-cyan-500/10 blur-[90px]"
          aria-hidden
        />

        {/* Hero */}
        <section className="relative mx-auto flex max-w-6xl flex-col items-center px-4 pb-24 pt-12 text-center sm:px-6 sm:pb-28 sm:pt-16">
          {/* Hero logo mark — sized between nav and CTA for hierarchy */}
          {/* <div className="landing-hero-item-scale landing-hero-delay-1 relative mb-6">
            <Image
              src="/logo.png"
              alt="DocIt"
              width={78}
              height={78}
              className="relative h-14 w-14 rounded-xl object-cover sm:h-[4.2rem] sm:w-[4.2rem] sm:rounded-2xl"
              priority
            />
          </div> */}

          <div className="landing-hero-item landing-hero-delay-2 relative mb-8 inline-flex items-center gap-2 rounded-full border border-cyan-400/35 bg-cyan-400/5 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.35em] text-cyan-200/95 shadow-[0_0_28px_-8px_rgba(34,211,238,0.55)] transition duration-300 hover:border-cyan-400/50 hover:shadow-[0_0_36px_-6px_rgba(34,211,238,0.45)]">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-40" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
            </span>
            Live beta · ships with your commits
          </div>

          <h1 className="landing-hero-item landing-hero-delay-3 max-w-4xl text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl sm:leading-[1.06] lg:text-6xl lg:leading-[1.05]">
            Documentation that ships{" "}
            <span className="landing-animate-gradient bg-gradient-to-r from-cyan-300 via-sky-400 to-blue-500 bg-clip-text text-transparent [text-shadow:0_0_40px_rgba(34,211,238,0.15)]">
              as fast as your commits
            </span>
            .
          </h1>

          <div className="landing-hero-item landing-hero-delay-4 relative mt-8 max-w-2xl overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.03] px-6 py-5 backdrop-blur-md transition duration-500 hover:border-cyan-400/20">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/10 via-transparent to-blue-600/5" />
            <div className="landing-hero-line-pulse pointer-events-none absolute left-0 right-0 top-0 h-px overflow-hidden bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent" />
            <p className="relative text-sm leading-relaxed text-slate-300 sm:text-base">
              DocIt is your AI technical writer on GitHub—baseline docs,
              PR-aware updates, and review-ready publish flows without leaving
              the repo.
            </p>
          </div>

          <div className="landing-hero-item landing-hero-delay-5 relative mt-10 flex flex-col items-center gap-4 sm:flex-row sm:gap-5">
            <button
              type="button"
              onClick={goApp}
              className="cursor-pointer group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-slate-950 shadow-[0_0_40px_-10px_rgba(255,255,255,0.35)] transition hover:bg-cyan-50 hover:shadow-[0_0_48px_-8px_rgba(34,211,238,0.35)] active:scale-[0.98]"
            >
              <span className="pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100">
                <span className="absolute inset-0 translate-x-[-100%] bg-gradient-to-r from-transparent via-white/40 to-transparent duration-700 group-hover:translate-x-[100%] cursor-pointer" />
              </span>
              Open DocIt
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </button>
            <button
              type="button"
              onClick={() => {
                document.getElementById("features")?.scrollIntoView({
                  behavior: "smooth",
                });
              }}
              className="cursor-pointer inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-slate-200 backdrop-blur-sm transition hover:border-cyan-400/35 hover:bg-cyan-400/10 hover:text-white active:scale-[0.98]"
            >
              Explore product
            </button>
          </div>

          <p className="landing-hero-item landing-hero-delay-6 mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5 transition hover:text-slate-400">
              <Shield className="h-3.5 w-3.5 text-cyan-500/70" />
              GitHub-native installs
            </span>
            <span className="inline-flex items-center gap-1.5 transition hover:text-slate-400">
              <Sparkles className="h-3.5 w-3.5 text-cyan-500/70" />
              Multi-org aware
            </span>
          </p>
        </section>

        {/* Product spotlight + mock */}
        <section className="relative mx-auto max-w-6xl px-4 pb-24 sm:px-6">
          <div className="mb-6 flex justify-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-200/90">
              <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
              AI-powered
            </span>
          </div>

          <div className="relative overflow-hidden rounded-3xl border border-cyan-400/25 bg-gradient-to-b from-white/[0.06] to-transparent p-[1px] shadow-[0_0_60px_-20px_rgba(34,211,238,0.45)]">
            <div className="rounded-[22px] bg-[#050b14]/95 p-6 sm:p-10">
              <div className="flex flex-col items-center gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex max-w-xl flex-col items-center text-center lg:items-start lg:text-left">
                  <div className="mb-4 flex items-center gap-3 text-cyan-300/90">
                    <GitBranch className="h-6 w-6" />
                    <span className="h-px w-12 bg-gradient-to-r from-cyan-400/60 to-transparent sm:w-20" />
                    <BookOpen className="h-6 w-6" />
                  </div>
                  <h2 className="text-2xl font-semibold text-white sm:text-3xl">
                    Git commit → AI documentation
                  </h2>
                  <p className="mt-3 text-sm text-slate-400 sm:text-base">
                    Watch merges flow into polished docbooks—summaries,
                    diagrams, and callouts aligned to how your team actually
                    ships.
                  </p>
                </div>

                {/* Mini mock browser */}
                <div className="landing-animate-float w-full max-w-md rounded-xl border border-white/10 bg-[#020817] shadow-2xl shadow-cyan-950/40">
                  <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2.5">
                    <span className="flex gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                      <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                    </span>
                    <div className="mx-auto flex flex-1 items-center gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5">
                      <Search className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                      <span className="truncate text-[11px] text-slate-500">
                        Search docbook or ask DocIt…
                      </span>
                    </div>
                    <span className="flex shrink-0 items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                      <CircleDot className="h-3 w-3 text-emerald-400" />
                      synced
                    </span>
                  </div>
                  <div className="flex gap-0">
                    <div className="w-[28%] border-r border-white/10 p-3">
                      <p className="mb-2 text-[9px] font-semibold uppercase tracking-widest text-slate-500">
                        Workspace
                      </p>
                      <div className="space-y-1">
                        {["Quickstart", "Changelog", "Architecture"].map(
                          (item, i) => (
                            <div
                              key={item}
                              className={`rounded-md px-2 py-1.5 text-[11px] ${
                                i === 0
                                  ? "border border-cyan-400/35 bg-cyan-400/15 text-white"
                                  : "text-slate-500"
                              }`}
                            >
                              {item}
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                    <div className="flex-1 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                        Docbook preview
                      </p>
                      <p className="mt-1 text-sm font-medium text-white">
                        Generated from your repo
                      </p>
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        <div className="rounded-lg border border-cyan-400/40 bg-cyan-400/10 p-2">
                          <p className="text-[10px] font-semibold text-cyan-100">
                            From PR to page
                          </p>
                          <p className="mt-0.5 text-[9px] text-cyan-200/70">
                            Intent-aware summaries
                          </p>
                        </div>
                        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">
                          <p className="text-[10px] font-semibold text-slate-300">
                            Always current
                          </p>
                          <p className="mt-0.5 text-[9px] text-slate-500">
                            Webhook-backed
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section
          id="features"
          className="relative mx-auto max-w-6xl scroll-mt-24 px-4 pb-24 sm:px-6"
        >
          <div className="mb-12 text-center">
            <span className="text-[11px] font-semibold uppercase tracking-[0.32em] text-cyan-400/80">
              Trust layer
            </span>
            <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
              Built for teams who ship continuously
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm text-slate-400 sm:text-base">
              Same discipline as your CI/CD pipeline—docs become versioned,
              reviewable artifacts attached to real commits.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {features.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="group relative overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.02] p-6 transition duration-300 hover:border-cyan-400/30 hover:shadow-[0_0_40px_-18px_rgba(34,211,238,0.35)]"
              >
                <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-cyan-400/10 blur-2xl transition group-hover:bg-cyan-400/20" />
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/25 bg-cyan-400/10 text-cyan-200 shadow-[0_0_24px_-8px_rgba(34,211,238,0.5)]">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section
          id="how-it-works"
          className="relative border-y border-white/[0.06] bg-[#020817]/80 py-24"
        >
          <div className="pointer-events-none absolute inset-0 landing-grid-bg opacity-20" />
          <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
            <div className="mb-14 text-center">
              <span className="inline-flex items-center rounded-full border border-cyan-400/25 bg-cyan-400/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-200/90">
                Flow
              </span>
              <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
                Three steps from repo to polished docs
              </h2>
              <p className="mx-auto mt-4 max-w-2xl text-sm text-slate-400 sm:text-base">
                Your engineers keep pushing—we capture intent and translate it
                into trustworthy narratives your whole org can read.
              </p>
            </div>

            <div className="grid gap-8 md:grid-cols-3">
              {steps.map(({ step, icon: Icon, title, description }) => (
                <div key={step} className="relative text-center md:text-left">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-400/20 bg-gradient-to-br from-cyan-400/15 to-transparent text-cyan-200 shadow-[0_0_32px_-12px_rgba(34,211,238,0.45)] md:mx-0">
                    <Icon className="h-6 w-6" />
                  </div>
                  <span className="font-mono text-xs font-medium text-cyan-400/70">
                    {step}
                  </span>
                  <h3 className="mt-2 text-xl font-semibold text-white">
                    {title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section
          id="cta"
          className="relative mx-auto max-w-6xl scroll-mt-24 px-4 py-24 sm:px-6"
        >
          <div className="relative overflow-hidden rounded-3xl border border-cyan-400/20 bg-gradient-to-br from-cyan-400/[0.08] via-[#050b14] to-blue-600/[0.06] px-8 py-16 text-center sm:px-14">
            <div className="pointer-events-none absolute inset-0 opacity-40">
              <div className="absolute left-1/2 top-1/2 h-[120%] w-[120%] -translate-x-1/2 -translate-y-1/2 bg-[radial-gradient(circle,rgba(34,211,238,0.12)_0%,transparent_55%)]" />
            </div>
            {/* <div className="relative mx-auto mb-6 flex justify-center">
              <Image
                src="/logo.png"
                alt="DocIt"
                width={128}
                height={128}
                className="landing-logo-mark h-24 w-24 rounded-2xl object-cover ring-2 ring-cyan-400/35 shadow-[0_0_48px_-10px_rgba(34,211,238,0.55)] sm:h-28 sm:w-28 sm:rounded-[1.35rem]"
                priority
              />
            </div> */}
            <span className="relative inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.35em] text-cyan-100/90">
              Early access
            </span>
            <h2 className="relative mt-6 text-3xl font-semibold text-white sm:text-5xl">
              Ready when{" "}
              <span className="bg-gradient-to-r from-cyan-300 to-sky-400 bg-clip-text text-transparent">
                you are
              </span>
            </h2>
            <p className="relative mx-auto mt-4 max-w-xl text-sm text-slate-300 sm:text-base">
              Spin up DocIt on GitHub in minutes—staging docs, review queues,
              and publish paths included.
            </p>
            <div className="relative mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                type="button"
                onClick={goApp}
                className="inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-slate-950 shadow-lg transition hover:bg-cyan-50 cursor-pointer"
              >
                Continue with GitHub
                <Github className="h-4 w-4 " />
              </button>
            </div>
            <p className="relative mt-8 text-xs text-slate-500">
              Free tier · No credit card to explore · Built for production teams
            </p>
          </div>
        </section>

        {/* Footer — whitelist-style multi-column */}
        <footer className="border-t border-white/[0.06] bg-[#020617] px-4 pb-8 pt-14 sm:px-6">
          <div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-2 lg:grid-cols-12 lg:gap-10">
            {/* Brand + description */}
            <div className="lg:col-span-5">
              <div className="flex items-start gap-3">
                <Image
                  src="/logo.png"
                  alt=""
                  width={40}
                  height={40}
                  className="h-9 w-9 shrink-0 rounded-lg object-cover -mt-2"
                />
                <div>
                  <p className="text-lg font-bold tracking-tight text-white">
                    DocIt
                  </p>
                  <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-400">
                    Documentation that ships with your commits. Living docbooks
                    from GitHub—accurate, auditable, and actually fun to read.
                  </p>
                  <p className="mt-3 text-xs font-semibold uppercase tracking-[0.2em] text-sky-400">
                    Beta · Whitelist open
                  </p>
                </div>
              </div>

              <div className="mt-8">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                  Contact
                </p>
                <a
                  href="mailto:hello@docit.in"
                  className="mt-2 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-sky-400"
                >
                  <Mail className="h-4 w-4 shrink-0 text-slate-500" />
                  hello@docit.in
                </a>
              </div>
            </div>

            {/* Product */}
            <div className="lg:col-span-3 lg:pl-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                Product
              </p>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li>
                  <a href="#features" className="transition hover:text-white">
                    Features
                  </a>
                </li>
                <li>
                  <a
                    href="#how-it-works"
                    className="transition hover:text-white"
                  >
                    How it works
                  </a>
                </li>
                <li>
                  <a
                    href="https://whitelist.docit.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="transition hover:text-white"
                  >
                    Whitelist
                  </a>
                </li>
                <li>
                  <a href="#cta" className="transition hover:text-white">
                    Ready when you are
                  </a>
                </li>
              </ul>
            </div>

            {/* Legal */}
            <div className="lg:col-span-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                Legal
              </p>
              <ul className="mt-4 space-y-3 text-sm text-slate-400">
                <li>
                  <span className="cursor-not-allowed text-slate-500">
                    Privacy <span className="text-slate-600">(soon)</span>
                  </span>
                </li>
                <li>
                  <span className="cursor-not-allowed text-slate-500">
                    Terms <span className="text-slate-600">(soon)</span>
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mx-auto mt-14 max-w-6xl border-t border-white/[0.06] pt-8">
            <div className="flex flex-col items-center justify-between gap-4 text-[11px] text-slate-600 sm:flex-row">
              <p>© {new Date().getFullYear()} DocIt. All rights reserved.</p>
              <p>Built for teams who ship in public.</p>
            </div>
          </div>
        </footer>
      </div>
    </Layout>
  );
}

export default HomePageClient;
