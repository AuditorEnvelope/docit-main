# 💳 Razorpay Payment Gateway & Subscription Management Integration

## ✅ Implementation Complete

This guide covers the complete Razorpay payment gateway integration for India (replacing Stripe).

---

## 📋 What's Been Implemented

### 1. Database Schema (`migrations/006_razorpay_integration.sql`)

- **Added Razorpay columns to existing tables:**
  - `plans`: `razorpay_plan_id`, `razorpay_price_id`
  - `subscriptions`: `razorpay_subscription_id`, `razorpay_order_id`, `razorpay_payment_id`, `razorpay_customer_id`
  - `users`: `razorpay_customer_id`

- **Stripe columns remain** (commented out in code) for future use if needed

### 2. Backend Razorpay Service (`src/services/razorpay_service.py`)

Complete Razorpay integration service with:

- ✅ Create Razorpay orders for organizations
- ✅ Handle all Razorpay webhooks:
  - `payment.captured` - Payment successful
  - `payment.failed` - Payment failed
  - `order.paid` - Order completed
  - `subscription.activated` - Subscription activated
  - `subscription.cancelled` - Subscription cancelled → downgrade to free
- ✅ Get organization subscriptions
- ✅ Cancel subscriptions
- ✅ **Automatic downgrade to free on expiry**
- ✅ Payment signature verification

### 3. Backend API Endpoints (`src/main.py`)

#### Subscription Management

- `GET /api/plans` - Get all available plans
- `GET /api/organizations/{org_name}/subscription` - Get org subscription details
- `POST /api/checkout/create` - Create Razorpay order
- `POST /api/payment/verify` - Verify payment after completion
- `POST /api/razorpay/webhook` - Handle Razorpay webhooks
- `POST /api/organizations/{org_name}/subscription/cancel` - Cancel subscription
- `GET /api/organizations/{org_name}/billing-portal` - Get billing management URL

### 4. Frontend Integration

- ✅ Updated checkout page (`pustak/src/app/checkout/page.tsx`)
  - Loads Razorpay checkout script
  - Creates order via backend
  - Opens Razorpay payment modal
  - Handles success/error callbacks
  
- ✅ Payment success page (`pustak/src/app/payment/success/page.tsx`)
  - Shows success message
  - Displays order/payment details
  - Redirects to dashboard
  
- ✅ Payment error page (`pustak/src/app/payment/error/page.tsx`)
  - Shows error message based on failure reason
  - Displays order ID for support
  - Options to retry or go back

- ✅ Updated checkout API route (`pustak/src/app/api/create-checkout/route.ts`)
  - Passes org_name to backend
  - Handles authentication

### 5. Stripe Code (Commented Out)

- All Stripe code is **commented out** (not deleted) in:
  - `src/services/stripe_service.py` - Entire service commented
  - `src/main.py` - Stripe endpoints commented
  - `requirements.txt` - Stripe package commented

---

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install razorpay>=1.4.0
```

Or it's already in `requirements.txt`:
```
razorpay>=1.4.0
```

### Step 2: Run Database Migration

```bash
psql -U postgres -d lekhak_ai < migrations/006_razorpay_integration.sql
```

This will add Razorpay columns to existing tables.

### Step 3: Configure Razorpay

1. **Get your Razorpay API keys** from [Razorpay Dashboard](https://dashboard.razorpay.com/app/keys)
   - Go to Settings → API Keys
   - Copy Key ID and Key Secret

2. **Set environment variables** in `.env`:
```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_xxxxx  # Your Razorpay Key ID
RAZORPAY_KEY_SECRET=your_secret_key_here  # Your Razorpay Key Secret

# Frontend URL (for redirects)
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

3. **Update plans table** with Razorpay Plan IDs (optional - if using Razorpay Plans):
```sql
-- If you created plans in Razorpay Dashboard
UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'basic';
UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'premium';
UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'enterprise';
```

**Note:** You can also use Razorpay Orders (which we're doing) without creating plans in Razorpay Dashboard.

### Step 4: Configure Razorpay Webhook

1. Go to [Razorpay Dashboard → Webhooks](https://dashboard.razorpay.com/app/webhooks)
2. Click **"Add New Webhook"**
3. Set webhook URL: `https://your-domain.com/api/razorpay/webhook`
4. Select events to listen to:
   - `payment.captured`
   - `payment.failed`
   - `order.paid`
   - `subscription.activated` (if using subscriptions)
   - `subscription.cancelled` (if using subscriptions)
5. Copy the **Webhook Secret** (starts with `whsec_`)
6. Add to `.env`:
```bash
RAZORPAY_WEBHOOK_SECRET=whsec_xxxxx
```

**For local development**, use [ngrok](https://ngrok.com/) to expose your local server:
```bash
ngrok http 8000
# Use the ngrok URL for webhook endpoint
```

### Step 5: Update Frontend Environment

Add to `pustak/.env.local`:
```bash
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxx  # Same as backend RAZORPAY_KEY_ID
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 🔄 How It Works

### User Flow

1. **User selects plan** → `/pricing`
2. **Clicks "Start Free Trial"** → `/checkout?plan=pro&org=my-org`
3. **Checkout page** → Creates Razorpay order via `/api/checkout/create`
4. **Backend creates order** → Returns order details with Razorpay Key ID
5. **Frontend opens Razorpay modal** → User enters payment details
6. **Payment successful** → Razorpay calls success handler
7. **Frontend verifies payment** → Calls `/api/payment/verify`
8. **Redirects to success page** → `/payment/success?order_id=xxx&payment_id=xxx`
9. **Webhook received** → Creates subscription in database

### Payment Verification

Payment verification happens in two places:

1. **Frontend (immediate)**: After Razorpay success callback, frontend verifies signature
2. **Webhook (async)**: Razorpay sends webhook to create subscription record

Both are handled for reliability.

---

## 🎨 Payment Pages

### Success Page (`/payment/success`)

- Shows success message
- Displays plan and organization info
- Shows order ID and payment ID
- Redirects to dashboard
- Option to view plans

### Error Page (`/payment/error`)

Handles different error scenarios:
- `payment_failed` - Payment could not be processed
- `user_cancelled` - User closed payment modal
- `verification_failed` - Payment signature verification failed
- `verification_error` - Error during verification process

Each shows appropriate message and action buttons.

---

## 🔒 Security Notes

1. **Webhook Signature Verification**: All webhooks are verified using HMAC SHA256
2. **Payment Verification**: Payment signatures are verified on both frontend and backend
3. **Authentication**: All subscription endpoints require authenticated user
4. **Authorization**: Users can only manage organizations they own
5. **Razorpay Customer**: Created per organization for billing tracking

---

## 📊 Database Schema Updates

### New Columns Added

**plans table:**
- `razorpay_plan_id` VARCHAR(255)
- `razorpay_price_id` VARCHAR(255)

**subscriptions table:**
- `razorpay_subscription_id` VARCHAR(255)
- `razorpay_order_id` VARCHAR(255)
- `razorpay_payment_id` VARCHAR(255)
- `razorpay_customer_id` VARCHAR(255)

**users table:**
- `razorpay_customer_id` VARCHAR(255)

---

## 🧪 Testing

### Test Payment Flow

1. **Start backend**: `python src/main.py`
2. **Start frontend**: `cd pustak && npm run dev`
3. **Navigate to** `/pricing`
4. **Click "Start Free Trial"** on any plan
5. **Use Razorpay test card**:
   - Card: `4111 1111 1111 1111`
   - CVV: Any 3 digits
   - Expiry: Any future date
   - Name: Any name
6. **Complete payment**
7. **Verify subscription** created in database:
```sql
SELECT * FROM subscriptions WHERE razorpay_order_id IS NOT NULL;
SELECT * FROM organizations WHERE subscription_id IS NOT NULL;
```

### Test Webhooks Locally

1. **Expose local server** using ngrok:
```bash
ngrok http 8000
```

2. **Add webhook URL** in Razorpay Dashboard:
   - URL: `https://your-ngrok-url.ngrok.io/api/razorpay/webhook`
   - Events: `payment.captured`, `payment.failed`

3. **Test payment** and check webhook logs in Razorpay Dashboard

---

## ⚠️ Important Notes

1. **Price Storage**: `price_cents` should store amount in smallest currency unit (paise for INR)
   - Example: ₹29 = 2900 paise (store as `2900`)

2. **Currency**: All payments are in INR (Indian Rupees)

3. **Razorpay Plans**: Optional - you can use Orders directly without creating plans in Razorpay Dashboard

4. **Webhook Secret**: Must be set for webhook signature verification to work

5. **Frontend Key**: Razorpay Key ID must be exposed to frontend (it's safe - it's public)

6. **Backward Compatibility**: All existing Stripe code is commented, not deleted, so it can be restored if needed

---

## 🐛 Troubleshooting

### "Razorpay client not initialized"
- Check `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`

### "Invalid payment signature"
- Verify webhook secret matches in Razorpay Dashboard
- Check signature calculation in `verify_payment()`

### Payment modal doesn't open
- Check if Razorpay script loaded: `window.Razorpay` should exist
- Verify `razorpay_key_id` is correct
- Check browser console for errors

### Webhook not receiving events
- Verify webhook URL is accessible (use ngrok for local dev)
- Check webhook secret matches
- View webhook logs in Razorpay Dashboard

### Subscription not created after payment
- Check webhook is configured correctly
- Verify webhook handler is receiving events
- Check database for subscription records

---

## 📝 Next Steps (Optional Enhancements)

1. **Razorpay Subscriptions**: Use Razorpay's subscription API instead of manual Orders
2. **Automatic Renewals**: Set up recurring billing via Razorpay subscriptions
3. **Refunds**: Add refund handling
4. **Invoice Generation**: Generate invoices for payments
5. **Payment History**: Show payment history in dashboard

---

## ✅ Migration from Stripe to Razorpay

### What Changed:
- ✅ Payment gateway: Stripe → Razorpay
- ✅ Currency: USD → INR
- ✅ Checkout: Stripe Checkout → Razorpay Payment Modal
- ✅ Webhooks: Stripe webhooks → Razorpay webhooks

### What Stayed the Same:
- ✅ Database schema (just added Razorpay columns)
- ✅ Subscription management logic
- ✅ Organization-based billing
- ✅ Automatic downgrade on expiry
- ✅ API endpoint structure

---

## ✅ Integration Complete!

The Razorpay payment gateway is fully integrated and ready for use in India. All Stripe code is preserved (commented) for future reference.

**Important:** Make sure to:
1. Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`
2. Configure webhook endpoint in Razorpay Dashboard
3. Run migration `006_razorpay_integration.sql`
4. Update frontend with `NEXT_PUBLIC_RAZORPAY_KEY_ID`
