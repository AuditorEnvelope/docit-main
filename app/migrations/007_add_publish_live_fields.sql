-- Migration: Add live publishing fields to docbook_repos
-- Purpose: Track when docs are published live and their public URL

-- Add new columns to docbook_repos
ALTER TABLE docbook_repos 
ADD COLUMN IF NOT EXISTS last_published_commit VARCHAR(40),
ADD COLUMN IF NOT EXISTS live_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS live_theme JSONB,
ADD COLUMN IF NOT EXISTS live_sidebar_config JSONB;

-- Create docbook_publish_events table to track publish history
CREATE TABLE IF NOT EXISTS docbook_publish_events (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    org_id VARCHAR(255) NOT NULL,
    repo_id VARCHAR(255) NOT NULL,
    
    staging_commit VARCHAR(40),
    main_commit VARCHAR(40) NOT NULL,
    published_by UUID NOT NULL,
    
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_publish_events_org (org_id),
    INDEX idx_publish_events_repo (repo_id),
    INDEX idx_publish_events_user (user_id),
    INDEX idx_publish_events_status (status)
);

COMMENT ON TABLE docbook_publish_events IS 'Tracks history of live documentation publishing events';
COMMENT ON COLUMN docbook_repos.last_published_commit IS 'SHA of the last commit published to live';
COMMENT ON COLUMN docbook_repos.live_url IS 'Public URL where docs are accessible (e.g., https://org.docbook.site/repo)';
COMMENT ON COLUMN docbook_repos.live_theme IS 'Optional theme overrides for live site';
COMMENT ON COLUMN docbook_repos.live_sidebar_config IS 'Optional sidebar configuration for live site';
