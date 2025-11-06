-- Safe migration: Store GitHub App installations and their accessible repositories
-- This allows us to query which repos an app can access without calling GitHub API
-- SAFE: Uses IF NOT EXISTS to avoid breaking existing tables

BEGIN;

-- Store GitHub App installations and their accessible repositories
CREATE TABLE IF NOT EXISTS app_installations (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,
    app_id INTEGER NOT NULL,
    installation_id INTEGER NOT NULL,
    repository_selection VARCHAR(50) NOT NULL DEFAULT 'all',  -- 'all' or 'selected'
    user_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_org_app UNIQUE(org_id, app_id)
);

-- Store which repos each app can access
CREATE TABLE IF NOT EXISTS app_installation_repos (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,
    app_id INTEGER NOT NULL,
    repo_id INTEGER NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    repo_full_name VARCHAR(512) NOT NULL,  -- e.g., "org/repo"
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_org_app_repo UNIQUE(org_id, app_id, repo_id)
);

-- Create indexes for faster queries (safe: IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_app_installations_org_app ON app_installations(org_id, app_id);
CREATE INDEX IF NOT EXISTS idx_app_installation_repos_org_app ON app_installation_repos(org_id, app_id);
CREATE INDEX IF NOT EXISTS idx_app_installation_repos_full_name ON app_installation_repos(repo_full_name);

COMMIT;
