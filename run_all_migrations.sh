#!/bin/bash

# Script to run all database migrations in order
# Usage: ./run_all_migrations.sh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="${DB_NAME:-lekhak_ai}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Migration files in order
MIGRATIONS=(
    "migrations/001_auth_and_billing.sql"
    "migrations/002_multi_org_support.sql"
    "migrations/003_org_registrations.sql"
    "migrations/004_repo_sync_state.sql"
    "migrations/005_stripe_subscription_management.sql"
)

echo -e "${BLUE}🗄️  Lekhak AI Database Migration Script${NC}"
echo "=========================================="
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ Error: psql command not found${NC}"
    echo "Please install PostgreSQL and ensure psql is in your PATH"
    exit 1
fi

# Check if database exists
echo -e "${BLUE}Checking if database exists...${NC}"
if ! psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo -e "${BLUE}Database '$DB_NAME' not found. Creating...${NC}"
    createdb -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME"
    echo -e "${GREEN}✅ Database created${NC}"
else
    echo -e "${GREEN}✅ Database exists${NC}"
fi

echo ""
echo -e "${BLUE}Running migrations...${NC}"
echo ""

# Run each migration
for migration in "${MIGRATIONS[@]}"; do
    if [ ! -f "$migration" ]; then
        echo -e "${RED}❌ Error: Migration file not found: $migration${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Running: $migration${NC}"
    
    if psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f "$migration" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $migration completed${NC}"
    else
        echo -e "${RED}❌ Error running $migration${NC}"
        echo "Run manually to see error details:"
        echo "  psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -f $migration"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}✅ All migrations completed successfully!${NC}"
echo ""
echo "Verifying setup..."
echo ""

# Verify tables exist
TABLE_COUNT=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)

echo "Tables created: $TABLE_COUNT"

# Verify plans
PLAN_COUNT=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM plans;" | xargs)
echo "Plans created: $PLAN_COUNT"

if [ "$PLAN_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✅ Database setup complete!${NC}"
else
    echo -e "${RED}⚠️  Warning: Expected 4+ plans, found $PLAN_COUNT${NC}"
fi

echo ""
echo "Next steps:"
echo "1. Set DATABASE_URL in .env file"
echo "2. Configure Stripe keys (if using payments)"
echo "3. Start backend: python src/main.py"
