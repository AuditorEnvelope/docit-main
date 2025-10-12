import fs from "fs";
import path from "path";

export interface MarkdownFile {
  content: string;
  lastModified: Date;
  fileName: string;
}

export interface RepoDocumentation {
  summary?: MarkdownFile;
  api?: MarkdownFile;
  changelog?: MarkdownFile;
  changes?: MarkdownFile[];
  migrationGuide?: MarkdownFile;
  readme?: MarkdownFile;
  [key: string]: MarkdownFile | MarkdownFile[] | undefined;
}

export function loadMarkdownFiles(repoPath: string): RepoDocumentation {
  const docsPath = path.join(repoPath, "docs");
  const result: RepoDocumentation = {};

  if (!fs.existsSync(docsPath)) {
    return result;
  }

  // Load individual markdown files
  const markdownFiles = [
    "README.md",
    "api.md",
    "migration-guide.md",
    "SUMMARY.md",
    "DOC_AI_RUN_LOG.md",
    "processor.py.md",
  ];

  markdownFiles.forEach((fileName) => {
    const filePath = path.join(docsPath, fileName);
    if (fs.existsSync(filePath)) {
      const stats = fs.statSync(filePath);
      const content = fs.readFileSync(filePath, "utf-8");

      // Map file names to proper keys
      let key = fileName.replace(/\.md$/, "").replace(/-/g, "");
      if (fileName === "README.md") key = "readme";
      if (fileName === "api.md") key = "api";
      if (fileName === "migration-guide.md") key = "migrationGuide";
      if (fileName === "SUMMARY.md") key = "summary";
      if (fileName === "DOC_AI_RUN_LOG.md") key = "docAIRunLog";
      if (fileName === "processor.py.md") key = "processorPy";

      result[key] = {
        content,
        lastModified: stats.mtime,
        fileName,
      };
    }
  });

  // Load changes directory
  const changesPath = path.join(docsPath, "changes");
  if (fs.existsSync(changesPath)) {
    const changeFiles = fs
      .readdirSync(changesPath)
      .filter((file) => file.endsWith(".md"))
      .map((fileName) => {
        const filePath = path.join(changesPath, fileName);
        const stats = fs.statSync(filePath);
        const content = fs.readFileSync(filePath, "utf-8");

        return {
          content,
          lastModified: stats.mtime,
          fileName,
        };
      })
      .sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime()); // Sort by newest first

    result.changes = changeFiles;
  }

  // Load CHANGELOG.md from root
  const changelogPath = path.join(repoPath, "CHANGELOG.md");
  if (fs.existsSync(changelogPath)) {
    const stats = fs.statSync(changelogPath);
    const content = fs.readFileSync(changelogPath, "utf-8");

    result.changelog = {
      content,
      lastModified: stats.mtime,
      fileName: "CHANGELOG.md",
    };
  }

  return result;
}

export function getRepoList(): string[] {
  // For now, return the current repo since we're running locally
  return ["doc-ai"];
}

export function getLatestUpdateTime(repoPath: string): Date {
  const docsPath = path.join(repoPath, "docs");
  let latestTime = new Date(0);

  if (!fs.existsSync(docsPath)) {
    return latestTime;
  }

  // Check all markdown files
  const files = [
    "README.md",
    "api.md",
    "migration-guide.md",
    "SUMMARY.md",
    "CHANGELOG.md",
  ];

  files.forEach((file) => {
    const filePath =
      file === "CHANGELOG.md"
        ? path.join(repoPath, file)
        : path.join(docsPath, file);

    if (fs.existsSync(filePath)) {
      const stats = fs.statSync(filePath);
      if (stats.mtime > latestTime) {
        latestTime = stats.mtime;
      }
    }
  });

  return latestTime;
}
