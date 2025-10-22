import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');
    
    if (!query || query.length <= 2) {
      return NextResponse.json([]);
    }
    
    // Forward search request to backend
    const response = await fetch(
      `${BACKEND_URL}/api/search?query=${encodeURIComponent(query)}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    if (!response.ok) {
      throw new Error(`Backend search failed: ${response.statusText}`);
    }
    
    const results = await response.json();
    return NextResponse.json(results);
    
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}
