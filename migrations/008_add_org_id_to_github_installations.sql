-- Migration: Add org_id column to github_installations
-- Aligns legacy DocbookPublisher expectations with new schema

BEGIN;

-- 1. Add org_id column if missing
ALTER TABLE github_installations
    ADD COLUMN IF NOT EXISTS org_id VARCHAR(255);

UPDATE github_installations
SET org_id = account_login
WHERE org_id IS NULL;

UPDATE github_installations
SET org_id = 'unknown-org'
WHERE org_id IS NULL;

ALTER TABLE github_installations
    ALTER COLUMN org_id SET NOT NULL;

-- 4. Add helper index for lookups by org_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = current_schema()
          AND indexname = 'idx_github_installations_org_id'
    ) THEN
        CREATE INDEX idx_github_installations_org_id
            ON github_installations (org_id);
    END IF;
END $$;

COMMIT;
