// Dynamic repository loader - fetches real data from GitHub
import { fetchAllRepositoriesFromGitHub, hasDocsFolder } from "./realGitHubAPI";

// Re-export types for compatibility
export interface SimpleRepo {
  name: string;
  fullName: string;
  description: string;
  lastUpdated: string;
  hasLocalDocs: boolean;
}

// Get all repositories from GitHub
export async function getAllRepos(): Promise<SimpleRepo[]> {
  try {
    const repositories = await fetchAllRepositoriesFromGitHub();

    // Check which repos have docs folders
    const reposWithDocsCheck = await Promise.all(
      repositories.map(async (repo) => {
        const hasDocs = await hasDocsFolder(repo.name);
        return {
          name: repo.name,
          fullName: repo.full_name,
          description: repo.description || "No description available",
          lastUpdated: repo.updated_at,
          hasLocalDocs: hasDocs,
        };
      })
    );

    // Filter to only show repos with docs
    return reposWithDocsCheck.filter(repo => repo.hasLocalDocs);
  } catch (error) {
    console.error("Failed to load repositories:", error);
    return [];
  }
}

// Get repository path (for local file access if needed) - DEPRECATED
// This is only used for local development, should not be used in production
export function getRepoPath(repoName: string): string | null {
  // No longer using hardcoded paths
  return null;
}

// Check if repo has docs
export async function hasRepoDocs(repoName: string): Promise<boolean> {
  try {
    return await hasDocsFolder(repoName);
  } catch (error) {
    console.error(`Failed to check docs for ${repoName}:`, error);
    return false;
  }
}
