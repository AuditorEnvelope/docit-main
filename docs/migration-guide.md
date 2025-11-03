# Migration Guide

*Updated: 2025-10-22*

This migration guide outlines the necessary steps to upgrade your application to accommodate the new GitHub OAuth authentication system and related changes. This is a significant update that impacts authentication, user management, frontend UI, backend API, and application configuration.

---

# Migration Guide: GitHub OAuth Authentication System (Breaking Change)

## Overview

This guide details the steps required to migrate your application to integrate the new GitHub OAuth authentication system. This update introduces robust user authentication, JWT-based session management, and a revised user experience across both the backend and frontend. It also prepares the application for multi-organization support by refining repository handling.

**Version:** [Insert New Version Number Here, e.g., v1.0.0]
**Date:** [Insert Date]

## 1. What Changed and Why

This release introduces a fundamental shift in how users authenticate and manage their sessions. Previously, there might have been no authentication, or a simpler, less integrated system. This update brings a full-fledged GitHub OAuth flow.

**Why the Change?**
The primary reason for these changes is to establish a secure, standardized, and user-friendly authentication and session management system. This enables:
*   **Secure User Identification:** Using GitHub OAuth for reliable user authentication.
*   **Personalized Experiences:** Allowing users to log in, manage profiles, and access features based on their identity.
*   **Enhanced Session Management:** Implementing JWT for secure, stateless user sessions.
*   **Foundation for Enterprise Features:** Setting the groundwork for organization-level features and multi-organization support.
*   **Improved User Flow:** Streamlining the signup/login process and integrating user management into the UI.

**Key Changes Introduced:**

*   **GitHub OAuth Integration:** The backend now fully supports GitHub OAuth for user login and callback handling.
*   **JWT-Based Sessions:** User sessions are now managed using JSON Web Tokens (JWTs), replacing any previous session management or introducing it where none existed.
*   **New API Endpoints:** New backend endpoints (`/api/auth/github/login`, `/api/auth/github/callback`, `/api/auth/me`) are introduced for authentication and user information retrieval.
*   **Global Frontend Authentication Context:** A new `AuthContext` and `AuthProvider` provide global access to the authentication state in the frontend.
*   **User UI Components:** The frontend `Layout` now includes a conditional user menu for authenticated users (Profile, Organization Settings, Billing, Logout).
*   **Configuration Changes:** Crucial new environment variables are required for GitHub OAuth (Client ID, Client Secret) and JWT (Secret), along with an optional GitHub organization setting.
*   **Revised Pricing Flow:** Direct `/signup` routes have been removed, with free plans redirecting to the home page and paid plans to a `/checkout` page.
*   **Repository Handling Refinement:** Repository references now explicitly require the `owner/repo` format for better multi-organization support.

**Summary of Breaking Changes:**

1.  **New Required Environment Variables:** Your application will not run without `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SECRET`. `GITHUB_ORG` is also highly recommended.
2.  **Backend API Changes:** If you had any existing authentication logic or relied on a specific user identity, it must be migrated to use the new OAuth and JWT system.
3.  **Frontend Authentication Logic:** Any components relying on user authentication state or requiring user details must be updated to use the new `AuthContext`.
4.  **Frontend Layout/UI:** The application's main layout will need adjustments to integrate the new user menu and `AuthProvider`.
5.  **Pricing Page Links:** Direct links to `/signup` are deprecated and must be updated.
6.  **Repository Path Format:** Any part of your application (frontend or backend) that constructs or parses repository names must now use the `owner/repo` format consistently.

---

## 2. Step-by-Step Migration Instructions

Please follow these instructions carefully. It's highly recommended to perform these steps in a development or staging environment first.

### Pre-migration Checklist

*   **Backup your entire application codebase and database.**
*   Ensure you have Git installed and are familiar with basic Git commands.
*   Have access to your GitHub account settings to register an OAuth application.

---

### Phase 1: Backend Setup and Configuration

1.  **Update Backend Dependencies:**
    Install the new Python packages required for JWT and OAuth handling.

    ```bash
    pip install "fastapi-jwt-auth[fastapi]" python-jose
    ```

2.  **Register a GitHub OAuth Application:**
    You need to register a new OAuth App with GitHub.
    *   Go to your GitHub profile settings (or your organization's settings).
    *   Navigate to **Developer settings** -> **OAuth Apps**.
    *   Click **"New OAuth App"**.
    *   Fill in the details:
        *   **Application name:** `[Your App Name]` (e.g., "Pustak Development")
        *   **Homepage URL:** `[Your Application's Public URL]` (e.g., `http://localhost:3000` for local development, or `https://app.yourdomain.com`)
        *   **Authorization callback URL:** This is critical. It must point to your backend's OAuth callback endpoint.
            *   For local development: `http://localhost:8000/api/auth/github/callback`
            *   For production: `https://api.yourdomain.com/api/auth/github/callback` (or your backend's public URL)
    *   Click **"Register application"**.
    *   You will be given a **Client ID** and a **Client Secret**. **Copy these values immediately.** The Client Secret is shown only once. If you lose it, you'll have to generate a new one.

3.  **Update Environment Variables (`.env`):**
    Add the following new variables to your `.env` file. These are **mandatory**.

    ```ini
    # GitHub OAuth Configuration
    GITHUB_CLIENT_ID="<Your GitHub OAuth Client ID>"
    GITHUB_CLIENT_SECRET="<Your GitHub OAuth Client Secret>"
    GITHUB_ORG="<Optional: Your GitHub Organization Name for filtering repos, e.g., 'pustak-org'>" # Required for organization-specific features

    # JWT Authentication Configuration
    JWT_SECRET="<A long, random, and secret string for JWT signing>"
    ```

    *   **`GITHUB_CLIENT_ID`**: Paste the Client ID obtained from GitHub.
    *   **`GITHUB_CLIENT_SECRET`**: Paste the Client Secret obtained from GitHub.
    *   **`GITHUB_ORG`**: If your application is designed to primarily work with repositories from a specific GitHub organization, provide its name here (e.g., `my-company-org`). This enables filtering and specific organization features. If omitted, the application might default to showing all accessible repositories for a user.
    *   **`JWT_SECRET`**: Generate a strong, random secret key. You can use tools like `openssl rand -hex 32` or an online secret key generator for this. **Never commit this to version control.**

4.  **Modify Backend (`src/main.py`):**
    You need to integrate the new authentication routes and JWT configuration.

    *   **Import necessary libraries:**
        ```python
        from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
        from fastapi.responses import RedirectResponse
        from fastapi_jwt_auth import AuthJWT
        from fastapi_jwt_auth.exceptions import AuthJWTException
        from pydantic import BaseModel # Or your existing Pydantic models for user
        import os
        import httpx # For making requests to GitHub API
        import base64
        import json

        # Ensure these are imported from your project's structure if they exist
        # from .lib.github_api_client import GitHubAPIClient # Example
        # from .models.user import User # Example
        ```

    *   **Initialize `AuthJWT` settings:**
        ```python
        # Configuration for JWT
        class Settings(BaseModel):
            authjwt_secret_key: str = os.getenv("JWT_SECRET")
            authjwt_cookie_samesite: str = "lax"
            authjwt_token_location: set = {"cookies"}
            authjwt_cookie_csrf_protect: bool = True # Highly recommended for production

        @AuthJWT.load_config
        def get_config():
            return Settings()

        # ... your existing FastAPI app initialization ...
        app = FastAPI()

        # ... your existing CORS middleware or other app configs ...
        # Example CORS (ensure your frontend URL is allowed)
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "https://app.yourdomain.com"], # Add your frontend domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        ```

    *   **Add GitHub OAuth and JWT Authentication Routes:**
        This will involve creating several new endpoints. The exact implementation details might vary based on your existing code structure, but here's a conceptual outline.

        ```python
        GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
        GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
        GITHUB_ORG = os.getenv("GITHUB_ORG") # Optional, for filtering
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000") # Your frontend's URL

        # Endpoint to initiate GitHub OAuth login
        @app.get("/api/auth/github/login")
        async def github_login():
            if not GITHUB_CLIENT_ID:
                raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
            
            # Generate a state parameter to prevent CSRF attacks
            # In a real app, you'd store this securely (e.g., in a session)
            # For simplicity here, we'll just use a random string.
            state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
            
            github_oauth_url = (
                f"https://github.com/login/oauth/authorize?"
                f"client_id={GITHUB_CLIENT_ID}&"
                f"redirect_uri={os.getenv('GITHUB_CALLBACK_URL', 'http://localhost:8000/api/auth/github/callback')}&"
                f"scope=read:user,repo&" # Adjust scopes as needed
                f"state={state}"
            )
            return RedirectResponse(github_oauth_url)

        # Endpoint to handle GitHub OAuth callback
        @app.get("/api/auth/github/callback")
        async def github_callback(code: str, state: str, Auth: AuthJWT = Depends()):
            if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
                raise HTTPException(status_code=500, detail="GitHub credentials not configured")

            # In a real app, verify the 'state' parameter against what you sent in /login
            # If state is not validated, it's a CSRF vulnerability.

            # Exchange code for an access token
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    json={
                        "client_id": GITHUB_CLIENT_ID,
                        "client_secret": GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                )
                token_data = token_response.json()

            if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail="Failed to get GitHub access token")

            github_access_token = token_data["access_token"]

            # Use the access token to get user info from GitHub
            async with httpx.AsyncClient() as client:
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"token {github_access_token}",
                        "Accept": "application/json",
                    },
                )
                user_info = user_response.json()

            if "id" not in user_info:
                raise HTTPException(status_code=400, detail="Failed to get GitHub user info")

            # --- Your User Management Logic Here ---
            # You would typically:
            # 1. Look up user by user_info['id'] (GitHub ID) in your database.
            # 2. If user doesn't exist, create a new user record.
            # 3. Store the github_access_token (encrypted!) for future API calls.
            # 4. Get your internal user ID.
            # For this example, we'll just use the GitHub login as identity
            user_id = user_info['login'] # Or your internal user ID

            # Create JWT tokens
            access_token = Auth.create_access_token(subject=user_id)
            refresh_token = Auth.create_refresh_token(subject=user_id)

            response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard") # Redirect to your dashboard
            Auth.set_access_cookies(access_token, response)
            Auth.set_refresh_cookies(refresh_token, response)
            return response

        # Endpoint to get current user info
        @app.get("/api/auth/me")
        async def get_current_user(Auth: AuthJWT = Depends()):
            Auth.jwt_required()
            current_user = Auth.get_jwt_subject()
            # In a real app, fetch detailed user info from your DB based on current_user (e.g., GitHub login)
            return {"user_id": current_user, "message": "Authenticated"}

        # Endpoint for logout
        @app.delete("/api/auth/logout")
        def logout(Auth: AuthJWT = Depends()):
            Auth.jwt_required()
            response = Response(status_code=status.HTTP_200_OK)
            Auth.unset_jwt_cookies(response)
            return response

        # Example: Handle JWT exceptions globally
        @app.exception_handler(AuthJWTException)
        def authjwt_exception_handler(request: Request, exc: AuthJWTException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.message}
            )

        ```

    *   **Refine Repository Handling (if applicable to `main.py`):**
        Ensure any backend logic that fetches or processes repository information uses the `owner/repo` format. For instance, if you have an endpoint like `/api/repo/{repo_name}` it should likely become `/api/repo/{owner}/{repo_name}` or `/api/repo/{owner_repo_name}` and parse the combined string.

    *   **Restart your backend server** after these changes to load new dependencies and environment variables.

---

### Phase 2: Frontend Integration

1.  **Create an Authentication Context (`src/contexts/AuthContext.tsx`):**
    This will provide the authentication state to your entire application.

    ```typescript
    // pustak/src/contexts/AuthContext.tsx
    import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
    import axios from 'axios'; // Or your preferred HTTP client

    interface User {
      id: string; // Or whatever uniquely identifies your user
      // Add other user properties you might get from /api/auth/me
    }

    interface AuthContextType {
      isAuthenticated: boolean;
      user: User | null;
      isLoading: boolean;
      login: () => void;
      logout: () => Promise<void>;
      fetchUser: () => Promise<void>;
    }

    const AuthContext = createContext<AuthContextType | undefined>(undefined);

    export const AuthProvider = ({ children }: { children: ReactNode }) => {
      const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
      const [user, setUser] = useState<User | null>(null);
      const [isLoading, setIsLoading] = useState<boolean>(true);

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'; // Or your actual backend URL

      const fetchUser = async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/auth/me`, { withCredentials: true });
          setUser({ id: response.data.user_id }); // Adapt to your actual user data
          setIsAuthenticated(true);
        } catch (error) {
          console.error("Failed to fetch user:", error);
          setUser(null);
          setIsAuthenticated(false);
        } finally {
          setIsLoading(false);
        }
      };

      useEffect(() => {
        fetchUser();
      }, []);

      const login = () => {
        // Redirect to backend for GitHub OAuth initiation
        window.location.href = `${API_BASE_URL}/api/auth/github/login`;
      };

      const logout = async () => {
        try {
          await axios.delete(`${API_BASE_URL}/api/auth/logout`, { withCredentials: true });
          setUser(null);
          setIsAuthenticated(false);
        } catch (error) {
          console.error("Logout failed:", error);
          // Even if logout fails on server, clear client state for better UX
          setUser(null);
          setIsAuthenticated(false);
        }
      };

      return (
        <AuthContext.Provider value={{ isAuthenticated, user, isLoading, login, logout, fetchUser }}>
          {children}
        </AuthContext.Provider>
      );
    };

    export const useAuth = () => {
      const context = useContext(AuthContext);
      if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
      }
      return context;
    };
    ```

2.  **Wrap Application with `AuthProvider` (`pustak/src/app/providers.tsx`):**
    Ensure your entire application (or at least the parts needing auth) is wrapped by the `AuthProvider`.

    ```typescript
    // pustak/src/app/providers.tsx
    'use client';

    import { ThemeProvider } from 'next-themes';
    import { AuthProvider } from '@/contexts/AuthContext'; // Import your new AuthProvider
    import React from 'react';

    export function Providers({ children }: { children: React.ReactNode }) {
      return (
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider> {/* Wrap with AuthProvider */}
            {children}
          </AuthProvider>
        </ThemeProvider>
      );
    }
    ```

3.  **Update Layout Component (`pustak/src/components/Layout.tsx` or similar):**
    Integrate the user menu based on authentication status.

    ```typescript
    // pustak/src/components/Layout.tsx (conceptual)
    'use client';

    import React from 'react';
    import Link from 'next/link';
    import { useAuth } from '@/contexts/AuthContext'; // Import useAuth
    import { Button } from '@/components/ui/button'; // Example UI component

    export default function Layout({ children }: { children: React.ReactNode }) {
      const { isAuthenticated, user, isLoading, login, logout } = useAuth();

      if (isLoading) {
        return <div>Loading authentication...</div>; // Or a spinner
      }

      return (
        <div className="min-h-screen flex flex-col">
          <header className="bg-gray-800 text-white p-4 flex justify-between items-center">
            <Link href="/" className="text-xl font-bold">Your App Name</Link>
            <nav className="flex space-x-4">
              <Link href="/pricing">Pricing</Link>
              {isAuthenticated ? (
                <div className="relative group">
                  <Button variant="ghost">
                    Hello, {user?.id || 'User'} {/* Display user ID/name */}
                  </Button>
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-20 hidden group-hover:block">
                    <Link href="/profile" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Profile</Link>
                    <Link href="/organization" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Organization Settings</Link>
                    <Link href="/billing" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Billing</Link>
                    <button onClick={logout} className="block w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-100">Logout</button>
                  </div>
                </div>
              ) : (
                <Button onClick={login}>Login with GitHub</Button>
              )}
            </nav>
          </header>
          <main className="flex-grow p-4">
            {children}
          </main>
          {/* Footer or other global elements */}
        </div>
      );
    }
    ```

4.  **Update Pricing Page Links (`pustak/src/app/pricing/page.tsx`):**
    Adjust `signup` links to the new flow.

    ```typescript
    // pustak/src/app/pricing/page.tsx (conceptual)
    'use client';
    import React from 'react';
    import Link from 'next/link';
    import { useAuth } from '@/contexts/AuthContext'; // Import useAuth
    import { Button } from '@/components/ui/button'; // Example UI component

    export default function PricingPage() {
      const { isAuthenticated, login } = useAuth();

      return (
        <div className="container mx-auto p-8">
          <h1 className="text-4xl font-bold text-center mb-12">Our Plans</h1>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Free Plan */}
            <div className="border p-6 rounded-lg shadow-lg text-center">
              <h2 className="text-2xl font-semibold mb-4">Free Plan</h2>
              <p className="text-lg mb-6">Start building for free.</p>
              {isAuthenticated ? (
                <Link href="/" passHref>
                  <Button>Go to Dashboard</Button>
                </Link>
              ) : (
                <Button onClick={login}>Get Started for Free</Button>
              )}
            </div>

            {/* Pro Plan */}
            <div className="border p-6 rounded-lg shadow-lg text-center">
              <h2 className="text-2xl font-semibold mb-4">Pro Plan</h2>
              <p className="text-lg mb-6">$19/month</p>
              <Link href="/checkout?plan=pro" passHref> {/* Redirect to checkout */}
                <Button>Choose Pro</Button>
              </Link>
            </div>

            {/* Enterprise Plan */}
            <div className="border p-6 rounded-lg shadow-lg text-center">
              <h2 className="text-2xl font-semibold mb-4">Enterprise</h2>
              <p className="text-lg mb-6">Custom pricing</p>
              <Link href="/contact" passHref> {/* Or a different contact/quote page */}
                <Button>Contact Us</Button>
              </Link>
            </div>
          </div>
        </div>
      );
    }
    ```

5.  **Refine Repository Handling (`pustak/src/app/repo/[repoName]/[docType]/page.tsx` and `pustak/src/lib/realGitHubAPI.ts`):**
    Ensure all components that deal with GitHub repositories use the full `owner/repo` format.

    *   **In `pustak/src/app/repo/[repoName]/[docType]/page.tsx`:**
        If `repoName` was previously just the repository name, it now needs to encompass the owner as well.
        ```typescript
        // Old (if repoName was just 'my-repo'):
        // const repo = params.repoName; // e.g., 'my-repo'
        // const [owner, repoName] = ['some-default-owner', repo]; // Inferred owner

        // New (repoName from URL should be 'owner/my-repo'):
        const fullRepoName = params.repoName; // e.g., 'pustak-org/my-repo'
        const [owner, repoName] = fullRepoName.split('/');

        // Pass 'owner' and 'repoName' to your API calls or GitHub client
        // E.g., fetchDoc(owner, repoName, docType);
        ```
    *   **In `pustak/src/lib/realGitHubAPI.ts` (and any other GitHub API clients):**
        Modify functions that fetch repository data to accept `owner` and `repoName` separately, or a combined `fullRepoName` string which is then parsed.

        ```typescript
        // Old (if functions accepted only repoName)
        // async function getRepoContents(repoName: string, path: string): Promise<any> {
        //   const response = await fetch(`https://api.github.com/repos/default-org/${repoName}/contents/${path}`);
        //   // ...
        // }

        // New
        async function getRepoContents(owner: string, repoName: string, path: string): Promise<any> {
          const response = await fetch(`https://api.github.com/repos/${owner}/${repoName}/contents/${path}`, {
            headers: {
              'Authorization': `token <your-github-token-if-authenticated>`, // If you pass a token
              'Accept': 'application/vnd.github.v3+json'
            }
          });
          if (!response.ok) {
            throw new Error(`Failed to fetch ${owner}/${repoName}/${path}: ${response.statusText}`);
          }
          return response.json();
        }

        // Or if you prefer to pass the combined string:
        // async function getRepoContents(fullRepoName: string, path: string): Promise<any> {
        //   const [owner, repoName] = fullRepoName.split('/');
        //   // ... same logic as above ...
        // }
        ```

### Phase 3: Testing

1.  **Start your backend and frontend servers.**
2.  **Verify GitHub OAuth Flow:**
    *   Navigate to your frontend application.
    *   Click on the "Login with GitHub" button.
    *   You should be redirected to GitHub for authorization.
    *   After authorizing, you should be redirected back to your frontend (e.g., `/dashboard`) and see your user information in the header.
3.  **Test Logout:** Verify that clicking "Logout" clears the session and returns you to an unauthenticated state.
4.  **Test Pricing Links:** Ensure "Get Started for Free" uses the login flow, and paid plans redirect to `/checkout`.
5.  **Test Repository Access:** Verify that repository pages (`/repo/owner/repo-name/docType`) load correctly and fetch data using the new `owner/repo` format.
6.  **Check API Endpoints:** Use a tool like Postman or your browser's dev tools to confirm `/api/auth/me` returns user data when authenticated and `401 Unauthorized` when not.

---

## 3. Code Examples (Before/After)

### `.env.example`

**Before:**
(Potentially empty or existing non-auth variables)
```ini
# No authentication specific variables
# ... other variables ...
```

**After:**
```ini
# GitHub OAuth Configuration
GITHUB_CLIENT_ID="your_github_client_id_here"
GITHUB_CLIENT_SECRET="your_github_client_secret_here"
GITHUB_ORG="pustak-org" # Optional, but recommended for specific features

# JWT Authentication Configuration
JWT_SECRET="a_very_long_and_random_jwt_secret_key"

# Frontend URL (for redirects)
FRONTEND_URL="http://localhost:3000"
# Backend Callback URL (explicitly set if different from default)
GITHUB_CALLBACK_URL="http://localhost:8000/api/auth/github/callback"

# ... other existing variables ...
```

### `src/main.py` (Backend FastAPI)

**Before (Conceptual - no auth or basic auth):**
```python
# src/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# No GitHub OAuth or JWT routes
# ...
```

**After (Simplified example):**
```python
# src/main.py
from fastapi import FastAPI, Depends, HTTPException, Response, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
import os
import httpx
import base64

# Add CORS middleware (crucial for frontend communication)
from fastapi.middleware.cors import CORSMiddleware

# JWT Configuration
class Settings(BaseModel):
    authjwt_secret_key: str = os.getenv("JWT_SECRET", "super_secret_dev_key") # Fallback for dev only, use real secret
    authjwt_cookie_samesite: str = "lax"
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_csrf_protect: bool = True

@AuthJWT.load_config
def get_config():
    return Settings()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")], # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for JWT errors
@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# Get env vars
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/api/auth/github/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# GitHub OAuth Login
@app.get("/api/auth/github/login")
async def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    github_oauth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={GITHUB_CALLBACK_URL}&"
        f"scope=read:user,repo&"
        f"state={state}"
    )
    return RedirectResponse(github_oauth_url)

# GitHub OAuth Callback
@app.get("/api/auth/github/callback")
async def github_callback(code: str, state: str, Auth: AuthJWT = Depends()):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub credentials not configured")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        token_data = token_response.json()

    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail="Failed to get GitHub access token")

    github_access_token = token_data["access_token"]
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {github_access_token}",
                "Accept": "application/json",
            },
        )
        user_info = user_response.json()

    user_id = user_info['login'] # Using GitHub login as user ID

    access_token = Auth.create_access_token(subject=user_id)
    refresh_token = Auth.create_refresh_token(subject=user_id)

    response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
    Auth.set_access_cookies(access_token, response)
    Auth.set_refresh_cookies(refresh_token, response)
    return response

# Get Current User
@app.get("/api/auth/me")
async def get_current_user(Auth: AuthJWT = Depends()):
    Auth.jwt_required()
    current_user = Auth.get_jwt_subject()
    return {"user_id": current_user, "message": "Authenticated"}

# Logout
@app.delete("/api/auth/logout")
def logout(Auth: AuthJWT = Depends()):
    Auth.jwt_required()
    response = Response(status_code=status.HTTP_200_OK)
    Auth.unset_jwt_cookies(response)
    return response

# ... other existing routes ...
```

### `pustak/src/app/providers.tsx` (Frontend Next.js)

**Before:**
```tsx
// pustak/src/app/providers.tsx
'use client';

import { ThemeProvider } from 'next-themes';
import React from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

**After:**
```tsx
// pustak/src/app/providers.tsx
'use client';

import { ThemeProvider } from 'next-themes';
import { AuthProvider } from '@/contexts/AuthContext'; // NEW: Import AuthProvider
import React from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <AuthProvider> {/* NEW: Wrap children with AuthProvider */}
        {children}
      </AuthProvider>
    </ThemeProvider>
  );
}
```

### `pustak/src/components/Layout.tsx` (Frontend)

**Before (Conceptual - no user menu or simple login button):**
```tsx
// pustak/src/components/Layout.tsx
import React from 'react';
import Link from 'next/link';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-800 text-white p-4 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold">Your App Name</Link>
        <nav className="flex space-x-4">
          <Link href="/pricing">Pricing</Link>
          <Link href="/login">Login</Link> {/* Or a simple button */}
        </nav>
      </header>
      <main className="flex-grow p-4">
        {children}
      </main>
    </div>
  );
}
```

**After:**
```tsx
// pustak/src/components/Layout.tsx
'use client';
import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext'; // NEW: Import useAuth
import { Button } from '@/components/ui/button'; // Example UI component, adjust as needed

export default function Layout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, isLoading, login, logout } = useAuth(); // NEW: Use auth context

  if (isLoading) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <p>Loading application...</p> {/* Or a proper spinner */}
        </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-800 text-white p-4 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold">Your App Name</Link>
        <nav className="flex space-x-4">
          <Link href="/pricing">Pricing</Link>
          {isAuthenticated ? (
            <div className="relative group"> {/* User Menu */}
              <Button variant="ghost">Hello, {user?.id || 'User'}</Button>
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-20 hidden group-hover:block">
                <Link href="/profile" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Profile</Link>
                <Link href="/organization" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Organization Settings</Link>
                <Link href="/billing" className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Billing</Link>
                <button onClick={logout} className="block w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-100">Logout</button>
              </div>
            </div>
          ) : (
            <Button onClick={login}>Login with GitHub</Button> // NEW: Call login function
          )}
        </nav>
      </header>
      <main className="flex-grow p-4">
        {children}
      </main>
    </div>
  );
}
```

### `pustak/src/app/repo/[repoName]/[docType]/page.tsx` (Frontend Repository Page)

**Before (if `repoName` was just the repository name):**
```tsx
// pustak/src/app/repo/[repoName]/[docType]/page.tsx
'use client';
import React from 'react';
import { useParams } from 'next/navigation';
// import { fetchRepoContent } from '@/lib/realGitHubAPI'; // Example API client

export default function RepoDocPage() {
  const params = useParams();
  const repoName = params.repoName as string; // e.g., 'my-awesome-repo'
  const docType = params.docType as string;

  // Assume a default owner or infer it
  const owner = 'default-owner'; // Hardcoded or from env

  // Example usage:
  // const { data, error, isLoading } = useQuery(['repoContent', owner, repoName, docType], () =>
  //   fetchRepoContent(owner, repoName, docType)
  // );

  return (
    <div>
      <h1>Viewing {docType} in {repoName} (Owner: {owner})</h1>
      {/* ... */}
    </div>
  );
}
```

**After (expecting `repoName` from URL to be `owner/repo-name`):**
```tsx
// pustak/src/app/repo/[repoName]/[docType]/page.tsx
'use client';
import React from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext'; // May need auth for private repos
// import { fetchRepoContent } from '@/lib/realGitHubAPI'; // Example API client

export default function RepoDocPage() {
  const params = useParams();
  const fullRepoName = params.repoName as string; // NEW: expects 'owner/my-awesome-repo'
  const docType = params.docType as string;

  // NEW: Parse owner and repoName
  const [owner, repoName] = fullRepoName.split('/');
  if (!owner || !repoName) {
    // Handle invalid URL format, e.g., redirect or show error
    return <div>Invalid repository path. Expected format: /repo/owner/repo-name/docType</div>;
  }

  // Example usage:
  // const { data, error, isLoading } = useQuery(['repoContent', owner, repoName, docType], () =>
  //   fetchRepoContent(owner, repoName, docType) // Pass owner and repoName explicitly
  // );

  return (
    <div>
      <h1>Viewing {docType} in {repoName} (Owner: {owner})</h1>
      {/* ... */}
    </div>
  );
}
```

---

## 4. Common Issues and Solutions

1.  **Issue: Missing Environment Variables.**
    *   **Symptom:** Backend fails to start or gives "KeyError" for `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SECRET`, or `GITHUB_ORG`.
    *   **Solution:** Double-check your `.env` file for all required variables (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SECRET`, `GITHUB_ORG`, `FRONTEND_URL`, `GITHUB_CALLBACK_URL`). Ensure they are correctly set and accessible to your backend process. Remember to restart your backend server after updating `.env`.

2.  **Issue: GitHub OAuth Callback URL Mismatch.**
    *   **Symptom:** After clicking "Login with GitHub" and authorizing, GitHub redirects with an error like "The redirect_uri parameter does not match the pre-registered value."
    *   **Solution:** Go to your GitHub OAuth App settings. Ensure the "Authorization callback URL" exactly matches the `redirect_uri` you're providing in the `/api/auth/github/login` endpoint (which should be `GITHUB_CALLBACK_URL` from your `.env`). Pay close attention to `http` vs `https`, domain, port, and path (`/api/auth/github/callback`).

3.  **Issue: JWT Authentication Errors (e.g., "Signature verification failed").**
    *   **Symptom:** After logging in, subsequent requests to `/api/auth/me` or other protected endpoints fail with authentication errors.
    *   **Solution:**
        *   Ensure `JWT_SECRET` in your `.env` is a long, random, and **identical** string across all deployments/environments if they share JWTs.
        *   Verify `fastapi_jwt_auth` settings (especially `authjwt_secret_key`) in `src/main.py` correctly load the `JWT_SECRET` from environment variables.
        *   Ensure your frontend is sending cookies (`withCredentials: true` in `axios` or `fetch` calls).

4.  **Issue: Frontend Not Updating Authentication State / User Information.**
    *   **Symptom:** User logs in successfully, but the frontend UI (e.g., header menu) doesn't switch to the authenticated state or display user data.
    *   **Solution:**
        *   Verify that your entire application is wrapped by `AuthProvider` in `pustak/src/app/providers.tsx`.
        *   Ensure components like `Layout.tsx` are correctly using the `useAuth()` hook.
        *   Check browser developer tools for any JavaScript errors related to the `AuthContext` or API calls.
        *   Make sure `fetchUser` in `AuthContext` is correctly making the request to `/api/auth/me` and updating state.

5.  **Issue: CORS Errors (Cross-Origin Resource Sharing).**
    *   **Symptom:** Browser console shows errors like "Access to fetch has been blocked by CORS policy" when making API calls from frontend to backend.
    *   **Solution:**
        *   Ensure `fastapi.middleware.cors.CORSMiddleware` is correctly configured in your `src/main.py`.
        *   The `allow_origins` list **must** include the exact URL of your frontend application (e.g., `http://localhost:3000` for development, `https://app.yourdomain.com` for production).
        *   `allow_credentials=True` is crucial for sending/receiving cookies.

6.  **Issue: Repository Not Found / Invalid Path.**
    *   **Symptom:** Pages like `/repo/my-repo/doc` fail to load data, or the backend API returns 404s for repository requests.
    *   **Solution:**
        *   Verify that all links and API calls to repository-related endpoints on the frontend are using the `owner/repo-name` format (e.g., `/repo/pustak-org/my-book/doc`).
        *   Ensure your backend and `pustak/src/lib/realGitHubAPI.ts` functions are correctly parsing `owner` and `repoName` from the combined string or accepting them as separate parameters.

---

## 5. Rollback Instructions

If you encounter critical issues during or after the migration and need to revert to the previous state, follow these steps:

1.  **Revert Codebase Changes:**
    *   If you're using Git, discard all changes made during the migration.
        ```bash
        git restore .
        git clean -fd
        # If you made a dedicated migration branch:
        # git checkout main # Or your previous stable branch
        # git reset --hard HEAD # CAUTION: This will discard ALL uncommitted changes!
        ```
    *   If you created a backup, restore your entire application codebase from that backup.

2.  **Revert Environment Variables:**
    *   Remove the new environment variables (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SECRET`, `GITHUB_ORG`, `FRONTEND_URL`, `GITHUB_CALLBACK_URL`) from your `.env` file.
    *   Restore any previous authentication-related environment variables if they were replaced.

3.  **Uninstall New Backend Dependencies:**
    *   Remove the newly installed Python packages:
        ```bash
        pip uninstall fastapi-jwt-auth python-jose
        ```

4.  **Remove GitHub OAuth App (Optional):**
    *   You can remove the GitHub OAuth application you registered if you no longer need it. Go to GitHub **Developer settings** -> **OAuth Apps**, select your app, and click "Delete application".

5.  **Restore Database (if applicable):**
    *   If your migration involved any database schema changes or data modifications related to user authentication, restore your database from the backup you took before starting the migration.

6.  **Restart Services:**
    *   Restart your backend and frontend application servers to ensure they pick up the reverted codebase and environment variables.

---

This comprehensive guide should provide you with all the necessary information to successfully migrate your application. If you encounter specific issues not covered here, please consult the documentation for `fastapi-jwt-auth`, GitHub OAuth, and your respective frontend framework.