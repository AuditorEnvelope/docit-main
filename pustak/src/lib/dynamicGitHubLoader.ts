// Dynamic documentation loader - fetches data from GitHub
import { fetchDocsFromRepo } from "./realGitHubAPI";

export interface RepoDocumentation {
  readme?: string;
  changelog?: string;
  summary?: string;
  api?: string;
  changes: Array<{
    content: string;
    fileName: string;
  }>;
}

// Load documentation for a specific repository from GitHub
export async function loadRepoDocumentation(
  repoName: string
): Promise<RepoDocumentation> {
  try {
    const docs = await fetchDocsFromRepo(repoName);

    return {
      readme: docs.readme,
      changelog: docs.changelog,
      summary: docs.summary,
      api: docs.api,
      changes: docs.changes || [],
    };
  } catch (error) {
    console.error(`Error loading docs for ${repoName}:`, error);
    return { changes: [] };
  }
}

// Check if a repository has documentation
export async function hasRepositoryDocs(repoName: string): Promise<boolean> {
  try {
    const docs = await loadRepoDocumentation(repoName);
    return !!(
      docs.readme ||
      docs.changelog ||
      docs.summary ||
      docs.api ||
      docs.changes.length > 0
    );
  } catch (error) {
    console.error(`Failed to check docs for ${repoName}:`, error);
    return false;
  }
}
