# 🗄️ Complete Database Setup Guide

Step-by-step instructions to set up the Lekhak AI database with all migrations.

---

## 📋 Prerequisites

- PostgreSQL installed (version 12+)
- Command-line access (Terminal/PowerShell)
- `psql` command available

---

## 🚀 Step-by-Step Setup

### Step 1: Install PostgreSQL (If Not Installed)

#### **Windows:**

1. Download from: https://www.postgresql.org/download/windows/
2. Run installer, follow setup wizard
3. Remember the password you set for `postgres` user
4. Add PostgreSQL to PATH (usually done automatically)

#### **macOS:**

```bash
# Using Homebrew
brew install postgresql@14
brew services start postgresql@14
```

#### **Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 2: Start PostgreSQL Service

#### **Windows:**

- PostgreSQL service should start automatically after installation
- Or start via Services: Search "Services" → Find "postgresql" → Start

#### **macOS/Linux:**

```bash
# Check if running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Start if not running
sudo systemctl start postgresql  # Linux
brew services start postgresql@14  # macOS
```

### Step 3: Create Database

Open terminal/command prompt and run:

```bash
# Connect to PostgreSQL as postgres user
psql -U postgres

# If it asks for password, enter the password you set during installation
```

Once connected to PostgreSQL, run:

```sql
-- Create database
CREATE DATABASE lekhak_ai;

-- Verify it was created
\l
-- You should see 'lekhak_ai' in the list

-- Connect to the new database
\c lekhak_ai

-- Verify you're connected (should show 'lekhak_ai')
SELECT current_database();
```

**Exit psql:** Type `\q` and press Enter

---

### Step 4: Run Migrations in Order

Migrations must be run in order because later ones depend on earlier ones.

#### **Option A: Run All Migrations at Once (Recommended)**

From your project root directory:

```bash
# Navigate to project root
cd /path/to/lekhak_ai

# Run all migrations in order
psql -U postgres -d lekhak_ai -f migrations/001_auth_and_billing.sql
psql -U postgres -d lekhak_ai -f migrations/002_multi_org_support.sql
psql -U postgres -d lekhak_ai -f migrations/003_org_registrations.sql
psql -U postgres -d lekhak_ai -f migrations/004_repo_sync_state.sql
psql -U postgres -d lekhak_ai -f migrations/005_stripe_subscription_management.sql
```

#### **Option B: Run Migrations One by One (For Debugging)**

```bash
# Connect to database
psql -U postgres -d lekhak_ai

# Then run each migration:
\i migrations/001_auth_and_billing.sql
\i migrations/002_multi_org_support.sql
\i migrations/003_org_registrations.sql
\i migrations/004_repo_sync_state.sql
\i migrations/005_stripe_subscription_management.sql

# Exit
\q
```

#### **Option C: Using Full Path (If in Different Directory)**

```bash
# Windows (PowerShell)
psql -U postgres -d lekhak_ai -f "E:\Projects\lekhak_ai\migrations\001_auth_and_billing.sql"

# macOS/Linux
psql -U postgres -d lekhak_ai -f "/path/to/lekhak_ai/migrations/001_auth_and_billing.sql"
```

---

### Step 5: Verify Database Setup

Connect to database and verify all tables exist:

```bash
psql -U postgres -d lekhak_ai
```

Run these commands:

```sql
-- List all tables
\dt

-- Expected tables (you should see these):
-- commit_events
-- users
-- subscriptions
-- github_installations
-- user_repositories
-- api_usage
-- payment_events
-- sessions
-- audit_logs
-- org_webhooks
-- user_github_tokens
-- org_registrations
-- organizations
-- plans
-- doc_nodes (if you have documentation)
-- overlays (if you have overlays)

-- Check specific tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Verify plans table has default plans
SELECT name, price_cents, stripe_price_id FROM plans;

-- Should show:
-- free | 0 | NULL
-- basic | 2900 | NULL (or your Stripe Price ID)
-- premium | 9900 | NULL (or your Stripe Price ID)
-- enterprise | 49900 | NULL (or your Stripe Price ID)

-- Check organizations table structure
\d organizations

-- Check subscriptions table has new columns
\d subscriptions
-- Should show: org_id, plan_id columns
```

**Exit:** Type `\q` and press Enter

---

### Step 6: Configure Environment Variables

Create or update your `.env` file in the project root:

```bash
# Database Connection
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/lekhak_ai

# Replace 'your_password' with your PostgreSQL password
# For example:
# DATABASE_URL=postgresql://postgres:mypassword123@localhost:5432/lekhak_ai

# If using different user:
# DATABASE_URL=postgresql://username:password@localhost:5432/lekhak_ai
```

**Important:**

- Replace `your_password` with your actual PostgreSQL password
- If you created a different user, use that instead of `postgres`
- Port is usually `5432` (default PostgreSQL port)

---

### Step 7: Test Database Connection

Test if your application can connect to the database:

```bash
# Option 1: Run backend (will test connection on startup)
python src/main.py

# You should see:
# ✅ Commit Bus initialized
# ✅ Auth Service initialized
# ✅ Stripe Service initialized
# ✅ Lekhak AI ready!
```

If you see connection errors, check:

1. PostgreSQL is running
2. `DATABASE_URL` in `.env` is correct
3. Database `lekhak_ai` exists
4. Password is correct

---

## 🔍 Troubleshooting

### Problem: "psql: command not found"

**Solution:**

- Add PostgreSQL to PATH
- Windows: Reinstall PostgreSQL with "Add to PATH" option
- macOS: `brew link postgresql@14`
- Linux: Usually already in PATH

---

### Problem: "password authentication failed"

**Solution:**

```bash
# Try connecting with explicit password prompt
psql -U postgres -d lekhak_ai

# Or use environment variable
export PGPASSWORD=your_password
psql -U postgres -d lekhak_ai
```

---

### Problem: "database lekhak_ai does not exist"

**Solution:**

```bash
# Create it manually
psql -U postgres
CREATE DATABASE lekhak_ai;
\q
```

---

### Problem: "relation already exists" errors

**Solution:**
This means tables already exist. Either:

**Option A: Drop and recreate (⚠️ Deletes all data):**

```sql
DROP DATABASE lekhak_ai;
CREATE DATABASE lekhak_ai;
```

Then rerun migrations.

**Option B: Skip existing tables (Safe):**
Migrations use `CREATE TABLE IF NOT EXISTS`, so they're safe to rerun. The error might be from other objects. Check what's causing it:

```sql
\dt  -- List tables
\df  -- List functions
```

---

### Problem: Migration fails with "permission denied"

**Solution:**

```bash
# Make sure you're using postgres user or a superuser
psql -U postgres -d lekhak_ai -f migrations/001_auth_and_billing.sql

# Or grant permissions:
psql -U postgres -d lekhak_ai
GRANT ALL PRIVILEGES ON DATABASE lekhak_ai TO your_username;
\q
```

---

## 📊 Migration Overview

Here's what each migration does:

### Migration 001: `001_auth_and_billing.sql`

- Creates `users` table (GitHub OAuth)
- Creates `subscriptions` table (basic structure)
- Creates `github_installations` table
- Creates `user_repositories` table
- Creates `api_usage`, `payment_events`, `sessions`, `audit_logs` tables
- Sets up triggers and functions

### Migration 002: `002_multi_org_support.sql`

- Adds `user_id`, `org_id`, `github_token_id` to `commit_events`
- Creates `org_webhooks` table
- Creates `user_github_tokens` table
- Adds indexes

### Migration 003: `003_org_registrations.sql`

- Creates `org_registrations` table
- Links users to organizations

### Migration 004: `004_repo_sync_state.sql`

- Adds sync state columns to relevant tables
- (Check file for specific changes)

### Migration 005: `005_stripe_subscription_management.sql`

- Creates `plans` table with default plans
- Creates `organizations` table
- Updates `subscriptions` table (adds `org_id`, `plan_id`)
- Sets up triggers for automatic downgrade
- Creates downgrade function

---

## ✅ Quick Verification Script

Run this to verify everything is set up correctly:

```bash
psql -U postgres -d lekhak_ai <<EOF
-- Check tables exist
SELECT COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public';

-- Check plans exist
SELECT name, price_cents FROM plans ORDER BY llm_priority_tier;

-- Check extensions
SELECT extname FROM pg_extension WHERE extname = 'uuid-ossp';

-- Check indexes
SELECT COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public';
EOF
```

Expected output:

- `table_count`: Should be 10+ tables
- `plans`: 4 rows (free, basic, premium, enterprise)
- `uuid-ossp`: Extension should exist
- `index_count`: Should be 20+ indexes

---

## 🎯 Next Steps

After database setup:

1. **Configure Stripe** (if using payments):

   - Update `plans` table with Stripe Price IDs
   - Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in `.env`

2. **Configure GitHub OAuth**:

   - Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`

3. **Start Backend**:

   ```bash
   python src/main.py
   ```

4. **Start Frontend**:
   ```bash
   cd pustak
   npm run dev
   ```

---

## 📝 Notes

- **All migrations are idempotent**: Safe to rerun (use `IF NOT EXISTS`)
- **Order matters**: Always run migrations in numerical order
- **Backup before production**: Always backup database before running migrations in production
- **Test first**: Run migrations on a test database first

---

## 🔗 Related Documentation

- `STRIPE_INTEGRATION_GUIDE.md` - Stripe setup details
- `SETUP_AUTH.md` - GitHub OAuth setup
- `PRODUCTION_DEPLOY.md` - Production deployment guide
