-- ============================================================================
-- MIGRATION 002: Multi-Organization Support for Webhook & Event Bus
-- Version: 2.0.0
-- Date: 2025-10-23
-- Description: Add user/org context to commit events for multi-org support
-- 
-- BACKWARD COMPATIBLE: All new columns are NULLABLE with defaults
-- No existing data is modified
-- ============================================================================

-- ============================================================================
-- STEP 1: Add columns to commit_events (NULLABLE - backward compatible)
-- ============================================================================

ALTER TABLE commit_events 
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS org_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS github_token_id UUID;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_user_org ON commit_events(user_id, org_id);

-- ============================================================================
-- STEP 2: Create org_webhooks table (NEW)
-- Stores webhook registration per org with unique secrets
-- ============================================================================

CREATE TABLE IF NOT EXISTS org_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Organization identification
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    
    -- Webhook security
    webhook_secret VARCHAR(255) NOT NULL UNIQUE,
    
    -- Token reference
    github_token_id UUID NOT NULL,
    
    -- Metadata
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure one webhook per user+org
    UNIQUE(user_id, org_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_org_webhooks_user ON org_webhooks(user_id);
CREATE INDEX IF NOT EXISTS idx_org_webhooks_org ON org_webhooks(org_id);
CREATE INDEX IF NOT EXISTS idx_org_webhooks_secret ON org_webhooks(webhook_secret);
CREATE INDEX IF NOT EXISTS idx_org_webhooks_token ON org_webhooks(github_token_id);

-- ============================================================================
-- STEP 3: Create user_github_tokens table (NEW)
-- Stores encrypted GitHub tokens per user/org
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_github_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User identification
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255),
    
    -- Token (will be encrypted in application layer)
    github_token TEXT NOT NULL,
    
    -- Token metadata
    token_type VARCHAR(50) DEFAULT 'oauth',  -- oauth|personal|app
    scopes VARCHAR(255),  -- Comma-separated scopes
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_github_tokens_user ON user_github_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_user_github_tokens_org ON user_github_tokens(org_id);
CREATE INDEX IF NOT EXISTS idx_user_github_tokens_active ON user_github_tokens(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_github_tokens_user_org ON user_github_tokens(user_id, org_id);

-- ============================================================================
-- STEP 4: Add trigger to update org_webhooks.updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_org_webhooks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_org_webhooks_updated_at_trigger 
BEFORE UPDATE ON org_webhooks
FOR EACH ROW 
EXECUTE FUNCTION update_org_webhooks_updated_at();

-- ============================================================================
-- STEP 5: Add comments for documentation
-- ============================================================================

COMMENT ON TABLE org_webhooks IS 'Webhook registrations per organization - each org has unique secret';
COMMENT ON TABLE user_github_tokens IS 'Encrypted GitHub tokens per user/org for authentication';
COMMENT ON COLUMN commit_events.user_id IS 'User who owns the repository (for multi-org support)';
COMMENT ON COLUMN commit_events.org_id IS 'Organization name (for multi-org support)';
COMMENT ON COLUMN commit_events.github_token_id IS 'Reference to encrypted GitHub token for this org';

-- ============================================================================
-- STEP 6: Verification queries (for testing)
-- ============================================================================

-- Verify new columns exist
-- SELECT column_name FROM information_schema.columns WHERE table_name='commit_events' AND column_name IN ('user_id', 'org_id', 'github_token_id');

-- Verify new tables exist
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('org_webhooks', 'user_github_tokens');

-- ============================================================================
-- NOTES FOR IMPLEMENTATION
-- ============================================================================
-- 
-- BACKWARD COMPATIBILITY:
-- - All new columns are NULLABLE, so existing code continues to work
-- - Old events (without user_id/org_id) will have NULL values
-- - Event consumer can handle both old and new events
--
-- NEXT STEPS:
-- 1. Deploy this migration
-- 2. Update CommitEvent model to include new fields (optional)
-- 3. Update webhook endpoint to extract and store user_id/org_id
-- 4. Update event consumer to get token from user_github_tokens table
-- 5. Create webhook registration endpoint
--
-- ROLLBACK (if needed):
-- ALTER TABLE commit_events DROP COLUMN IF EXISTS user_id, org_id, github_token_id;
-- DROP TABLE IF EXISTS org_webhooks CASCADE;
-- DROP TABLE IF EXISTS user_github_tokens CASCADE;
-- DROP FUNCTION IF EXISTS update_org_webhooks_updated_at();
--
-- ============================================================================
