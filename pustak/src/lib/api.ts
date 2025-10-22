// Production API integration for DocAI backend

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export interface RepoData {
  name: string;
  fullName: string;
  description: string;
  lastUpdated: string;
  hasLocalDocs: boolean;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  type: string;
  repo_id: string;
  path: string;
  created_at: string;
}

export interface HierarchicalNode {
  id: string;
  type: string;
  title: string;
  slug: string;
  path: string;
  parent_id: string | null;
  depth: number;
  position: number;
  content: any;
  children?: HierarchicalNode[];
}

// Fetch repositories from backend
export async function fetchRepositories(): Promise<RepoData[]> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/repositories`, {
      next: { revalidate: 30 }, // Revalidate every 30 seconds
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch repositories: ${response.statusText}`);
    }
    
    const repos = await response.json();
    return repos;
  } catch (error) {
    console.error('Error fetching repositories:', error);
    return [];
  }
}

// Fetch single repository data
export async function fetchRepoData(
  repoName: string
): Promise<RepoData | null> {
  try {
    const repos = await fetchRepositories();
    return repos.find((repo) => repo.name === repoName) || null;
  } catch (error) {
    console.error(`Error fetching repo ${repoName}:`, error);
    return null;
  }
}

// Fetch hierarchical tree for repository
export async function fetchRepoTree(
  repoName: string
): Promise<HierarchicalNode | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/repos/${repoName}/tree`, {
      next: { revalidate: 60 }, // Revalidate every 60 seconds
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return null;
      }
      throw new Error(`Failed to fetch tree: ${response.statusText}`);
    }
    
    const tree = await response.json();
    return tree;
  } catch (error) {
    console.error(`Error fetching tree for ${repoName}:`, error);
    return null;
  }
}

// Fetch specific node details
export async function fetchNodeDetails(
  repoName: string,
  nodeId: string
): Promise<HierarchicalNode | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/repos/${repoName}/node/${nodeId}`, {
      next: { revalidate: 60 },
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return null;
      }
      throw new Error(`Failed to fetch node: ${response.statusText}`);
    }
    
    const node = await response.json();
    return node;
  } catch (error) {
    console.error(`Error fetching node ${nodeId}:`, error);
    return null;
  }
}

// Search across all documentation
export async function searchDocs(
  query: string,
  repoName?: string
): Promise<SearchResult[]> {
  if (query.length <= 2) return [];
  
  try {
    const url = repoName 
      ? `${BACKEND_URL}/api/repos/${repoName}/search?query=${encodeURIComponent(query)}`
      : `${BACKEND_URL}/api/search?query=${encodeURIComponent(query)}`;
    
    const response = await fetch(url, {
      next: { revalidate: 10 }, // Short cache for search
    });
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    
    const results = await response.json();
    return results;
  } catch (error) {
    console.error('Error searching docs:', error);
    return [];
  }
}

// Fetch backend health status
export async function fetchBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/`, {
      next: { revalidate: 5 },
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}

// Real API integration functions (to be implemented)
export async function syncWithDocAI(): Promise<void> {
  // This would trigger a sync with the DocAI backend
  // POST /api/sync
  console.log("Syncing with DocAI backend...");
}

export async function triggerDocGeneration(repoName: string): Promise<void> {
  // This would trigger documentation generation for a specific repo
  // POST /api/generate-docs
  console.log(`Triggering documentation generation for ${repoName}...`);
}
