/**
 * Start GitHub OAuth in the browser (same flow as /login).
 * On success, redirects to GitHub; user returns via /auth/callback.
 */
const RAW_BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function apiV1Base(): string {
  const trimmed = RAW_BACKEND.replace(/\/$/, "");
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
}

export async function startGitHubOAuth(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  const redirectUri = `${window.location.origin}/auth/callback`;
  const response = await fetch(
    `${apiV1Base()}/auth/github?redirect_uri=${encodeURIComponent(redirectUri)}`,
  );

  if (!response.ok) {
    throw new Error("Failed to get OAuth URL");
  }

  const data = (await response.json()) as { url?: string };
  if (!data.url) {
    throw new Error("Invalid OAuth response");
  }

  window.location.href = data.url;
}
