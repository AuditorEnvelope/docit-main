// Search API client for DocAI backend
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export interface SearchResult {
  repo: string;
  type: string;
  title: string;
  content: string;
  url: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
}

// Search across all documentation
export async function searchDocumentation(query: string): Promise<SearchResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/search?query=${encodeURIComponent(query)}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error(`Search API error: ${response.status} ${response.statusText}`);
      return { results: [], total: 0 };
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to search documentation:', error);
    return { results: [], total: 0 };
  }
}
