# 💳 Stripe Payment Gateway & Subscription Management Integration

## ✅ Implementation Complete

This guide covers the complete Stripe payment gateway and subscription management system integrated into Lekhak AI (V3).

---

## 📋 What's Been Implemented

### 1. Database Schema (`migrations/005_stripe_subscription_management.sql`)

- **Plans Table**: Stores subscription plans with Stripe price IDs
  - `plan_id`, `name`, `price_cents`, `interval`, `stripe_price_id`, `features` (JSONB)
  
- **Organizations Table**: Multi-tenant organization support
  - `org_id`, `org_name`, `org_slug`, `subscription_id` (FK to Stripe subscription ID), `owner_user_id`
  
- **Updated Subscriptions Table**: 
  - Added `org_id` (FK to organizations)
  - Added `plan_id` (FK to plans)
  - Links subscriptions to organizations instead of just users

- **Default Plans**: Free, Basic ($29/month), Premium ($99/month), Enterprise ($499/month)

### 2. Backend Stripe Service (`src/services/stripe_service.py`)

Complete Stripe integration service with:

- ✅ Create checkout sessions for organizations
- ✅ Handle all Stripe webhooks:
  - `checkout.session.completed` - Subscription created
  - `customer.subscription.updated` - Plan changed/upgraded
  - `customer.subscription.deleted` - Subscription cancelled → downgrade to free
  - `invoice.payment_succeeded` - Payment successful
  - `invoice.payment_failed` - Payment failed
  - `customer.subscription.trial_will_end` - Trial ending soon
- ✅ Get organization subscriptions
- ✅ Cancel subscriptions (cancels at period end)
- ✅ Billing portal integration
- ✅ **Automatic downgrade to free on expiry** (via `downgrade_expired_subscriptions()`)

### 3. Backend API Endpoints (`src/main.py`)

#### Subscription Management

- `GET /api/plans` - Get all available plans
- `GET /api/organizations/{org_name}/subscription` - Get org subscription details
- `POST /api/checkout/create` - Create Stripe checkout session
- `POST /api/stripe/webhook` - Handle Stripe webhooks
- `POST /api/organizations/{org_name}/subscription/cancel` - Cancel subscription
- `GET /api/organizations/{org_name}/billing-portal` - Get Stripe billing portal URL

### 4. Frontend Integration

- ✅ Updated checkout page (`pustak/src/app/checkout/page.tsx`)
  - Handles organization-based checkout
  - Integrates with backend API
  
- ✅ Updated checkout API route (`pustak/src/app/api/create-checkout/route.ts`)
  - Passes org_name to backend
  - Handles authentication
  
- ✅ Updated pricing page (`pustak/src/app/pricing/page.tsx`)
  - Links to checkout with plan and org params

---

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install stripe>=5.0.0
```

Or add to `requirements.txt` (already done):
```
stripe>=5.0.0
```

### Step 2: Run Database Migration

```bash
psql -U postgres -d lekhak_ai < migrations/005_stripe_subscription_management.sql
```

This will:
- Create `plans` table with default plans
- Create `organizations` table
- Update `subscriptions` table to support organizations
- Add indexes and triggers

### Step 3: Configure Stripe

1. Get your Stripe API keys from [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. Create Products and Prices in Stripe Dashboard for each plan:
   - Basic: $29/month
   - Premium: $99/month
   - Enterprise: $499/month
3. Update the `stripe_price_id` in the `plans` table:

```sql
-- Update with your Stripe Price IDs
UPDATE plans SET stripe_price_id = 'price_xxxxx' WHERE name = 'basic';
UPDATE plans SET stripe_price_id = 'price_xxxxx' WHERE name = 'premium';
UPDATE plans SET stripe_price_id = 'price_xxxxx' WHERE name = 'enterprise';
```

### Step 4: Set Environment Variables

Add to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxxxx  # Your Stripe secret key
STRIPE_WEBHOOK_SECRET=whsec_xxxxx  # Your webhook signing secret

# Frontend URL (for redirects)
FRONTEND_URL=http://localhost:3000
```

### Step 5: Configure Stripe Webhook

1. Go to [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://your-domain.com/api/stripe/webhook`
3. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.trial_will_end`
4. Copy the **Signing Secret** and add to `.env` as `STRIPE_WEBHOOK_SECRET`

### Step 6: Set Up Automated Downgrade (Optional)

To automatically downgrade expired subscriptions to free:

**Option A: Cron Job (Recommended)**
```bash
# Add to crontab (runs every hour)
0 * * * * psql -U postgres -d lekhak_ai -c "SELECT downgrade_expired_subscriptions();"
```

**Option B: Application Scheduler**
Use APScheduler, Celery, or similar to call:
```python
await stripe_service.downgrade_expired_subscriptions()
```

---

## 🔄 How It Works

### User Flow

1. **User selects plan** → `/pricing`
2. **Clicks "Start Free Trial"** → `/checkout?plan=pro&org=my-org`
3. **Checkout page** → Creates Stripe checkout session via `/api/checkout/create`
4. **Stripe Checkout** → User completes payment
5. **Webhook received** → `checkout.session.completed` creates subscription in database
6. **Organization upgraded** → Subscription linked to org, org gets upgraded plan

### Subscription Management

- **Upgrade/Downgrade**: Handled via Stripe Billing Portal (accessible via `/api/organizations/{org_name}/billing-portal`)
- **Cancellation**: User cancels → Subscription cancels at period end → Auto-downgrades to free
- **Expiry**: When `current_period_end < NOW()`, subscription is downgraded to free

---

## 🔒 Security Notes

1. **Webhook Signature Verification**: All webhooks are verified using Stripe's signature
2. **Authentication**: All subscription endpoints require authenticated user
3. **Authorization**: Users can only manage organizations they own
4. **Stripe Customer**: Created per organization (reuses owner's customer for simplicity)

---

## 📊 Database Schema

### Plans Table
```sql
CREATE TABLE plans (
    plan_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'free', 'basic', 'premium', 'enterprise'
    price_cents INTEGER NOT NULL,
    interval VARCHAR(20) DEFAULT 'month',
    stripe_price_id VARCHAR(255) UNIQUE,
    stripe_product_id VARCHAR(255),
    llm_priority_tier INTEGER DEFAULT 0,
    features JSONB DEFAULT '{}',
    description TEXT,
    is_active BOOLEAN DEFAULT true
);
```

### Organizations Table
```sql
CREATE TABLE organizations (
    org_id SERIAL PRIMARY KEY,
    org_name VARCHAR(255) UNIQUE NOT NULL,
    org_slug VARCHAR(255) UNIQUE NOT NULL,
    subscription_id VARCHAR(255),  -- Stripe subscription ID
    owner_user_id UUID REFERENCES users(id),
    description TEXT,
    is_active BOOLEAN DEFAULT true
);
```

### Subscriptions Table (Updated)
```sql
-- Added columns:
org_id INTEGER REFERENCES organizations(org_id),
plan_id INTEGER REFERENCES plans(plan_id)
```

---

## 🧪 Testing

### Test Checkout Flow

1. Start backend: `python src/main.py`
2. Start frontend: `cd pustak && npm run dev`
3. Navigate to `/pricing`
4. Click "Start Free Trial" on any plan
5. Use Stripe test card: `4242 4242 4242 4242`
6. Complete checkout
7. Verify subscription created in database:
```sql
SELECT * FROM subscriptions WHERE org_id IS NOT NULL;
SELECT * FROM organizations WHERE subscription_id IS NOT NULL;
```

### Test Webhooks Locally

Use [Stripe CLI](https://stripe.com/docs/stripe-cli):
```bash
stripe listen --forward-to http://localhost:8000/api/stripe/webhook
```

Trigger test events:
```bash
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
```

---

## ⚠️ Important Notes

1. **Organization Creation**: Organizations are auto-created on checkout if they don't exist
2. **Plan Names**: Use lowercase: `free`, `basic`, `premium`, `enterprise`
3. **Stripe Price IDs**: Must be set in database before checkout will work
4. **Free Plan**: Doesn't require checkout - automatically assigned on org creation
5. **Backward Compatibility**: Legacy user-based subscriptions still work (not broken)

---

## 🐛 Troubleshooting

### "Stripe price ID not configured"
- Update `plans` table with your Stripe Price IDs from dashboard

### "Organization not found"
- Organizations are created automatically on checkout
- Make sure org_name is valid (alphanumeric, no special chars)

### Webhook not receiving events
- Check webhook URL is accessible from internet (use ngrok for local dev)
- Verify webhook secret matches in `.env`
- Check Stripe Dashboard webhook logs

### Subscription not downgrading
- Run `downgrade_expired_subscriptions()` manually
- Check `current_period_end` is in the past
- Verify free plan exists in database

---

## 📝 Next Steps (Optional Enhancements)

1. **Subscription Management UI** in dashboard
   - Show current plan
   - Upgrade/downgrade buttons
   - Billing portal link
   - Usage statistics

2. **Usage Limits Enforcement**
   - Check plan limits before operations
   - Block operations that exceed limits

3. **Trial Periods**
   - Add trial support to plans
   - Handle trial expiration

4. **Multiple Payment Methods**
   - Store multiple cards
   - Default payment method selection

---

## ✅ Integration Complete!

The Stripe payment gateway and subscription management system is fully integrated and ready for use. All existing GitHub OAuth and repo onboarding logic remains intact and functional.
