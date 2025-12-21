import { NextRequest, NextResponse } from 'next/server';

const RAW_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Normalize backend URL - remove /api/v1 if it exists, we'll add it back
const BACKEND_URL = RAW_BACKEND_URL.replace(/\/api\/v1\/?$/, '');
const API_BASE = `${BACKEND_URL}/api/v1`;

export async function PUT(request: NextRequest) {
  try {
    const userToken = request.headers.get('authorization')?.replace('Bearer ', '');

    if (!userToken) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { org_id, repo_id, persona, structure } = body;

    if (!org_id || !repo_id || !persona || !structure) {
      return NextResponse.json(
        { error: 'Missing required fields: org_id, repo_id, persona, structure' },
        { status: 400 }
      );
    }

    // Call backend
    const backendUrl = `${API_BASE}/docbook/update-structure`;
    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`,
      },
      body: JSON.stringify({
        org_id,
        repo_id,
        persona,
        structure,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || errorData.message || 'Failed to update structure' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating structure:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

