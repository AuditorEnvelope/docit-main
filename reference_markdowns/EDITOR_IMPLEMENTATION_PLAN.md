# WYSIWYG Editor Implementation Plan

## 📋 Overview
Transform the read-only documentation viewer (`/docs/[org]/[repo]/...`) into a Notion-style WYSIWYG editor with GitHub commit capabilities.

## 🎯 Current Architecture Understanding

### Frontend Flow
1. **Route**: `/docs/[org]/[repo]/[[...slug]]` → redirects to `/repo/[...slug]`
2. **Page Component**: `pustak/src/app/repo/[...slug]/page.tsx`
3. **Content Fetch**: 
   - Frontend calls `/api/fetch-doc` (Next.js API route)
   - Next.js route proxies to backend `/api/v1/docs/fetch-file`
   - Backend fetches from GitHub API using user's token
4. **Rendering**: `MarkdownRenderer` component displays markdown

### Backend Flow
1. **Endpoint**: `GET /api/v1/docs/fetch-file`
2. **Authentication**: JWT token from `Authorization: Bearer <token>`
3. **GitHub API**: Uses user's `github_access_token` to fetch file content
4. **Branch**: Defaults to "staging", can be specified via query param

## 📦 Files to Create/Modify

### Frontend (`@pustak`)

#### New Files:
1. **`src/components/BlockNoteEditor.tsx`**
   - BlockNote editor component
   - Markdown → BlockNote blocks conversion
   - BlockNote blocks → Markdown conversion
   - Handles image uploads

2. **`src/components/CommitModal.tsx`**
   - Modal for commit message input
   - Branch selection (optional)
   - Loading states

3. **`src/app/api/commit-doc/route.ts`**
   - Next.js API route to proxy commit requests to backend

#### Modified Files:
1. **`src/app/repo/[...slug]/page.tsx`**
   - Add Edit/View mode toggle
   - Add Edit/Cancel/Commit buttons in header
   - Replace `MarkdownRenderer` with `BlockNoteEditor` in edit mode
   - Handle commit flow

### Backend (`@app`)

#### New Files:
1. **`app/api/v1/endpoints/docs_commit.py`** (or add to existing `docs.py`)
   - `POST /api/v1/docs/commit` endpoint
   - Handles GitHub file commit via GitHub API
   - Validates user permissions
   - Returns commit SHA

#### Modified Files:
1. **`app/api/v1/endpoints/docs.py`**
   - Add commit endpoint (or create separate file)

## 🔧 Implementation Steps

### Step 1: Install Dependencies
```bash
cd pustak
npm install @blocknote/core @blocknote/react @blocknote/mantine
```

### Step 2: Create BlockNote Editor Component
- Convert Markdown to BlockNote blocks on load
- Convert BlockNote blocks to Markdown on save
- Handle slash commands, drag-drop, code blocks

### Step 3: Create Commit Modal
- Input for commit message
- Optional branch selector
- Loading/error states

### Step 4: Modify Repo Page
- Add `isEditing` state
- Toggle between view/edit modes
- Add header buttons (Edit/Cancel/Commit)
- Integrate BlockNote editor

### Step 5: Create Backend Commit Endpoint
- Validate user authentication
- Get current file SHA from GitHub
- Create commit via GitHub API
- Use user's identity as commit author
- Commit to tracked branch (or staging)

### Step 6: Create Next.js API Route
- Proxy commit requests to backend
- Handle authentication token forwarding

## 🔐 Security Considerations

1. **Authentication**: All requests require valid JWT token
2. **Authorization**: Verify user has write access to repository
3. **Branch Protection**: Don't commit directly to `main` unless explicitly allowed
4. **File Validation**: Ensure file path is within allowed directories
5. **Content Validation**: Validate markdown content before commit

## 📊 Data Flow

### Edit Flow:
1. User clicks "Edit" button
2. Page switches to edit mode
3. Markdown content → BlockNote blocks
4. User edits in BlockNote editor
5. User clicks "Commit Changes"
6. Commit modal opens
7. User enters commit message
8. BlockNote blocks → Markdown
9. POST to `/api/commit-doc`
10. Backend commits to GitHub
11. Page refreshes to show updated content

### View Flow:
1. Page loads in read mode
2. Fetch markdown from GitHub
3. Display via `MarkdownRenderer`

## 🎨 UI/UX Considerations

1. **Edit Button**: Top right, next to "Preview live docs" and "View on GitHub"
2. **Cancel Button**: Appears when editing, cancels changes
3. **Commit Button**: Appears when editing, opens commit modal
4. **Loading States**: Show loading during commit
5. **Error Handling**: Display errors if commit fails
6. **Success Feedback**: Show success message after commit

## 🧪 Testing Checklist

- [ ] Editor loads existing markdown correctly
- [ ] Markdown → Blocks conversion works
- [ ] Blocks → Markdown conversion works
- [ ] Edit mode toggles correctly
- [ ] Commit modal opens/closes correctly
- [ ] Commit succeeds with valid message
- [ ] Commit fails gracefully with errors
- [ ] Page refreshes after successful commit
- [ ] Authentication works correctly
- [ ] Branch selection works (if implemented)

## 🚀 Post-Implementation Result

After implementation:
- Users can click "Edit" on any documentation page
- Content becomes editable in a Notion-style editor
- Users can commit changes directly to GitHub
- Changes appear in GitHub history with user's identity
- No breaking changes to existing read-only functionality

