-- ============================================================================
-- MIGRATION 017: Usage Ledger (Immutable Usage Tracking)
-- Version: 17.0.0
-- Date: 2026-01-14
-- Description:
--   - Create subscription_usage table for ledger-based usage tracking
--   - Replace mutable counters with immutable append-only usage events
--   - Enable automatic "reset" via time-window queries (no midnight scripts)
-- ============================================================================

-- ============================================================================
-- STEP 1: Create subscription_usage ledger table
-- ============================================================================

CREATE TABLE IF NOT EXISTS subscription_usage (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What billing cycle is this usage tied to?
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- What was consumed?
    resource_type VARCHAR(50) NOT NULL,
    
    -- How much?
    amount INTEGER NOT NULL DEFAULT 1,
    
    -- Optional: ID of the resource for audit trail
    -- E.g., document ID, repository ID, API call ID
    resource_id VARCHAR(255),
    
    -- When was it consumed?
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Audit timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_usage_positive_amount CHECK (amount > 0),
    CONSTRAINT chk_usage_valid_resource_type CHECK (
        resource_type IN (
            'docs_generated',
            'repos_connected',
            'api_calls',
            'pages_processed',
            'tokens_used'
        )
    )
);

-- ============================================================================
-- STEP 2: Create indexes for performance
-- ============================================================================

-- Primary index: Fast summation queries by subscription and time window
-- This is THE MAGIC INDEX that makes ledger queries fast:
-- "SELECT SUM(amount) WHERE subscription_id = X AND consumed_at >= cycle_start"
CREATE INDEX idx_usage_subscription_time ON subscription_usage(subscription_id, consumed_at DESC);

-- Secondary indexes for analytics and filtering
CREATE INDEX idx_usage_user_id ON subscription_usage(user_id, consumed_at DESC);
CREATE INDEX idx_usage_resource_type ON subscription_usage(resource_type, consumed_at);
CREATE INDEX idx_usage_consumed_at ON subscription_usage(consumed_at DESC);

-- Composite index for user + resource type queries (dashboard views)
CREATE INDEX idx_usage_user_resource ON subscription_usage(user_id, resource_type, consumed_at DESC);

-- ============================================================================
-- STEP 3: Add helpful comments
-- ============================================================================

COMMENT ON TABLE subscription_usage IS 'Immutable usage ledger. Each row represents a consumption event. Never UPDATE or DELETE rows - only INSERT. Usage "resets" are handled by time-window queries against entitlement_start/end.';

COMMENT ON COLUMN subscription_usage.subscription_id IS 'Links usage to a specific billing cycle (subscription phase). When a new cycle starts, this changes, automatically "resetting" usage.';

COMMENT ON COLUMN subscription_usage.resource_type IS 'Type of resource consumed: docs_generated, repos_connected, api_calls, pages_processed, tokens_used';

COMMENT ON COLUMN subscription_usage.amount IS 'Quantity consumed. Typically 1 for discrete resources (docs, repos), but can be N for metered resources (tokens, pages).';

COMMENT ON COLUMN subscription_usage.resource_id IS 'Optional audit trail: ID of the specific resource created/consumed (document ID, repo ID, etc.)';

COMMENT ON COLUMN subscription_usage.consumed_at IS 'Timestamp of consumption. Used in time-window queries to calculate usage within billing cycle.';

-- ============================================================================
-- STEP 4: Create helper view (optional - for easy querying)
-- ============================================================================

-- View: Current cycle usage summary per user
CREATE OR REPLACE VIEW v_current_usage_summary AS
WITH active_subscriptions AS (
    SELECT 
        id AS subscription_id,
        user_id,
        plan,
        entitlement_start,
        entitlement_end
    FROM subscriptions
    WHERE status = 'active'
      AND entitlement_start <= NOW()
      AND entitlement_end > NOW()
)
SELECT 
    a.user_id,
    a.plan,
    a.subscription_id,
    a.entitlement_start AS cycle_start,
    a.entitlement_end AS cycle_end,
    u.resource_type,
    COALESCE(SUM(u.amount), 0) AS total_used,
    COUNT(u.id) AS event_count,
    MAX(u.consumed_at) AS last_consumed_at
FROM active_subscriptions a
LEFT JOIN subscription_usage u 
    ON u.subscription_id = a.subscription_id
   AND u.consumed_at >= a.entitlement_start
   AND u.consumed_at < a.entitlement_end
GROUP BY 
    a.user_id, 
    a.plan, 
    a.subscription_id, 
    a.entitlement_start, 
    a.entitlement_end,
    u.resource_type;

COMMENT ON VIEW v_current_usage_summary IS 'Real-time usage summary for active billing cycles. Shows total usage per resource type within the current entitlement window.';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify table creation
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'subscription_usage') AS column_count
FROM information_schema.tables
WHERE table_name = 'subscription_usage';

-- Verify indexes
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'subscription_usage'
ORDER BY indexname;

-- Verify constraints
SELECT 
    conname AS constraint_name,
    contype AS constraint_type
FROM pg_constraint
WHERE conrelid = 'subscription_usage'::regclass
ORDER BY conname;

-- ============================================================================
-- EXAMPLE QUERIES (For Documentation)
-- ============================================================================

/*
-- Example 1: Get current usage for a user
WITH active_sub AS (
    SELECT id, entitlement_start, entitlement_end, plan
    FROM subscriptions
    WHERE user_id = 'USER_UUID_HERE'
      AND status = 'active'
      AND entitlement_start <= NOW()
      AND entitlement_end > NOW()
    LIMIT 1
)
SELECT 
    s.plan,
    u.resource_type,
    SUM(u.amount) AS total_used
FROM active_sub s
JOIN subscription_usage u ON u.subscription_id = s.id
WHERE u.consumed_at >= s.entitlement_start
  AND u.consumed_at < s.entitlement_end
GROUP BY s.plan, u.resource_type;

-- Example 2: Check if user can generate a document
WITH active_sub AS (
    SELECT id, entitlement_start, entitlement_end
    FROM subscriptions
    WHERE user_id = 'USER_UUID_HERE'
      AND status = 'active'
      AND entitlement_start <= NOW()
      AND entitlement_end > NOW()
    LIMIT 1
),
current_usage AS (
    SELECT COALESCE(SUM(amount), 0) AS docs_used
    FROM subscription_usage
    WHERE subscription_id = (SELECT id FROM active_sub)
      AND resource_type = 'docs_generated'
      AND consumed_at >= (SELECT entitlement_start FROM active_sub)
)
SELECT 
    docs_used,
    500 AS plan_limit,  -- Example: Pro plan limit
    (500 - docs_used) AS remaining
FROM current_usage;

-- Example 3: Usage history over time (for charts)
SELECT 
    DATE_TRUNC('day', consumed_at) AS usage_date,
    resource_type,
    SUM(amount) AS daily_total
FROM subscription_usage
WHERE user_id = 'USER_UUID_HERE'
  AND consumed_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', consumed_at), resource_type
ORDER BY usage_date DESC, resource_type;
*/

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 017_usage_ledger.sql completed successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Usage Ledger Features:';
    RAISE NOTICE '  • Immutable append-only design (never UPDATE/DELETE)';
    RAISE NOTICE '  • Automatic "reset" via time-window queries';
    RAISE NOTICE '  • Comprehensive indexes for fast aggregation';
    RAISE NOTICE '  • Audit trail with resource_id tracking';
    RAISE NOTICE '  • Helper view: v_current_usage_summary';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Next Steps:';
    RAISE NOTICE '  1. Create app/models/usage.py ORM model';
    RAISE NOTICE '  2. Create app/services/usage.py service layer';
    RAISE NOTICE '  3. Integrate usage recording in document generation';
    RAISE NOTICE '  4. Update API endpoints to use ledger queries';
END $$;
