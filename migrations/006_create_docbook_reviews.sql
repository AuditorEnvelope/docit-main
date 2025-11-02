-- Migration: Create docbook_reviews table for tracking pending documentation reviews
-- Tracks which docs are pending review in staging branch

CREATE TABLE IF NOT EXISTS docbook_reviews (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    source_repo_name VARCHAR(255) NOT NULL,  -- e.g., "alpha-testing"
    docbook_full_name VARCHAR(255) NOT NULL,  -- e.g., "Testing-Org-For-Pustak/lekhak-docbook-org-..."
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review',  -- pending_review, approved, merged, rejected
    commit_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: one pending review per source repo per org
    UNIQUE(user_id, org_id, source_repo_name)
);

-- Create indexes for faster lookups
CREATE INDEX idx_docbook_reviews_user_org ON docbook_reviews(user_id, org_id);
CREATE INDEX idx_docbook_reviews_status ON docbook_reviews(status);
CREATE INDEX idx_docbook_reviews_pending ON docbook_reviews(user_id, status) WHERE status = 'pending_review';
