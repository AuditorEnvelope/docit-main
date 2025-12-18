"""
Razorpay Integration Service - Complete Subscription Management
Handles payments, subscriptions, webhooks, and organization billing for India
"""

import os
import razorpay
import hmac
import hashlib
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncpg
from fastapi import HTTPException
import json
import time

# Initialize Razorpay Client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
    print("⚠️  WARNING: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET not configured!")

class RazorpayService:
    """
    Comprehensive Razorpay Service for User Subscriptions (mapped to email)
    
    Features:
    - Create orders and payment links for users
    - Handle Razorpay webhooks
    - Manage subscriptions (create, update, cancel)
    - Automatic downgrade to free on expiry
    - User-level billing (no organizations needed)
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.client = razorpay_client
    
    async def get_plan_by_name(self, plan_name: str) -> Optional[Dict]:
        """Get plan details from database by name"""
        async with self.pool.acquire() as conn:
            # Try case-insensitive match first
            row = await conn.fetchrow("""
                SELECT plan_id, name, price_cents, interval, 
                       razorpay_plan_id, razorpay_price_id,
                       llm_priority_tier, features, description
                FROM plans
                WHERE LOWER(name) = LOWER($1) AND is_active = true
            """, plan_name)
            
            if not row:
                # Check if plans table exists and has any data
                plan_count = await conn.fetchval("SELECT COUNT(*) FROM plans")
                if plan_count == 0:
                    print(f"⚠️  Plans table is empty! Inserting default plans...")
                    await self._ensure_default_plans(conn)
                    # Retry after inserting
                    row = await conn.fetchrow("""
                        SELECT plan_id, name, price_cents, interval, 
                               razorpay_plan_id, razorpay_price_id,
                               llm_priority_tier, features, description
                        FROM plans
                        WHERE LOWER(name) = LOWER($1) AND is_active = true
                    """, plan_name)
                else:
                    # List available plans for debugging
                    available_plans = await conn.fetch("SELECT name FROM plans WHERE is_active = true")
                    plan_names = [p['name'] for p in available_plans]
                    print(f"⚠️  Plan '{plan_name}' not found. Available plans: {plan_names}")
            
            if not row:
                return None
            
            return dict(row)
    
    async def _ensure_default_plans(self, conn):
        """Ensure default plans exist in database"""
        try:
            await conn.execute("""
                INSERT INTO plans (name, price_cents, interval, razorpay_plan_id, llm_priority_tier, features, description, is_active)
                VALUES
                    ('free', 0, 'month', NULL, 0, 
                     '{"repos": 1, "queries_per_day": 100, "storage_gb": 1, "support": "community"}'::JSONB,
                     'Free plan for individuals and open source projects', true),
                    ('basic', 290000, 'month', NULL, 1,
                     '{"repos": 5, "queries_per_day": 1000, "storage_gb": 10, "support": "email", "api_access": true}'::JSONB,
                     'Basic plan for professional developers', true),
                    ('premium', 990000, 'month', NULL, 2,
                     '{"repos": 20, "queries_per_day": 10000, "storage_gb": 50, "support": "priority", "api_access": true, "custom_branding": true}'::JSONB,
                     'Premium plan for growing teams', true),
                    ('enterprise', 4990000, 'month', NULL, 3,
                     '{"repos": -1, "queries_per_day": -1, "storage_gb": -1, "support": "dedicated", "api_access": true, "custom_branding": true, "sso": true, "on_premise": true}'::JSONB,
                     'Enterprise plan with unlimited everything', true)
                ON CONFLICT (name) DO UPDATE SET
                    price_cents = EXCLUDED.price_cents,
                    interval = EXCLUDED.interval,
                    features = EXCLUDED.features,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active
            """)
            print("✅ Default plans inserted/updated")
        except Exception as e:
            print(f"❌ Error inserting default plans: {e}")
            import traceback
            traceback.print_exc()
    
    async def get_or_create_razorpay_customer(
        self, 
        user_id: str,
        user_email: str,
        user_name: Optional[str] = None,
        user_phone: Optional[str] = None
    ) -> Optional[str]:
        """
        Get or create Razorpay customer for a user (mapped to email)
        
        Returns:
            Razorpay customer ID (or None if customer creation fails)
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")
        
        async with self.pool.acquire() as conn:
            # Check if user already has a customer in our database
            user_row = await conn.fetchrow("""
                SELECT razorpay_customer_id FROM users WHERE id = $1
            """, user_id)
            
            if user_row and user_row['razorpay_customer_id']:
                return user_row['razorpay_customer_id']
            
            # Try to create Razorpay customer (optional - not required for orders)
            # If it fails, we'll just skip customer creation
            try:
                # Razorpay customer creation format per docs:
                # - name: required
                # - email: required, must be unique
                # - contact: required, must be valid 10-digit phone number
                # - notes: optional dict
                customer_data = {
                    "name": user_name or user_email.split('@')[0],
                    "email": user_email,
                    "contact": user_phone or "9999999999",  # Valid 10-digit format
                    "notes": {
                        "user_id": str(user_id),
                        "user_email": user_email
                    }
                }
                
                razorpay_customer = self.client.customer.create(customer_data)
                customer_id = razorpay_customer['id']
                
                # Store customer ID in user record
                await conn.execute("""
                    UPDATE users
                    SET razorpay_customer_id = $1
                    WHERE id = $2
                """, customer_id, user_id)
                
                return customer_id
                
            except razorpay.errors.BadRequestError as e:
                error_msg = str(e)
                # If customer already exists or any other error, skip customer creation
                # Orders work fine without customer field
                if "already exists" in error_msg.lower() or "exists" in error_msg.lower():
                    print(f"ℹ️  Customer with email {user_email} already exists in Razorpay. Continuing without customer.")
                else:
                    print(f"⚠️  Razorpay customer creation failed: {error_msg}. Continuing without customer.")
                return None
            except Exception as e:
                print(f"⚠️  Error creating Razorpay customer: {e}. Continuing without customer.")
                return None
    
    async def create_order(
        self,
        user_id: str,
        user_email: str,
        plan_name: str,
        user_name: Optional[str] = None
    ) -> Dict:
        """
        Create Razorpay order for user subscription (mapped to email)
        
        Args:
            user_id: User ID
            user_email: User's email
            plan_name: Plan name (free, basic, premium, enterprise)
            user_name: User's name (optional)
        
        Returns:
            Dict with order_id, amount, currency, and payment options
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")
        
        try:
            # Get plan from database
            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                # Provide helpful error message
                raise HTTPException(
                    status_code=404, 
                    detail=f"Plan '{plan_name}' not found. Available plans: free, basic, premium, enterprise. Please ensure plans table is populated."
                )
            
            if plan['name'] == 'free':
                raise HTTPException(status_code=400, detail="Free plan doesn't require payment")
            
            # Get or create Razorpay customer for user (optional - not required for orders)
            customer_id = await self.get_or_create_razorpay_customer(
                user_id, user_email, user_name
            )
            
            # Create Razorpay order
            # price_cents stores amount in paise (e.g., ₹2,900 = 290000 paise)
            amount_paise = int(plan['price_cents'])  # Already in paise
            
            # Receipt must be max 40 characters (Razorpay requirement)
            # Use short hash of user_id + timestamp for uniqueness
            receipt_hash = hashlib.md5(f"{user_id}{int(time.time())}".encode()).hexdigest()[:16]
            receipt = f"{plan_name[:4]}_{receipt_hash}"  # e.g., "basi_a1b2c3d4e5f6g7h8" (max 21 chars, well under 40 limit)
            
            order_data = {
                "amount": amount_paise,  # Amount in paise (₹1 = 100 paise)
                "currency": "INR",
                "receipt": receipt,  # Max 40 chars - using short hash
                "notes": {
                    "user_id": str(user_id),
                    "user_email": user_email,
                    "plan_name": plan_name,
                    "plan_id": str(plan['plan_id']),
                }
            }
            
            # Customer field is optional in Razorpay orders
            # If provided, it should be passed as "customer_id" (string), not nested object
            # We'll skip it entirely since it's optional and causing issues
            
            razorpay_order = self.client.order.create(order_data)
            
            return {
                "order_id": razorpay_order['id'],
                "amount": razorpay_order['amount'],
                "currency": razorpay_order['currency'],
                "key_id": RAZORPAY_KEY_ID,  # For frontend integration
                "customer_id": customer_id if customer_id else None,  # Optional
                "metadata": {
                    "user_id": str(user_id),
                    "user_email": user_email,
                    "user_name": user_name,
                    "plan_name": plan_name,
                    "plan_id": str(plan['plan_id']),
                }
            }
            
        except razorpay.errors.BadRequestError as e:
            print(f"❌ Razorpay error creating order: {e}")
            raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Razorpay webhook signature
        
        Args:
            payload: Raw webhook payload (bytes)
            signature: X-Razorpay-Signature header value
        
        Returns:
            True if signature is valid
        """
        if not RAZORPAY_KEY_SECRET:
            return False
        
        secret = RAZORPAY_KEY_SECRET.encode('utf-8')
        expected_signature = hmac.new(
            secret,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Razorpay webhook events
        
        Events handled:
        - payment.captured: Payment successful
        - payment.failed: Payment failed
        - order.paid: Order completed
        - subscription.activated: Subscription activated
        - subscription.cancelled: Subscription cancelled
        """
        if not self.verify_webhook_signature(payload, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        try:
            event_data = json.loads(payload.decode('utf-8'))
            event_type = event_data.get('event')
            payload_data = event_data.get('payload', {})
            
            print(f"🔔 Razorpay webhook received: {event_type}")
            
            try:
                if event_type == 'payment.captured':
                    await self.handle_payment_captured(payload_data.get('payment', {}).get('entity', {}))
                
                elif event_type == 'payment.failed':
                    await self.handle_payment_failed(payload_data.get('payment', {}).get('entity', {}))
                
                elif event_type == 'order.paid':
                    await self.handle_order_paid(payload_data.get('order', {}).get('entity', {}))
                
                elif event_type == 'subscription.activated':
                    await self.handle_subscription_activated(payload_data.get('subscription', {}).get('entity', {}))
                
                elif event_type == 'subscription.cancelled':
                    await self.handle_subscription_cancelled(payload_data.get('subscription', {}).get('entity', {}))
                
                else:
                    print(f"⚠️  Unhandled webhook event type: {event_type}")
                
                return {'status': 'success', 'event_type': event_type}
                
            except Exception as e:
                print(f"❌ Error handling webhook {event_type}: {e}")
                import traceback
                traceback.print_exc()
                return {'status': 'error', 'error': str(e), 'event_type': event_type}
                
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
    
    async def handle_payment_captured(self, payment: Dict):
        """Handle successful payment capture - create subscription for user"""
        order_id = payment.get('order_id')
        
        if not order_id:
            print("⚠️  No order_id in payment")
            return
        
        async with self.pool.acquire() as conn:
            # Get order details from Razorpay to get metadata
            try:
                razorpay_order = self.client.order.fetch(order_id)
                notes = razorpay_order.get('notes', {})
                
                # Get user_id from order notes (new approach - no org_id)
                user_id = notes.get('user_id')
                user_email = notes.get('user_email')
                plan_name = notes.get('plan_name')
                plan_id_str = notes.get('plan_id')
                
                if not user_id:
                    print(f"⚠️  No user_id in order notes for order {order_id}")
                    return
                
                if not plan_name:
                    print(f"⚠️  No plan_name in order notes for order {order_id}")
                    return
                
                # Get plan details - if plan_id not available, fetch by name
                plan = await self.get_plan_by_name(plan_name)
                if not plan:
                    print(f"⚠️  Plan '{plan_name}' not found in database")
                    return
                
                plan_id = plan['plan_id']  # Use plan_id from database lookup
                
                # Create or update subscription record
                # subscriptions table uses: id (UUID PK), stripe_subscription_id (UNIQUE), user_id (FK)
                # For Razorpay, we'll use razorpay_payment_id as unique identifier
                razorpay_payment_id = payment.get('id')
                
                if not razorpay_payment_id:
                    print(f"⚠️  No payment ID in payment object")
                    return
                
                # Calculate period end (1 month from now)
                period_start = datetime.now()
                period_end = period_start + timedelta(days=30)  # Monthly subscription
                
                # Create subscription record mapped to user_id (org_id = NULL)
                # subscriptions table: id (UUID PK), user_id (FK), org_id (FK, nullable), plan_id (FK), plan (VARCHAR), stripe_subscription_id (UNIQUE)
                # Store Razorpay payment ID in stripe_subscription_id for uniqueness (reusing existing column)
                subscription_uuid = await conn.fetchval("""
                    INSERT INTO subscriptions (
                        user_id, org_id, plan_id, plan, status,
                        stripe_subscription_id,  -- Store Razorpay payment ID here (reusing column)
                        razorpay_order_id, razorpay_payment_id, razorpay_customer_id,
                        current_period_start, current_period_end,
                        amount_cents, currency, interval
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        plan_id = EXCLUDED.plan_id,
                        plan = EXCLUDED.plan,
                        status = EXCLUDED.status,
                        razorpay_order_id = EXCLUDED.razorpay_order_id,
                        razorpay_payment_id = EXCLUDED.razorpay_payment_id,
                        razorpay_customer_id = EXCLUDED.razorpay_customer_id,
                        current_period_start = EXCLUDED.current_period_start,
                        current_period_end = EXCLUDED.current_period_end,
                        amount_cents = EXCLUDED.amount_cents,
                        updated_at = NOW()
                    RETURNING id
                """,
                    user_id,  # user_id (FK) - mapped to email
                    None,  # org_id = NULL (no organization needed)
                    plan_id,  # plan_id (FK)
                    plan_name,  # plan (VARCHAR) - for backward compatibility
                    'active',  # status
                    razorpay_payment_id,  # Use stripe_subscription_id column to store Razorpay payment ID (for uniqueness)
                    order_id,
                    razorpay_payment_id,
                    payment.get('customer_id'),
                    period_start,
                    period_end,
                    payment.get('amount'),  # Amount in paise (store as-is)
                    payment.get('currency', 'INR').upper(),
                    'month',
                )
                
                print(f"✅ Payment captured for user {user_id} ({user_email}): {plan_name} (Order: {order_id}, Payment: {razorpay_payment_id})")
                
            except Exception as e:
                print(f"❌ Error processing payment capture: {e}")
                import traceback
                traceback.print_exc()
    
    async def handle_payment_failed(self, payment: Dict):
        """Handle failed payment"""
        order_id = payment.get('order_id')
        print(f"❌ Payment failed for order: {order_id}")
        # Optionally: Send notification email, update order status
    
    async def handle_order_paid(self, order: Dict):
        """Handle order paid event"""
        order_id = order.get('id')
        print(f"✅ Order paid: {order_id}")
        # Similar to payment_captured, but triggered differently
    
    async def handle_subscription_activated(self, subscription: Dict):
        """Handle subscription activation"""
        subscription_id = subscription.get('id')
        print(f"✅ Subscription activated: {subscription_id}")
    
    async def handle_subscription_cancelled(self, subscription: Dict):
        """Handle subscription cancellation - downgrade to free"""
        subscription_id = subscription.get('id')
        
        async with self.pool.acquire() as conn:
            # Get subscription record by Razorpay subscription ID
            sub_row = await conn.fetchrow("""
                SELECT user_id, plan_id, id FROM subscriptions
                WHERE razorpay_subscription_id = $1 
                   OR stripe_subscription_id = $1
            """, subscription_id)
            
            if not sub_row:
                print(f"⚠️  Subscription {subscription_id} not found")
                return
            
            # Get free plan
            free_plan = await self.get_plan_by_name('free')
            if not free_plan:
                print(f"⚠️  Free plan not found")
                return
            
            # Update subscription to canceled and free plan
            await conn.execute("""
                UPDATE subscriptions
                SET 
                    status = 'canceled',
                    plan_id = $1,
                    plan = 'free',
                    cancelled_at = NOW(),
                    updated_at = NOW()
                WHERE id = $2
            """, free_plan['plan_id'], sub_row['id'])
            
            print(f"❌ Subscription cancelled for user {sub_row['user_id']}: {subscription_id}")
    
    async def get_subscription_for_org(self, org_id: int) -> Optional[Dict]:
        """Get subscription details for an organization"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    s.id as subscription_id,
                    s.org_id,
                    s.plan_id,
                    s.plan as plan_name,
                    s.status,
                    s.razorpay_order_id,
                    s.razorpay_payment_id,
                    s.current_period_start,
                    s.current_period_end,
                    s.amount_cents,
                    s.currency,
                    s.interval,
                    p.name as plan_name_db,
                    p.price_cents,
                    p.features,
                    o.org_name
                FROM subscriptions s
                LEFT JOIN plans p ON s.plan_id = p.plan_id
                LEFT JOIN organizations o ON s.org_id = o.org_id
                WHERE s.org_id = $1
                AND s.status IN ('active', 'trialing')
                ORDER BY s.created_at DESC
                LIMIT 1
            """, org_id)
            
            if not row:
                # Return free plan as default
                free_plan = await self.get_plan_by_name('free')
                if free_plan:
                    return {
                        'plan_name': 'free',
                        'plan_id': free_plan['plan_id'],
                        'status': 'active',
                        'features': free_plan['features'],
                        'price_cents': 0,
                    }
                return None
            
            result = dict(row)
            # Ensure plan_name is set (use plan_name_db if available, else plan_name)
            if 'plan_name_db' in result and result['plan_name_db']:
                result['plan_name'] = result['plan_name_db']
            return result
    
    async def cancel_subscription(self, org_id: int) -> Dict:
        """Cancel organization's subscription"""
        async with self.pool.acquire() as conn:
            # Get active subscription
            sub_row = await conn.fetchrow("""
                SELECT id, razorpay_payment_id, stripe_subscription_id
                FROM subscriptions
                WHERE org_id = $1
                AND status IN ('active', 'trialing')
                ORDER BY created_at DESC
                LIMIT 1
            """, org_id)
            
            if not sub_row:
                raise HTTPException(status_code=404, detail="No active subscription found")
            
            subscription_uuid = sub_row['id']
            razorpay_payment_id = sub_row['razorpay_payment_id']
            
            # Note: Razorpay doesn't have subscription cancellation API like Stripe
            # We just mark it as cancelled in our database
            # Future recurring payments would need to be handled via Razorpay Subscriptions API
            
            # Update database
            await conn.execute("""
                UPDATE subscriptions
                SET 
                    status = 'canceled',
                    cancelled_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """, subscription_uuid)
            
            # Update organization
            await conn.execute("""
                UPDATE organizations
                SET subscription_id = NULL
                WHERE org_id = $1
            """, org_id)
            
            return {'status': 'cancelled', 'message': 'Subscription cancelled successfully'}
    
    async def downgrade_expired_subscriptions(self):
        """Downgrade expired subscriptions to free plan"""
        async with self.pool.acquire() as conn:
            # Get free plan
            free_plan = await self.get_plan_by_name('free')
            if not free_plan:
                print("⚠️  Free plan not found")
                return
            
            # Find expired subscriptions
            expired_subs = await conn.fetch("""
                SELECT id, org_id
                FROM subscriptions
                WHERE status IN ('active', 'trialing')
                AND current_period_end < NOW()
                AND current_period_end IS NOT NULL
            """)
            
            for sub in expired_subs:
                # Update to free plan
                await conn.execute("""
                    UPDATE subscriptions
                    SET 
                        plan_id = $1,
                        plan = 'free',
                        status = 'expired',
                        updated_at = NOW()
                    WHERE id = $2
                """, free_plan['plan_id'], sub['id'])
                
                # Update organization
                if sub['org_id']:
                    await conn.execute("""
                        UPDATE organizations
                        SET subscription_id = NULL
                        WHERE org_id = $1
                    """, sub['org_id'])
                
                print(f"✅ Downgraded expired subscription {sub['subscription_id']} to free")
    
    async def get_all_plans(self) -> List[Dict]:
        """Get all active plans"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT plan_id, name, price_cents, interval, 
                       razorpay_plan_id, razorpay_price_id,
                       llm_priority_tier, features, description
                FROM plans
                WHERE is_active = true
                ORDER BY llm_priority_tier, price_cents
            """)
            
            return [dict(row) for row in rows]
    
    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify Razorpay payment signature
        
        Args:
            order_id: Razorpay order ID
            payment_id: Razorpay payment ID
            signature: Payment signature from frontend
        
        Returns:
            True if payment is verified
        """
        if not RAZORPAY_KEY_SECRET:
            print("⚠️  RAZORPAY_KEY_SECRET not configured")
            return False
        
        try:
            # Razorpay signature verification format: order_id + "|" + payment_id
            message = f"{order_id}|{payment_id}"
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            expected_signature = hmac.new(
                secret,
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            print(f"🔍 Signature verification:")
            print(f"   Order ID: {order_id}")
            print(f"   Payment ID: {payment_id}")
            print(f"   Message: {message}")
            print(f"   Expected signature: {expected_signature[:20]}...")
            print(f"   Received signature: {signature[:20] if signature else 'None'}...")
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if is_valid:
                print(f"✅ Payment signature verified successfully")
            else:
                print(f"❌ Invalid payment signature - signatures don't match")
            
            return is_valid
        except Exception as e:
            print(f"❌ Error verifying payment signature: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def handle_payment_captured_sync(self, order_id: str, payment_id: str):
        """
        Handle payment captured synchronously (after verification)
        Fetches payment details from Razorpay and creates subscription
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")
        
        try:
            # Fetch payment details from Razorpay
            payment = self.client.payment.fetch(payment_id)
            
            if payment.get('status') != 'captured':
                print(f"⚠️  Payment {payment_id} is not captured yet (status: {payment.get('status')})")
                return
            
            # Call the existing handler
            await self.handle_payment_captured(payment)
            
        except Exception as e:
            print(f"❌ Error handling payment capture synchronously: {e}")
            import traceback
            traceback.print_exc()
            raise

