-- Migration: Add last_documented_at to repositories table
-- Purpose: Track when docs were last generated for each repository

-- Add last_documented_at column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'repositories' 
        AND column_name = 'last_documented_at'
    ) THEN
        ALTER TABLE repositories 
        ADD COLUMN last_documented_at TIMESTAMP WITH TIME ZONE;
        
        RAISE NOTICE 'Added last_documented_at column to repositories table';
    ELSE
        RAISE NOTICE 'Column last_documented_at already exists in repositories table';
    END IF;
END $$;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_repositories_last_documented_at 
ON repositories(last_documented_at);

COMMENT ON COLUMN repositories.last_documented_at IS 'Timestamp when documentation was last generated for this repository';
