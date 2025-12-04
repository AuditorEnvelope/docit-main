const DEFAULT_PERSONA = "dev";
const VALID_PERSONAS = new Set(["dev", "internal"]);

const DOCBOOK_REPO_PREFIX = "pustak-docbook-";

interface DocsRouteInput {
  org: string;
  repo: string;
  slug?: string[];
}

interface DocsRouteMapping {
  repoSlug: string[];
  canonicalSlug: string[];
  persona: string;
  docbookRepoName: string;
}

interface DocbookPathInput {
  org: string;
  pathSegments: string[];
}

export function getDocbookRepoName(org: string): string {
  return `${DOCBOOK_REPO_PREFIX}${org}`;
}

function sanitizeSegments(segments: string[] | undefined): string[] {
  if (!segments) return [];
  return segments
    .map((segment) => segment?.trim())
    .filter((segment): segment is string => Boolean(segment && segment.length));
}

function stripExtension(segment: string): string {
  return segment.replace(/\.md$/i, "");
}

function ensureMarkdownFile(segment: string): string {
  return segment.toLowerCase().endsWith(".md") ? segment : `${segment}.md`;
}

function normalizeRepoPath(repo: string, persona: string, segments: string[]): string[] {
  const lowerFirst = segments[0]?.toLowerCase();
  const remainder = segments.slice(1);

  if (segments.length === 0) {
    return [repo, "docs", persona, "SUMMARY.md"];
  }

  if (segments.length === 1) {
    if (lowerFirst === "introduction" || lowerFirst === "summary" || lowerFirst === "readme") {
      return [repo, "docs", persona, "SUMMARY.md"];
    }

    if (lowerFirst === "architecture" || lowerFirst === "workflow") {
      return [repo, "docs", persona, segments[0], "current.md"];
    }

    return [repo, "docs", persona, ensureMarkdownFile(segments[0])];
  }

  const pathSegments = segments.map((segment, index) => {
    if (index === segments.length - 1) {
      return ensureMarkdownFile(segment);
    }
    return segment;
  });

  return [repo, "docs", persona, ...pathSegments];
}

export function mapDocsRouteToRepoSlug({ org, repo, slug }: DocsRouteInput): DocsRouteMapping {
  const sanitized = sanitizeSegments(slug);

  let persona = DEFAULT_PERSONA;
  let remainingSegments = sanitized;

  if (remainingSegments.length > 0 && VALID_PERSONAS.has(remainingSegments[0].toLowerCase())) {
    persona = remainingSegments[0].toLowerCase();
    remainingSegments = remainingSegments.slice(1);
  }

  if (remainingSegments.length === 0) {
    remainingSegments = ["introduction"];
  }

  const normalizedPath = normalizeRepoPath(repo, persona, remainingSegments);
  const docbookRepoName = getDocbookRepoName(org);

  const canonicalSlug = persona === DEFAULT_PERSONA ? remainingSegments : [persona, ...remainingSegments];

  return {
    repoSlug: [org, docbookRepoName, ...normalizedPath],
    canonicalSlug,
    persona,
    docbookRepoName,
  };
}

export function mapDocbookPathToDocsSlug({
  org,
  pathSegments,
}: DocbookPathInput): { href: string; slugSegments: string[]; persona: string } | null {
  if (!Array.isArray(pathSegments) || pathSegments.length < 4) {
    return null;
  }

  const [repoName, docsKeyword, personaRaw, ...rest] = pathSegments;
  if (docsKeyword !== "docs" || rest.length === 0) {
    return null;
  }

  const persona = personaRaw?.toLowerCase() || DEFAULT_PERSONA;
  const slugSegments = rest.map((segment) => stripExtension(segment));

  if (slugSegments.length === 1) {
    const alias = slugSegments[0].toLowerCase();
    if (alias === "summary" || alias === "readme") {
      slugSegments[0] = "introduction";
    }
  }

  const finalSlug = persona === DEFAULT_PERSONA ? slugSegments : [persona, ...slugSegments];
  const encodedSlug = finalSlug.map((segment) => encodeURIComponent(segment)).join("/");

  const href = encodedSlug.length
    ? `/docs/${encodeURIComponent(org)}/${encodeURIComponent(repoName)}/${encodedSlug}`
    : `/docs/${encodeURIComponent(org)}/${encodeURIComponent(repoName)}`;

  return { href, slugSegments: finalSlug, persona };
}

export { DEFAULT_PERSONA, VALID_PERSONAS };
