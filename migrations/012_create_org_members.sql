-- ============================================================================
-- MIGRATION 012: Organization member directory for internal docs access
-- Adds org_members table and supporting indexes/constraints.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    github_username VARCHAR(255),
    github_user_id BIGINT,
    role VARCHAR(50) DEFAULT 'member',
    is_owner BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_active ON org_members(org_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_org_members_role ON org_members(org_id, role);

CREATE OR REPLACE FUNCTION update_org_members_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_org_members_updated_at
BEFORE UPDATE ON org_members
FOR EACH ROW
EXECUTE FUNCTION update_org_members_updated_at();

COMMIT;
