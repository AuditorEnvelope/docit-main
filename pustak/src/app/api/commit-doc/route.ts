import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    console.log('[/api/commit-doc] Request received');
    const userToken = request.headers.get('authorization')?.replace('Bearer ', '');

    if (!userToken) {
      console.log('[/api/commit-doc] No user token');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { repo, filePath, content, commitMessage, branch } = body;
    console.log('[/api/commit-doc] Request body:', { repo, filePath, hasContent: !!content, commitMessage, branch });

    if (!repo || !filePath || !content || !commitMessage) {
      return NextResponse.json(
        { error: 'Missing required fields: repo, filePath, content, commitMessage' },
        { status: 400 }
      );
    }

    // Call backend to commit file
    // BACKEND_URL from .env.local includes /api/v1, so we call /docs/commit
    // Full URL: http://localhost:8000/api/v1/docs/commit
    const backendUrl = `${BACKEND_URL}/docs/commit`;
    console.log('[/api/commit-doc] Calling backend:', backendUrl);
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`,
      },
      body: JSON.stringify({
        repo,
        file_path: filePath,
        content,
        commit_message: commitMessage,
        branch: branch || 'staging',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || errorData.error || 'Failed to commit changes' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error committing doc:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

