-- Migration: Add app_id to github_installations
-- Aligns installation records with DocbookPublisher expectations

BEGIN;

-- 1. Add app_id column if missing
ALTER TABLE github_installations
    ADD COLUMN IF NOT EXISTS app_id INTEGER;

-- 2. Backfill app_id from app_installations table when available
UPDATE github_installations gi
SET app_id = ai.app_id
FROM app_installations ai
WHERE gi.app_id IS NULL
  AND gi.installation_id = ai.installation_id;

-- 3. Ensure every row has an app_id (fail fast if any are still NULL)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM github_installations
        WHERE app_id IS NULL
    ) THEN
        RAISE EXCEPTION 'github_installations.app_id could not be backfilled for all rows. Please confirm app_installations data.';
    END IF;
END $$;

-- 4. Enforce NOT NULL and uniqueness per org/app pair
ALTER TABLE github_installations
    ALTER COLUMN app_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = current_schema()
          AND indexname = 'uq_github_installations_org_app'
    ) THEN
        CREATE UNIQUE INDEX uq_github_installations_org_app
            ON github_installations (org_id, app_id);
    END IF;
END $$;

COMMIT;
