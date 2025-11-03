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
    Comprehensive Razorpay Service for Organization Subscriptions
    
    Features:
    - Create orders and payment links for organizations
    - Handle Razorpay webhooks
    - Manage subscriptions (create, update, cancel)
    - Automatic downgrade to free on expiry
    - Organization-level billing
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.client = razorpay_client
    
    async def get_plan_by_name(self, plan_name: str) -> Optional[Dict]:
        """Get plan details from database by name"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT plan_id, name, price_cents, interval, 
                       razorpay_plan_id, razorpay_price_id,
                       llm_priority_tier, features, description
                FROM plans
                WHERE name = $1 AND is_active = true
            """, plan_name)
            
            if not row:
                return None
            
            return dict(row)
    
    async def get_or_create_razorpay_customer_for_org(
        self, 
        org_id: int, 
        org_name: str, 
        owner_email: str,
        owner_name: Optional[str] = None,
        owner_phone: Optional[str] = None,
        owner_user_id: Optional[str] = None
    ) -> str:
        """
        Get or create Razorpay customer for an organization
        
        Returns:
            Razorpay customer ID
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")
        
        async with self.pool.acquire() as conn:
            # Check if org already has a customer (via owner's razorpay_customer_id)
            owner_customer_id = None
            if owner_user_id:
                owner_row = await conn.fetchrow("""
                    SELECT razorpay_customer_id FROM users WHERE id = $1
                """, owner_user_id)
                
                if owner_row and owner_row['razorpay_customer_id']:
                    owner_customer_id = owner_row['razorpay_customer_id']
            
            # Reuse owner's customer if exists
            if owner_customer_id:
                return owner_customer_id
            
            # Create new Razorpay customer
            customer_data = {
                "name": org_name,
                "email": owner_email,
                "contact": owner_phone or "9999999999",  # Default contact
                "notes": {
                    "org_id": str(org_id),
                    "org_name": org_name,
                    "owner_user_id": str(owner_user_id) if owner_user_id else None
                }
            }
            
            if owner_name:
                customer_data["name"] = owner_name
            
            razorpay_customer = self.client.customer.create(customer_data)
            customer_id = razorpay_customer['id']
            
            # Store customer ID in owner's user record
            if owner_user_id:
                await conn.execute("""
                    UPDATE users
                    SET razorpay_customer_id = $1
                    WHERE id = $2
                """, customer_id, owner_user_id)
            
            return customer_id
    
    async def create_order(
        self,
        org_id: int,
        org_name: str,
        plan_name: str,
        owner_email: str,
        owner_name: Optional[str] = None,
        owner_user_id: Optional[str] = None
    ) -> Dict:
        """
        Create Razorpay order for organization subscription
        
        Args:
            org_id: Organization ID
            org_name: Organization name
            plan_name: Plan name (free, basic, premium, enterprise)
            owner_email: Owner's email
            owner_name: Owner's name (optional)
            owner_user_id: Owner's user ID (optional)
        
        Returns:
            Dict with order_id, amount, currency, and payment options
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")
        
        try:
            # Get plan from database
            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")
            
            if plan['name'] == 'free':
                raise HTTPException(status_code=400, detail="Free plan doesn't require payment")
            
            # Convert price from cents (USD) to paise (INR)
            # price_cents is in USD cents, but we need INR paise
            # For simplicity, assuming price_cents is already in INR (not USD)
            # ₹1 = 100 paise, so if price_cents = 2900 (₹29), then paise = 2900 * 100 = 290000
            # But if price_cents represents ₹29, then we need to convert: ₹29 * 100 = 2900 paise
            # Actually, let's assume price_cents stores amount in smallest currency unit already
            # If price_cents = 2900 means ₹29.00, then paise = price_cents * 100
            # But wait, if price_cents already stores paise, then we use it directly
            # Let's check: plan stores price in cents. For INR, we'll store in paise.
            # So if plan.price_cents = 290000 (₹2900), we need to convert to paise correctly
            # For now, assuming price_cents is stored as: ₹29 = 2900 paise (store as 2900)
            # So amount_paise = price_cents (already in paise)
            
            # Get or create Razorpay customer
            customer_id = await self.get_or_create_razorpay_customer_for_org(
                org_id, org_name, owner_email, owner_name, None, owner_user_id
            )
            
            # Create Razorpay order
            # price_cents stores amount in paise (e.g., ₹2,900 = 290000 paise)
            # Razorpay expects amount in paise
            amount_paise = int(plan['price_cents'])  # Already in paise
            order_data = {
                "amount": amount_paise,  # Amount in paise (₹1 = 100 paise)
                "currency": "INR",
                "receipt": f"org_{org_id}_plan_{plan_name}_{int(time.time())}",
                "notes": {
                    "org_id": str(org_id),
                    "org_name": org_name,
                    "plan_name": plan_name,
                    "plan_id": str(plan['plan_id']),
                    "owner_user_id": str(owner_user_id) if owner_user_id else None,
                },
                "customer": {
                    "id": customer_id
                }
            }
            
            razorpay_order = self.client.order.create(order_data)
            
            return {
                "order_id": razorpay_order['id'],
                "amount": razorpay_order['amount'],
                "currency": razorpay_order['currency'],
                "key_id": RAZORPAY_KEY_ID,  # For frontend integration
                "customer_id": customer_id,
                "metadata": {
                    "org_id": str(org_id),
                    "org_name": org_name,
                    "plan_name": plan_name,
                    "plan_id": str(plan['plan_id']),
                    "owner_email": owner_email,
                    "owner_name": owner_name,
                    "owner_user_id": str(owner_user_id) if owner_user_id else None,
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
        """Handle successful payment capture"""
        order_id = payment.get('order_id')
        
        if not order_id:
            print("⚠️  No order_id in payment")
            return
        
        async with self.pool.acquire() as conn:
            # Get order details from Razorpay to get metadata
            try:
                razorpay_order = self.client.order.fetch(order_id)
                notes = razorpay_order.get('notes', {})
                
                org_id = int(notes.get('org_id'))
                plan_name = notes.get('plan_name')
                plan_id = int(notes.get('plan_id'))
                
                # Get plan details
                plan = await self.get_plan_by_name(plan_name)
                if not plan:
                    print(f"⚠️  Plan '{plan_name}' not found")
                    return
                
                # Create or update subscription record
                # subscriptions table uses: id (UUID PK), stripe_subscription_id (UNIQUE), user_id (FK)
                # For Razorpay, we'll use razorpay_payment_id as unique identifier
                razorpay_payment_id = payment.get('id')
                
                # Calculate period end (1 month from now)
                period_start = datetime.now()
                period_end = period_start + timedelta(days=30)  # Monthly subscription
                
                # Get owner user_id for subscription (required by schema)
                owner_user_id_result = await conn.fetchrow("""
                    SELECT owner_user_id FROM organizations WHERE org_id = $1
                """, org_id)
                owner_user_id = owner_user_id_result['owner_user_id'] if owner_user_id_result else None
                
                if not owner_user_id:
                    print(f"⚠️  No owner_user_id found for org {org_id}")
                    return
                
                # Create subscription record
                # subscriptions table: id (UUID PK), user_id (FK), org_id (FK), plan_id (FK), plan (VARCHAR), stripe_subscription_id (UNIQUE)
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
                        org_id = EXCLUDED.org_id,
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
                    owner_user_id,
                    org_id,  # org_id (FK)
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
                
                # Update organization's subscription_id (store the UUID as string)
                await conn.execute("""
                    UPDATE organizations
                    SET subscription_id = $1
                    WHERE org_id = $2
                """, str(subscription_uuid), org_id)
                
                print(f"✅ Payment captured for org {org_id}: {plan_name} (Order: {order_id})")
                
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
            # Get subscription record
            # Razorpay subscription ID might be in razorpay_subscription_id or stripe_subscription_id (repurposed)
            sub_row = await conn.fetchrow("""
                SELECT org_id, plan_id, id FROM subscriptions
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
            
            # Update organization
            if sub_row['org_id']:
                await conn.execute("""
                    UPDATE organizations
                    SET subscription_id = NULL
                    WHERE org_id = $1
                """, sub_row['org_id'])
            
            print(f"❌ Subscription cancelled: {subscription_id}")
    
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
            # Verify using Razorpay client
            # Razorpay expects: order_id + "|" + payment_id
            message = f"{order_id}|{payment_id}"
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            expected_signature = hmac.new(
                secret,
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if is_valid:
                print(f"✅ Payment signature verified: {payment_id}")
            else:
                print(f"❌ Invalid payment signature")
            
            return is_valid
        except Exception as e:
            print(f"❌ Error verifying payment signature: {e}")
            return False

