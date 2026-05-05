import Link from "next/link";

export default function NotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-slate-950 px-6 text-center text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.25),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(168,85,247,0.2),_transparent_55%)]" />
      <div className="relative z-10 w-full max-w-lg space-y-8 rounded-3xl border border-white/10 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-sm">
        <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-slate-300">
          404
        </span>
        <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
          This docbook isn&apos;t published yet
        </h1>
        <p className="text-sm text-slate-300 sm:text-base">
          We couldn&apos;t find an active publication for this subdomain.
          Double-check the org slug or ask the admin to publish the docs again.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/10 px-5 py-2 text-sm font-medium text-white transition hover:border-blue-400/70 hover:bg-blue-500/20"
          >
            View marketing site
          </Link>
          <a
            href="https://DocIt.ai/contact"
            className="inline-flex items-center justify-center rounded-full border border-white/10 px-5 py-2 text-sm font-medium text-slate-200 transition hover:border-blue-400/70 hover:text-white"
          >
            Contact support
          </a>
        </div>
      </div>
    </main>
  );
}
