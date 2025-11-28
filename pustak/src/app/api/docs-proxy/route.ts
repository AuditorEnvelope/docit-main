import { NextRequest, NextResponse } from "next/server";

/**
 * API route that acts as a proxy for documentation requests
 * This allows us to use query parameters instead of path parameters
 * which gives us more control over the parameter extraction
 */
export async function GET(request: NextRequest) {
  // Get query parameters
  const searchParams = request.nextUrl.searchParams;
  const org = searchParams.get("org");
  const repo = searchParams.get("repo");
  const persona = searchParams.get("persona");
  const path = searchParams.get("path");

  console.log(`[DOCS_PROXY] 📡 Received request with params:`, { org, repo, persona, path });

  if (!org || !repo || !persona) {
    return NextResponse.json(
      { error: "Missing required parameters" },
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
