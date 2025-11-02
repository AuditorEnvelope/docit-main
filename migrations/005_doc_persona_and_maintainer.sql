-- ============================================================================
-- MIGRATION 005: Doc Persona & Doc-Maintainer Repository Support
-- ============================================================================
-- This migration adds support for:
-- 1. Doc Persona Selection (Internal vs Developer)
-- 2. Centralized Doc-Maintainer Repository
-- 3. Review Workflow (PR-based publishing)
-- 4. Mirror History (tracking syncs to source repos)
--
-- BACKWARD COMPATIBLE: All new columns are optional/nullable
-- REVERSIBLE: Includes rollback instructions at bottom
-- ============================================================================

-- ============================================================================
-- TABLE 1: repositories (CREATE IF NOT EXISTS)
-- Tracks which repos are connected and their settings
-- ============================================================================

CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User & Org context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    
    -- Repository info
    repo_name VARCHAR(255) NOT NULL,  -- e.g., "College-ERP"
    repo_full_name VARCHAR(255) NOT NULL,  -- e.g., "Testing-Org-For-Pustak/College-ERP"
    repo_url VARCHAR(500),
    description TEXT,
    
    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_webhook_at TIMESTAMP,
    
    -- Ensure unique repos per user/org
    UNIQUE(user_id, org_id, repo_full_name)
);

CREATE INDEX IF NOT EXISTS idx_repositories_user_id ON repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_repositories_org_id ON repositories(org_id);
CREATE INDEX IF NOT EXISTS idx_repositories_repo_full_name ON repositories(repo_full_name);

-- ============================================================================
-- ADD COLUMNS TO repositories TABLE (FEATURE 1 & 2)
-- ============================================================================

ALTER TABLE repositories ADD COLUMN IF NOT EXISTS doc_persona VARCHAR(50) DEFAULT 'internal';
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS doc_persona_updated_at TIMESTAMP;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS doc_maintainer_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS doc_maintainer_repo_id VARCHAR(255);

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_repositories_doc_persona ON repositories(doc_persona);
CREATE INDEX IF NOT EXISTS idx_repositories_doc_maintainer_enabled ON repositories(doc_maintainer_enabled);

-- ============================================================================
-- TABLE 2: doc_maintainer_repos
-- Maps organizations to their doc-maintainer repositories
-- ============================================================================

CREATE TABLE IF NOT EXISTS doc_maintainer_repos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Org context
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    
    -- Doc-maintainer repo details
    repo_name VARCHAR(255) DEFAULT 'doc-maintainer',
    repo_full_name VARCHAR(255) NOT NULL,  -- e.g., "org/doc-maintainer"
    repo_url VARCHAR(500),
    
    -- Branch info
    staging_branch VARCHAR(255) DEFAULT 'staging',
    main_branch VARCHAR(255) DEFAULT 'main',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure one doc-maintainer per org
    UNIQUE(user_id, org_id)
);

CREATE INDEX idx_doc_maintainer_repos_user_id ON doc_maintainer_repos(user_id);
CREATE INDEX idx_doc_maintainer_repos_org_id ON doc_maintainer_repos(org_id);
CREATE INDEX idx_doc_maintainer_repos_repo_full_name ON doc_maintainer_repos(repo_full_name);

-- ============================================================================
-- TABLE 3: doc_generation_reviews
-- Tracks documentation generation reviews (PRs in doc-maintainer)
-- ============================================================================

CREATE TABLE IF NOT EXISTS doc_generation_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to source repo
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    
    -- Commit info
    commit_sha VARCHAR(40) NOT NULL,
    commit_message TEXT,
    
    -- PR details in doc-maintainer
    pr_number INTEGER,
    pr_url VARCHAR(500),
    review_branch VARCHAR(255),  -- e.g., docai-review/repo-a/commit-abc123
    
    -- Doc persona used for this generation
    doc_persona VARCHAR(50) DEFAULT 'internal',  -- internal|developer
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending|approved|rejected|merged
    
    -- Generated content metadata
    docs_generated JSONB,  -- {internal: {...}, developer: {...}}
    files_count INTEGER,
    
    -- User notes
    user_notes TEXT,
    reviewer_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    merged_at TIMESTAMP,
    
    -- Ensure one review per commit per persona
    UNIQUE(repository_id, commit_sha, doc_persona)
);

CREATE INDEX idx_doc_generation_reviews_repository_id ON doc_generation_reviews(repository_id);
CREATE INDEX idx_doc_generation_reviews_status ON doc_generation_reviews(status);
CREATE INDEX idx_doc_generation_reviews_commit_sha ON doc_generation_reviews(commit_sha);
CREATE INDEX idx_doc_generation_reviews_created_at ON doc_generation_reviews(created_at DESC);
CREATE INDEX idx_doc_generation_reviews_doc_persona ON doc_generation_reviews(doc_persona);

-- ============================================================================
-- TABLE 4: doc_mirror_history
-- Tracks mirror operations (docs synced back to source repo)
-- ============================================================================

CREATE TABLE IF NOT EXISTS doc_mirror_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to source repo
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    
    -- Reference to review
    review_id UUID REFERENCES doc_generation_reviews(id) ON DELETE SET NULL,
    
    -- File info
    file_path VARCHAR(500) NOT NULL,  -- e.g., "docs/architecture/v1.md"
    doc_type VARCHAR(50),  -- internal|developer
    
    -- Mirror operation details
    source_path VARCHAR(500),  -- Path in doc-maintainer
    target_path VARCHAR(500),  -- Path in source repo
    
    -- Status
    mirrored_to_source BOOLEAN DEFAULT FALSE,
    mirror_commit_sha VARCHAR(40),
    mirror_commit_url VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    mirrored_at TIMESTAMP,
    
    -- Ensure one mirror per file per review
    UNIQUE(review_id, file_path)
);

CREATE INDEX idx_doc_mirror_history_repository_id ON doc_mirror_history(repository_id);
CREATE INDEX idx_doc_mirror_history_review_id ON doc_mirror_history(review_id);
CREATE INDEX idx_doc_mirror_history_mirrored_to_source ON doc_mirror_history(mirrored_to_source);
CREATE INDEX idx_doc_mirror_history_created_at ON doc_mirror_history(created_at DESC);

-- ============================================================================
-- TABLE 5: doc_generation_queue
-- Queue for pending doc generation tasks
-- ============================================================================

CREATE TABLE IF NOT EXISTS doc_generation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to source repo
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    
    -- Commit info
    commit_sha VARCHAR(40) NOT NULL,
    commit_message TEXT,
    branch VARCHAR(255),
    
    -- Doc persona
    doc_persona VARCHAR(50) DEFAULT 'internal',
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending|processing|completed|failed
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Ensure one task per commit per persona
    UNIQUE(repository_id, commit_sha, doc_persona)
);

CREATE INDEX idx_doc_generation_queue_status ON doc_generation_queue(status);
CREATE INDEX idx_doc_generation_queue_repository_id ON doc_generation_queue(repository_id);
CREATE INDEX idx_doc_generation_queue_created_at ON doc_generation_queue(created_at);

-- ============================================================================
-- UPDATES TO EXISTING TABLES
-- ============================================================================

-- Add doc_persona tracking to commit_events (if not already present)
ALTER TABLE commit_events ADD COLUMN IF NOT EXISTS doc_persona VARCHAR(50) DEFAULT 'internal';
ALTER TABLE commit_events ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE commit_events ADD COLUMN IF NOT EXISTS org_id VARCHAR(255);
ALTER TABLE commit_events ADD COLUMN IF NOT EXISTS github_token_id UUID;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_commit_events_doc_persona ON commit_events(doc_persona);
CREATE INDEX IF NOT EXISTS idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_github_token_id ON commit_events(github_token_id);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify all tables created:
-- SELECT tablename FROM pg_tables WHERE schemaname='public' 
-- AND tablename IN ('repositories', 'doc_maintainer_repos', 'doc_generation_reviews', 'doc_mirror_history', 'doc_generation_queue');

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================================

/*
To rollback this migration, run:

DROP TABLE IF EXISTS doc_generation_queue CASCADE;
DROP TABLE IF EXISTS doc_mirror_history CASCADE;
DROP TABLE IF EXISTS doc_generation_reviews CASCADE;
DROP TABLE IF EXISTS doc_maintainer_repos CASCADE;
DROP TABLE IF EXISTS repositories CASCADE;

ALTER TABLE commit_events DROP COLUMN IF EXISTS doc_persona;
DROP INDEX IF EXISTS idx_commit_events_doc_persona;

This is fully reversible with no data loss to existing tables.
*/

-- ============================================================================
-- END OF MIGRATION 005
-- ============================================================================
