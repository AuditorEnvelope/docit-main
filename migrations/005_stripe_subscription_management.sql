-- ============================================================================
-- MIGRATION 005: Stripe Payment Gateway & Organization Subscription Management
-- Version: 5.0.0
-- Date: 2025-01-XX
-- Description: Complete Stripe integration for multi-tenant SaaS with organization subscriptions
-- ============================================================================

-- ============================================================================
-- STEP 1: Create PLANS table
-- Stores subscription plans with Stripe price IDs and features
-- ============================================================================

CREATE TABLE IF NOT EXISTS plans (
    plan_id SERIAL PRIMARY KEY,
    
    -- Plan identification
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'free', 'basic', 'premium', 'enterprise'
    
    -- Pricing
    price_cents INTEGER NOT NULL DEFAULT 0,  -- Price in cents (0 for free)
    interval VARCHAR(20) NOT NULL DEFAULT 'month',  -- 'month', 'year'
    
    -- Stripe integration
    stripe_price_id VARCHAR(255) UNIQUE,  -- Stripe Price ID from dashboard
    stripe_product_id VARCHAR(255),  -- Stripe Product ID
    
    -- Plan features
    llm_priority_tier INTEGER DEFAULT 0,  -- 0=free, 1=basic, 2=premium, 3=enterprise
    features JSONB DEFAULT '{}',  -- Flexible feature set
    
    -- Metadata
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_plans_name ON plans(name);
CREATE INDEX idx_plans_stripe_price_id ON plans(stripe_price_id) WHERE stripe_price_id IS NOT NULL;
CREATE INDEX idx_plans_active ON plans(is_active) WHERE is_active = true;

-- Comments
COMMENT ON TABLE plans IS 'Subscription plans with Stripe price IDs';
COMMENT ON COLUMN plans.stripe_price_id IS 'Stripe Price ID from Stripe Dashboard';
COMMENT ON COLUMN plans.features IS 'Plan features in JSON format: {repos: 10, queries_per_day: 10000, ...}';

-- ============================================================================
-- STEP 2: Create ORGANIZATIONS table (if not exists)
-- Stores organization information for multi-tenant support
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    org_id SERIAL PRIMARY KEY,
    
    -- Organization identification
    org_name VARCHAR(255) UNIQUE NOT NULL,  -- GitHub org name or custom name
    org_slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-friendly slug
    
    -- Subscription reference
    subscription_id VARCHAR(255),  -- FK to subscriptions.subscription_id (Stripe subscription ID)
    
    -- Organization details
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Primary owner/admin
    description TEXT,
    avatar_url TEXT,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_organizations_org_name ON organizations(org_name);
CREATE INDEX idx_organizations_org_slug ON organizations(org_slug);
CREATE INDEX idx_organizations_subscription_id ON organizations(subscription_id) WHERE subscription_id IS NOT NULL;
CREATE INDEX idx_organizations_owner_user_id ON organizations(owner_user_id);
CREATE INDEX idx_organizations_active ON organizations(is_active) WHERE is_active = true;

-- Comments
COMMENT ON TABLE organizations IS 'Organizations for multi-tenant subscription management';
COMMENT ON COLUMN organizations.subscription_id IS 'Reference to Stripe subscription ID in subscriptions table';

-- ============================================================================
-- STEP 3: Update SUBSCRIPTIONS table to support organizations
-- Add org_id and plan_id foreign keys
-- ============================================================================

-- Add organization reference (nullable for backward compatibility)
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(org_id) ON DELETE SET NULL;

-- Add plan reference
ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS plan_id INTEGER REFERENCES plans(plan_id) ON DELETE SET NULL;

-- Update subscription_id column if needed (it should be VARCHAR to match Stripe IDs)
-- Check if subscription_id column exists and update its type
DO $$
BEGIN
    -- Check if subscription_id column exists and is not VARCHAR
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'subscriptions' 
        AND column_name = 'subscription_id'
        AND data_type != 'character varying'
    ) THEN
        -- Note: This might fail if there's data. Handle manually if needed.
        -- ALTER TABLE subscriptions ALTER COLUMN subscription_id TYPE VARCHAR(255);
        RAISE NOTICE 'subscription_id column exists but type may need adjustment';
    END IF;
END $$;

-- Add index for organization subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_org_id ON subscriptions(org_id) WHERE org_id IS NOT NULL;

-- Comments
COMMENT ON COLUMN subscriptions.org_id IS 'Organization this subscription belongs to (nullable for user subscriptions)';
COMMENT ON COLUMN subscriptions.plan_id IS 'Reference to plans table';

-- ============================================================================
-- STEP 4: Update ORGANIZATIONS table to link subscription_id properly
-- Make subscription_id reference subscriptions table
-- ============================================================================

-- Note: Since subscription_id in subscriptions is VARCHAR (Stripe ID), 
-- we'll use a trigger to maintain referential integrity instead of FK constraint

-- ============================================================================
-- STEP 5: Insert default plans
-- ============================================================================

INSERT INTO plans (name, price_cents, interval, stripe_price_id, razorpay_plan_id, llm_priority_tier, features, description, is_active)
VALUES
    (
        'free',
        0,
        'month',
        NULL,  -- No Stripe price for free plan (COMMENTED OUT - Using Razorpay)
        NULL,  -- No Razorpay price for free plan
        0,
        '{"repos": 1, "queries_per_day": 100, "storage_gb": 1, "support": "community"}'::JSONB,
        'Free plan for individuals and open source projects',
        true
    ),
    (
        'basic',
        290000,  -- ₹2,900/month (in paise: 2900 * 100 = 290000)
        'month',
        NULL,  -- Stripe Price ID (COMMENTED OUT - Using Razorpay)
        NULL,  -- Set this with your Razorpay Plan ID
        1,
        '{"repos": 5, "queries_per_day": 1000, "storage_gb": 10, "support": "email", "api_access": true}'::JSONB,
        'Basic plan for professional developers',
        true
    ),
    (
        'premium',
        990000,  -- ₹9,900/month (in paise: 9900 * 100)
        'month',
        NULL,  -- Stripe Price ID (COMMENTED OUT - Using Razorpay)
        NULL,  -- Set this with your Razorpay Plan ID
        2,
        '{"repos": 20, "queries_per_day": 10000, "storage_gb": 50, "support": "priority", "api_access": true, "custom_branding": true}'::JSONB,
        'Premium plan for growing teams',
        true
    ),
    (
        'enterprise',
        4990000,  -- ₹49,900/month (in paise: 49900 * 100)
        'month',
        NULL,  -- Stripe Price ID (COMMENTED OUT - Using Razorpay)
        NULL,  -- Set this with your Razorpay Plan ID
        3,
        '{"repos": -1, "queries_per_day": -1, "storage_gb": -1, "support": "dedicated", "api_access": true, "custom_branding": true, "sso": true, "on_premise": true}'::JSONB,
        'Enterprise plan with unlimited everything',
        true
    )
ON CONFLICT (name) DO UPDATE SET
    price_cents = EXCLUDED.price_cents,
    interval = EXCLUDED.interval,
    features = EXCLUDED.features,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ============================================================================
-- STEP 6: Create function to downgrade expired subscriptions to free
-- ============================================================================

CREATE OR REPLACE FUNCTION downgrade_expired_subscriptions()
RETURNS void AS $$
DECLARE
    expired_sub RECORD;
    free_plan_id INTEGER;
BEGIN
    -- Get free plan ID
    SELECT plan_id INTO free_plan_id FROM plans WHERE name = 'free' LIMIT 1;
    
    IF free_plan_id IS NULL THEN
        RAISE EXCEPTION 'Free plan not found';
    END IF;
    
    -- Find expired subscriptions
    FOR expired_sub IN
        SELECT s.subscription_id, s.org_id
        FROM subscriptions s
        WHERE s.status IN ('active', 'trialing')
        AND s.current_period_end < NOW()
        AND s.current_period_end IS NOT NULL
    LOOP
        -- Update subscription to free plan
        UPDATE subscriptions
        SET 
            plan_id = free_plan_id,
            status = 'expired',
            updated_at = NOW()
        WHERE subscription_id = expired_sub.subscription_id;
        
        -- Update organization to remove subscription reference
        IF expired_sub.org_id IS NOT NULL THEN
            UPDATE organizations
            SET subscription_id = NULL
            WHERE org_id = expired_sub.org_id;
        END IF;
        
        RAISE NOTICE 'Downgraded subscription % to free plan', expired_sub.subscription_id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 7: Create trigger to update organizations.subscription_id
-- ============================================================================

CREATE OR REPLACE FUNCTION sync_org_subscription()
RETURNS TRIGGER AS $$
BEGIN
    -- If subscription has org_id, update organization's subscription_id
    IF NEW.org_id IS NOT NULL THEN
        UPDATE organizations
        SET subscription_id = NEW.subscription_id,
            updated_at = NOW()
        WHERE org_id = NEW.org_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_org_subscription_trigger
AFTER INSERT OR UPDATE ON subscriptions
FOR EACH ROW
WHEN (NEW.org_id IS NOT NULL)
EXECUTE FUNCTION sync_org_subscription();

-- ============================================================================
-- STEP 8: Create function to update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_plans_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_plans_updated_at_trigger
BEFORE UPDATE ON plans
FOR EACH ROW
EXECUTE FUNCTION update_plans_updated_at();

CREATE TRIGGER update_organizations_updated_at_trigger
BEFORE UPDATE ON organizations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 9: Create scheduled job helper (comment - actual scheduling done in app)
-- ============================================================================

-- Note: To run downgrade_expired_subscriptions() periodically, set up a cron job:
-- SELECT cron.schedule('downgrade-expired', '0 * * * *', 'SELECT downgrade_expired_subscriptions()');
-- Or run it from your application scheduler (Celery, APScheduler, etc.)

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify plans were created
-- SELECT * FROM plans;

-- Verify organizations table exists
-- SELECT * FROM organizations LIMIT 1;

-- Verify subscriptions have new columns
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'subscriptions' AND column_name IN ('org_id', 'plan_id');

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 005_stripe_subscription_management.sql completed successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update Stripe Price IDs in plans table';
    RAISE NOTICE '2. Set up Stripe webhook endpoint';
    RAISE NOTICE '3. Configure cron job for downgrade_expired_subscriptions()';
END $$;
