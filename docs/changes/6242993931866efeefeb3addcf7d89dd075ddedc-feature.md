# Implement GitHub OAuth Authentication and UI

**Type:** feature  
**Significance:** 9/10  
**Date:** 2025-10-22 15:22:10 UTC  
**Commit:** 6242993931866efeefeb3addcf7d89dd075ddedc  
**Branch:** refs/heads/main  

# Documentation: GitHub OAuth Authentication & UI Integration

This document provides comprehensive details for the "Implement GitHub OAuth Authentication and UI" feature, covering its purpose, technical implementation, user impact, and necessary migration steps for existing deployments.

---

## 1. Overview

This major feature introduces a robust GitHub OAuth authentication system, fundamentally changing how users interact with the application. The primary goal is to provide secure, standard-based user login and session management. This involves building new backend API endpoints for the OAuth flow and JWT-based session handling, alongside integrating a seamless frontend user experience for login, logout, and profile management. It also lays the groundwork for organization-specific features and refines how repositories are identified and managed, ensuring better support for multi-organization environments.

This is a significant update affecting both the backend API and the frontend user experience, requiring new configuration and a revised user flow. The introduction of new environment variables and changes to repository URL handling are considered breaking changes for existing deployments.

## 2. Impact

This change has a broad impact across several core aspects of the system:

*   **Authentication**: Introduces the primary method for user login and session management.
*   **User Management**: Establishes user identity and provides mechanisms for profile and organization settings.
*   **Frontend UI**: Significant updates to the application layout, navigation, and user interaction flows.
*   **Backend API**: New endpoints for authentication and user information.
*   **Configuration**: Requires new environment variables for GitHub OAuth and JWT security.
*   **GitHub Integration**: Deepens the integration with GitHub for user authentication and repository access.

**Affected Components:**

*   `.env.example`: Updated with new required environment variables.
*   `pustak/src/app/pricing/page.tsx`: Pricing plan links updated.
*   `pustak/src/app/providers.tsx`: Application wrapped with `AuthProvider`.
*   `pustak/src/app/repo/[repoName]/[docType]/page.tsx`: Repository handling adjusted.
*   `pustak/src/components/Layout.tsx`: Enhanced with conditional user menu.
*   `pustak/src/lib/realGitHubAPI.ts`: Repository handling adjusted.
*   `src/main.py`: New FastAPI routes for authentication and user data.
*   `contexts/AuthContext`: New context for global authentication state.

## 3. New Features

The following key features have been introduced:

*   **GitHub OAuth Login/Callback API**: Backend endpoints (`/api/auth/github/login`, `/api/auth/github/callback`) to initiate and complete the GitHub OAuth 2.0 flow.
*   **JWT-based User Sessions**: Secure, stateless user session management using JSON Web Tokens, issued upon successful GitHub authentication.
*   **Global AuthContext for Frontend**: A React Context (`AuthProvider`) that makes the user's authentication state and profile information globally accessible throughout the frontend application.
*   **User Profile Menu in Layout**: A new, conditional UI component in `pustak/src/components/Layout.tsx` that appears when a user is authenticated, providing quick access to 'Profile', 'Organization Settings', 'Billing', and 'Logout'.
*   **Configurable GitHub Organization Setting**: Support for specifying a default GitHub organization via `GITHUB_ORG` environment variable, which can be leveraged for organization-specific features.
*   **Redirects for Pricing Plans**: The pricing page (`/pricing`) has been updated to remove direct `/signup` routes. Free plans now redirect to the home page, and paid plans are directed to a `/checkout` page (to be implemented).
*   **New Environment Variables for OAuth and JWT**: Introduction of `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SECRET`, and `GITHUB_ORG` for secure and configurable operation.
*   **Current User Endpoint**: A new `/api/auth/me` endpoint to retrieve details of the currently authenticated user.

## 4. Breaking Changes

This release introduces several breaking changes that require attention during deployment and upgrades:

1.  **Mandatory Environment Variables**:
    *   The application now *requires* the following new environment variables to be set: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `JWT_SECRET`. Without these, authentication features will not function, and the application may fail to start or operate correctly.
    *   `GITHUB_ORG` is also introduced, which is crucial for defining the context of repository fetching and organization-specific features.
2.  **Repository Handling (Owner/Repo Format)**:
    *   The internal handling of repositories in components like `pustak/src/app/repo/[repoName]/[docType]/page.tsx` and `pustak/src/lib/realGitHubAPI.ts` has been refined to explicitly use the full `owner/repo` name format.
    *   **Impact**: If any existing parts of the application or external integrations relied solely on a bare `repoName` without the owner, they might need adjustment. This change improves support for multi-organization environments.
3.  **Removal of `/signup` Page Link**:
    *   Direct links to a `/signup` page from the pricing page have been removed. The user flow for "signing up" is now implicitly through the GitHub OAuth login process.
    *   **Impact**: Any direct links or bookmarks to a `/signup` page will no longer be valid within the intended user flow.

## 5. Technical Details

### Backend Implementation (`src/main.py`)

*   **FastAPI Routes**:
    *   `/api/auth/github/login`: Initiates the GitHub OAuth flow. Redirects the user to GitHub's authorization page with `client_id` and `scope` parameters.
    *   `/api/auth/github/callback`: Handles the redirect back from GitHub after user authorization. It exchanges the authorization code for an access token, fetches user data from GitHub, generates a JWT token, and sets it as an HTTP-only cookie.
    *   `/api/auth/me`: A protected endpoint that returns information about the currently authenticated user (derived from the JWT in the request cookie).
    *   `/api/auth/logout`: Clears the authentication cookie, effectively logging the user out.
*   **JWT Integration**:
    *   The `fastapi_jwt_auth` and `python-jose` libraries are integrated for secure JWT creation, signing, and verification.
    *   JWTs are signed using `JWT_SECRET` and contain user-specific claims (e.g., GitHub ID, username, avatar).
    *   Tokens are sent as secure, HTTP-only cookies to prevent XSS attacks.
*   **GitHub API Interaction**: Utilizes `httpx` or similar for making direct requests to GitHub's OAuth and User API endpoints to obtain user details.
*   **Environment Variables**: The `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `JWT_SECRET` are loaded from environment variables for secure and flexible configuration.

### Frontend Implementation

*   **`contexts/AuthContext`**: A new React Context (`AuthProvider`) is introduced to manage and provide global access to the authentication state. It typically holds information like `isAuthenticated`, `user` object (containing profile details), and methods for `login` and `logout`.
*   **`pustak/src/app/providers.tsx`**: The root `App` component is wrapped with the `AuthProvider` to make the authentication state available throughout the application's component tree.
*   **`pustak/src/components/Layout.tsx`**:
    *   Modified to conditionally render a user menu based on the `isAuthenticated` state from the `AuthContext`.
    *   The user menu includes options like "Profile", "Organization Settings", "Billing", and "Logout," leading to respective actions or pages.
*   **`pustak/src/app/pricing/page.tsx`**:
    *   Links for "Free" and paid plans have been updated. The "Free" plan now directs to the home page (`/`) after authentication, implying that a free user simply logs in.
    *   Paid plans now link to a `/checkout` page (placeholder for future billing integration).
*   **Repository Handling Refinement**:
    *   `pustak/src/app/repo/[repoName]/[docType]/page.tsx` and `pustak/src/lib/realGitHubAPI.ts` are updated to expect and consistently use the `owner/repo` format for repository identification, ensuring correct access in multi-organization or multi-user GitHub contexts.

### Configuration (`.env.example`)

The `.env.example` file has been updated to include the following essential variables:

```dotenv
# GitHub OAuth Configuration
GITHUB_CLIENT_ID="your_github_oauth_client_id"
GITHUB_CLIENT_SECRET="your_github_oauth_client_secret"
GITHUB_ORG="your_github_organization_name" # Optional but recommended for specific org scope

# JWT Configuration
JWT_SECRET="a_strong_secret_key_for_jwt_signing"
```

## 6. Usage Examples

### User Experience

1.  **Login**: Users will navigate to the application and see a "Login with GitHub" button (or similar prompt). Clicking this button will redirect them to GitHub's authorization page. After granting permission, they will be redirected back to the application, now logged in.
2.  **Accessing Profile/Settings**: Once logged in, a new user-specific menu (e.g., an avatar or username) will appear in the top navigation. Clicking it reveals options like "Profile," "Organization Settings," "Billing," and "Logout."
3.  **Logout**: Selecting "Logout" from the user menu will clear their session and return them to an unauthenticated state.

### Developer Usage (Frontend)

To access the authentication state in any React component:

```typescript
// Example: A component displaying user info
import { useAuth } from '@/contexts/AuthContext'; // Assuming this path for AuthContext

function UserGreeting() {
  const { isAuthenticated, user, login, logout } = useAuth();

  if (!isAuthenticated) {
    return <button onClick={login}>Login with GitHub</button>;
  }

  return (
    <div>
      Welcome, {user?.username}!
      <img src={user?.avatar_url} alt="User Avatar" width="32" height="32" />
      <button onClick={logout}>Logout</button>
      {/* Access other user details from `user` object */}
    </div>
  );
}
```

## 7. Testing

Thorough testing of the new authentication system is crucial. Consider the following scenarios:

*   **Successful Login Flow**:
    *   Clicking "Login with GitHub."
    *   Authorizing the application on GitHub.
    *   Successful redirection back to the application.
    *   Verification that the user is logged in (user menu appears, `/api/auth/me` returns data).
    *   Verification that a secure, HTTP-only JWT cookie is set.
*   **Logout Flow**:
    *   Clicking "Logout" from the user menu.
    *   Verification that the user is logged out (user menu disappears, `/api/auth/me` returns unauthorized).
    *   Verification that the JWT cookie is cleared.
*   **Authentication State Persistence**:
    *   Log in, then refresh the page. User should remain logged in.
    *   Close and reopen the browser (if not using session cookies, should remain logged in).
*   **Error Handling**:
    *   What happens if GitHub authorization fails or is denied?
    *   What happens if environment variables are missing or incorrect?
    *   Test with an expired or invalid JWT (e.g., manually modify the cookie).
*   **Protected Routes**: (If any are now protected)
    *   Attempt to access a protected route without being logged in (should be redirected or receive an error).
    *   Access a protected route while logged in (should succeed).
*   **UI Elements**:
    *   Verify the user menu appears only when logged in.
    *   Verify menu options are clickable and lead to the correct actions/pages.
    *   Check responsiveness of the layout with the new menu.
*   **Pricing Page Links**:
    *   Verify "Free" plan links correctly redirect to `/`.
    *   Verify paid plan links correctly redirect to `/checkout`.
*   **Repository Handling**:
    *   Ensure that existing repository links (if any) using `owner/repo` format still work correctly.
    *   Test fetching documentation for repositories from the configured `GITHUB_ORG`.

## 8. Migration Guide

For existing deployments, follow these steps to integrate the new authentication system:

1.  **Update Environment Variables**:
    *   Obtain a GitHub OAuth App Client ID and Client Secret:
        *   Go to your GitHub profile settings -> Developer settings -> OAuth Apps.
        *   Click "New OAuth App."
        *   Fill in "Application name," "Homepage URL," and "Authorization callback URL" (e.g., `http://localhost:8000/api/auth/github/callback` for local development, or your production URL).
        *   Generate a new client secret.
    *   Add the following variables to your `.env` file (or equivalent environment configuration):
        ```dotenv
        GITHUB_CLIENT_ID="YOUR_GITHUB_CLIENT_ID"
        GITHUB_CLIENT_SECRET="YOUR_GITHUB_CLIENT_SECRET"
        # Generate a strong, random string for JWT_SECRET
        JWT_SECRET="YOUR_STRONG_RANDOM_JWT_SECRET" 
        # Replace with your target GitHub organization, e.g., "pustak-org"
        GITHUB_ORG="YOUR_GITHUB_ORGANIZATION_NAME" 
        ```
    *   **Action**: Create a new `.env` file or update your existing one with these new variables.

2.  **Backend Dependencies**:
    *   Ensure the required Python libraries for JWT are installed:
        ```bash
        pip install fastapi_jwt_auth python-jose
        ```
    *   **Action**: Update your `requirements.txt` and install dependencies.

3.  **Frontend Code Update**:
    *   **`pustak/src/app/providers.tsx`**: Ensure your root layout or application wrapper component (`pustak/src/app/providers.tsx` in this case) is updated to include the `AuthProvider`. This is critical for making authentication state available globally.
    *   **Layout Component (`pustak/src/components/Layout.tsx`)**: Verify your application's main layout component is updated to conditionally render the user menu and incorporate the new login/logout functionality via `AuthContext`.
    *   **Pricing Page (`pustak/src/app/pricing/page.tsx`)**: If you have a pricing page, update its links to reflect the new authentication flow (i.e., remove direct `/signup` links, adjust free/paid plan redirects).
    *   **Action**: Pull the latest frontend code changes and rebuild your frontend application.

4.  **Repository URL Handling Review**:
    *   Review any custom logic or hardcoded links in your application that deal with GitHub repositories. Ensure they are compatible with the `owner/repo` format.
    *   **Action**: Identify and update any components or functions that might be affected by the `owner/repo` format requirement.

5.  **Documentation Updates**:
    *   **README.md**: Update your project's `README.md` to reflect the new authentication method, setup instructions, and required environment variables.
    *   **API Documentation**: Update your API documentation to include the new authentication endpoints (`/api/auth/github/login`, `/api/auth/github/callback`, `/api/auth/me`, `/api/auth/logout`) and explain how JWTs are used for authentication.
    *   **Action**: Create/Update relevant documentation.

After performing these steps, rebuild and redeploy your application. Thoroughly test the new authentication flow as described in the "Testing" section.