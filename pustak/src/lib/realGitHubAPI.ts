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

// Get GitHub token from backend (for authenticated user)
// This is called server-side during page rendering
let cachedToken: string | null = null;

async function getGitHubTokenFromBackend(jwtToken: string): Promise<string | null> {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/auth/github-token`, {
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
      },
    });
    
    if (response.ok) {
      const data = await response.json();
      cachedToken = data.token;
      return data.token;
    }
  } catch (error) {
    console.error('Failed to fetch GitHub token from backend:', error);
  }
  
  return null;
}

function getGitHubToken(): string | null {
  if (typeof window !== "undefined") {
    // Client-side: cannot access token
    return null;
  }
  // Server-side: use cached token or fallback to environment
  return cachedToken || process.env.GITHUB_TOKEN || null;
}

// Get GitHub organization from environment (fallback only)
// For authenticated users, org comes from the repo name itself
function getGitHubOrg(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  // Fallback to environment org if needed
  return process.env.GITHUB_ORG || "";
}

// Export for use in page components
export { getGitHubTokenFromBackend };

// Fetch all repositories from your GitHub organization
// Fetch repositories (uses user's token from backend)
export async function fetchAllRepositoriesFromGitHub(userToken?: string): Promise<GitHubRepo[]> {
  try {
    // Use provided user token, or fall back to environment token
    const token = userToken || getGitHubToken();
    const org = getGitHubOrg();

    if (!token) {
      console.error("No GitHub token available.");
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
  filePath: string,
  userToken?: string
): Promise<string | null> {
  try {
    // Use provided user token, or fall back to environment token
    const token = userToken || getGitHubToken();

    if (!token) {
      console.error("No GitHub token available. Cannot fetch file.");
      return null;
    }

    const org = getGitHubOrg();
    const repoPath = repo.includes('/') ? repo : `${org}/${repo}`;
    const response = await fetch(
      `https://api.github.com/repos/${repoPath}/contents/${filePath}`,
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
        console.log(`File not found: ${repo}/${filePath}`);
        return null;
      }
      throw new Error(
        `GitHub API error: ${response.status} ${response.statusText}`
      );
    }

    const fileData = await response.json();

    if (fileData.type !== "file") {
      console.log(`Path is not a file: ${repo}/${filePath}`);
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
    console.error(`Failed to fetch file ${filePath} from ${repo}:`, error);
    return null;
  }
}

// List files in a directory
export async function listDirectoryContents(
  repo: string,
  path: string,
  userToken?: string
): Promise<string[]> {
  try {
    // Use provided user token, or fall back to environment token
    const token = userToken || getGitHubToken();

    if (!token) {
      console.error("No GitHub token available. Cannot list directory contents.");
      return [];
    }

    const org = getGitHubOrg();
    const repoPath = repo.includes('/') ? repo : `${org}/${repo}`;
    const response = await fetch(
      `https://api.github.com/repos/${repoPath}/contents/${path}`,
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
export async function hasDocsFolder(repo: string, userToken?: string): Promise<boolean> {
  try {
    // Use provided user token, or fall back to environment token
    const token = userToken || getGitHubToken();

    if (!token) {
      return false;
    }

    const org = getGitHubOrg();
    const repoPath = repo.includes('/') ? repo : `${org}/${repo}`;

    const response = await fetch(
      `https://api.github.com/repos/${repoPath}/contents/docs`,
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
  architectureVersions: Array<{ version: string; fileName: string }>;
  workflowVersions: Array<{ version: string; fileName: string }>;
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
      architectureVersions: Array<{ version: string; fileName: string }>;
      workflowVersions: Array<{ version: string; fileName: string }>;
      changes: Array<{ content: string; fileName: string }>;
    } = {
      architectureVersions: [],
      workflowVersions: [],
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

    // Fetch README.md from root (primary source for summary)
    if (!docs.readme) {
      const rootReadme = await fetchFileFromGitHub(repo, "README.md");
      if (rootReadme) {
        docs.readme = rootReadme;
      }
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

    // Fetch architecture versions from docs/architecture/
    const archFiles = await listDirectoryContents(repo, "docs/architecture");
    for (const fileName of archFiles) {
      const match = fileName.match(/^v([\d.]+)-architecture\.md$/);
      if (match) {
        docs.architectureVersions.push({
          version: `v${match[1]}`,
          fileName: `architecture/${fileName}`
        });
      }
    }
    // Sort versions in descending order (v3.3, v3.2, v3.1, v3, v2, v1)
    docs.architectureVersions.sort((a, b) => {
      const aVer = a.version.substring(1).split('.').map(Number);
      const bVer = b.version.substring(1).split('.').map(Number);
      
      for (let i = 0; i < Math.max(aVer.length, bVer.length); i++) {
        const aNum = aVer[i] || 0;
        const bNum = bVer[i] || 0;
        if (aNum !== bNum) return bNum - aNum;
      }
      return 0;
    });

    // Fetch workflow versions from docs/workflow/
    const workflowFiles = await listDirectoryContents(repo, "docs/workflow");
    for (const fileName of workflowFiles) {
      const match = fileName.match(/^v([\d.]+)-workflow\.md$/);
      if (match) {
        docs.workflowVersions.push({
          version: `v${match[1]}`,
          fileName: `workflow/${fileName}`
        });
      }
    }
    // Sort versions in descending order (v3.3, v3.2, v3.1, v3, v2, v1)
    docs.workflowVersions.sort((a, b) => {
      const aVer = a.version.substring(1).split('.').map(Number);
      const bVer = b.version.substring(1).split('.').map(Number);
      
      for (let i = 0; i < Math.max(aVer.length, bVer.length); i++) {
        const aNum = aVer[i] || 0;
        const bNum = bVer[i] || 0;
        if (aNum !== bNum) return bNum - aNum;
      }
      return 0;
    });

    return docs;
  } catch (error) {
    console.error(`Failed to fetch docs from ${repo}:`, error);
    return { 
      architectureVersions: [],
      workflowVersions: [],
      changes: [] 
    };
  }
}

// Get GitHub organization name (for use in components)
export function getGitHubOrgName(): string {
  return getGitHubOrg();
}
