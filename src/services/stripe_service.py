"""
STRIPE INTEGRATION SERVICE - COMMENTED OUT (REPLACED WITH RAZORPAY)
This file is kept for reference. All functionality moved to razorpay_service.py

Stripe Integration Service - Complete Subscription Management
Handles payments, subscriptions, webhooks, and organization billing
"""

# ============================================================================
# STRIPE CODE COMMENTED OUT - Using Razorpay instead
# ============================================================================

"""
import os
import stripe
from typing import Dict, Optional, List
from datetime import datetime
import asyncpg
from fastapi import HTTPException
import json

# Initialize Stripe - COMMENTED OUT
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# if not stripe.api_key:
#     print("⚠️  WARNING: STRIPE_SECRET_KEY not configured!")
"""

"""
# ============================================================================
# ENTIRE STRIPE SERVICE COMMENTED OUT - See razorpay_service.py for active code
# ============================================================================

class StripeService:
    """
    Comprehensive Stripe Service for Organization Subscriptions
    
    Features:
    - Create checkout sessions for organizations
    - Handle Stripe webhooks
    - Manage subscriptions (create, update, cancel)
    - Automatic downgrade to free on expiry
    - Organization-level billing
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
    
    async def get_plan_by_name(self, plan_name: str) -> Optional[Dict]:
        """Get plan details from database by name"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT plan_id, name, price_cents, interval, stripe_price_id, 
                       stripe_product_id, llm_priority_tier, features, description
                FROM plans
                WHERE name = $1 AND is_active = true
            """, plan_name)
            
            if not row:
                return None
            
            return dict(row)
    
    async def get_or_create_stripe_customer_for_org(
        self, 
        org_id: int, 
        org_name: str, 
        owner_email: str,
        owner_user_id: Optional[str] = None
    ) -> str:
        """
        Get or create Stripe customer for an organization
        
        Returns:
            Stripe customer ID
        """
        async with self.pool.acquire() as conn:
            # Check if org already has a customer (via owner's stripe_customer_id)
            # For now, we'll create customer per org
            # In the future, you might want org-specific customer
            
            # Get owner's customer ID if available
            owner_customer_id = None
            if owner_user_id:
                owner_row = await conn.fetchrow("""
                    SELECT stripe_customer_id FROM users WHERE id = $1
                """, owner_user_id)
                
                if owner_row and owner_row['stripe_customer_id']:
                    owner_customer_id = owner_row['stripe_customer_id']
            
            # For org billing, create a new customer or reuse owner's
            if owner_customer_id:
                # Reuse owner's customer for simplicity
                # You can create org-specific customers if needed
                return owner_customer_id
            
            # Create new Stripe customer
            stripe_customer = stripe.Customer.create(
                email=owner_email,
                name=org_name,
                metadata={
                    'org_id': str(org_id),
                    'org_name': org_name,
                    'owner_user_id': str(owner_user_id) if owner_user_id else None
                }
            )
            
            # Store customer ID in owner's user record
            if owner_user_id:
                await conn.execute("""
                    UPDATE users
                    SET stripe_customer_id = $1
                    WHERE id = $2
                """, stripe_customer.id, owner_user_id)
            
            return stripe_customer.id
    
    async def create_checkout_session(
        self,
        org_id: int,
        org_name: str,
        plan_name: str,
        owner_email: str,
        owner_user_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict:
        """
        Create Stripe checkout session for organization subscription
        
        Args:
            org_id: Organization ID
            org_name: Organization name
            plan_name: Plan name (free, basic, premium, enterprise)
            owner_email: Owner's email
            owner_user_id: Owner's user ID (optional)
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
        
        Returns:
            Dict with session_id and url
        """
        try:
            # Get plan from database
            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")
            
            if plan['name'] == 'free':
                raise HTTPException(status_code=400, detail="Free plan doesn't require checkout")
            
            if not plan['stripe_price_id']:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Stripe price ID not configured for plan '{plan_name}'. Please set it in the database."
                )
            
            # Get or create Stripe customer
            customer_id = await self.get_or_create_stripe_customer_for_org(
                org_id, org_name, owner_email, owner_user_id
            )
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan['stripe_price_id'],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard?checkout=success",
                cancel_url=cancel_url or f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/pricing?checkout=cancelled",
                metadata={
                    'org_id': str(org_id),
                    'org_name': org_name,
                    'plan_name': plan_name,
                    'plan_id': str(plan['plan_id']),
                    'owner_user_id': str(owner_user_id) if owner_user_id else None,
                },
                subscription_data={
                    'metadata': {
                        'org_id': str(org_id),
                        'org_name': org_name,
                        'plan_name': plan_name,
                        'plan_id': str(plan['plan_id']),
                    }
                },
                allow_promotion_codes=True,
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
            }
            
        except stripe.error.StripeError as e:
            print(f"❌ Stripe error creating checkout: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
        except Exception as e:
            print(f"❌ Error creating checkout session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Stripe webhook events
        
        Events handled:
        - checkout.session.completed: Subscription created
        - customer.subscription.updated: Subscription changed/upgraded/downgraded
        - customer.subscription.deleted: Subscription cancelled
        - invoice.payment_succeeded: Payment successful
        - invoice.payment_failed: Payment failed
        - customer.subscription.trial_will_end: Trial ending soon
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not webhook_secret:
            raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")
        
        event_type = event['type']
        event_data = event['data']['object']
        
        print(f"🔔 Stripe webhook received: {event_type}")
        
        try:
            if event_type == 'checkout.session.completed':
                await self.handle_checkout_completed(event_data)
            
            elif event_type == 'customer.subscription.updated':
                await self.handle_subscription_updated(event_data)
            
            elif event_type == 'customer.subscription.deleted':
                await self.handle_subscription_deleted(event_data)
            
            elif event_type == 'invoice.payment_succeeded':
                await self.handle_payment_succeeded(event_data)
            
            elif event_type == 'invoice.payment_failed':
                await self.handle_payment_failed(event_data)
            
            elif event_type == 'customer.subscription.trial_will_end':
                await self.handle_trial_will_end(event_data)
            
            else:
                print(f"⚠️  Unhandled webhook event type: {event_type}")
            
            return {'status': 'success', 'event_type': event_type}
            
        except Exception as e:
            print(f"❌ Error handling webhook {event_type}: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - return error so Stripe knows we received it
            return {'status': 'error', 'error': str(e), 'event_type': event_type}
    
    async def handle_checkout_completed(self, session: Dict):
        """Handle successful checkout - create subscription record"""
        metadata = session.get('metadata', {})
        org_id = metadata.get('org_id')
        plan_name = metadata.get('plan_name')
        plan_id = metadata.get('plan_id')
        subscription_id = session.get('subscription')
        
        if not org_id or not subscription_id:
            print(f"⚠️  Missing org_id or subscription_id in checkout session")
            return
        
        async with self.pool.acquire() as conn:
            # Get subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get plan if plan_id not in metadata
            if not plan_id and plan_name:
                plan = await self.get_plan_by_name(plan_name)
                if plan:
                    plan_id = plan['plan_id']
            
            if not plan_id:
                print(f"⚠️  Could not find plan_id for plan '{plan_name}'")
                return
            
            # Create or update subscription record
            # Note: subscription_id in DB is stripe_subscription_id
            await conn.execute("""
                INSERT INTO subscriptions (
                    stripe_subscription_id, org_id, plan_id, status,
                    stripe_price_id,
                    current_period_start, current_period_end,
                    amount_cents, currency, interval
                )
                VALUES ($1, $2, $3, $4, $5, 
                        to_timestamp($6), to_timestamp($7), 
                        $8, $9, $10)
                ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                    org_id = EXCLUDED.org_id,
                    plan_id = EXCLUDED.plan_id,
                    status = EXCLUDED.status,
                    stripe_price_id = EXCLUDED.stripe_price_id,
                    current_period_start = EXCLUDED.current_period_start,
                    current_period_end = EXCLUDED.current_period_end,
                    amount_cents = EXCLUDED.amount_cents,
                    currency = EXCLUDED.currency,
                    interval = EXCLUDED.interval,
                    updated_at = NOW()
            """,
                subscription_id,  # stripe_subscription_id
                int(org_id),
                int(plan_id),
                stripe_subscription['status'],
                stripe_subscription['items']['data'][0]['price']['id'],  # stripe_price_id
                stripe_subscription['current_period_start'],
                stripe_subscription['current_period_end'],
                stripe_subscription['items']['data'][0]['price']['unit_amount'],
                stripe_subscription['currency'].upper(),
                stripe_subscription['items']['data'][0]['price']['recurring']['interval'],
            )
            
            # Update organization's subscription_id
            await conn.execute("""
                UPDATE organizations
                SET subscription_id = $1
                WHERE org_id = $2
            """, subscription_id, int(org_id))
            
            print(f"✅ Subscription created for org {org_id}: {plan_name} ({subscription_id})")
    
    async def handle_subscription_updated(self, subscription: Dict):
        """Handle subscription update (plan change, status change, etc.)"""
        subscription_id = subscription['id']
        metadata = subscription.get('metadata', {})
        org_id = metadata.get('org_id')
        plan_name = metadata.get('plan_name')
        
        async with self.pool.acquire() as conn:
            # Get current subscription record
            sub_row = await conn.fetchrow("""
                SELECT org_id, plan_id FROM subscriptions
                WHERE stripe_subscription_id = $1
            """, subscription_id)
            
            if not sub_row:
                print(f"⚠️  Subscription {subscription_id} not found in database")
                return
            
            # Get plan from Stripe price
            price_id = subscription['items']['data'][0]['price']['id']
            plan_row = await conn.fetchrow("""
                SELECT plan_id FROM plans WHERE stripe_price_id = $1
            """, price_id)
            
            if plan_row:
                plan_id = plan_row['plan_id']
            else:
                # Try to get by plan name from metadata
                if plan_name:
                    plan = await self.get_plan_by_name(plan_name)
                    if plan:
                        plan_id = plan['plan_id']
                    else:
                        print(f"⚠️  Could not find plan for name '{plan_name}'")
                        return
                else:
                    print(f"⚠️  Could not find plan for price_id '{price_id}'")
                    return
            
            # Update subscription
            await conn.execute("""
                UPDATE subscriptions
                SET 
                    plan_id = $1,
                    status = $2,
                    stripe_price_id = $3,
                    current_period_start = to_timestamp($4),
                    current_period_end = to_timestamp($5),
                    amount_cents = $6,
                    updated_at = NOW()
                WHERE subscription_id = $7
            """,
                plan_id,
                subscription['status'],
                price_id,
                subscription['current_period_start'],
                subscription['current_period_end'],
                subscription['items']['data'][0]['price']['unit_amount'],
                subscription_id,
            )
            
            print(f"✅ Subscription updated: {subscription_id} -> {subscription['status']}")
    
    async def handle_subscription_deleted(self, subscription: Dict):
        """Handle subscription cancellation - downgrade to free"""
        subscription_id = subscription['id']
        
        async with self.pool.acquire() as conn:
            # Get subscription record
            sub_row = await conn.fetchrow("""
                SELECT org_id, plan_id FROM subscriptions
                WHERE stripe_subscription_id = $1
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
                    cancelled_at = NOW(),
                    updated_at = NOW()
                WHERE stripe_subscription_id = $2
            """, free_plan['plan_id'], subscription_id)
            
            # Update organization to remove subscription reference
            if sub_row['org_id']:
                await conn.execute("""
                    UPDATE organizations
                    SET subscription_id = NULL
                    WHERE org_id = $1
                """, sub_row['org_id'])
            
            print(f"❌ Subscription cancelled: {subscription_id}")
    
    async def handle_payment_succeeded(self, invoice: Dict):
        """Handle successful payment"""
        subscription_id = invoice.get('subscription')
        print(f"✅ Payment succeeded for subscription: {subscription_id}")
    
    async def handle_payment_failed(self, invoice: Dict):
        """Handle failed payment"""
        subscription_id = invoice.get('subscription')
        print(f"❌ Payment failed for subscription: {subscription_id}")
        
        # Optionally: Send notification email, update subscription status
    
    async def handle_trial_will_end(self, subscription: Dict):
        """Handle trial ending soon"""
        subscription_id = subscription['id']
        print(f"⚠️  Trial ending soon for subscription: {subscription_id}")
        # Optionally: Send notification email
    
    async def get_subscription_for_org(self, org_id: int) -> Optional[Dict]:
        """Get subscription details for an organization"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    s.stripe_subscription_id as subscription_id,
                    s.org_id,
                    s.plan_id,
                    s.status,
                    s.current_period_start,
                    s.current_period_end,
                    s.amount_cents,
                    s.currency,
                    s.interval,
                    p.name as plan_name,
                    p.price_cents,
                    p.features,
                    o.org_name
                FROM subscriptions s
                JOIN plans p ON s.plan_id = p.plan_id
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
            
            return dict(row)
    
    async def cancel_subscription(self, org_id: int) -> Dict:
        """Cancel organization's subscription"""
        async with self.pool.acquire() as conn:
            # Get active subscription
            sub_row = await conn.fetchrow("""
                SELECT stripe_subscription_id
                FROM subscriptions
                WHERE org_id = $1
                AND status IN ('active', 'trialing')
                ORDER BY created_at DESC
                LIMIT 1
            """, org_id)
            
            if not sub_row:
                raise HTTPException(status_code=404, detail="No active subscription found")
            
            stripe_subscription_id = sub_row['stripe_subscription_id']
            
            if not stripe_subscription_id:
                # Subscription not in Stripe, just cancel in DB
                await conn.execute("""
                    UPDATE subscriptions
                    SET status = 'canceled', cancelled_at = NOW()
                    WHERE org_id = $1 AND stripe_subscription_id IS NULL
                """, org_id)
            else:
                # Cancel in Stripe (will cancel at period end)
                stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
                
                # Update database
                await conn.execute("""
                    UPDATE subscriptions
                    SET 
                        cancel_at_period_end = true,
                        updated_at = NOW()
                    WHERE stripe_subscription_id = $1
                """, stripe_subscription_id)
            
            return {'status': 'cancelled', 'message': 'Subscription will cancel at period end'}
    
    async def get_billing_portal_url(self, org_id: int, return_url: str) -> str:
        """Get Stripe billing portal URL for organization"""
        async with self.pool.acquire() as conn:
            # Get org's subscription
            sub_row = await conn.fetchrow("""
                SELECT s.stripe_subscription_id, o.owner_user_id
                FROM subscriptions s
                JOIN organizations o ON s.org_id = o.org_id
                WHERE s.org_id = $1
                AND s.status IN ('active', 'trialing')
                LIMIT 1
            """, org_id)
            
            if not sub_row:
                raise HTTPException(status_code=404, detail="No active subscription found")
            
            # Get customer ID from owner
            owner_row = await conn.fetchrow("""
                SELECT stripe_customer_id FROM users WHERE id = $1
            """, sub_row['owner_user_id'])
            
            if not owner_row or not owner_row['stripe_customer_id']:
                raise HTTPException(status_code=404, detail="Stripe customer not found")
            
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=owner_row['stripe_customer_id'],
                return_url=return_url,
            )
            
            return session.url
    
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
                SELECT stripe_subscription_id, org_id
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
                        status = 'expired',
                        updated_at = NOW()
                    WHERE stripe_subscription_id = $2
                """, free_plan['plan_id'], sub['stripe_subscription_id'])
                
                # Update organization
                if sub['org_id']:
                    await conn.execute("""
                        UPDATE organizations
                        SET subscription_id = NULL
                        WHERE org_id = $1
                    """, sub['org_id'])
                
                print(f"✅ Downgraded expired subscription {sub['stripe_subscription_id']} to free")
    
    async def get_all_plans(self) -> List[Dict]:
        """Get all active plans"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT plan_id, name, price_cents, interval, stripe_price_id,
                       llm_priority_tier, features, description
                FROM plans
                WHERE is_active = true
                ORDER BY llm_priority_tier, price_cents
            """)
            
            return [dict(row) for row in rows]
