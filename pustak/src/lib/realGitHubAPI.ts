// REAL GitHub API integration - NO MOCK DATA
export interface GitHubRepo {
  name: string;
  full_name: string;
  description: string;
  updated_at: string;
  default_branch: string;
  private: boolean;
  language: string;
  stargazers_count: number;
  forks_count: number;
}

export interface GitHubFile {
  name: string;
  path: string;
  sha: string;
  size: number;
  url: string;
  html_url: string;
  git_url: string;
  download_url: string;
  type: string;
  content?: string;
  encoding?: string;
}

// Get GitHub token from environment
function getGitHubToken(): string | null {
  if (typeof window !== "undefined") {
    // Client-side: token should be passed from server
    return null;
  }
  // Server-side: get from environment
  return process.env.GITHUB_TOKEN || null;
}

// Get GitHub organization from environment
function getGitHubOrg(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.GITHUB_ORG || "";
}

// Fetch all repositories from your GitHub organization
export async function fetchAllRepositoriesFromGitHub(): Promise<GitHubRepo[]> {
  try {
    const token = getGitHubToken();
    const org = getGitHubOrg();

    if (!token) {
      console.error("GITHUB_TOKEN not found in environment variables.");
      return [];
    }

    if (!org) {
      console.error("GITHUB_ORG not found in environment variables.");
      return [];
    }

    const response = await fetch(
      `https://api.github.com/orgs/${org}/repos?per_page=100`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github.v3+json",
          "User-Agent": "Pustak-Documentation-Platform",
        },
        next: { revalidate: 30 }, // Cache for 30 seconds (faster updates)
      }
    );

    if (!response.ok) {
      throw new Error(
        `GitHub API error: ${response.status} ${response.statusText}`
      );
    }

    const repos = await response.json();

    return repos.map((repo: any) => ({
      name: repo.name,
      full_name: repo.full_name,
      description: repo.description || "No description available",
      updated_at: repo.updated_at,
      default_branch: repo.default_branch,
      private: repo.private,
      language: repo.language || "Unknown",
      stargazers_count: repo.stargazers_count,
      forks_count: repo.forks_count,
    }));
  } catch (error) {
    console.error("Failed to fetch repositories from GitHub:", error);
    return [];
  }
}

// Fetch file content from GitHub
export async function fetchFileFromGitHub(
  repo: string,
  path: string
): Promise<string | null> {
  try {
    const token = getGitHubToken();
    const org = getGitHubOrg();

    if (!token || !org) {
      console.error("GITHUB_TOKEN or GITHUB_ORG not found. Cannot fetch file content.");
      return null;
    }

    const response = await fetch(
      `https://api.github.com/repos/${org}/${repo}/contents/${path}`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github.v3+json",
          "User-Agent": "Pustak-Documentation-Platform",
        },
        next: { revalidate: 10 }, // Cache for 10 seconds (faster updates)
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        console.log(`File not found: ${repo}/${path}`);
        return null;
      }
      throw new Error(
        `GitHub API error: ${response.status} ${response.statusText}`
      );
    }

    const fileData = await response.json();

    if (fileData.type !== "file") {
      console.log(`Path is not a file: ${repo}/${path}`);
      return null;
    }

    // Decode base64 content
    if (fileData.encoding === "base64" && fileData.content) {
      // Remove newlines from base64 content (GitHub API adds them)
      const base64Content = fileData.content.replace(/\n/g, '');
      return Buffer.from(base64Content, "base64").toString("utf-8");
    }

    return fileData.content || null;
  } catch (error) {
    console.error(`Failed to fetch file ${path} from ${repo}:`, error);
    return null;
  }
}

// List files in a directory
export async function listDirectoryContents(
  repo: string,
  path: string
): Promise<string[]> {
  try {
    const token = getGitHubToken();
    const org = getGitHubOrg();

    if (!token || !org) {
      console.error("GITHUB_TOKEN or GITHUB_ORG not found. Cannot list directory contents.");
      return [];
    }

    const response = await fetch(
      `https://api.github.com/repos/${org}/${repo}/contents/${path}`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github.v3+json",
          "User-Agent": "Pustak-Documentation-Platform",
        },
        next: { revalidate: 10 }, // Cache for 10 seconds (faster updates)
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        console.log(`Directory not found: ${repo}/${path}`);
        return [];
      }
      throw new Error(
        `GitHub API error: ${response.status} ${response.statusText}`
      );
    }

    const directoryData = await response.json();

    if (!Array.isArray(directoryData)) {
      console.log(`Path is not a directory: ${repo}/${path}`);
      return [];
    }

    // Filter for markdown files only
    return directoryData
      .filter((item: any) => item.type === "file" && item.name.endsWith(".md"))
      .map((item: any) => item.name);
  } catch (error) {
    console.error(`Failed to list directory ${path} in ${repo}:`, error);
    return [];
  }
}

// Check if a repository has a docs folder
export async function hasDocsFolder(repo: string): Promise<boolean> {
  try {
    const token = getGitHubToken();
    const org = getGitHubOrg();

    if (!token || !org) {
      return false;
    }

    const response = await fetch(
      `https://api.github.com/repos/${org}/${repo}/contents/docs`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: "application/vnd.github.v3+json",
          "User-Agent": "Pustak-Documentation-Platform",
        },
        next: { revalidate: 30 }, // Cache for 30 seconds (faster updates)
      }
    );

    return response.ok;
  } catch (error) {
    console.error(`Failed to check docs folder for ${repo}:`, error);
    return false;
  }
}

// Fetch all markdown files from docs folder
export async function fetchDocsFromRepo(repo: string): Promise<{
  readme?: string;
  summary?: string;
  api?: string;
  changelog?: string;
  architecture?: string;
  workflow?: string;
  changes: Array<{ content: string; fileName: string }>;
}> {
  try {
    const markdownFiles = await listDirectoryContents(repo, "docs");
    
    const docs: {
      readme?: string;
      summary?: string;
      api?: string;
      changelog?: string;
      architecture?: string;
      workflow?: string;
      changes: Array<{ content: string; fileName: string }>;
    } = {
      changes: [],
    };

    // Fetch each markdown file from docs folder
    for (const fileName of markdownFiles) {
      const content = await fetchFileFromGitHub(repo, `docs/${fileName}`);
      
      if (!content) continue;

      const lowerFileName = fileName.toLowerCase();
      
      if (lowerFileName === "readme.md") {
        docs.readme = content;
      } else if (lowerFileName === "summary.md") {
        docs.summary = content;
      } else if (lowerFileName === "api.md") {
        docs.api = content;
      } else if (lowerFileName === "changelog.md") {
        docs.changelog = content;
      } else if (lowerFileName === "architecture.md") {
        docs.architecture = content;
      } else if (lowerFileName === "workflow.md") {
        docs.workflow = content;
      } else if (fileName.endsWith(".md")) {
        // Skip DocAI run logs and internal files (only if filename indicates it's a log)
        if (lowerFileName.includes("docai_run_log") || 
            lowerFileName.includes("run_log") ||
            lowerFileName === "doc_ai_run_log.md") {
          continue; // Skip DocAI internal logs
        }
        // All other markdown files go to changes
        docs.changes.push({ content, fileName });
      }
    }

    // Also fetch from docs/changes/ subdirectory
    const changesFiles = await listDirectoryContents(repo, "docs/changes");
    for (const fileName of changesFiles) {
      const content = await fetchFileFromGitHub(repo, `docs/changes/${fileName}`);
      
      if (!content) continue;

      const lowerFileName = fileName.toLowerCase();
      
      // Skip DocAI run logs
      if (lowerFileName.includes("docai_run_log") || 
          lowerFileName.includes("run_log") ||
          lowerFileName === "doc_ai_run_log.md") {
        continue;
      }
      
      // Add to changes array
      docs.changes.push({ content, fileName: `changes/${fileName}` });
    }

    // Also check for CHANGELOG.md in root folder (DocAI creates it there)
    if (!docs.changelog) {
      const rootChangelog = await fetchFileFromGitHub(repo, "CHANGELOG.md");
      if (rootChangelog) {
        docs.changelog = rootChangelog;
      }
    }

    // Fetch architecture from docs/architecture/current.md
    if (!docs.architecture) {
      const archCurrent = await fetchFileFromGitHub(repo, "docs/architecture/current.md");
      if (archCurrent) {
        docs.architecture = archCurrent;
      }
    }

    // Fetch workflow from docs/workflow/current.md
    if (!docs.workflow) {
      const workflowCurrent = await fetchFileFromGitHub(repo, "docs/workflow/current.md");
      if (workflowCurrent) {
        docs.workflow = workflowCurrent;
      }
    }

    return docs;
  } catch (error) {
    console.error(`Failed to fetch docs from ${repo}:`, error);
    return { changes: [] };
  }
}

// Get GitHub organization name (for use in components)
export function getGitHubOrgName(): string {
  return getGitHubOrg();
}
