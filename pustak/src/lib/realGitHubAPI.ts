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
  // Only available on server-side
  if (typeof process !== 'undefined' && process.env) {
    return process.env.GITHUB_TOKEN || null;
  }
  return null;
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

// Fetch file content from GitHub via backend
export async function fetchFileFromGitHub(
  repo: string,
  filePath: string
): Promise<string | null> {
  try {
    console.log("[fetchFileFromGitHub] Called with:", { repo, filePath });
    const isServer = typeof window === 'undefined';
    console.log("[fetchFileFromGitHub] Is server-side:", isServer);
    
    if (isServer) {
      // Server-side: use env token
      console.log("[fetchFileFromGitHub] Using server-side fetch");
      const token = getGitHubToken();
      console.log("[fetchFileFromGitHub] Token available:", !!token);
      if (!token) {
        console.log("[fetchFileFromGitHub] No token, returning null");
        return null;
      }
      const org = getGitHubOrg();
      const repoPath = repo.includes('/') ? repo : `${org}/${repo}`;
      console.log("[fetchFileFromGitHub] Repo path:", repoPath);
      const url = `https://api.github.com/repos/${repoPath}/contents/${filePath}`;
      console.log("[fetchFileFromGitHub] GitHub API URL:", url);
      const response = await fetch(
        url,
        {
          headers: {
            Authorization: `token ${token}`,
            Accept: "application/vnd.github.v3+json",
            "User-Agent": "Pustak-Documentation-Platform",
          },
          next: { revalidate: 10 },
        }
      );
      console.log("[fetchFileFromGitHub] Response status:", response.status);
      if (!response.ok) {
        console.log("[fetchFileFromGitHub] Response not OK, returning null");
        return null;
      }
      const fileData = await response.json();
      console.log("[fetchFileFromGitHub] File data received, encoding:", fileData.encoding);
      if (fileData.encoding === "base64" && fileData.content) {
        const base64Content = fileData.content.replace(/\n/g, '');
        const decoded = Buffer.from(base64Content, "base64").toString("utf-8");
        console.log("[fetchFileFromGitHub] Decoded content length:", decoded.length);
        return decoded;
      }
      console.log("[fetchFileFromGitHub] Returning raw content, length:", fileData.content?.length || 0);
      return fileData.content || null;
    }

    // Client-side: use backend endpoint
    console.log("[fetchFileFromGitHub] Using client-side fetch");
    const userToken = localStorage.getItem('pustak_access_token');
    console.log("[fetchFileFromGitHub] User token available:", !!userToken);
    if (!userToken) {
      console.log("[fetchFileFromGitHub] No user token, returning null");
      return null;
    }

    const url = `/api/fetch-doc?repo=${encodeURIComponent(repo)}&filePath=${encodeURIComponent(filePath)}`;
    console.log("[fetchFileFromGitHub] API URL:", url);
    const response = await fetch(
      url,
      {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
      }
    );

    console.log("[fetchFileFromGitHub] API response status:", response.status);
    if (!response.ok) {
      console.log("[fetchFileFromGitHub] API response not OK, returning null");
      return null;
    }

    const data = await response.json();
    console.log("[fetchFileFromGitHub] API data received, content length:", data.content?.length || 0);
    return data.content || null;
  } catch (error) {
    console.error("[fetchFileFromGitHub] Error:", error);
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

    if (!token) {
      console.error("GITHUB_TOKEN not found. Cannot list directory contents.");
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
      if (response.status === 401 || response.status === 403) {
        console.error(`Auth error (${response.status}): Token may not have access to ${repoPath}`);
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

// Check doc structure status
export interface DocStructureStatus {
  hasDocsFolder: boolean;
  hasReadme: boolean;
  hasChangelog: boolean;
  hasSummary: boolean;
  hasArchitecture: boolean;
  hasWorkflow: boolean;
  hasApi: boolean;
  architectureVersions: string[];
  workflowVersions: string[];
}

export async function checkDocStructure(
  repo: string,
  userToken?: string
): Promise<DocStructureStatus> {
  try {
    const token = userToken || getGitHubToken();
    if (!token) {
      return {
        hasDocsFolder: false,
        hasReadme: false,
        hasChangelog: false,
        hasSummary: false,
        hasArchitecture: false,
        hasWorkflow: false,
        hasApi: false,
        architectureVersions: [],
        workflowVersions: [],
      };
    }

    const repoPath = repo.includes('/') ? repo : `${getGitHubOrg()}/${repo}`;
    const baseUrl = `https://api.github.com/repos/${repoPath}`;

    // Check each file/folder
    const checks = await Promise.all([
      // Check docs folder
      fetch(`${baseUrl}/contents/docs`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check README
      fetch(`${baseUrl}/contents/README.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check CHANGELOG
      fetch(`${baseUrl}/contents/CHANGELOG.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check docs/SUMMARY.md
      fetch(`${baseUrl}/contents/docs/SUMMARY.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check docs/ARCHITECTURE.md
      fetch(`${baseUrl}/contents/docs/ARCHITECTURE.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check docs/WORKFLOW.md
      fetch(`${baseUrl}/contents/docs/WORKFLOW.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
      // Check docs/API.md
      fetch(`${baseUrl}/contents/docs/API.md`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' },
      }).then(r => r.ok),
    ]);

    const [hasDocsFolder, hasReadme, hasChangelog, hasSummary, hasArchitecture, hasWorkflow, hasApi] = checks;

    // Get architecture versions
    const archVersions = await getVersionsFromFolder(repo, 'docs/architecture', token);
    const workflowVersions = await getVersionsFromFolder(repo, 'docs/workflow', token);

    return {
      hasDocsFolder,
      hasReadme,
      hasChangelog,
      hasSummary,
      hasArchitecture,
      hasWorkflow,
      hasApi,
      architectureVersions: archVersions,
      workflowVersions: workflowVersions,
    };
  } catch (error) {
    console.error(`Failed to check doc structure for ${repo}:`, error);
    return {
      hasDocsFolder: false,
      hasReadme: false,
      hasChangelog: false,
      hasSummary: false,
      hasArchitecture: false,
      hasWorkflow: false,
      hasApi: false,
      architectureVersions: [],
      workflowVersions: [],
    };
  }
}

// Helper: Get versions from a folder
async function getVersionsFromFolder(
  repo: string,
  folderPath: string,
  token: string
): Promise<string[]> {
  try {
    const repoPath = repo.includes('/') ? repo : `${getGitHubOrg()}/${repo}`;
    const response = await fetch(
      `https://api.github.com/repos/${repoPath}/contents/${folderPath}`,
      {
        headers: {
          Authorization: `token ${token}`,
          Accept: 'application/vnd.github.v3+json',
        },
      }
    );

    if (!response.ok) return [];

    const files = await response.json();
    return files
      .filter((f: any) => f.type === 'file' && f.name.endsWith('.md') && f.name !== 'current.md')
      .map((f: any) => f.name.replace('.md', ''))
      .sort((a: string, b: string) => {
        // Sort versions numerically
        const aParts = a.split('.').map(Number);
        const bParts = b.split('.').map(Number);
        for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
          const aNum = aParts[i] || 0;
          const bNum = bParts[i] || 0;
          if (aNum !== bNum) return bNum - aNum;
        }
        return 0;
      });
  } catch (error) {
    console.error(`Failed to get versions from ${folderPath}:`, error);
    return [];
  }
}
