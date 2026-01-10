-- ============================================================================
-- MIGRATION 015: Proration & Entitlement Windows
-- Version: 15.0.0
-- Date: 2026-01-07
-- Description:
--   - Add proration metadata to payments
--   - Add entitlement window fields to subscriptions
--   - Add generated entitlement_range and exclusion constraint to prevent
--     overlapping active entitlements per user
-- ============================================================================

-- ============================================================================
-- STEP 1: Extend payments with proration metadata
-- ============================================================================

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS stacking_type VARCHAR(20) DEFAULT 'new' NOT NULL,
    ADD COLUMN IF NOT EXISTS extends_subscription_id UUID,
    ADD COLUMN IF NOT EXISTS proration_basis_amount NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS proration_unused_ratio NUMERIC(8, 6),
    ADD COLUMN IF NOT EXISTS proration_credit_amount NUMERIC(10, 2);

-- Backfill any NULL stacking_type values to 'new' before enforcing NOT NULL
UPDATE payments
SET stacking_type = 'new'
WHERE stacking_type IS NULL;

-- Ensure foreign key to subscriptions exists for extends_subscription_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_payments_extends_subscription_id'
    ) THEN
        ALTER TABLE payments
        ADD CONSTRAINT fk_payments_extends_subscription_id
        FOREIGN KEY (extends_subscription_id) REFERENCES subscriptions(id);
    END IF;
END $$;

-- Optional: index for extends_subscription_id if not already present
CREATE INDEX IF NOT EXISTS idx_payments_extends_subscription_id
    ON payments(extends_subscription_id)
    WHERE extends_subscription_id IS NOT NULL;

-- Optional: index for stacking_type
CREATE INDEX IF NOT EXISTS idx_payments_stacking_type
    ON payments(stacking_type);


-- ============================================================================
-- STEP 2: Extend subscriptions with entitlement window and payment link
-- ============================================================================

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS entitlement_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS entitlement_end   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS payment_id       UUID,
    ADD COLUMN IF NOT EXISTS previous_subscription_id UUID;

-- Ensure foreign key to payments exists for payment_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_subscriptions_payment_id'
    ) THEN
        ALTER TABLE subscriptions
        ADD CONSTRAINT fk_subscriptions_payment_id
        FOREIGN KEY (payment_id) REFERENCES payments(id);
    END IF;
END $$;


-- ============================================================================
-- STEP 3: Generated entitlement_range and exclusion constraint
-- ============================================================================

-- Required for GiST index on ranges
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Add generated tsrange column representing the entitlement window
ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS entitlement_range TSRANGE
    GENERATED ALWAYS AS (tsrange(entitlement_start, entitlement_end, '[)')) STORED;

-- Prevent overlapping active entitlements for the same user
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'no_overlapping_active_entitlements'
    ) THEN
        ALTER TABLE subscriptions
        ADD CONSTRAINT no_overlapping_active_entitlements
        EXCLUDE USING gist (
            user_id WITH =,
            entitlement_range WITH &&
        )
        WHERE (status = 'active');
    END IF;
END $$;


-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify payments columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'payments'
  AND column_name IN (
      'stacking_type',
      'extends_subscription_id',
      'proration_basis_amount',
      'proration_unused_ratio',
      'proration_credit_amount'
  );

-- Verify subscriptions columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'subscriptions'
  AND column_name IN (
      'entitlement_start',
      'entitlement_end',
      'payment_id',
      'previous_subscription_id',
      'entitlement_range'
  );

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 015_proration_and_entitlements.sql completed successfully!';
END $$;
