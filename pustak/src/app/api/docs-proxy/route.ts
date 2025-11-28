import { NextRequest, NextResponse } from "next/server";

/**
 * API route that acts as a proxy for documentation requests
 * This allows us to use query parameters instead of path parameters
 * which gives us more control over the parameter extraction
 */
export async function GET(request: NextRequest) {
  // Get query parameters
  const searchParams = request.nextUrl.searchParams;
  const url = request.url;
  const headers = Object.fromEntries(request.headers);
  
  console.log(`[DOCS_PROXY] 📡 Received request:`, { url, headers });
  console.log(`[DOCS_PROXY] 📡 Search params:`, Object.fromEntries(searchParams.entries()));
  
  // Extract parameters from URL path if not in query params
  const urlPath = new URL(request.url).pathname;
  const pathSegments = urlPath.split('/').filter(Boolean);
  
  // Get parameters from query string
  let org = searchParams.get("org");
  let repo = searchParams.get("repo");
  let persona = searchParams.get("persona");
  let path = searchParams.get("path");
  
  console.log(`[DOCS_PROXY] 📡 Initial params:`, { org, repo, persona, path });
  console.log(`[DOCS_PROXY] 📡 URL path segments:`, pathSegments);
  
  // Extract org from hostname if not in query params
  if (!org) {
    const hostname = headers.host || '';
    const subdomain = hostname.split('.')[0];
    if (subdomain && subdomain !== 'www' && subdomain !== 'localhost') {
      org = subdomain;
      console.log(`[DOCS_PROXY] 📡 Extracted org from hostname:`, org);
    }
  }
  
  // Extract repo from path if not in query params
  if (!repo && pathSegments.length > 0 && pathSegments[0] !== 'api') {
    repo = pathSegments[0];
    console.log(`[DOCS_PROXY] 📡 Extracted repo from path:`, repo);
  }
  
  // Use default persona if not specified
  if (!persona) {
    persona = "dev";
    console.log(`[DOCS_PROXY] 📡 Using default persona:`, persona);
  }
  
  console.log(`[DOCS_PROXY] 📡 Final params:`, { org, repo, persona, path });
  
  if (!org || !repo) {
    console.log(`[DOCS_PROXY] ❌ Missing required parameters`);
    return NextResponse.json(
      { error: "Missing required parameters", details: { org, repo, persona, path } },
      { status: 400 }
    );
  }

  // Construct the path for the docs page
  let docsPath = `/docs/${org}/${repo}/${persona}`;
  if (path) {
    docsPath += `/${path}`;
  }

  console.log(`[DOCS_PROXY] 🔀 Redirecting to: ${docsPath}`);

  // Redirect to the docs page with the correct parameters
  return NextResponse.redirect(new URL(docsPath, request.url));
}
