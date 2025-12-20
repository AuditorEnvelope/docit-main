import { NextRequest, NextResponse } from "next/server";

const RAW_BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// Normalize backend URL - remove /api/v1 if it exists, we'll add it back
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/api\/v1\/?$/, '');
const API_BASE = `${BACKEND_URL}/api/v1`;

export async function GET(request: NextRequest, context: any) {
  try {
    // Extract the orgId from params (await for Next.js 15+)
    const params = await context.params;
    const { orgId } = params;
    const branch = request.nextUrl.searchParams.get("branch") || "staging";
    const authHeader = request.headers.get("authorization");

    if (!authHeader) {
      return NextResponse.json(
        { error: "No authorization header" },
        { status: 401 }
      );
    }

    // Get docbook structure from backend
    const response = await fetch(
      `${API_BASE}/docbook/${orgId}/structure?branch=${branch}`,
      {
        headers: {
          Authorization: authHeader,
        },
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Docbook repository not found" },
          { status: 404 }
        );
      }
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching docbook structure:", error);
    return NextResponse.json(
      { error: "Failed to fetch docbook structure" },
      { status: 500 }
    );
  }
}
