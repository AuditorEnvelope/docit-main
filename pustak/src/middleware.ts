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
    // Special case: www subdomain should be treated as the main portal, not an org
    if (hostParts.length >= 3 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 3 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(`[Middleware] 🌐 www subdomain detected - treating as main portal`);
      // No org extraction needed - this is the main portal
    }
  } else if (hostname.includes("localhost") || hostname.includes("127.0.0.1")) {
    // Local: org.localhost -> ["org", "localhost"]
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 2 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(`[Middleware] 🌐 www subdomain detected on localhost - treating as main portal`);
      // No org extraction needed - this is the main portal
    }
  } else {
    // Custom domain handling (future proofing)
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    } else if (hostParts.length >= 2 && hostParts[0] === "www") {
      // www subdomain - treat as main portal
      console.log(`[Middleware] 🌐 www subdomain detected on custom domain - treating as main portal`);
      // No org extraction needed - this is the main portal
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

      const alreadyDocsPath =
        pathname === `/docs/${org}` || pathname.startsWith(`/docs/${org}/`);

      if (alreadyDocsPath) {
        console.log(
          `[Middleware] ✅ Path already rewritten (${pathname}). Passing through.`
        );
        const response = NextResponse.next({ request });
        response.headers.set("x-middleware-cache", "no-cache");
        response.headers.set("x-org-id", org);
        return response;
      }

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
      
      // Parse path to extract repo and possibly persona
      const pathSegments = originalPath.split("/").filter(Boolean);
      
      // IMPORTANT: First segment is ALWAYS the repo name in the subdomain pattern
      // bajrangbalikijai.docbook.site/jaishreram -> repo=jaishreram
      const repoName = pathSegments[0] || ""; // First segment is repo name
      
      console.log(`[Middleware] 🔍 Path segments: ${JSON.stringify(pathSegments)}, repoName: ${repoName}`);
      console.log(`[Middleware] 🔍 Original URL: ${request.url}`);
      console.log(`[Middleware] 🔍 Subdomain org: ${org}, repo: ${repoName}`);
      
      // Special case for settings path or any path with "settings" in it
      if (originalPath.includes("/settings") || repoName === "settings" || pathSegments.includes("settings")) {
        console.log(`[Middleware] ⚠️ Settings path detected: ${originalPath}`);
        
        // For any settings path, redirect to the main app domain
        // This is a safety measure to prevent settings paths from being processed as documentation
        const settingsUrl = new URL(request.url);
        
        // Remove the subdomain to get back to the main app domain
        if (hostname.includes(".")) {
          settingsUrl.hostname = hostname.replace(/^[^.]+\./, ""); // Remove subdomain
          
          // Keep the original path - the main app will handle it correctly
          console.log(`[Middleware] 🔄 Redirecting settings path to main app: ${settingsUrl.toString()}`);
          return NextResponse.redirect(settingsUrl);
        }
      }
      
      // Check if the second segment is a valid persona, otherwise it's part of the path
      const validPersonas = ["internal", "dev"];
      let personaName = pathSegments[1] || "";
      let remainingPath = "";
      
      if (validPersonas.includes(personaName)) {
        // Second segment is a valid persona
        remainingPath = pathSegments.slice(2).join("/");
        console.log(`[Middleware] 🔍 Valid persona found: ${personaName}, remaining path: ${remainingPath}`);
      } else {
        // Second segment is not a valid persona, so it's part of the path
        personaName = "dev"; // Default to dev persona
        remainingPath = pathSegments.slice(1).join("/");
        console.log(`[Middleware] 🔍 No valid persona found, using default: ${personaName}, remaining path: ${remainingPath}`);
      }
      
      // Check for auth when accessing internal persona
      if (personaName === "internal") {
        // Get auth token from cookies or headers
        const authToken = request.cookies.get("pustak_access_token")?.value || 
                         request.headers.get("authorization")?.replace("Bearer ", "");
        
        if (!authToken) {
          console.log(`[Middleware] ⚠️ Unauthorized access attempt to internal docs for ${repoName}`);
          
          // Redirect to login page
          const loginUrl = request.nextUrl.clone();
          loginUrl.pathname = "/login";
          loginUrl.searchParams.set("redirect", request.url);
          
          return NextResponse.redirect(loginUrl);
        }
        
        // Here we could also validate the token with the backend
        // For now, we just check if it exists
        console.log(`[Middleware] ✅ Authorized access to internal docs for ${repoName}`);
      }
      
      console.log(`[Middleware] Path Analysis: repo=${repoName}, persona=${personaName}, remaining=${remainingPath}`);
      
      // CRITICAL FIX: For subdomain access, we must ensure:
      // 1. repo_id is ALWAYS the first path segment (not 'docs')
      // 2. persona is ALWAYS a valid value (not the org name)
      
      if (!originalPath && liveUrlPath) {
        // Homepage with live URL path
        url.pathname = `/docs/${org}${liveUrlPath}`;
      } else if (!originalPath) {
        // Homepage without live URL path
        url.pathname = `/docs/${org}`;
      } else if (repoName) {
        // We have a repo name from the first path segment
        
        // IMPORTANT: For subdomain access, NEVER use the org as persona
        // ALWAYS use a valid persona (dev or internal) or default to dev
        let persona = "dev"; // Default persona
        
        // Check if second segment is a valid persona
        if (validPersonas.includes(pathSegments[1] || "")) {
          persona = pathSegments[1];
          const remainingSegments = pathSegments.slice(2).join("/");
          url.pathname = `/docs/${org}/${repoName}/${persona}${remainingSegments ? "/" + remainingSegments : ""}`;
          console.log(`[Middleware] 📝 Rewriting with explicit persona: ${url.pathname}`);
        } else {
          // No valid persona specified - use default
          const remainingSegments = pathSegments.slice(1).join("/");
          url.pathname = `/docs/${org}/${repoName}/${persona}${remainingSegments ? "/" + remainingSegments : ""}`;
          console.log(`[Middleware] 📝 Rewriting with default persona: ${url.pathname}`);
        }
        
        // Add debug info
        console.log(`[Middleware] 🔑 Final rewrite: org=${org}, repo=${repoName}, persona=${persona}`);
      } else {
        // Fallback - just rewrite to docs page
        url.pathname = `/docs/${org}${originalPath}`;
        console.log(`[Middleware] 📝 Fallback rewriting: ${url.pathname}`);
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

  // Special handling for /repo/settings path on www subdomain or localhost
  if ((hostname.startsWith('www.') || hostname === 'www.localhost' || hostname === 'www.127.0.0.1') && 
      pathname.startsWith('/repo/settings')) {
    console.log(`[Middleware] 🔍 Settings path detected on www domain: ${pathname}`);
    // This is already on the main domain, so just pass through
    return NextResponse.next();
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
