-- ============================================================================
-- MIGRATION 013: Add payments table and update user subscription fields
-- Version: 13.0.0
-- Date: 2025-01-XX
-- Description: Add payments table for full payment history and update user fields for subscription status
-- ============================================================================

-- ============================================================================
-- STEP 1: Create payments table
-- ============================================================================

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100) UNIQUE,  -- UNIQUE constraint for idempotency
    razorpay_subscription_id VARCHAR(100),
    razorpay_customer_id VARCHAR(100),
    amount NUMERIC(10, 2) NOT NULL,  -- Amount in INR
    currency VARCHAR(3) DEFAULT 'INR' NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    plan_id INTEGER,  -- Reference to subscription_plans.id
    plan_name VARCHAR(50),  -- Name of the plan
    raw_payload TEXT,  -- Store the full webhook payload
    billing_start_date TIMESTAMPTZ,
    billing_end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_order_id ON payments(razorpay_order_id) WHERE razorpay_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_payment_id ON payments(razorpay_payment_id) WHERE razorpay_payment_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_subscription_id ON payments(razorpay_subscription_id) WHERE razorpay_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_customer_id ON payments(razorpay_customer_id) WHERE razorpay_customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_plan_id ON payments(plan_id) WHERE plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_plan_name ON payments(plan_name) WHERE plan_name IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE payments IS 'Payment records for tracking all payment transactions with raw payload for audit purposes';
COMMENT ON COLUMN payments.razorpay_payment_id IS 'Razorpay Payment ID - UNIQUE for idempotency';
COMMENT ON COLUMN payments.raw_payload IS 'Raw Razorpay webhook payload for audit and debugging';

-- ============================================================================
-- STEP 2: Add new subscription fields to users table
-- ============================================================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS current_plan VARCHAR(20) DEFAULT 'free' NOT NULL,
ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'inactive' NOT NULL,
ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;

-- Add comments for documentation
COMMENT ON COLUMN users.current_plan IS 'Current plan of the user';
COMMENT ON COLUMN users.subscription_status IS 'Current subscription status (active, inactive, expired, etc.)';
COMMENT ON COLUMN users.subscription_expires_at IS 'When the current subscription expires';

-- ============================================================================
-- STEP 3: Update existing users to set current_plan from plan column
-- ============================================================================

UPDATE users SET current_plan = plan WHERE current_plan = 'free' OR current_plan IS NULL;

-- ============================================================================
-- STEP 4: Create index on new user fields for better performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_current_plan ON users(current_plan);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_subscription_expires_at ON users(subscription_expires_at) WHERE subscription_expires_at IS NOT NULL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify payments table was created
SELECT 'payments table exists' AS verification_result
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'payments'
);

-- Verify user columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users' 
AND column_name IN ('current_plan', 'subscription_status', 'subscription_expires_at');

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 013_add_payments_table_and_update_user_fields.sql completed successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. The payments table is ready to store full payment history';
    RAISE NOTICE '2. User subscription fields are updated for better tracking';
    RAISE NOTICE '3. Razorpay service needs to be updated to use new fields';
END $$;