import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { repoName, docType, content } = body;

    // Validate request
    if (!repoName || !docType || !content) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 },
      );
    }

    // In production, this would:
    // 1. Validate the request (authentication, etc.)
    // 2. Store the content in a database or file system
    // 3. Trigger a rebuild of the documentation
    // 4. Update the search index

    console.log(`Syncing documentation for ${repoName}/${docType}`);

    // Mock successful response
    return NextResponse.json({
      success: true,
      message: `Documentation synced for ${repoName}/${docType}`,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Sync error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: "ok",
    message: "DocIt API is running",
    timestamp: new Date().toISOString(),
  });
}
