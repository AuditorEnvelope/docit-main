-- Migration 007: Create subscription_plans table
-- This table stores the configuration for different subscription plans.

CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly NUMERIC(10, 2) DEFAULT 0,
    price_yearly NUMERIC(10, 2) DEFAULT 0,
    max_repositories INTEGER DEFAULT 1,
    max_docs_per_month INTEGER DEFAULT 100,
    max_team_members INTEGER DEFAULT 1,
    has_priority_support BOOLEAN DEFAULT FALSE,
    has_custom_templates BOOLEAN DEFAULT FALSE,
    has_api_access BOOLEAN DEFAULT FALSE,
    has_advanced_analytics BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create an index on the name column for faster lookups
CREATE INDEX IF NOT EXISTS idx_subscription_plans_name ON subscription_plans(name);
