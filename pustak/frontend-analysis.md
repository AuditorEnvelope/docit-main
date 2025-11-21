# Pustak Frontend Architecture Overview

## 1. Entry Points & Global Structure
- Root layout (`src/app/layout.tsx`) sets global Inter font, applies theme/auth providers, and injects metadata for SEO.
- `Providers` (`src/app/providers.tsx`) wraps the app in `ThemeProvider` and custom `AuthProvider` to expose theme toggling and auth context.
- Styling is centralized in `src/app/globals.css` with Tailwind classes tuned via `tailwind.config.js`.

### App Routes (Next.js App Router)
- `src/app/page.tsx`: Landing/dashboard-lite home view showing hero, stats, marketing content. Fetches repo stats when JWT available.
- `src/app/login/page.tsx`: GitHub OAuth entry with login CTA. Uses `useAuth` to redirect authenticated users.
- `src/app/auth/callback/page.tsx`: Handles OAuth return (parses query params, exchanges code with backend, stores tokens via context, redirects to dashboard).
- `src/app/dashboard/page.tsx`: Authenticated control center. Heavy client state orchestrates onboarding steps (connect org, set up docbook, install apps, manage repos, view reviews).
- `src/app/repo/[...slug]/page.tsx`: Dynamic documentation viewer for a docbook repository file path.
- `src/app/search/page.tsx`: Full-page search (paired with `GlobalSearch` modal) for documentation content.
- `src/app/pricing/page.tsx`, `src/app/checkout/page.tsx`: Billing funnel.

### API Route Proxies (Next.js)
Located in `src/app/api/*` — each wraps backend REST endpoints, adding server-side secrets if needed.
Key handlers:
- `/api/repositories` → fetches linked repos for stats.
- `/api/fetch-doc` → fetch Markdown file from backend/docbook.
- `/api/docbook/...` → docbook structure checks, linking, publishing proxies.
- `/api/user/organizations` → list user orgs via backend.
- `/api/search` → documentation search.
- `/api/generate-docs`, `/api/sync`, `/api/webhook`, `/api/create-checkout` — action endpoints hitting backend services.

## 2. Core Context & Utilities
- `AuthContext` (`src/contexts/AuthContext.tsx`): stores user profile, tokens in localStorage, exposes `login`, `logout`, auth state, auto-validates token via `/auth/me` on load.
- `src/lib/api.ts`: typed client helpers for backend (repo list, tree, search, health). Primarily used by dashboard/search modules.
- `src/lib/dynamicGitHubLoader.ts`, `src/lib/realGitHubAPI.ts`: fallbacks/stubs for repo data (not deeply integrated in production flow).

## 3. Component Library Highlights
- `Layout`: global chrome — header with brand, search trigger, theme toggle, user menu, mobile sidebar toggle.
- `EnhancedSidebar`: loads all docbook repos, renders tree of folders/files per org, handles navigation to `/repo/...`.
- `GlobalSearch`: modal search with keyboard navigation (⌘K). Calls backend search, highlights matches.
- `ConnectOrganizationModal`: guides installing GitHub App, registering webhook via `/webhook/register`.
- `DocbookSetupModal`: stepper to create/link docbook repo via `/documentation/link-repo`.
- `PendingReviewsTab`: displays docbook review queue from backend.
- `GenerateDocsButton`, `DocPersonaSelector`, `TreeSidebar`, `NodeContent`, `MarkdownRenderer` support doc display UI.
- `Breadcrumbs`, `DocStatusBadge`: helper UI elements.

## 4. Dashboard Flow (User Perspective)
1. **Authentication**: `AuthContext` loads tokens; unauthenticated users redirected to `/login` which triggers GitHub OAuth.
2. **Landing on /dashboard**:
   - Fetch user repos, summaries, docbook link status, app installation state using backend REST calls (`/repositories`, `/docbook/check-*`, `/org/*`).
   - UI shows onboarding checklist tabs: "Getting Started" and "Reviews".
3. **Connect Organization**:
   - Opens `ConnectOrganizationModal`→ list GitHub orgs from `/auth/user-organizations`.
   - Checks GitHub App installation via `/webhook/check-app-installation`.
   - On "Connect" posts to `/webhook/register` (inserts org registration & webhook secret).
4. **Set Up Docbook**:
   - `DocbookSetupModal` suggests repo name, opens GitHub create page.
   - Links repository via backend `POST /docbook/link-repo` (now also upserts org registration so worker sees it).
5. **Verify Apps & Access**:
   - Dashboard polls `/org/{id}/verify-apps` and `/org/{id}/verify-writer-app-access` to ensure Reader/Writer GitHub Apps installed and have repo access.
6. **Generate Docs / Manage Reviews**:
   - `GenerateDocsButton` triggers backend doc generation (`/api/generate-docs`).
   - `PendingReviewsTab` fetches pending docbook reviews; user can view, approve via backend endpoints.
7. **Navigation to Docs**:
   - `EnhancedSidebar` lists docbook repos. Clicking file loads `/repo/...` page which fetches Markdown (`/api/fetch-doc`) and renders via `MarkdownRenderer` (uses `remark`/`rehype`).
8. **Search**:
   - Keyboard shortcut or search page uses `GlobalSearch` to query backend search index and navigate to doc pages.

## 5. Frontend Data Flow
- Auth tokens stored in localStorage; context components guard routes and attach `Authorization` headers.
- Most data flows through Next.js API proxies to the FastAPI backend. Client components (`useEffect`) fetch via `fetch` hitting `/api/...` routes to avoid CORS/env issues.
- The dashboard orchestrates state machines for onboarding tasks (polling to detect installed apps, docbook link status, tracked branch management).

## 6. UX Journey Summary
1. **Home (`/`)**: marketing overview, quick search CTA.
2. **Login (`/login`)**: GitHub SSO. On success, redirects to `/dashboard`.
3. **Dashboard Onboarding**:
   - Connect GitHub Organization.
   - Create/link docbook repo.
   - Verify Writer/Reader apps.
   - Generate docs & review outputs.
4. **Documentation Browsing (`/repo/...`)**: Tree navigation on left, markdown content on right, GitHub links, last-updated metadata.
5. **Search (modal or `/search`)**: type to find docs across orgs.
6. **Billing (`/pricing`, `/checkout`)** optional.

## 7. Major Files & Responsibilities
- **`src/app/dashboard/page.tsx`**: central orchestrator for authenticated experience (largest file, handles polling, modals, tracked branch updates, doc generation triggers).
- **`src/components/ConnectOrganizationModal.tsx`** & **`DocbookSetupModal.tsx`**: onboarding modals tying UI to webhook/docbook backend endpoints.
- **`src/components/EnhancedSidebar.tsx`** & **`TreeSidebar.tsx`**: navigation & repository tree rendering.
- **`src/components/GlobalSearch.tsx`**: search UX.
- **`src/app/repo/[...slug]/page.tsx`**: markdown viewer.
- **`src/contexts/AuthContext.tsx`**: auth lifecycle.
- **`src/lib/api.ts`**: typed backend client.
- **`src/components/Layout.tsx`**: header, theme toggle, user menu, global search binding.

## 8. Notable Behaviors & Considerations
- Heavy reliance on client components (`"use client"`) due to localStorage, polling, modals.
- Auth gating via context; `useEffect` redirect ensures protected routes.
- Polling/verification loops in dashboard ensure external GitHub app setup completes.
- Next.js API routes act as serverless proxies; ensure environment variables for backend URL, secrets configured.
- Markdown rendering sanitized via remark/rehype pipeline in `MarkdownRenderer` (not inspected but implied by dependencies).

## 9. Suggested Enhancements (optional observations)
1. Break up `dashboard/page.tsx` into smaller hooks/components to improve maintainability.
2. Consolidate docbook setup endpoints to use consistent naming (`pustak-docbook-` vs `lekhak-docbook-org-`).
3. Add error states/loading spinners for API route failures in modals/sidebar.
4. Consider central API client with auth header injection to reduce repeated token logic.

---

This document captures the current frontend logic, entry/exit points, and user experience flow for Pustak. It can serve as onboarding reference and checklist when modifying the UI/UX or integrating new backend capabilities.
