# 🚀 Razorpay Integration - Quick Start

## ✅ What's Done

- ✅ Stripe code commented out (not deleted)
- ✅ Razorpay service created
- ✅ Frontend checkout updated
- ✅ Success and error pages created
- ✅ Webhook handler ready

---

## 📋 Quick Setup (5 Steps)

### Step 1: Install Razorpay

```bash
pip install razorpay>=1.4.0
```

### Step 2: Run Migration

```bash
psql -U postgres -d lekhak_ai < migrations/006_razorpay_integration.sql
```

### Step 3: Get Razorpay Keys

1. Go to [Razorpay Dashboard](https://dashboard.razorpay.com/app/keys)
2. Copy **Key ID** and **Key Secret**

### Step 4: Set Environment Variables

Add to `.env`:
```bash
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=your_secret_here

# Frontend
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Add to `pustak/.env.local`:
```bash
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxxxx  # Same as backend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Step 5: Update Plans (Optional)

Update plans with Razorpay Plan IDs if using Razorpay Plans:
```sql
UPDATE plans SET razorpay_plan_id = 'plan_xxxxx' WHERE name = 'basic';
```

---

## 🧪 Test Payment

1. **Start backend**: `python src/main.py`
2. **Start frontend**: `cd pustak && npm run dev`
3. **Go to**: `/pricing`
4. **Click**: "Start Free Trial"
5. **Use test card**: `4111 1111 1111 1111`
6. **Complete payment**
7. **Should redirect to**: `/payment/success`

---

## 📄 Files Changed

### Backend
- `src/services/stripe_service.py` - Commented out
- `src/services/razorpay_service.py` - **NEW**
- `src/main.py` - Updated to use Razorpay
- `migrations/006_razorpay_integration.sql` - **NEW**

### Frontend
- `pustak/src/app/checkout/page.tsx` - Updated for Razorpay
- `pustak/src/app/payment/success/page.tsx` - **NEW**
- `pustak/src/app/payment/error/page.tsx` - **NEW**
- `pustak/src/app/api/create-checkout/route.ts` - Updated

---

## ✅ Done!

Razorpay is now fully integrated. Stripe code is preserved (commented) for future reference.
