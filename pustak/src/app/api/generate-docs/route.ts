import { NextResponse, NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface GenerateDocsRequest {
  repoName: string;
}

// Call backend to generate docs
export async function POST(request: NextRequest) {
  try {
    const body: GenerateDocsRequest = await request.json();
    const { repoName } = body;

    if (!repoName) {
      return NextResponse.json(
        { error: "Missing repoName" },
        { status: 400 }
      );
    }

    // Get user's JWT token from Authorization header
    const authHeader = request.headers.get("Authorization");
    const userToken = authHeader?.replace("Bearer ", "");

    if (!userToken) {
      return NextResponse.json(
        { error: "No authorization token provided" },
        { status: 401 }
      );
    }

    console.log(`📝 Calling backend to generate docs for ${repoName}...`);

    // Call backend /docs/generate endpoint
    const response = await fetch(`${BACKEND_URL}/docs/generate?repo_name=${repoName}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${userToken}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`Backend error: ${response.status} - ${error}`);
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ Docs generation started for ${repoName}`);

    return NextResponse.json(
      {
        success: true,
        message: `Docs generation started for ${repoName}`,
        repoName,
        status: "generating",
        estimatedTime: "2-5 minutes",
      },
      { status: 202 } // 202 Accepted - processing
    );
  } catch (error) {
    console.error("❌ Failed to generate docs:", error);
    return NextResponse.json(
      {
        error: "Failed to generate docs",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

// GET endpoint to check generation status
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const repoName = searchParams.get("repo");

    if (!repoName) {
      return NextResponse.json(
        { error: "Missing repo parameter" },
        { status: 400 }
      );
    }

    // Get user's JWT token
    const authHeader = request.headers.get("Authorization");
    const userToken = authHeader?.replace("Bearer ", "");

    if (!userToken) {
      return NextResponse.json(
        { error: "No authorization token provided" },
        { status: 401 }
      );
    }

    // Call backend to check status
    const response = await fetch(
      `${BACKEND_URL}/docs/generate?repo_name=${repoName}`,
      {
        headers: {
          "Authorization": `Bearer ${userToken}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();

    return NextResponse.json(
      {
        repoName,
        status: "completed",
        docsGenerated: true,
        timestamp: new Date().toISOString(),
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("❌ Failed to check generation status:", error);
    return NextResponse.json(
      { error: "Failed to check status" },
      { status: 500 }
    );
  }
}
