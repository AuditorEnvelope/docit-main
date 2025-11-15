-- Add tracked_branch column to repositories for per-repo trigger branch selection
-- Safe migration: uses IF NOT EXISTS so it can be run multiple times without errors

BEGIN;

ALTER TABLE repositories
    ADD COLUMN IF NOT EXISTS tracked_branch VARCHAR(100) DEFAULT 'main';

UPDATE repositories
   SET tracked_branch = COALESCE(NULLIF(tracked_branch, ''), 'main');

COMMIT;
