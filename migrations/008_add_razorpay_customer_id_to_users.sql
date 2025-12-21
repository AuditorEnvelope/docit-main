-- Migration 008: Add razorpay_customer_id to users table
-- This column stores the Razorpay customer ID for each user.

ALTER TABLE users
ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR(100);

-- Create an index on the new column for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_razorpay_customer_id ON users(razorpay_customer_id);
