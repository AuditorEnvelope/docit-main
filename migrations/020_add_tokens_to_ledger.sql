-- ============================================================================
-- Migration 020: Add Token Tracking to Usage Ledger (Shadow Metrics)
-- ============================================================================
-- 
-- Purpose: Track LLM token usage for cost analysis and optimization
-- 
-- Business Context:
-- - We bill by "Document Count" but need token-level visibility
-- - Token data helps optimize costs and detect expensive operations
-- - Future-proofs for potential token-based billing tiers
-- 
-- Shadow Ledger Pattern:
-- - These columns track internal metrics WITHOUT affecting billing
-- - `resource_type = 'docs_generated'` still drives billing
-- - Token data is for analytics, cost monitoring, and optimization
-- 
-- ============================================================================

BEGIN;

-- Add token tracking columns to subscription_usage table
ALTER TABLE subscription_usage
ADD COLUMN IF NOT EXISTS input_tokens INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS output_tokens INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS model_name VARCHAR(100) DEFAULT 'unknown' NOT NULL,
ADD COLUMN IF NOT EXISTS cost DECIMAL(10, 4) DEFAULT 0.0000;

-- Add comments for documentation
COMMENT ON COLUMN subscription_usage.input_tokens IS 'LLM prompt tokens consumed (shadow metric)';
COMMENT ON COLUMN subscription_usage.output_tokens IS 'LLM completion tokens generated (shadow metric)';
COMMENT ON COLUMN subscription_usage.model_name IS 'LLM model used (e.g., gpt-4o, gemini-2.0-flash)';
COMMENT ON COLUMN subscription_usage.cost IS 'Estimated cost in USD (optional, for future use)';

-- Create index for cost analysis queries
CREATE INDEX IF NOT EXISTS idx_usage_tokens_cost 
ON subscription_usage(user_id, consumed_at DESC, input_tokens, output_tokens);

-- Create index for model usage analysis
CREATE INDEX IF NOT EXISTS idx_usage_model_name 
ON subscription_usage(model_name, consumed_at DESC);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check that columns were added successfully
SELECT 
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'subscription_usage'
  AND column_name IN ('input_tokens', 'output_tokens', 'model_name', 'cost')
ORDER BY ordinal_position;

-- Check indexes
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'subscription_usage'
  AND indexname LIKE 'idx_usage_%'
ORDER BY indexname;

COMMIT;

-- ============================================================================
-- Example Usage Queries (Post-Migration)
-- ============================================================================

-- Total tokens consumed by user
-- SELECT 
--     user_id,
--     SUM(input_tokens) as total_input,
--     SUM(output_tokens) as total_output,
--     SUM(input_tokens + output_tokens) as total_tokens
-- FROM subscription_usage
-- WHERE resource_type = 'docs_generated'
--   AND consumed_at >= NOW() - INTERVAL '30 days'
-- GROUP BY user_id
-- ORDER BY total_tokens DESC;

-- Model usage breakdown
-- SELECT 
--     model_name,
--     COUNT(*) as generation_count,
--     SUM(input_tokens) as total_input,
--     SUM(output_tokens) as total_output,
--     AVG(input_tokens) as avg_input,
--     AVG(output_tokens) as avg_output
-- FROM subscription_usage
-- WHERE resource_type = 'docs_generated'
-- GROUP BY model_name
-- ORDER BY generation_count DESC;

-- Most expensive generations
-- SELECT 
--     resource_id,
--     model_name,
--     input_tokens,
--     output_tokens,
--     (input_tokens + output_tokens) as total_tokens,
--     cost,
--     consumed_at
-- FROM subscription_usage
-- WHERE resource_type = 'docs_generated'
-- ORDER BY (input_tokens + output_tokens) DESC
-- LIMIT 20;
