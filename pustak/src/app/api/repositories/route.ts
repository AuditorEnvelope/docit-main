import { NextResponse, NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    // Get user's JWT token from Authorization header
    const authHeader = request.headers.get("Authorization");
    const userToken = authHeader?.replace("Bearer ", "");

    if (!userToken) {
      return NextResponse.json(
        { error: "No authorization token provided" },
        { status: 401 }
      );
    }

    console.log("📡 Calling backend /auth/repositories with token...");

    // Call backend /auth/repositories endpoint
    const response = await fetch(`${BACKEND_URL}/auth/repositories`, {
      headers: {
        Authorization: `Bearer ${userToken}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error(`Backend error: ${response.status}`);
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ Got ${data.repositories?.length || 0} repos from backend`);

    // Return repos from backend
    return NextResponse.json(data.repositories || []);
  } catch (error) {
    console.error("❌ Failed to fetch repositories:", error);
    return NextResponse.json(
      {
        error: "Failed to fetch repositories",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
