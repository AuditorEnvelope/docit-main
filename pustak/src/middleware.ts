// src/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { mapPublicRouteToRepoPath } from "@/lib/docsPathMapper";

const RAW_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "https://cd17ff078a8e.ngrok-free.app";
const API_BASE = RAW_BACKEND_URL.endsWith("/api/v1")
  ? RAW_BACKEND_URL
  : `${RAW_BACKEND_URL.replace(/\/$/, "")}/api/v1`;

const buildRenderDocsPath = (
  org: string,
  repo: string,
  persona: string,
  segments: string[] = [],
) => {
  const sanitizedSegments = segments.filter(
    (segment) => segment && segment.trim().length > 0,
  );
  if (sanitizedSegments.length === 0) {
    return `/render-docs/${org}/${repo}/${persona}`;
  }
  return `/render-docs/${org}/${repo}/${persona}/${sanitizedSegments.join("/")}`;
};

export async function middleware(request: NextRequest) {
  const { search, origin } = request.nextUrl;

  console.log(`[DOCS_DEBUG] 🚀 MIDDLEWARE START - URL: ${request.url}`);

  // 1. GET HOSTNAME AND PATHNAME SAFELY
  // Check multiple headers for hostname (Render/Cloudflare proxies may use different headers)
  const hostHeader = request.headers.get("host") || "";
  const xForwardedHost = request.headers.get("x-forwarded-host") || "";
  const xOriginalHost = request.headers.get("x-original-host") || "";

  // Try headers in order of preference
  let hostname =
    xOriginalHost || xForwardedHost || hostHeader || request.nextUrl.hostname;
  hostname = hostname.split(":")[0]; // Remove port if present

  const pathname = request.nextUrl.pathname || "/";
  const method = request.method;
  const acceptHeader = request.headers.get("accept") || "";

  console.log(`[DOCS_DEBUG] 📌 Pathname: ${pathname}`);
  console.log(`[DOCS_DEBUG] 🔍 Host header: ${hostHeader}`);
  console.log(`[DOCS_DEBUG] 🔍 X-Forwarded-Host: ${xForwardedHost}`);
  console.log(`[DOCS_DEBUG] 🔍 X-Original-Host: ${xOriginalHost}`);
  console.log(
    `[DOCS_DEBUG] 🔍 request.nextUrl.hostname: ${request.nextUrl.hostname}`,
  );
  console.log(`[DOCS_DEBUG] 🔍 request.url: ${request.url}`);
  console.log(`[DOCS_DEBUG] 🔍 Final hostname: ${hostname}`);
  console.log(`[DOCS_DEBUG] 🔍 Search params: ${search}`);
  console.log(`[DOCS_DEBUG] 🌐 Origin: ${origin}`);
  console.log(
    `[DOCS_DEBUG] 🔍 All headers:`,
    JSON.stringify(Object.fromEntries(request.headers)),
  );

  const isPrefetch = request.headers.get("purpose") === "prefetch";
  const isStaticAssetRequest =
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/robots") ||
    pathname.startsWith("/manifest") ||
    pathname.startsWith("/sitemap") ||
    pathname.startsWith("/404") ||
    /\.(?:css|js|mjs|json|ico|png|jpg|jpeg|gif|svg|webp|avif|txt|xml|woff|woff2|ttf|map)$/i.test(
      pathname,
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

  // if (hostname.includes("docbook.site")) {
  if (hostname.includes("docit.in")) {

    // Production: fakeorg.docbook.site -> ["fakeorg", "docbook", "site"]
    // We want to verify we actually HAVE a subdomain (length >= 3)
    // Special case: www subdomain should be treated as the main portal, not an org
    if (hostParts.length >= 3 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 3 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(
        `[Middleware] 🌐 www subdomain detected - treating as main portal`,
      );
      // No org extraction needed - this is the main portal
    }
  } else if (hostname.includes("localhost") || hostname.includes("127.0.0.1")) {
    // Local: org.localhost -> ["org", "localhost"]
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 2 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(
        `[Middleware] 🌐 www subdomain detected on localhost - treating as main portal`,
      );
      // No org extraction needed - this is the main portal
    }
  } else {
    // Custom domain handling (future proofing)
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 2 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(
        `[Middleware] 🌐 www subdomain detected on custom domain - treating as main portal`,
      );
      // No org extraction needed - this is the main portal
    }
  }

  console.log(`[Middleware] Extracted Org: ${org}`);

  // 3. VALIDATION LOGIC
  const isHtmlRequest =
    (method === "GET" || method === "HEAD") &&
    (acceptHeader.includes("text/html") ||
      acceptHeader.includes("*/*") ||
      !acceptHeader);

  console.log(
    `[Middleware] Request meta -> method=${method}, accept='${acceptHeader}', isHtmlRequest=${isHtmlRequest}`,
  );

  if (org && isHtmlRequest) {
    // Check if this is a request for the root path or docs path
    // We generally want to intercept EVERYTHING on this subdomain

    try {
      const liveStatusUrl = `${API_BASE}/docbook/live-org-status?org_id=${encodeURIComponent(
        org,
      )}`;
      console.log(`[Middleware] 🔍 Checking live status for org: ${org}`);

      const validationResponse = await fetch(liveStatusUrl, {
        headers: {
          "Content-Type": "application/json",
        },
        next: { revalidate: 60 }, // Cache for 60 seconds
      });

      if (!validationResponse.ok) {
        console.log(
          `[Middleware] ❌ Org '${org}' not found or not live. Rewriting to 404.`,
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

      // Log the successful validation
      console.log(`[Middleware] ✅ Org '${org}' is valid and live.`);

      console.log(`[Middleware] ✅ Org '${org}' is valid. Serving docs.`);

      const alreadyDocsPath =
        pathname === `/docs/${org}` ||
        pathname.startsWith(`/docs/${org}/`) ||
        pathname === `/render-docs/${org}` ||
        pathname.startsWith(`/render-docs/${org}/`);

      if (alreadyDocsPath) {
        console.log(
          `[Middleware] ✅ Path already rewritten (${pathname}). Passing through.`,
        );
        const response = NextResponse.next({ request });
        response.headers.set("x-middleware-cache", "no-cache");
        response.headers.set("x-org-id", org);
        return response;
      }

      let liveUrlPath = "";
      let repoExists = false;
      try {
        const parsed = (await validationResponse.json()) as {
          live_url?: string;
          repos?: string[];
        };

        // Extract repo information from response
        const availableRepos = parsed?.repos || [];

        const pathSegments =
          pathname === "/" ? [] : pathname.split("/").filter(Boolean);
        const requestedRepo = pathSegments[0] || "";
        if (requestedRepo) {
          if (availableRepos.includes(requestedRepo)) {
            repoExists = true;
            console.log(
              `[Middleware] ✅ Repo '${requestedRepo}' listed for org '${org}'`,
            );
          } else {
            console.log(
              `[Middleware] ⚠️ Repo '${requestedRepo}' not present in backend list. Proceeding anyway.`,
            );
          }
        }

        if (parsed?.live_url) {
          const liveUrl = new URL(parsed.live_url);
          liveUrlPath = liveUrl.pathname === "/" ? "" : liveUrl.pathname;
          console.log(`[Middleware] 🔍 Found live URL path: ${liveUrlPath}`);
        } else {
          console.log(`[Middleware] ⚠️ No live URL found in response`);
        }
      } catch (error) {
        console.warn(
          `[Middleware] ⚠️ Error parsing live URL: ${error}. Continuing with empty path.`,
        );
      }

      // REWRITE TO DOCS PAGE
      const url = request.nextUrl.clone();
      const originalPath = pathname === "/" ? "" : pathname;

      // Parse path to extract repo and possibly persona
      const pathSegments = originalPath.split("/").filter(Boolean);

      // IMPORTANT: First segment is ALWAYS the repo name in the subdomain pattern
      const repoName = pathSegments[0] || ""; // First segment is repo name

      console.log(
        `[Middleware] 🔍 Path segments: ${JSON.stringify(pathSegments)}, repoName: ${repoName}`,
      );
      console.log(`[Middleware] 🔍 Original URL: ${request.url}`);
      console.log(`[Middleware] 🔍 Subdomain org: ${org}, repo: ${repoName}`);

      // Special case for settings path or any path with "settings" in it
      if (
        originalPath.includes("/settings") ||
        repoName === "settings" ||
        pathSegments.includes("settings")
      ) {
        console.log(`[Middleware] ⚠️ Settings path detected: ${originalPath}`);

        // For any settings path, redirect to the main app domain
        // This is a safety measure to prevent settings paths from being processed as documentation
        const settingsUrl = new URL(request.url);

        // Remove the subdomain to get back to the main app domain
        if (hostname.includes(".")) {
          settingsUrl.hostname = hostname.replace(/^[^.]+\./, ""); // Remove subdomain

          // Keep the original path - the main app will handle it correctly
          console.log(
            `[Middleware] 🔄 Redirecting settings path to main app: ${settingsUrl.toString()}`,
          );
          return NextResponse.redirect(settingsUrl);
        }
      }

      // CRITICAL FIX: For subdomain access, we must ensure:
      // 1. repo_id is ALWAYS the first path segment (not 'docs')
      // 2. persona is ALWAYS a valid value (not the org name)

      console.log(`[DOCS_DEBUG] 📚 Starting URL rewriting logic`);
      console.log(
        `[DOCS_DEBUG] 📚 originalPath=${originalPath}, liveUrlPath=${liveUrlPath}, repoName=${repoName}`,
      );

      if (!originalPath && liveUrlPath) {
        // Homepage with live URL path returned from backend
        const normalizedPath = liveUrlPath.replace(/^\/+/, "");
        const liveSegmentsRaw = normalizedPath.split("/").filter(Boolean);
        if (
          liveSegmentsRaw[0] === "docs" ||
          liveSegmentsRaw[0] === "render-docs"
        ) {
          liveSegmentsRaw.shift();
        }

        const liveRepo = liveSegmentsRaw[0] || "";
        const liveSlugSegments = liveSegmentsRaw.slice(1);

        console.log(
          `[DOCS_DEBUG] 📚 Case 1: Normalized live URL path -> repo=${liveRepo}, segments=${JSON.stringify(liveSlugSegments)}`,
        );

        if (!liveRepo) {
          // Default to a generic docs page for the org
          url.pathname = `/dashboard`;
          console.log(
            `[DOCS_DEBUG] 📚 Case 1: Live URL path missing repo. Redirecting to dashboard: ${url.pathname}`,
          );
        } else {
          const mapping = mapPublicRouteToRepoPath({
            repo: liveRepo,
            slug: liveSlugSegments,
          });

          if (mapping.persona === "internal") {
            const authToken =
              request.cookies.get("DocIt_access_token")?.value ||
              request.headers.get("authorization")?.replace("Bearer ", "");

            if (!authToken) {
              console.log(
                `[Middleware] ⚠️ Unauthorized access attempt to internal docs for ${liveRepo} from live URL`,
              );
              const loginUrl = request.nextUrl.clone();
              loginUrl.pathname = "/login";
              loginUrl.searchParams.set("redirect", request.url);
              return NextResponse.redirect(loginUrl);
            }
          }

          url.pathname = buildRenderDocsPath(
            org,
            liveRepo,
            mapping.persona,
            mapping.renderSlug,
          );
          console.log(
            `[DOCS_DEBUG] 📚 Case 1: Homepage with live URL path -> ${url.pathname} (canonical=${JSON.stringify(mapping.canonicalSlug)})`,
          );
        }
      } else if (!originalPath) {
        // Homepage without live URL path - redirect to dashboard
        // Since we need repo and persona for the new route pattern, we can't just go to /docs/${org}
        // Instead, we'll redirect to the dashboard where the user can select a repo
        url.pathname = `/dashboard`;
        console.log(
          `[DOCS_DEBUG] 📚 Case 2: Homepage without live URL path -> ${url.pathname}`,
        );
      } else if (repoName) {
        // We have a repo name from the first path segment
        console.log(`[DOCS_DEBUG] 📚 Case 3: We have a repo name: ${repoName}`);

        // Check if this repo exists in the available repos list or matches the live URL path
        const liveUrlRepo = liveUrlPath
          ? liveUrlPath.split("/").filter(Boolean)[0]
          : null;
        const isValidRepo =
          repoExists || (liveUrlRepo && liveUrlRepo === repoName);
        console.log(
          `[Middleware] 🔍 Repo validation (non-blocking): repoName=${repoName}, liveUrlRepo=${liveUrlRepo}, isValidRepo=${isValidRepo}`,
        );

        const slugSegments = pathSegments.slice(1);
        const mapping = mapPublicRouteToRepoPath({
          repo: repoName,
          slug: slugSegments,
        });

        if (mapping.persona === "internal") {
          const authToken =
            request.cookies.get("DocIt_access_token")?.value ||
            request.headers.get("authorization")?.replace("Bearer ", "");

          if (!authToken) {
            console.log(
              `[Middleware] ⚠️ Unauthorized access attempt to internal docs for ${repoName}`,
            );
            const loginUrl = request.nextUrl.clone();
            loginUrl.pathname = "/login";
            loginUrl.searchParams.set("redirect", request.url);
            return NextResponse.redirect(loginUrl);
          }
          console.log(
            `[Middleware] ✅ Authorized access to internal docs for ${repoName}`,
          );
        }

        url.pathname = buildRenderDocsPath(
          org,
          repoName,
          mapping.persona,
          mapping.renderSlug,
        );

        console.log(
          `[DOCS_DEBUG] 📚 Case 3: Mapping slug -> repo=${repoName}, persona=${mapping.persona}, renderSlug=${JSON.stringify(
            mapping.renderSlug,
          )}, canonical=${JSON.stringify(mapping.canonicalSlug)}`,
        );
        console.log(`[Middleware] 📝 Rewriting to: ${url.pathname}`);
      } else {
        // Fallback - redirect to dashboard instead of using docs path
        url.pathname = `/dashboard`;
        console.log(
          `[DOCS_DEBUG] 📚 Case 4: Fallback redirecting to dashboard: ${url.pathname}`,
        );
      }

      // Add additional debugging headers to help diagnose issues
      console.log(`[Middleware] 🚀 Final rewrite URL: ${url.toString()}`);

      // Check if the URL contains 'render-docs' to ensure we're using the new path
      if (!url.pathname.includes("/render-docs/")) {
        console.warn(
          `[Middleware] ⚠️ WARNING: URL does not contain /render-docs/ path: ${url.pathname}`,
        );
      }

      const response = NextResponse.rewrite(url);
      response.headers.set("x-middleware-cache", "no-cache");
      response.headers.set("x-org-id", org);
      response.headers.set("x-middleware-rewrite-path", url.pathname);
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

  // Special handling for /repo/settings path on www subdomain or localhost
  if (
    (hostname.startsWith("www.") ||
      hostname === "www.localhost" ||
      hostname === "www.127.0.0.1") &&
    pathname.startsWith("/repo/settings")
  ) {
    console.log(
      `[Middleware] 🔍 Settings path detected on www domain: ${pathname}`,
    );
    // This is already on the main domain, so just pass through
    return NextResponse.next();
  }

  // 4. LANDING PAGE FALLBACK
  // If no org subdomain, serve the landing page normally.
  console.log(
    org
      ? `[Middleware] ⚠️ Skipping org rewrite because isHtmlRequest=${isHtmlRequest}`
      : "[Middleware] No subdomain detected. Passing through to landing page.",
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
