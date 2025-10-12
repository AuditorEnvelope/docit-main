// src/lib/backendAPI.ts
// Dynamic documentation fetcher from DocAI backend

export interface BackendDocs {
  readme?: string;
  changelog?: string;
  summary?: string;
  api?: string;
  changes?: Array<{
    content: string;
    fileName: string;
    lastModified: string;
  }>;
}

/**
 * Fetch repository documentation from DocAI backend.
 * @param repoName - Name of the repository
 * @returns BackendDocs object
 */
export async function fetchRepositoryDocumentation(
  repoName: string
): Promise<BackendDocs> {
  try {
    // Replace this URL with your actual DocAI backend endpoint
    const response = await fetch(
      `http://localhost:8000/repos/${repoName}/docs`
    );

    if (!response.ok) {
      throw new Error(
        `Failed to fetch documentation for ${repoName}: ${response.statusText}`
      );
    }

    const data: BackendDocs = await response.json();

    // Ensure changes is always an array
    data.changes = data.changes || [];

    return data;
  } catch (error) {
    console.error(`Error fetching repository docs for ${repoName}:`, error);
    return { changes: [] };
  }
}
