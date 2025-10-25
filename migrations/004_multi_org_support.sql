-- Migration: Multi-Org Support
-- Adds webhook registration and token management for multi-org support

-- ============================================================================
-- Organization webhook registrations (one per org)
-- ============================================================================

CREATE TABLE IF NOT EXISTS org_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255) UNIQUE NOT NULL,
    github_token_id UUID NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);

CREATE INDEX IF NOT EXISTS idx_org_webhooks_secret ON org_webhooks(webhook_secret);
CREATE INDEX IF NOT EXISTS idx_org_webhooks_user_org ON org_webhooks(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_org_webhooks_org ON org_webhooks(org_id);

-- ============================================================================
-- User GitHub tokens (encrypted, per-org)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_github_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255),
    github_token TEXT NOT NULL,  -- Encrypted in production
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_tokens_user ON user_github_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tokens_user_token ON user_github_tokens(user_id, token_id);
CREATE INDEX IF NOT EXISTS idx_user_tokens_active ON user_github_tokens(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- Add multi-org context columns to commit_events
-- ============================================================================

ALTER TABLE commit_events
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS org_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS github_token_id UUID REFERENCES user_github_tokens(token_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS installation_id INTEGER,
ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_user_org ON commit_events(user_id, org_id);
CREATE INDEX IF NOT EXISTS idx_commit_events_installation ON commit_events(installation_id);

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE org_webhooks IS 'Organization webhook registrations for multi-org support';
COMMENT ON TABLE user_github_tokens IS 'Encrypted GitHub tokens per user/org for multi-org support';
COMMENT ON COLUMN commit_events.user_id IS 'User who owns the repository';
COMMENT ON COLUMN commit_events.org_id IS 'Organization name';
COMMENT ON COLUMN commit_events.github_token_id IS 'Reference to encrypted GitHub token';
COMMENT ON COLUMN commit_events.installation_id IS 'GitHub App installation ID';
COMMENT ON COLUMN commit_events.webhook_secret IS 'Organization webhook secret';
