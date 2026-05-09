-- ============================================================================
-- MIGRATION 014: Production-Ready Subscription System
-- Version: 14.0.0
-- Date: 2025-12-31
-- Description: Add TEAM plan, subscription queuing, plan hierarchy, and edge case handling
-- ============================================================================

-- ============================================================================
-- STEP 1: Add new columns to subscription_plans table
-- ============================================================================

ALTER TABLE subscription_plans
ADD COLUMN IF NOT EXISTS plan_tier INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS features JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS stripe_price_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS razorpay_plan_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_subscription_plans_tier ON subscription_plans(plan_tier);
CREATE INDEX IF NOT EXISTS idx_subscription_plans_stripe_price ON subscription_plans(stripe_price_id) WHERE stripe_price_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscription_plans_razorpay_plan ON subscription_plans(razorpay_plan_id) WHERE razorpay_plan_id IS NOT NULL;

COMMENT ON COLUMN subscription_plans.plan_tier IS 'Plan hierarchy: 0=free, 1=pro, 2=team, 3=enterprise';
COMMENT ON COLUMN subscription_plans.features IS 'Plan features in JSON format';

-- ============================================================================
-- STEP 2: Insert/Update all 4 plans (free, pro, team, enterprise)
-- ============================================================================

INSERT INTO subscription_plans (
    name, 
    display_name, 
    description,
    price_monthly, 
    price_yearly,
    plan_tier,
    max_repositories, 
    max_docs_per_month,
    max_team_members,
    has_priority_support,
    has_custom_templates,
    has_api_access,
    has_advanced_analytics,
    features,
    is_active
)
VALUES
    (
        'free',
        'Free',
        'Perfect for individuals and small projects',
        0.00,
        0.00,
        0,
        1,
        100,
        1,
        false,
        false,
        false,
        false,
        '{"repos": 1, "docs_per_month": 100, "team_members": 1, "support": "community", "storage_gb": 1}'::JSONB,
        true
    ),
    (
        'pro',
        'Pro',
        'For professional developers and growing teams',
        29.00,
        290.00,
        1,
        -1,
        1000,
        3,
        true,
        true,
        true,
        false,
        '{"repos": "unlimited", "docs_per_month": 1000, "team_members": 3, "support": "priority", "storage_gb": 50, "api_access": true, "custom_templates": true}'::JSONB,
        true
    ),
    (
        'team',
        'Team',
        'For teams and organizations with advanced collaboration needs',
        59.00,
        590.00,
        2,
        -1,
        5000,
        10,
        true,
        true,
        true,
        true,
        '{"repos": "unlimited", "docs_per_month": 5000, "team_members": 10, "support": "priority", "storage_gb": 200, "api_access": true, "custom_templates": true, "advanced_analytics": true, "sso": false}'::JSONB,
        true
    ),
    (
        'enterprise',
        'Enterprise',
        'For large organizations with unlimited needs',
        99.00,
        990.00,
        3,
        -1,
        -1,
        -1,
        true,
        true,
        true,
        true,
        '{"repos": "unlimited", "docs_per_month": "unlimited", "team_members": "unlimited", "support": "dedicated", "storage_gb": "unlimited", "api_access": true, "custom_templates": true, "advanced_analytics": true, "sso": true, "on_premise": true, "sla": true}'::JSONB,
        true
    )
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    price_monthly = EXCLUDED.price_monthly,
    price_yearly = EXCLUDED.price_yearly,
    plan_tier = EXCLUDED.plan_tier,
    max_repositories = EXCLUDED.max_repositories,
    max_docs_per_month = EXCLUDED.max_docs_per_month,
    max_team_members = EXCLUDED.max_team_members,
    has_priority_support = EXCLUDED.has_priority_support,
    has_custom_templates = EXCLUDED.has_custom_templates,
    has_api_access = EXCLUDED.has_api_access,
    has_advanced_analytics = EXCLUDED.has_advanced_analytics,
    features = EXCLUDED.features,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- ============================================================================
-- STEP 3: Add subscription queuing table for plan upgrades
-- ============================================================================

CREATE TABLE IF NOT EXISTS subscription_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    
    -- Queued plan details
    queued_plan_name VARCHAR(50) NOT NULL,
    queued_plan_id INTEGER REFERENCES subscription_plans(id),
    
    -- Activation details
    activation_date TIMESTAMPTZ NOT NULL,  -- When this plan should become active
    billing_start_date TIMESTAMPTZ NOT NULL,
    billing_end_date TIMESTAMPTZ NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,  -- pending, activated, cancelled
    
    -- Metadata
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_subscription_queue_user_id ON subscription_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_queue_activation_date ON subscription_queue(activation_date);
CREATE INDEX IF NOT EXISTS idx_subscription_queue_status ON subscription_queue(status);

COMMENT ON TABLE subscription_queue IS 'Queue for future subscription activations (upgrades, renewals)';
COMMENT ON COLUMN subscription_queue.activation_date IS 'When this subscription should become active';
COMMENT ON COLUMN subscription_queue.status IS 'pending, activated, cancelled';

-- ============================================================================
-- STEP 4: Add payment stacking support to payments table
-- ============================================================================

ALTER TABLE payments
ADD COLUMN IF NOT EXISTS stacking_type VARCHAR(20) DEFAULT 'new',
ADD COLUMN IF NOT EXISTS extends_subscription_id UUID REFERENCES subscriptions(id),
ADD COLUMN IF NOT EXISTS queued_activation_date TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_payments_stacking_type ON payments(stacking_type);
CREATE INDEX IF NOT EXISTS idx_payments_extends_subscription ON payments(extends_subscription_id) WHERE extends_subscription_id IS NOT NULL;

COMMENT ON COLUMN payments.stacking_type IS 'new, extension, upgrade';
COMMENT ON COLUMN payments.extends_subscription_id IS 'Subscription this payment extends (for same-plan renewals)';
COMMENT ON COLUMN payments.queued_activation_date IS 'For upgrades: when this should activate';

-- ============================================================================
-- STEP 5: Create function to activate queued subscriptions
-- ============================================================================

CREATE OR REPLACE FUNCTION activate_queued_subscriptions()
RETURNS INTEGER AS $$
DECLARE
    activated_count INTEGER := 0;
    queued_sub RECORD;
BEGIN
    -- Find all pending queued subscriptions that should be activated
    FOR queued_sub IN
        SELECT * FROM subscription_queue
        WHERE status = 'pending'
        AND activation_date <= NOW()
        ORDER BY activation_date ASC
    LOOP
        -- Update the user's subscription
        UPDATE subscriptions
        SET 
            plan = (SELECT name::text FROM subscription_plans WHERE id = queued_sub.queued_plan_id)::subscription_plan_enum,
            current_period_start = queued_sub.billing_start_date,
            current_period_end = queued_sub.billing_end_date,
            status = 'active',
            updated_at = NOW()
        WHERE user_id = queued_sub.user_id;
        
        -- Mark queue entry as activated
        UPDATE subscription_queue
        SET 
            status = 'activated',
            activated_at = NOW(),
            updated_at = NOW()
        WHERE id = queued_sub.id;
        
        activated_count := activated_count + 1;
        
        RAISE NOTICE 'Activated queued subscription % for user %', queued_sub.queued_plan_name, queued_sub.user_id;
    END LOOP;
    
    RETURN activated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION activate_queued_subscriptions() IS 'Activate all pending queued subscriptions that are due';

-- ============================================================================
-- STEP 6: Create function to handle subscription purchase
-- ============================================================================

CREATE OR REPLACE FUNCTION get_plan_tier(plan_name VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    tier INTEGER;
BEGIN
    SELECT plan_tier INTO tier FROM subscription_plans WHERE name = plan_name;
    RETURN COALESCE(tier, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 7: Create trigger to auto-update updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_subscription_queue_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_subscription_queue_updated_at_trigger
BEFORE UPDATE ON subscription_queue
FOR EACH ROW
EXECUTE FUNCTION update_subscription_queue_updated_at();

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all plans exist
SELECT name, display_name, plan_tier, price_monthly 
FROM subscription_plans 
ORDER BY plan_tier;

-- Verify new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('subscription_queue');

-- Verify new columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'payments' 
AND column_name IN ('stacking_type', 'extends_subscription_id', 'queued_activation_date');

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 014_production_ready_subscriptions.sql completed successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Plans created:';
    RAISE NOTICE '  • Free (tier 0): $0/mo';
    RAISE NOTICE '  • Pro (tier 1): $29/mo';
    RAISE NOTICE '  • Team (tier 2): $59/mo';
    RAISE NOTICE '  • Enterprise (tier 3): $99/mo';
    RAISE NOTICE '';
    RAISE NOTICE 'New features:';
    RAISE NOTICE '  • Subscription queuing for upgrades';
    RAISE NOTICE '  • Payment stacking support';
    RAISE NOTICE '  • Plan hierarchy tracking';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run: SELECT activate_queued_subscriptions(); (in cron job)';
    RAISE NOTICE '  2. Update application code to use new subscription logic';
    RAISE NOTICE '  3. Test subscription purchase, extension, and upgrade flows';
END $$;
