-- ============================================================================
-- MIGRATION 006: Razorpay Integration - Add Razorpay columns to existing tables
-- Version: 6.0.0
-- Date: 2025-01-XX
-- Description: Add Razorpay support alongside Stripe (commented out)
-- ============================================================================

-- ============================================================================
-- STEP 1: Add Razorpay columns to plans table
-- ============================================================================

ALTER TABLE plans 
ADD COLUMN IF NOT EXISTS razorpay_plan_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS razorpay_price_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_plans_razorpay_plan_id ON plans(razorpay_plan_id) WHERE razorpay_plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_plans_razorpay_price_id ON plans(razorpay_price_id) WHERE razorpay_price_id IS NOT NULL;

COMMENT ON COLUMN plans.razorpay_plan_id IS 'Razorpay Plan ID from Razorpay Dashboard';
COMMENT ON COLUMN plans.razorpay_price_id IS 'Razorpay Price ID from Razorpay Dashboard';

-- ============================================================================
-- STEP 2: Add Razorpay columns to subscriptions table
-- ============================================================================

ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_subscriptions_razorpay_subscription_id ON subscriptions(razorpay_subscription_id) WHERE razorpay_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_razorpay_order_id ON subscriptions(razorpay_order_id) WHERE razorpay_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_razorpay_payment_id ON subscriptions(razorpay_payment_id) WHERE razorpay_payment_id IS NOT NULL;

COMMENT ON COLUMN subscriptions.razorpay_subscription_id IS 'Razorpay Subscription ID';
COMMENT ON COLUMN subscriptions.razorpay_order_id IS 'Razorpay Order ID';
COMMENT ON COLUMN subscriptions.razorpay_payment_id IS 'Razorpay Payment ID';
COMMENT ON COLUMN subscriptions.razorpay_customer_id IS 'Razorpay Customer ID';

-- ============================================================================
-- STEP 3: Add Razorpay column to users table
-- ============================================================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_users_razorpay_customer_id ON users(razorpay_customer_id) WHERE razorpay_customer_id IS NOT NULL;

COMMENT ON COLUMN users.razorpay_customer_id IS 'Razorpay Customer ID for billing';

-- ============================================================================
-- STEP 4: Update plans with Razorpay IDs (set to NULL - configure manually)
-- ============================================================================

-- Note: Update these with your Razorpay Plan IDs from Razorpay Dashboard
-- UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'basic';
-- UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'premium';
-- UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'enterprise';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify columns were added
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'plans' AND column_name LIKE '%razorpay%';

-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'subscriptions' AND column_name LIKE '%razorpay%';

-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name = 'users' AND column_name LIKE '%razorpay%';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 006_razorpay_integration.sql completed successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update Razorpay Plan IDs in plans table';
    RAISE NOTICE '2. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env';
    RAISE NOTICE '3. Configure Razorpay webhook endpoint';
END $$;
