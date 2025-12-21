import { NextRequest, NextResponse } from 'next/server';

const RAW_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Normalize backend URL - remove /api/v1 if it exists, we'll add it back
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/api\/v1\/?$/, '');
const API_BASE = `${BACKEND_URL}/api/v1`;

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

    // Extract orgId from repo (format: orgId/repoName)
    // e.g., "bajrangbalikijai/pustak-docbook-bajrangbalikijai" -> orgId = "bajrangbalikijai"
    const [orgId] = repo.split('/');
    console.log('[/api/fetch-doc] Extracted orgId:', orgId);
    console.log('[/api/fetch-doc] File path:', filePath);

    // Use the new docbook-specific endpoint that handles folder structure correctly
    const backendUrl = `${API_BASE}/docbook/fetch-file?org_id=${encodeURIComponent(orgId)}&file_path=${encodeURIComponent(filePath)}&branch=staging`;
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
