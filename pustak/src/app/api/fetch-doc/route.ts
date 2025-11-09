import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const repo = searchParams.get('repo');
    const filePath = searchParams.get('filePath');
    const userToken = request.headers.get('authorization')?.replace('Bearer ', '');

    console.log('[/api/fetch-doc] Request received:', { repo, filePath, hasToken: !!userToken });

    if (!repo || !filePath) {
      console.log('[/api/fetch-doc] Missing parameters');
      return NextResponse.json(
        { error: 'Missing repo or filePath parameter' },
        { status: 400 }
      );
    }

    if (!userToken) {
      console.log('[/api/fetch-doc] No user token');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Use repo name as-is (frontend should pass fullName)
    const fullRepoName = repo;
    console.log('[/api/fetch-doc] Using repo name:', fullRepoName);

    // Call backend to fetch file using user's token and full repo name
    // BACKEND_URL already includes /api/v1 prefix (like other routes)
    const backendUrl = `${BACKEND_URL}/docs/fetch-file?repo=${encodeURIComponent(fullRepoName)}&filePath=${encodeURIComponent(filePath)}`;
    console.log('[/api/fetch-doc] Calling backend:', backendUrl);
    const response = await fetch(
      backendUrl,
      {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
      }
    );
    console.log('[/api/fetch-doc] Backend response status:', response.status);

    if (!response.ok) {
      console.log('[/api/fetch-doc] Backend response not OK');
      if (response.status === 404) {
        console.log('[/api/fetch-doc] File not found on backend');
        return NextResponse.json(
          { error: 'File not found' },
          { status: 404 }
        );
      }
      console.log('[/api/fetch-doc] Backend error');
      return NextResponse.json(
        { error: 'Failed to fetch file from backend' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('[/api/fetch-doc] Success, content length:', data.content?.length || 0);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching doc:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
