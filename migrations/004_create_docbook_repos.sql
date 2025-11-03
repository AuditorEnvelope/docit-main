-- Migration: Create docbook_repos table for V4 architecture
-- This replaces the old doc_maintainer_repos table
-- Users manually create lekhak-docbook-org-{ORG_ID} repos
-- This table just tracks which docbook is linked to which org

CREATE TABLE IF NOT EXISTS docbook_repos (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    docbook_repo_name VARCHAR(255) NOT NULL,  -- e.g., "lekhak-docbook-org-12345"
    docbook_full_name VARCHAR(255) NOT NULL,  -- e.g., "AuditorEnvelope/lekhak-docbook-org-12345"
    docbook_url TEXT NOT NULL,                 -- GitHub URL
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: one docbook per org per user
    UNIQUE(user_id, org_id)
);

-- Create index for faster lookups
CREATE INDEX idx_docbook_repos_user_org ON docbook_repos(user_id, org_id);
CREATE INDEX idx_docbook_repos_active ON docbook_repos(is_active);

-- Drop old doc_maintainer_repos table if it exists
DROP TABLE IF EXISTS doc_maintainer_repos CASCADE;
