import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ orgId: string }> }
) {
  try {
    // Await params before accessing properties
    const { orgId } = await context.params;
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
      `${BACKEND_URL}/docbook/${orgId}/structure?branch=${branch}`,
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
