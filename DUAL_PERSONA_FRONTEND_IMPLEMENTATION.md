# Dual Persona Frontend Implementation

## Overview

This document describes the implementation of the dual persona documentation frontend, which supports viewing documentation for two distinct personas:

1. **Internal** (`internal`) - Private documentation for authenticated users
2. **Developer** (`dev`) - Public documentation for unauthenticated users

The implementation follows a "Hub-and-Spoke" URL structure:
- `https://{org}.docbook.site/{repo}/{persona}/{path}`
- `internal/` docs are private and require authentication
- `dev/` docs are public and accessible without authentication
- If no persona is specified, it defaults to `dev`

## Implementation Details

### Phase 2: Frontend Routing & Middleware

#### 1. Updated `middleware.ts`

- Enhanced URL parsing to extract repo, persona, and path
- Added logic to default to 'dev' persona if missing
- Added auth guard for 'internal' persona
- Implemented redirection logic for various scenarios

```typescript
// Parse path to extract repo and possibly persona
const pathSegments = originalPath.split("/").filter(Boolean);
const repoName = pathSegments[0] || ""; // First segment is repo name
let personaName = pathSegments[1] || ""; // Second segment might be persona
const remainingPath = pathSegments.slice(personaName ? 2 : 1).join("/");

// Check if the second segment is a valid persona
const validPersonas = ["internal", "dev"];
if (!validPersonas.includes(personaName)) {
  // If persona is not valid, it's part of the path
  personaName = "dev"; // Default to dev persona
}

// Check for auth when accessing internal persona
if (personaName === "internal") {
  // Get auth token from cookies or headers
  const authToken = request.cookies.get("pustak_access_token")?.value || 
                   request.headers.get("authorization")?.replace("Bearer ", "");
  
  if (!authToken) {
    // Redirect to login page
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("redirect", request.url);
    
    return NextResponse.redirect(loginUrl);
  }
}
```

#### 2. Created New Page Structure

- Added new route: `/docs/[org]/[repo]/[persona]/[...slug]/page.tsx`
- Updated component to handle persona-specific paths
- Added persona indicator in the UI

```tsx
// Extract params
const params = useParams();
const org = params.org as string;
const repo = params.repo as string;
const persona = params.persona as string;
const slug = (params.slug as string[]) || [];

// Persona indicator UI
<div className={`fixed top-0 right-0 z-50 px-4 py-2 m-4 rounded-full text-sm font-medium ${
  persona === "internal" 
    ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" 
    : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
}`}>
  <div className="flex items-center gap-1">
    {persona === "internal" ? (
      <>
        <Shield className="h-4 w-4" />
        <span>Internal</span>
      </>
    ) : (
      <>
        <Globe className="h-4 w-4" />
        <span>Developer</span>
      </>
    )}
  </div>
</div>
```

#### 3. Updated API Endpoints

- Modified backend endpoints to accept persona parameter
- Added 404 handling for missing persona folders
- Updated content path construction to include persona

```python
@router.get("/docbook/live-manifest")
async def get_live_manifest(
    org_id: str = Query(...),
    repo_id: str = Query(...),
    persona: str = Query("dev", description="Documentation persona (internal or dev)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # ...
```

```python
# Include persona in the path
repo_path = f"{repo_id}/docs/{persona}/{relative_path}" if repo_id else f"docs/{persona}/{relative_path}"
```

#### 4. Added 404 Handling for Missing Persona Folders

- Added specific error messages for missing persona folders
- Added suggestions to try the dev persona when internal is not available

```python
if persona_error.status_code == 404:
    # Persona folder doesn't exist
    if persona == "internal":
        # For internal persona, suggest trying dev
        raise HTTPException(
            status_code=404,
            detail=f"Internal documentation not available for {repo_id}. Try accessing the dev documentation instead."
        )
    else:
        # For dev persona
        raise HTTPException(
            status_code=404,
            detail=f"Documentation not available for {repo_id}."
        )
```

## Testing

A test script (`test_dual_persona_frontend.js`) was created to verify the dual persona URL structure and routing logic:

1. Default URL (no persona) - Should redirect to dev persona
2. Explicit dev persona URL - Should load dev persona docs directly
3. Internal persona URL (unauthenticated) - Should redirect to login
4. Invalid persona - Should treat as path and default to dev
5. Nested path with dev persona - Should handle correctly
6. Nested path with internal persona - Should redirect to login

All tests pass, confirming that the routing logic works as expected.

## URL Structure Examples

Here are some examples of the new URL structure:

- `https://example.docbook.site/my-repo` → Redirects to `https://example.docbook.site/docs/example/my-repo/dev`
- `https://example.docbook.site/my-repo/dev` → Shows dev documentation
- `https://example.docbook.site/my-repo/internal` → Shows internal documentation (if authenticated)
- `https://example.docbook.site/my-repo/dev/api` → Shows dev API documentation
- `https://example.docbook.site/my-repo/internal/api` → Shows internal API documentation (if authenticated)

## Conclusion

Phase 2 of the dual persona implementation is complete. The frontend now supports viewing documentation for both internal and developer personas, with appropriate authentication checks and fallback logic. The system is backward compatible with existing URLs and provides helpful error messages when documentation is not available.

Next steps would be to integrate this with the authentication system and test with real documentation repositories.
