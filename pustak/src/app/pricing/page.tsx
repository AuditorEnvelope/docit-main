import { Layout } from "@/components/Layout";
import {
  Check,
  Zap,
  Users,
  Building2,
  ShieldCheck,
  Sparkles,
  Crown,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Choose the perfect plan for your documentation needs',
};

export default function PricingPage() {
  const plans = [
    {
      name: "Starter",
      price: "$0",
      period: "/month",
      description: "Limited access tier with monthly doc credits",
      icon: Zap,
      accent: {
        border: "border-slate-800",
        glow: "from-blue-500/25 via-slate-950 to-transparent",
        iconBg: "bg-blue-500/10",
        iconColor: "text-blue-200",
        button: "bg-slate-800/80 hover:bg-slate-800 text-slate-100",
        chip: "text-blue-200",
      },
      features: [
        "1 repository ",
        "2 Docs generation per month",
        "Credits refresh every 30 days",
        "Community support & changelog",
        "Upgrade when you need more",
      ],
      cta: "Start for $0",
      href: "/signup",
      popular: false,
      badge: "Limited access",
    },
    {
      name: "Pro",
      price: "$29",
      period: "/month",
      description: "For professional developers and small teams",
      icon: Users,
      accent: {
        border: "border-purple-400/60",
        glow: "from-purple-500/30 via-slate-950 to-transparent",
        iconBg: "bg-purple-500/15",
        iconColor: "text-purple-200",
        button: "bg-purple-500 hover:bg-purple-400 text-white",
        chip: "text-purple-200",
      },
      features: [
        "5 repositories",
        "Unlimited searches",
        "AI-powered Q&A",
        "Advanced documentation",
        "Priority support",
        "Custom branding",
        "Version history",
      ],
      cta: "Start Free Trial",
      href: "/checkout?plan=pro",
      popular: true,
      badge: "Most popular",
    },
    {
      name: "Team",
      price: "$99",
      period: " /month",
      description: "For growing teams and organizations",
      icon: Building2,
      accent: {
        border: "border-emerald-400/50",
        glow: "from-emerald-500/25 via-slate-950 to-transparent",
        iconBg: "bg-emerald-500/15",
        iconColor: "text-emerald-200",
        button: "bg-emerald-500/90 hover:bg-emerald-400 text-white",
        chip: "text-emerald-200",
      },
      features: [
        "20 repositories",
        "Unlimited searches",
        "AI-powered Q&A",
        "Team collaboration",
        "Admin overlays",
        "SSO (SAML)",
        "Priority support",
        "Custom domain",
        "Advanced analytics",
      ],
      cta: "Start Free Trial",
      href: "/checkout?plan=team",
      popular: false,
      badge: "For scaling squads",
    },
    {
      name: "Enterprise",
      price: "$499",
      period: " /month",
      description: "For large organizations with custom needs",
      icon: Building2,
      accent: {
        border: "border-orange-400/60",
        glow: "from-orange-500/25 via-slate-950 to-transparent",
        iconBg: "bg-orange-500/15",
        iconColor: "text-orange-200",
        button: "bg-orange-500/90 hover:bg-orange-400 text-white",
        chip: "text-orange-200",
      },
      features: [
        "Unlimited repositories",
        "Unlimited everything",
        "Dedicated support",
        "SLA guarantee",
        "Custom integrations",
        "On-premise deployment",
        "Advanced security",
        "Custom training",
        "Account manager",
      ],
      cta: "Contact Sales",
      href: "/contact?plan=enterprise",
      popular: false,
      badge: "Custom programs",
    },
  ];

  return (
    <Layout>
      <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-[-10%] top-[-5%] h-[360px] w-[360px] rounded-full bg-purple-500/25 blur-[180px]" aria-hidden />
          <div className="absolute right-[-15%] top-[15%] h-[420px] w-[420px] rounded-full bg-blue-500/20 blur-[200px]" aria-hidden />
          <div className="absolute inset-x-0 bottom-[-25%] h-[420px] bg-gradient-to-t from-blue-500/15 via-slate-950 to-transparent" aria-hidden />
        </div>

        {/* Hero */}
        <section className="relative mx-auto flex max-w-6xl flex-col items-center gap-8 px-6 pb-20 pt-24 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/60 px-4 py-1 text-[11px] uppercase tracking-[0.42em] text-slate-300">
            <Sparkles className="h-3.5 w-3.5 text-blue-300" /> Pricing built for shipping teams
          </span>
          <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">
            Simple pricing tuned for documentation velocity
          </h1>
          <p className="max-w-2xl text-base text-slate-400 sm:text-lg">
            Every plan includes AI-assisted doc orchestration, GitHub-native workflows, and a 14-day free trial. Upgrade only when your team is ready to scale.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-slate-400">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-slate-900/70 px-3 py-1">
              <ShieldCheck className="h-4 w-4 text-emerald-300" /> SOC2-aligned security
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-800/70 bg-slate-900/70 px-3 py-1">
              <Crown className="h-4 w-4 text-purple-300" /> 5,000+ docs published this quarter
            </div>
          </div>
        </section>

        {/* Plan grid */}
        <section className="relative mx-auto max-w-6xl px-6">
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {plans.map((plan) => {
              const Icon = plan.icon;
              return (
                <div
                  key={plan.name}
                  className={`group relative overflow-hidden rounded-3xl border ${plan.accent.border} bg-gradient-to-br from-slate-950/80 via-slate-950 to-slate-950/60 p-8 shadow-[0_35px_120px_-65px_rgba(56,189,248,0.8)] transition duration-300 hover:-translate-y-2`}
                >
                  <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${plan.accent.glow} opacity-0 transition duration-500 group-hover:opacity-100`} aria-hidden />
                  <div className="relative flex h-full flex-col gap-6">
                    <div className="flex items-start justify-between">
                      <div className={`inline-flex items-center gap-3 rounded-2xl ${plan.accent.iconBg} px-3 py-2`}> 
                        <Icon className={`h-5 w-5 ${plan.accent.iconColor}`} />
                        <span className={`text-xs font-semibold uppercase tracking-[0.32em] ${plan.accent.chip}`}>
                          {plan.badge}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-2xl font-semibold text-slate-100">{plan.name}</h3>
                      <div className="flex items-baseline gap-2 text-slate-300">
                        <span className="text-4xl font-bold text-white">{plan.price}</span>
                        <span className="text-sm uppercase tracking-[0.28em] text-slate-500 whitespace-nowrap">{plan.period}</span>
                      </div>
                      <p className="text-sm text-slate-400">{plan.description}</p>
                    </div>

                    <div className="flex flex-1 flex-col gap-3 text-sm text-slate-300">
                      {plan.features.map((feature) => (
                        <div key={feature} className="inline-flex items-start gap-3">
                          <Check className={`mt-0.5 h-4 w-4 flex-shrink-0 ${plan.accent.iconColor}`} />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>

                    <Link
                      href={plan.href}
                      className={`mt-4 inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 ${plan.accent.button}`}
                    >
                      {plan.cta}
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Value adds */}
        <section className="relative mx-auto mt-20 max-w-6xl px-6">
          <div className="grid gap-6 lg:grid-cols-3">
            {[
              {
                title: "Rollout with confidence",
                description:
                  "Every paid plan includes guided onboarding, docbook templates, and publish checklists tailored to your repositories.",
                icon: ShieldCheck,
              },
              {
                title: "Usage-based scaling",
                description:
                  "Transparent seat controls, GitHub org segregation, and auto-archival keep billing predictable as teams grow.",
                icon: Users,
              },
              {
                title: "Enterprise friendly",
                description:
                  "Need SOC2 reports, DPA, or custom integrations? Our enterprise team handles procurement so your engineers ship docs sooner.",
                icon: Building2,
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.title}
                  className="group relative overflow-hidden rounded-3xl border border-slate-800/80 bg-slate-950/80 p-6 transition hover:border-blue-400/50"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-transparent opacity-0 transition duration-300 group-hover:opacity-100" aria-hidden />
                  <div className="relative flex flex-col gap-4">
                    <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900/80 text-blue-200">
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3 className="text-lg font-semibold text-slate-100">{card.title}</h3>
                    <p className="text-sm text-slate-400">{card.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* FAQ */}
        <section className="relative mx-auto mt-24 max-w-4xl px-6 pb-24">
          <div className="text-center">
            <h2 className="text-3xl font-semibold text-slate-100">Frequently asked questions</h2>
            <p className="mt-3 text-sm text-slate-500">
              Everything you need to know about billing, upgrades, and how trials work.
            </p>
          </div>
          <div className="mt-10 space-y-4">
            {[{
              question: "Can I change plans later?",
              answer:
                "Absolutely. Upgrade or downgrade at any time. We prorate remaining credit automatically and your team keeps working without interruption.",
            },
            {
              question: "What payment methods do you accept?",
              answer:
                "Stripe powers card payments worldwide. Enterprise customers can request invoicing, ACH transfers, or virtual cards depending on region.",
            },
            {
              question: "Do paid tiers include a free trial?",
              answer:
                "Yes—Pro and Team come with a 14-day trial. Spin up docbooks, ship docs, and cancel anytime inside billing settings.",
            },
            {
              question: "How does enterprise onboarding work?",
              answer:
                "Our solutions engineers help map your org structure, configure GitHub Apps, and run enablement sessions for up to three cohorts.",
            }].map(({ question, answer }) => (
              <details
                key={question}
                className="group rounded-3xl border border-slate-800/80 bg-slate-950/70 p-6 transition hover:border-blue-500/40"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-base font-semibold text-slate-100">
                  {question}
                  <span className="text-sm text-slate-500 transition group-open:rotate-90">→</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="relative overflow-hidden border-t border-slate-900/60">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500 opacity-20 blur-[180px]" aria-hidden />
          <div className="relative mx-auto flex max-w-5xl flex-col items-center gap-6 px-6 py-16 text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white">
              Trusted by product squads shipping weekly
            </span>
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">Ready to publish smarter documentation?</h2>
            <p className="max-w-2xl text-base text-slate-100/80 sm:text-lg">
              Start your free trial in minutes. Invite teammates, connect docbooks, and watch every deployment ship with review-ready docs.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/checkout?plan=pro"
                className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-50"
              >
                Start free trial
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/contact?plan=enterprise"
                className="inline-flex items-center gap-2 rounded-full border border-white/50 px-6 py-3 text-sm font-semibold text-white transition hover:border-white"
              >
                Talk to sales
              </Link>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
