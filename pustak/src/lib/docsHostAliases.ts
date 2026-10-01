/**
 * Hardcoded public docs host aliases.
 * Used when an org should be served from a branded subdomain
 * instead of `<org>.docit.in`.
 *
 * Example: AuditorEnvelope (parent / product docs) → docs.docit.in
 */
export const DOCS_HOST_ALIASES: Record<string, string> = {
  // subdomain host → real GitHub/org id used in DocIt
  docs: "auditorenvelope",
};

export const ORG_CUSTOM_DOCS_HOSTS: Record<string, string> = {
  // org id (any casing) → public hostname
  auditorenvelope: "docs.docit.in",
};

export function resolveOrgFromHostname(hostname: string): string | null {
  const host = hostname.split(":")[0].toLowerCase();
  const subdomain = host.split(".")[0];

  if (!subdomain || subdomain === "www" || subdomain === "localhost") {
    return null;
  }

  if (DOCS_HOST_ALIASES[subdomain]) {
    return DOCS_HOST_ALIASES[subdomain];
  }

  // Never treat branded alias hosts as themselves if unmapped
  if (host === "docs.docit.in") {
    return DOCS_HOST_ALIASES.docs;
  }

  return subdomain;
}

export function getPublicDocsBaseUrl(orgId: string): string {
  const key = orgId.trim().toLowerCase();
  const customHost = ORG_CUSTOM_DOCS_HOSTS[key];
  if (customHost) {
    return `https://${customHost}`;
  }
  return `https://${key}.docit.in`;
}

export function getPublicDocsUrl(orgId: string, repoId: string, path = ""): string {
  const base = getPublicDocsBaseUrl(orgId).replace(/\/$/, "");
  const repo = encodeURIComponent(repoId);
  const suffix = path
    ? `/${path
        .split("/")
        .filter(Boolean)
        .map((segment) => encodeURIComponent(segment))
        .join("/")}`
    : "";
  return `${base}/${repo}${suffix}`;
}
