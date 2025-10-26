"""
Stripe Integration Service
Handles payments, subscriptions, and webhooks
"""

import os
import stripe
from typing import Dict, Optional
from datetime import datetime
import asyncpg
from fastapi import HTTPException

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Stripe Price IDs (create these in Stripe Dashboard)
STRIPE_PRICES = {
    "free": None,  # No payment needed
    "pro": os.getenv("STRIPE_PRICE_PRO"),  # $29/month
    "team": os.getenv("STRIPE_PRICE_TEAM"),  # $99/month
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),  # $499/month
}

class StripeService:
    """
    Stripe Service - Handle payments and subscriptions
    
    Features:
    - Create checkout sessions
    - Handle webhooks
    - Manage subscriptions
    - Track usage
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        plan: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """
        Create Stripe checkout session
        
        Args:
            user_id: User ID
            user_email: User email
            plan: Plan name (pro, team, enterprise)
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
        
        Returns: Checkout session data
        """
        try:
            if plan not in STRIPE_PRICES or not STRIPE_PRICES[plan]:
                raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")
            
            # Create Stripe customer if doesn't exist
            customer = await self.get_or_create_customer(user_id, user_email)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer['stripe_customer_id'],
                payment_method_types=['card'],
                line_items=[{
                    'price': STRIPE_PRICES[plan],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'plan': plan,
                },
                subscription_data={
                    'metadata': {
                        'user_id': user_id,
                        'plan': plan,
                    }
                }
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
            }
            
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_or_create_customer(self, user_id: str, user_email: str) -> Dict:
        """Get existing Stripe customer or create new one"""
        async with self.pool.acquire() as conn:
            # Check if customer exists
            customer = await conn.fetchrow("""
                SELECT stripe_customer_id FROM users
                WHERE id = $1
            """, user_id)
            
            if customer and customer['stripe_customer_id']:
                return {'stripe_customer_id': customer['stripe_customer_id']}
            
            # Create new Stripe customer
            stripe_customer = stripe.Customer.create(
                email=user_email,
                metadata={'user_id': user_id}
            )
            
            # Store customer ID
            await conn.execute("""
                UPDATE users
                SET stripe_customer_id = $1
                WHERE id = $2
            """, stripe_customer.id, user_id)
            
            return {'stripe_customer_id': stripe_customer.id}
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Stripe webhook events
        
        Events:
        - checkout.session.completed: Subscription created
        - customer.subscription.updated: Subscription changed
        - customer.subscription.deleted: Subscription cancelled
        - invoice.payment_succeeded: Payment successful
        - invoice.payment_failed: Payment failed
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            await self.handle_checkout_completed(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.updated':
            await self.handle_subscription_updated(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.deleted':
            await self.handle_subscription_deleted(event['data']['object'])
        
        elif event['type'] == 'invoice.payment_succeeded':
            await self.handle_payment_succeeded(event['data']['object'])
        
        elif event['type'] == 'invoice.payment_failed':
            await self.handle_payment_failed(event['data']['object'])
        
        return {'status': 'success'}
    
    async def handle_checkout_completed(self, session: Dict):
        """Handle successful checkout"""
        user_id = session['metadata']['user_id']
        plan = session['metadata']['plan']
        subscription_id = session['subscription']
        
        async with self.pool.acquire() as conn:
            # Create subscription record
            await conn.execute("""
                INSERT INTO subscriptions (
                    user_id, plan, status, stripe_subscription_id,
                    current_period_start, current_period_end
                ) VALUES ($1, $2, 'active', $3, NOW(), NOW() + INTERVAL '1 month')
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    plan = $2,
                    status = 'active',
                    stripe_subscription_id = $3,
                    current_period_start = NOW(),
                    current_period_end = NOW() + INTERVAL '1 month'
            """, user_id, plan, subscription_id)
        
        print(f"✅ Subscription created for user {user_id}: {plan}")
    
    async def handle_subscription_updated(self, subscription: Dict):
        """Handle subscription update"""
        stripe_sub_id = subscription['id']
        status = subscription['status']
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE subscriptions
                SET status = $1,
                    current_period_start = to_timestamp($2),
                    current_period_end = to_timestamp($3)
                WHERE stripe_subscription_id = $4
            """, status, subscription['current_period_start'],
                subscription['current_period_end'], stripe_sub_id)
        
        print(f"✅ Subscription updated: {stripe_sub_id} -> {status}")
    
    async def handle_subscription_deleted(self, subscription: Dict):
        """Handle subscription cancellation"""
        stripe_sub_id = subscription['id']
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE subscriptions
                SET status = 'cancelled',
                    cancelled_at = NOW()
                WHERE stripe_subscription_id = $1
            """, stripe_sub_id)
        
        print(f"❌ Subscription cancelled: {stripe_sub_id}")
    
    async def handle_payment_succeeded(self, invoice: Dict):
        """Handle successful payment"""
        print(f"✅ Payment succeeded: {invoice['id']}")
    
    async def handle_payment_failed(self, invoice: Dict):
        """Handle failed payment"""
        print(f"❌ Payment failed: {invoice['id']}")
        
        # Optionally: Send email notification, update subscription status
    
    async def cancel_subscription(self, user_id: str) -> Dict:
        """Cancel user's subscription"""
        async with self.pool.acquire() as conn:
            subscription = await conn.fetchrow("""
                SELECT stripe_subscription_id FROM subscriptions
                WHERE user_id = $1 AND status = 'active'
            """, user_id)
            
            if not subscription:
                raise HTTPException(status_code=404, detail="No active subscription")
            
            # Cancel in Stripe
            stripe.Subscription.delete(subscription['stripe_subscription_id'])
            
            # Update database
            await conn.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', cancelled_at = NOW()
                WHERE user_id = $1
            """, user_id)
            
            return {'status': 'cancelled'}
    
    async def get_billing_portal_url(self, user_id: str, return_url: str) -> str:
        """Get Stripe billing portal URL for customer"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT stripe_customer_id FROM users WHERE id = $1
            """, user_id)
            
            if not user or not user['stripe_customer_id']:
                raise HTTPException(status_code=404, detail="Customer not found")
            
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=user['stripe_customer_id'],
                return_url=return_url,
            )
            
            return session.url


# FastAPI endpoints
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Stripe Service", version="1.0.0")
stripe_service = None

class CreateCheckoutRequest(BaseModel):
    user_id: str
    user_email: str
    plan: str
    success_url: str
    cancel_url: str

@app.on_event("startup")
async def startup():
    global stripe_service
    db_url = os.getenv("DATABASE_URL")
    stripe_service = StripeService(db_url)
    await stripe_service.init_db()
    print("✅ Stripe Service started")

@app.post("/stripe/create-checkout")
async def create_checkout(request: CreateCheckoutRequest):
    """Create Stripe checkout session"""
    session = await stripe_service.create_checkout_session(
        request.user_id,
        request.user_email,
        request.plan,
        request.success_url,
        request.cancel_url
    )
    return session

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    signature = request.headers.get('stripe-signature')
    
    result = await stripe_service.handle_webhook(payload, signature)
    return result

@app.post("/stripe/cancel-subscription")
async def cancel_subscription(user_id: str):
    """Cancel user's subscription"""
    result = await stripe_service.cancel_subscription(user_id)
    return result

@app.get("/stripe/billing-portal")
async def get_billing_portal(user_id: str, return_url: str):
    """Get billing portal URL"""
    url = await stripe_service.get_billing_portal_url(user_id, return_url)
    return {'url': url}
