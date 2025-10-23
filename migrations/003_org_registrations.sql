-- Multi-Org Registration Support
-- Stores which organizations are registered by which users

CREATE TABLE IF NOT EXISTS org_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    org_id VARCHAR(255) NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);

CREATE INDEX idx_org_registrations_user_id ON org_registrations(user_id);
CREATE INDEX idx_org_registrations_org_id ON org_registrations(org_id);

-- Rollback:
-- DROP TABLE IF EXISTS org_registrations;
