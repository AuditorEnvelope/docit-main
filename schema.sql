-- Lekhak Ki Database Schema
-- Complete schema for commit bus, hierarchical docs, RAG, and overlays

-- ============================================================================
-- 1. COMMIT BUS - Event Store for Reliable Commit Tracking
-- ============================================================================

CREATE TABLE commit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Commit identification
    repo_id VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    parent_sha VARCHAR(40)[],  -- Array of parent commits
    
    -- Author information
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    
    -- Timing
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Git metadata
    branch VARCHAR(255),
    commit_message TEXT,
    push_id VARCHAR(255),
    source VARCHAR(50) DEFAULT 'github',  -- github|gitlab|cli|manual
    
    -- Changed files (JSONB for flexibility)
    -- Format: [{"path": "src/file.ts", "status": "modified", "patch": "diff..."}]
    files_changed JSONB,
    
    -- Processing state
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Additional metadata
    metadata JSONB,
    
    -- Ensure no duplicate events
    UNIQUE(repo_id, commit_sha)
);

-- Indexes for fast queries
CREATE INDEX idx_commit_events_repo_processed ON commit_events(repo_id, processed, timestamp);
CREATE INDEX idx_commit_events_timestamp ON commit_events(timestamp DESC);
CREATE INDEX idx_commit_events_sha ON commit_events(commit_sha);
CREATE INDEX idx_commit_events_unprocessed ON commit_events(processed) WHERE processed = FALSE;

-- ============================================================================
-- MULTI-ORG SUPPORT - Webhook Registration and Token Management
-- ============================================================================

-- Organization webhook registrations (one per org)
CREATE TABLE org_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255) UNIQUE NOT NULL,
    github_token_id UUID NOT NULL,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, org_id)
);

CREATE INDEX idx_org_webhooks_secret ON org_webhooks(webhook_secret);
CREATE INDEX idx_org_webhooks_user_org ON org_webhooks(user_id, org_id);
CREATE INDEX idx_org_webhooks_org ON org_webhooks(org_id);

-- User GitHub tokens (encrypted, per-org)
CREATE TABLE user_github_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id VARCHAR(255),
    github_token TEXT NOT NULL,  -- Encrypted in production
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX idx_user_tokens_user ON user_github_tokens(user_id);
CREATE INDEX idx_user_tokens_user_token ON user_github_tokens(user_id, token_id);
CREATE INDEX idx_user_tokens_active ON user_github_tokens(is_active) WHERE is_active = TRUE;

-- Add multi-org context columns to commit_events
ALTER TABLE commit_events
ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN org_id VARCHAR(255),
ADD COLUMN github_token_id UUID REFERENCES user_github_tokens(token_id) ON DELETE SET NULL,
ADD COLUMN installation_id INTEGER,
ADD COLUMN webhook_secret VARCHAR(255);

CREATE INDEX idx_commit_events_user_id ON commit_events(user_id);
CREATE INDEX idx_commit_events_org_id ON commit_events(org_id);
CREATE INDEX idx_commit_events_user_org ON commit_events(user_id, org_id);
CREATE INDEX idx_commit_events_installation ON commit_events(installation_id);

-- Processing log for audit trail
CREATE TABLE event_processing_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES commit_events(event_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,  -- started|completed|failed|retrying
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    error TEXT,
    metadata JSONB
);

CREATE INDEX idx_processing_log_event ON event_processing_log(event_id);
CREATE INDEX idx_processing_log_status ON event_processing_log(status, started_at DESC);

-- ============================================================================
-- 2. HIERARCHICAL DOCUMENTATION - Tree Structure
-- ============================================================================

CREATE TABLE doc_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    repo_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- repo|sdk|module|feature|function|class|interface
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) NOT NULL,  -- URL-friendly identifier
    path VARCHAR(1000) NOT NULL,  -- Full path (e.g., /payment-sdk/core/create)
    
    -- Hierarchy
    parent_id UUID REFERENCES doc_nodes(id) ON DELETE CASCADE,
    depth INTEGER DEFAULT 0,  -- Tree depth (0 = root)
    position INTEGER DEFAULT 0,  -- Order among siblings
    
    -- Version tracking
    commit_sha VARCHAR(40) NOT NULL,
    version VARCHAR(50),  -- Semantic version (e.g., v2.1.0)
    
    -- Content (JSONB for flexibility)
    -- For functions: {signature, description, parameters, returns, examples, related}
    -- For modules: {overview, exports, dependencies}
    content JSONB NOT NULL,
    
    -- Metadata
    metadata JSONB,  -- {file_path, line_numbers, tags, deprecated, etc.}
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure unique paths per commit
    UNIQUE(repo_id, path, commit_sha)
);

-- Indexes for hierarchical queries
CREATE INDEX idx_doc_nodes_repo ON doc_nodes(repo_id);
CREATE INDEX idx_doc_nodes_type ON doc_nodes(type);
CREATE INDEX idx_doc_nodes_path ON doc_nodes(path);
CREATE INDEX idx_doc_nodes_parent ON doc_nodes(parent_id);
CREATE INDEX idx_doc_nodes_commit ON doc_nodes(commit_sha);
CREATE INDEX idx_doc_nodes_slug ON doc_nodes(slug);
CREATE INDEX idx_doc_nodes_hierarchy ON doc_nodes(parent_id, position);

-- Version history for doc nodes
CREATE TABLE doc_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES doc_nodes(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    changes TEXT,  -- Human-readable summary of changes
    breaking BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(node_id, version)
);

CREATE INDEX idx_doc_versions_node ON doc_versions(node_id, created_at DESC);
CREATE INDEX idx_doc_versions_commit ON doc_versions(commit_sha);

-- ============================================================================
-- 3. CHANGELOGS - Auto-generated Change Documentation
-- ============================================================================

CREATE TABLE changelogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference
    repo_id VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40) NOT NULL,
    
    -- Change classification
    type VARCHAR(50) NOT NULL,  -- feature|bugfix|breaking|refactor|docs
    category VARCHAR(100),  -- payment|auth|api|etc.
    
    -- Content
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    
    -- Affected nodes
    affected_nodes UUID[],  -- Array of doc_node IDs
    
    -- Metadata
    breaking BOOLEAN DEFAULT FALSE,
    version VARCHAR(50),
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(repo_id, commit_sha)
);

CREATE INDEX idx_changelogs_repo ON changelogs(repo_id, timestamp DESC);
CREATE INDEX idx_changelogs_type ON changelogs(type);
CREATE INDEX idx_changelogs_breaking ON changelogs(breaking) WHERE breaking = TRUE;

-- ============================================================================
-- 4. ADMIN OVERLAYS - Non-code Edits with Provenance
-- ============================================================================

CREATE TABLE doc_overlays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to base doc
    node_id UUID NOT NULL REFERENCES doc_nodes(id) ON DELETE CASCADE,
    
    -- Overlay content (overrides base content)
    content JSONB NOT NULL,
    
    -- Provenance
    author_id VARCHAR(255) NOT NULL,
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    reason TEXT,  -- Why this edit was made
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active|archived|pr_created|merged
    pr_url VARCHAR(500),  -- If PR was created
    pr_number INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    archived_at TIMESTAMP
);

CREATE INDEX idx_overlays_node ON doc_overlays(node_id, status);
CREATE INDEX idx_overlays_author ON doc_overlays(author_id);
CREATE INDEX idx_overlays_status ON doc_overlays(status) WHERE status = 'active';

-- Overlay history (track all changes)
CREATE TABLE overlay_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    overlay_id UUID REFERENCES doc_overlays(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- created|updated|archived
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_overlay_history_overlay ON overlay_history(overlay_id, created_at DESC);

-- ============================================================================
-- 5. REPOSITORIES - Repo Configuration
-- ============================================================================

CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    repo_id VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "AuditorEnvelope/lekhak_ai"
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(500),
    
    -- Git configuration
    git_url VARCHAR(500),
    default_branch VARCHAR(100) DEFAULT 'main',
    
    -- Settings
    enabled BOOLEAN DEFAULT TRUE,
    indexing_frequency VARCHAR(50) DEFAULT 'realtime',  -- realtime|hourly|daily
    auto_generate_docs BOOLEAN DEFAULT TRUE,
    
    -- Subscription
    subscription_id UUID,  -- Reference to subscriptions table
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_indexed_at TIMESTAMP
);

CREATE INDEX idx_repositories_repo_id ON repositories(repo_id);
CREATE INDEX idx_repositories_enabled ON repositories(enabled) WHERE enabled = TRUE;

-- ============================================================================
-- 6. SUBSCRIPTIONS - Billing and Feature Gates
-- ============================================================================

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User/Organization
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    
    -- Plan
    plan VARCHAR(50) NOT NULL,  -- free|team|enterprise
    status VARCHAR(50) DEFAULT 'active',  -- active|cancelled|expired|trial
    
    -- Features (JSONB for flexibility)
    features JSONB,  -- {repos: 10, indexing: "realtime", overlays: true, seats: 5}
    limits JSONB,    -- {queries_per_day: 10000, storage_gb: 100}
    
    -- Billing
    billing_cycle VARCHAR(50),  -- monthly|yearly
    amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    trial_ends_at TIMESTAMP,
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan);

-- ============================================================================
-- 7. USERS - User Accounts
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    user_id VARCHAR(255) UNIQUE NOT NULL,  -- External ID (GitHub, email, etc.)
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    
    -- Authentication
    auth_provider VARCHAR(50),  -- github|gitlab|google|saml
    auth_provider_id VARCHAR(255),
    
    -- Role
    role VARCHAR(50) DEFAULT 'viewer',  -- viewer|editor|admin|integrator
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- 8. AUDIT LOGS - Security and Compliance
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    
    -- What
    action VARCHAR(100) NOT NULL,  -- create|update|delete|view|export
    resource_type VARCHAR(50) NOT NULL,  -- doc_node|overlay|repo|subscription
    resource_id VARCHAR(255),
    
    -- When & Where
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    
    -- Details
    changes JSONB,  -- Before/after for updates
    metadata JSONB
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, timestamp DESC);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- ============================================================================
-- 9. API USAGE - Rate Limiting and Analytics
-- ============================================================================

CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who
    user_id VARCHAR(255),
    subscription_id UUID REFERENCES subscriptions(id),
    
    -- What
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    
    -- When
    timestamp TIMESTAMP DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE,
    
    -- Metrics
    response_time_ms INTEGER,
    status_code INTEGER,
    
    -- Metadata
    metadata JSONB
);

CREATE INDEX idx_api_usage_user_date ON api_usage(user_id, date);
CREATE INDEX idx_api_usage_subscription_date ON api_usage(subscription_id, date);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp DESC);

-- ============================================================================
-- 10. VECTOR EMBEDDINGS METADATA (Milvus stores vectors, we store metadata)
-- ============================================================================

CREATE TABLE embeddings_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference
    vector_id VARCHAR(255) UNIQUE NOT NULL,  -- ID in Milvus
    source_type VARCHAR(50) NOT NULL,  -- doc_node|code_snippet|diff|overlay
    source_id UUID NOT NULL,  -- ID of the source (doc_node.id, etc.)
    
    -- Content reference
    repo_id VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(40),
    file_path VARCHAR(1000),
    
    -- Metadata
    content_preview TEXT,  -- First 500 chars
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector_id ON embeddings_metadata(vector_id);
CREATE INDEX idx_embeddings_source ON embeddings_metadata(source_type, source_id);
CREATE INDEX idx_embeddings_repo ON embeddings_metadata(repo_id);

-- ============================================================================
-- VIEWS - Convenient Queries
-- ============================================================================

-- View: Latest version of each doc node
CREATE VIEW doc_nodes_latest AS
SELECT DISTINCT ON (repo_id, path) *
FROM doc_nodes
ORDER BY repo_id, path, created_at DESC;

-- View: Active overlays with base docs
CREATE VIEW docs_with_overlays AS
SELECT 
    dn.*,
    do.id as overlay_id,
    do.content as overlay_content,
    do.author_name as overlay_author,
    do.updated_at as overlay_updated_at
FROM doc_nodes dn
LEFT JOIN doc_overlays do ON dn.id = do.node_id AND do.status = 'active';

-- View: Unprocessed events summary
CREATE VIEW unprocessed_events_summary AS
SELECT 
    repo_id,
    COUNT(*) as pending_count,
    MIN(timestamp) as oldest_event,
    MAX(timestamp) as newest_event
FROM commit_events
WHERE processed = FALSE
GROUP BY repo_id;

-- ============================================================================
-- FUNCTIONS - Helper Functions
-- ============================================================================

-- Function: Get doc node with all ancestors (breadcrumb)
CREATE OR REPLACE FUNCTION get_doc_breadcrumb(node_uuid UUID)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    path VARCHAR,
    depth INTEGER
) AS $$
WITH RECURSIVE breadcrumb AS (
    -- Base case: start with the given node
    SELECT id, title, path, parent_id, 0 as depth
    FROM doc_nodes
    WHERE id = node_uuid
    
    UNION ALL
    
    -- Recursive case: get parent
    SELECT dn.id, dn.title, dn.path, dn.parent_id, b.depth + 1
    FROM doc_nodes dn
    INNER JOIN breadcrumb b ON dn.id = b.parent_id
)
SELECT id, title, path, depth
FROM breadcrumb
ORDER BY depth DESC;
$$ LANGUAGE SQL;

-- Function: Get all children of a node
CREATE OR REPLACE FUNCTION get_doc_children(node_uuid UUID)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    type VARCHAR,
    path VARCHAR
) AS $$
WITH RECURSIVE children AS (
    -- Base case: direct children
    SELECT id, title, type, path, parent_id
    FROM doc_nodes
    WHERE parent_id = node_uuid
    
    UNION ALL
    
    -- Recursive case: children of children
    SELECT dn.id, dn.title, dn.type, dn.path, dn.parent_id
    FROM doc_nodes dn
    INNER JOIN children c ON dn.parent_id = c.id
)
SELECT id, title, type, path
FROM children;
$$ LANGUAGE SQL;

-- ============================================================================
-- TRIGGERS - Automatic Updates
-- ============================================================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_doc_nodes_updated_at BEFORE UPDATE ON doc_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_doc_overlays_updated_at BEFORE UPDATE ON doc_overlays
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA - Seed Data
-- ============================================================================

-- Insert default subscription plans (for reference)
INSERT INTO subscriptions (user_id, plan, status, features, limits) VALUES
('system', 'free', 'active', 
 '{"repos": 1, "indexing": "daily", "overlays": false, "seats": 1}'::jsonb,
 '{"queries_per_day": 100, "storage_gb": 1}'::jsonb),
('system', 'team', 'active',
 '{"repos": 10, "indexing": "realtime", "overlays": true, "seats": 5, "sso": false}'::jsonb,
 '{"queries_per_day": 10000, "storage_gb": 50}'::jsonb),
('system', 'enterprise', 'active',
 '{"repos": -1, "indexing": "realtime", "overlays": true, "seats": -1, "sso": true, "audit_logs": true}'::jsonb,
 '{"queries_per_day": -1, "storage_gb": -1}'::jsonb);

-- ============================================================================
-- COMMENTS - Documentation
-- ============================================================================

COMMENT ON TABLE commit_events IS 'Event store for all git commits - ensures no commits are lost';
COMMENT ON TABLE doc_nodes IS 'Hierarchical documentation tree - SDK→Module→Feature→Function';
COMMENT ON TABLE doc_overlays IS 'Admin edits that override generated docs without changing code';
COMMENT ON TABLE changelogs IS 'Auto-generated change documentation per commit';
COMMENT ON TABLE subscriptions IS 'Subscription plans and feature gates';
COMMENT ON TABLE audit_logs IS 'Security audit trail for compliance';

-- ============================================================================
-- GRANTS - Permissions (adjust as needed)
-- ============================================================================

-- Grant read access to application user
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO lekhak_app_user;
-- GRANT INSERT, UPDATE ON commit_events, doc_nodes, doc_overlays TO lekhak_app_user;
