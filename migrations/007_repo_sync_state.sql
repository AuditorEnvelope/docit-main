-- MIGRATION 004: Repository Sync State Tracking
-- Track last processed commit per repo for optimized startup

CREATE TABLE IF NOT EXISTS repo_sync_state (
    repo_id VARCHAR(255) PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL,
    last_processed_sha VARCHAR(40),
    last_processed_at TIMESTAMP,
    latest_sha_on_github VARCHAR(40),
    last_checked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repo_sync_org ON repo_sync_state(org_id);
CREATE INDEX IF NOT EXISTS idx_repo_sync_last_checked ON repo_sync_state(last_checked_at);

CREATE OR REPLACE FUNCTION update_repo_sync_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS update_repo_sync_state_updated_at_trigger 
BEFORE UPDATE ON repo_sync_state
FOR EACH ROW 
EXECUTE FUNCTION update_repo_sync_state_updated_at();
