"""Hardcoded public docs host aliases for branded org subdomains."""

from __future__ import annotations

# subdomain host → real GitHub/org id used in DocIt
DOCS_HOST_ALIASES = {
    "docs": "auditorenvelope",
}

# org id (lowercase) → public hostname
ORG_CUSTOM_DOCS_HOSTS = {
    "auditorenvelope": "docs.docit.in",
}


def get_public_docs_base_url(org_id: str) -> str:
    key = (org_id or "").strip().lower()
    custom_host = ORG_CUSTOM_DOCS_HOSTS.get(key)
    if custom_host:
        return f"https://{custom_host}"
    return f"https://{key}.docit.in"


def get_public_docs_url(org_id: str, repo_id: str, path: str = "") -> str:
    base = get_public_docs_base_url(org_id).rstrip("/")
    suffix = ""
    if path:
        cleaned = "/".join(segment for segment in path.split("/") if segment)
        if cleaned:
            suffix = f"/{cleaned}"
    return f"{base}/{repo_id}{suffix}"
