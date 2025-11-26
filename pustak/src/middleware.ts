import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { hostname, pathname } = request.nextUrl;

  // Extract subdomain (org name) from hostname
  // e.g., "demo.docbook.site" → org = "demo"
  // e.g., "localhost" or "docbook.site" → no subdomain
  const hostParts = hostname.split(".");
  
  // Check if we have a subdomain (not www, not bare domain)
  let org: string | null = null;
  
  if (hostname.includes("docbook.site")) {
    // Production: demo.docbook.site
    if (hostParts.length >= 3 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  } else if (hostname.includes("localhost") || hostname.includes("127.0.0.1")) {
    // Local development: org.pustak.test or org.localhost
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  } else {
    // Custom domains (e.g., docs.company.com)
    // For now, treat the first part as org
    if (hostParts.length >= 2 && hostParts[0] !== "www") {
      org = hostParts[0];
    }
  }

  // If we have an org subdomain, this is a docs viewer request
  if (org && pathname.startsWith("/")) {
    // Rewrite to the docs viewer route with org in the path
    // This allows Next.js to route to app/docs/[org]/[...slug]
    const url = request.nextUrl.clone();
    url.pathname = `/docs/${org}${pathname}`;
    
    // Add org as a header for easy access in the component
    const response = NextResponse.rewrite(url);
    response.headers.set("x-org-id", org);
    return response;
  }

  // No subdomain, proceed normally (landing page, dashboard, etc.)
  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * - api routes
     */
    "/((?!_next/static|_next/image|favicon.ico|api).*)",
  ],
};
