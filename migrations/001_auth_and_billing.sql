-- ============================================================================
-- PUSTAK - Authentication & Billing Schema
-- Version: 1.0.0
-- Date: 2025-10-22
-- Description: Production-grade schema for user auth, subscriptions, and billing
-- ============================================================================

-- Enable UUID extension for better ID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- Stores user accounts with GitHub OAuth integration
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id BIGINT UNIQUE NOT NULL,
    
    -- User profile
    email VARCHAR(255),
    name VARCHAR(255),
    username VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    company VARCHAR(255),
    location VARCHAR(255),
    
    -- Subscription info
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    plan_status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    -- Stripe integration
    stripe_customer_id VARCHAR(255) UNIQUE,
    
    -- Account status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_stripe_customer_id ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX idx_users_plan ON users(plan);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts with GitHub OAuth integration';
COMMENT ON COLUMN users.github_id IS 'GitHub user ID from OAuth';
COMMENT ON COLUMN users.plan IS 'Current subscription plan: free, pro, team, enterprise';
COMMENT ON COLUMN users.metadata IS 'Additional user metadata in JSON format';


-- ============================================================================
-- SUBSCRIPTIONS TABLE
-- Manages user subscriptions and billing cycles
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Subscription details
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    
    -- Stripe integration
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_price_id VARCHAR(255),
    stripe_product_id VARCHAR(255),
    
    -- Billing cycle
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    
    -- Cancellation
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    
    -- Pricing
    amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',
    interval VARCHAR(20), -- month, year
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_plan CHECK (plan IN ('free', 'pro', 'team', 'enterprise')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'trialing', 'past_due', 'canceled', 'unpaid', 'incomplete')),
    CONSTRAINT valid_currency CHECK (currency IN ('USD', 'EUR', 'GBP', 'INR'))
);

-- Indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);
CREATE INDEX idx_subscriptions_active ON subscriptions(user_id, status) WHERE status IN ('active', 'trialing');

-- Comments
COMMENT ON TABLE subscriptions IS 'User subscription records with Stripe integration';
COMMENT ON COLUMN subscriptions.status IS 'Stripe subscription status';
COMMENT ON COLUMN subscriptions.cancel_at_period_end IS 'Whether subscription will cancel at end of current period';


-- ============================================================================
-- GITHUB INSTALLATIONS TABLE
-- Tracks GitHub App installations per organization
-- ============================================================================
CREATE TABLE IF NOT EXISTS github_installations (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    installation_id BIGINT UNIQUE NOT NULL,
    
    -- User/Organization info
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    account_type VARCHAR(50) NOT NULL, -- 'User' or 'Organization'
    account_id BIGINT NOT NULL,
    account_login VARCHAR(255) NOT NULL,
    
    -- Installation details
    target_type VARCHAR(50) NOT NULL,
    permissions JSONB DEFAULT '{}',
    events JSONB DEFAULT '[]',
    
    -- Access token (encrypted in production!)
    access_token TEXT,
    token_expires_at TIMESTAMP,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    suspended_at TIMESTAMP,
    suspended_by VARCHAR(255),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_account_type CHECK (account_type IN ('User', 'Organization')),
    CONSTRAINT valid_target_type CHECK (target_type IN ('User', 'Organization'))
);

-- Indexes
CREATE INDEX idx_installations_installation_id ON github_installations(installation_id);
CREATE INDEX idx_installations_user_id ON github_installations(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_installations_account_id ON github_installations(account_id);
CREATE INDEX idx_installations_account_login ON github_installations(account_login);
CREATE INDEX idx_installations_active ON github_installations(is_active) WHERE is_active = true;

-- Comments
COMMENT ON TABLE github_installations IS 'GitHub App installations per user/organization';
COMMENT ON COLUMN github_installations.installation_id IS 'GitHub installation ID from webhook';
COMMENT ON COLUMN github_installations.access_token IS 'Installation access token (should be encrypted)';


-- ============================================================================
-- USER REPOSITORIES TABLE
-- Tracks which repositories each user has connected
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_repositories (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    installation_id BIGINT REFERENCES github_installations(installation_id) ON DELETE CASCADE,
    
    -- Repository info
    repo_id BIGINT NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    repo_full_name VARCHAR(255) NOT NULL,
    repo_owner VARCHAR(255) NOT NULL,
    
    -- Repository details
    is_private BOOLEAN NOT NULL DEFAULT false,
    default_branch VARCHAR(255) DEFAULT 'main',
    language VARCHAR(100),
    description TEXT,
    
    -- Webhook
    webhook_id VARCHAR(255),
    webhook_url TEXT,
    webhook_secret VARCHAR(255),
    
    -- Sync status
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_synced_at TIMESTAMP,
    last_commit_sha VARCHAR(40),
    sync_status VARCHAR(50) DEFAULT 'pending',
    sync_error TEXT,
    
    -- Documentation stats
    doc_count INTEGER DEFAULT 0,
    last_doc_generated_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Constraints
    UNIQUE(user_id, repo_full_name),
    CONSTRAINT valid_sync_status CHECK (sync_status IN ('pending', 'syncing', 'synced', 'error'))
);

-- Indexes
CREATE INDEX idx_user_repos_user_id ON user_repositories(user_id);
CREATE INDEX idx_user_repos_installation_id ON user_repositories(installation_id);
CREATE INDEX idx_user_repos_repo_id ON user_repositories(repo_id);
CREATE INDEX idx_user_repos_full_name ON user_repositories(repo_full_name);
CREATE INDEX idx_user_repos_active ON user_repositories(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_user_repos_sync_status ON user_repositories(sync_status);

-- Comments
COMMENT ON TABLE user_repositories IS 'Repositories connected by users for documentation';
COMMENT ON COLUMN user_repositories.sync_status IS 'Current synchronization status';


-- ============================================================================
-- API USAGE TABLE
-- Tracks API usage for rate limiting and analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_usage (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(500),
    
    -- Response details
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    
    -- Request metadata
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    
    -- Error tracking
    error_message TEXT,
    error_stack TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_method CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'))
);

-- Indexes (partitioned by date for performance)
CREATE INDEX idx_api_usage_user_id ON api_usage(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_api_usage_endpoint ON api_usage(endpoint, created_at DESC);
CREATE INDEX idx_api_usage_status_code ON api_usage(status_code, created_at DESC);
CREATE INDEX idx_api_usage_created_at ON api_usage(created_at DESC);
CREATE INDEX idx_api_usage_errors ON api_usage(created_at DESC) WHERE status_code >= 400;

-- Comments
COMMENT ON TABLE api_usage IS 'API request logs for analytics and rate limiting';
COMMENT ON COLUMN api_usage.response_time_ms IS 'Response time in milliseconds';


-- ============================================================================
-- PAYMENT EVENTS TABLE
-- Audit log for all payment-related events
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_events (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_source VARCHAR(50) NOT NULL DEFAULT 'stripe',
    
    -- Stripe details
    stripe_event_id VARCHAR(255) UNIQUE,
    stripe_object_type VARCHAR(100),
    stripe_object_id VARCHAR(255),
    
    -- Amount details
    amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Status
    status VARCHAR(50) NOT NULL,
    
    -- Raw data
    raw_data JSONB,
    
    -- Error tracking
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_event_source CHECK (event_source IN ('stripe', 'manual', 'system')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'canceled'))
);

-- Indexes
CREATE INDEX idx_payment_events_user_id ON payment_events(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_payment_events_subscription_id ON payment_events(subscription_id, created_at DESC) WHERE subscription_id IS NOT NULL;
CREATE INDEX idx_payment_events_stripe_event_id ON payment_events(stripe_event_id) WHERE stripe_event_id IS NOT NULL;
CREATE INDEX idx_payment_events_type ON payment_events(event_type, created_at DESC);
CREATE INDEX idx_payment_events_status ON payment_events(status, created_at DESC);

-- Comments
COMMENT ON TABLE payment_events IS 'Audit log for all payment and billing events';
COMMENT ON COLUMN payment_events.raw_data IS 'Complete webhook payload from Stripe';


-- ============================================================================
-- SESSIONS TABLE
-- User session management for authentication
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session details
    token VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500) UNIQUE,
    
    -- Device/Browser info
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    
    -- Location (optional)
    country VARCHAR(2),
    city VARCHAR(100),
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Expiration
    expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP,
    
    -- Last activity
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_device_type CHECK (device_type IN ('desktop', 'mobile', 'tablet', 'unknown'))
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id, created_at DESC);
CREATE INDEX idx_sessions_token ON sessions(token) WHERE is_active = true;
CREATE INDEX idx_sessions_active ON sessions(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Comments
COMMENT ON TABLE sessions IS 'User authentication sessions with JWT tokens';
COMMENT ON COLUMN sessions.token IS 'JWT access token';
COMMENT ON COLUMN sessions.refresh_token IS 'JWT refresh token for token renewal';


-- ============================================================================
-- AUDIT LOG TABLE
-- Complete audit trail for security and compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Action details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    
    -- Changes
    old_values JSONB,
    new_values JSONB,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Comments
COMMENT ON TABLE audit_logs IS 'Complete audit trail for security and compliance';
COMMENT ON COLUMN audit_logs.action IS 'Action performed: create, update, delete, login, etc.';


-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- Automated timestamp updates and data validation
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_installations_updated_at BEFORE UPDATE ON github_installations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_repos_updated_at BEFORE UPDATE ON user_repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Function to sync user plan with subscription
CREATE OR REPLACE FUNCTION sync_user_plan_from_subscription()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'active' OR NEW.status = 'trialing' THEN
        UPDATE users 
        SET plan = NEW.plan, 
            plan_status = NEW.status,
            updated_at = NOW()
        WHERE id = NEW.user_id;
    ELSIF NEW.status IN ('canceled', 'unpaid', 'past_due') THEN
        UPDATE users 
        SET plan = 'free',
            plan_status = NEW.status,
            updated_at = NOW()
        WHERE id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-sync user plan
CREATE TRIGGER sync_user_plan AFTER INSERT OR UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION sync_user_plan_from_subscription();


-- ============================================================================
-- INITIAL DATA
-- Default data for testing and development
-- ============================================================================

-- Insert default free plan for existing users
-- (This will be handled by application logic)

-- ============================================================================
-- GRANTS & PERMISSIONS
-- Set up proper database permissions
-- ============================================================================

-- Grant permissions to application user (replace 'pustak_app' with your DB user)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pustak_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pustak_app;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_auth_and_billing.sql completed successfully!';
    RAISE NOTICE 'Tables created: users, subscriptions, github_installations, user_repositories, api_usage, payment_events, sessions, audit_logs';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update DATABASE_URL in .env';
    RAISE NOTICE '2. Run: psql $DATABASE_URL < migrations/001_auth_and_billing.sql';
    RAISE NOTICE '3. Verify tables: \dt in psql';
END $$;
