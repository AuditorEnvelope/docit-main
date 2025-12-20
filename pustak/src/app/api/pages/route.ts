import { NextRequest, NextResponse } from 'next/server';

const RAW_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Normalize backend URL - remove /api/v1 if it exists, we'll add it back
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/api\/v1\/?$/, '');
const API_BASE = `${BACKEND_URL}/api/v1`;

export async function POST(request: NextRequest) {
  try {
    console.log('[/api/pages] Request received');
    const userToken = request.headers.get('authorization')?.replace('Bearer ', '');

    if (!userToken) {
      console.log('[/api/pages] No user token');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { action, ...params } = body;
    console.log('[/api/pages] Action:', action, 'Params:', params);

    let endpoint = '';
    switch (action) {
      case 'create':
        endpoint = '/docs/create-page';
        break;
      case 'delete':
        endpoint = '/docs/delete-page';
        break;
      case 'move':
        endpoint = '/docs/move-page';
        break;
      case 'batch':
        endpoint = '/docs/batch-commit';
        break;
      default:
        return NextResponse.json(
          { error: 'Invalid action. Must be one of: create, delete, move, batch' },
          { status: 400 }
        );
    }

    const backendUrl = `${API_BASE}${endpoint}`;
    console.log('[/api/pages] Calling backend:', backendUrl);

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`,
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('[/api/pages] Backend error:', errorData);
      return NextResponse.json(
        { error: errorData.detail || errorData.error || 'Operation failed' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('[/api/pages] Success:', data);
    return NextResponse.json(data);
  } catch (error) {
    console.error('[/api/pages] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
