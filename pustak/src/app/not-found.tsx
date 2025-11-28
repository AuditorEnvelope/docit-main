import Link from "next/link";

export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-slate-100">
      <div className="space-y-6">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">404</h1>
        <p className="max-w-md text-sm text-slate-400 sm:text-base">
          We couldn&apos;t find the docbook you were looking for. Double-check the
          org slug or head back to the marketing site.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-full border border-slate-700/70 bg-slate-900/70 px-5 py-2 text-sm font-medium text-slate-200 transition hover:border-blue-400/60 hover:text-white"
          >
            Go to pustak.ai
          </Link>
          <a
            href="https://pustak.ai/contact"
            className="inline-flex items-center justify-center rounded-full border border-slate-700/70 px-5 py-2 text-sm font-medium text-slate-200 transition hover:border-blue-400/60 hover:text-white"
          >
            Contact support
          </a>
        </div>
      </div>
    </main>
  );
}
