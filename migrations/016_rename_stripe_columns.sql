-- ============================================================================
-- MIGRATION 016: Rename Stripe Columns to Generic Names
-- Version: 16.0.0
-- Date: 2026-01-10
-- Description:
--   - Rename misleading Stripe-specific column names in payment_events
--   - Make column names payment-gateway-agnostic (works for Razorpay, Stripe, etc.)
-- ============================================================================

-- ============================================================================
-- STEP 1: Rename columns in payment_events table
-- ============================================================================

-- Rename stripe_event_id to razorpay_event_id (or generic event_id)
ALTER TABLE payment_events
    RENAME COLUMN stripe_event_id TO razorpay_event_id;

-- Rename stripe_object_type to object_type (generic)
ALTER TABLE payment_events
    RENAME COLUMN stripe_object_type TO object_type;

-- Rename stripe_object_id to object_id (generic)
ALTER TABLE payment_events
    RENAME COLUMN stripe_object_id TO object_id;

-- Update the index name to reflect new column name
DROP INDEX IF EXISTS idx_payment_events_stripe_event_id;
CREATE INDEX IF NOT EXISTS idx_payment_events_razorpay_event_id
    ON payment_events(razorpay_event_id)
    WHERE razorpay_event_id IS NOT NULL;

-- ============================================================================
-- STEP 2: Update comments to reflect Razorpay usage
-- ============================================================================

COMMENT ON COLUMN payment_events.razorpay_event_id IS 'Razorpay event ID for idempotency (format: payment_id_eventtype_timestamp)';
COMMENT ON COLUMN payment_events.object_type IS 'Type of payment object: payment, order, subscription, etc.';
COMMENT ON COLUMN payment_events.object_id IS 'Razorpay object ID (payment_id, order_id, etc.)';
COMMENT ON COLUMN payment_events.raw_data IS 'Complete webhook payload from Razorpay';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify renamed columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'payment_events'
  AND column_name IN ('razorpay_event_id', 'object_type', 'object_id');

-- Verify old columns no longer exist
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ Old Stripe columns successfully removed'
        ELSE '✗ Old Stripe columns still exist'
    END AS verification_result
FROM information_schema.columns
WHERE table_name = 'payment_events'
  AND column_name IN ('stripe_event_id', 'stripe_object_type', 'stripe_object_id');

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 016_rename_stripe_columns.sql completed successfully!';
    RAISE NOTICE 'Column naming is now payment-gateway-agnostic.';
END $$;
