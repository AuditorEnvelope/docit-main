// src/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const RAW_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || " https://cd17ff078a8e.ngrok-free.app";
const API_BASE = RAW_BACKEND_URL.endsWith("/api/v1")
  ? RAW_BACKEND_URL
  : `${RAW_BACKEND_URL.replace(/\/$/, "")}/api/v1`;

export async function middleware(request: NextRequest) {
  // 1. GET HOSTNAME SAFELY
  // Prefer the "Host" header which is more reliable behind proxies like Render/Cloudflare
  const hostHeader = request.headers.get("host") || "";
  const hostname = hostHeader.split(":")[0] || request.nextUrl.hostname;
  const pathname = request.nextUrl.pathname || "/";
  const method = request.method;
  const acceptHeader = request.headers.get("accept") || "";

  const isPrefetch = request.headers.get("purpose") === "prefetch";
  const isStaticAssetRequest =
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/robots") ||
    pathname.startsWith("/manifest") ||
    pathname.startsWith("/sitemap") ||
    pathname.startsWith("/404") ||
    /\.(?:css|js|mjs|json|ico|png|jpg|jpeg|gif|svg|webp|avif|txt|xml|woff|woff2|ttf|map)$/i.test(
      pathname
    );

  if (method === "OPTIONS" || isPrefetch || isStaticAssetRequest) {
    return NextResponse.next();
  }

  // 🔍 DEBUG LOGS (Check Render logs to see these!)
  console.log(`[Middleware] Processing: ${request.url}`);
  console.log(`[Middleware] Detected Hostname: ${hostname}`);

  const hostParts = hostname.split(".");
  let org: string | null = null;

  // 2. SUBDOMAIN EXTRACTION LOGIC
  if (hostname.includes("docbook.site")) {
    // Production: fakeorg.docbook.site -> ["fakeorg", "docbook", "site"]
    // We want to verify we actually HAVE a subdomain (length >= 3)
    if (hostParts.length >= 3 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  } else if (hostname.includes("localhost") || hostname.includes("127.0.0.1")) {
    // Local: org.localhost -> ["org", "localhost"]
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  } else {
    // Custom domain handling (future proofing)
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  }

  console.log(`[Middleware] Extracted Org: ${org}`);

  // 3. VALIDATION LOGIC
  const isHtmlRequest =
    method === "GET" &&
    (acceptHeader.includes("text/html") || acceptHeader === "*/*");

  if (org && isHtmlRequest) {
    // Check if this is a request for the root path or docs path
    // We generally want to intercept EVERYTHING on this subdomain

    try {
      const liveStatusUrl = `${API_BASE}/docbook/live-org-status?org_id=${encodeURIComponent(
        org
      )}`;
      console.log(`[Middleware] Validating against: ${liveStatusUrl}`);

      const validationResponse = await fetch(liveStatusUrl, {
        method: "GET",
        headers: {
          "User-Agent": "pustak-docbook-middleware",
        },
        cache: "no-store",
        // Add a timeout signal if possible to avoid hanging
      });

      if (!validationResponse.ok) {
        console.log(
          `[Middleware] ❌ Org '${org}' not found or not live. Rewriting to 404.`
        );

        // REWRITE TO 404 PAGE
        const notFoundUrl = request.nextUrl.clone();
        notFoundUrl.pathname = "/404";

        // We rewrite, not redirect, to keep the URL the same but show 404 content
        const response = NextResponse.rewrite(notFoundUrl, {
          status: 404,
        });
        response.headers.set("x-middleware-cache", "no-cache");
        return response;
      }

      console.log(`[Middleware] ✅ Org '${org}' is valid. Serving docs.`);

      let liveUrlPath = "";
      try {
        const parsed = (await validationResponse.json()) as {
          live_url?: string;
        };
        if (parsed?.live_url) {
          const liveUrl = new URL(parsed.live_url);
          liveUrlPath = liveUrl.pathname === "/" ? "" : liveUrl.pathname;
        }
      } catch (error) {
        console.warn(
          `[Middleware] Warning: unable to parse live status response for org '${org}':`,
          error
        );
      }

      // REWRITE TO DOCS PAGE
      const url = request.nextUrl.clone();
      const originalPath = pathname === "/" ? "" : pathname;

      if (!originalPath && liveUrlPath) {
        url.pathname = `/docs/${org}${liveUrlPath}`;
      } else if (!originalPath) {
        url.pathname = `/docs/${org}`;
      } else {
        url.pathname = `/docs/${org}${originalPath}`;
      }

      const response = NextResponse.rewrite(url);
      response.headers.set("x-middleware-cache", "no-cache");
      response.headers.set("x-org-id", org);
      return response;
    } catch (error) {
      console.error("[Middleware] 💥 Error validating org:", error);
      // In case of backend failure, we usually don't want to show the landing page.
      // Better to show an error or 404.
      const url = request.nextUrl.clone();
      url.pathname = "/404";
      return NextResponse.rewrite(url);
    }
  }

  // 4. LANDING PAGE FALLBACK
  // If no org subdomain, serve the landing page normally.
  console.log(
    "[Middleware] No subdomain detected. Passing through to landing page."
  );
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * - api routes (we don't want to intercept our own API calls)
     */
    "/((?!_next/static|_next/image|favicon.ico|api).*)",
  ],
};
