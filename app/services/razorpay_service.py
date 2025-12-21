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
from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from fastapi import HTTPException
import json
import time

from app.models.subscription import SubscriptionPlanConfig as Plan
from app.models.user import User
from app.models.subscription import Subscription

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
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.client = razorpay_client
    
    async def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        """Get plan details from database by name, ensuring defaults exist."""
        # First, ensure the default plans are in the database.
        # The ON CONFLICT clause in the SQL makes this safe to run every time.
        await self._ensure_default_plans()

        # Now, attempt to fetch the requested plan.
        stmt = select(Plan).where(Plan.name.ilike(plan_name), Plan.is_active == True)
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            print(f"⚠️ Plan '{plan_name}' not found in the database.")
            return None

        return plan
    
    async def _ensure_default_plans(self):
        """Ensure default plans exist in the database using SQLAlchemy.
        Note: ON CONFLICT is PostgreSQL-specific and is handled via raw SQL within the session.
        """
        try:
            # Using text() for the raw SQL with ON CONFLICT clause
            sql = text("""
                INSERT INTO subscription_plans (name, display_name, price_monthly, max_repositories, max_docs_per_month, is_active)
                VALUES
                    ('free', 'Free', 0, 1, 100, true),
                    ('pro', 'Pro', 29, -1, 1000, true),
                    ('enterprise', 'Enterprise', 99, -1, -1, true)
                ON CONFLICT (name) DO NOTHING;
            """)
            await self.db.execute(sql)
            await self.db.commit()
            print("✅ Default plans checked/inserted.")
        except Exception as e:
            print(f"❌ Error inserting default plans: {e}")
            await self.db.rollback()
            import traceback
            traceback.print_exc()
    
    async def get_or_create_razorpay_customer(
        self,
        user_id: str,
        user_email: str,
        user_name: Optional[str] = None,
        user_phone: Optional[str] = None,
    ) -> Optional[str]:
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")

        stmt = select(User.razorpay_customer_id).where(User.id == user_id)
        result = await self.db.execute(stmt)
        customer_id = result.scalar_one_or_none()

        if customer_id:
            return customer_id

        try:
            customer_data = {
                "name": user_name or user_email.split("@")[0],
                "email": user_email,
                "contact": user_phone or "9999999999",
                "notes": {"user_id": str(user_id), "user_email": user_email},
            }
            razorpay_customer = self.client.customer.create(customer_data)
            customer_id = razorpay_customer["id"]

            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(razorpay_customer_id=customer_id)
            )
            await self.db.execute(stmt)
            await self.db.commit()

            return customer_id
        except razorpay.errors.BadRequestError as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "exists" in error_msg:
                print(f"ℹ️ Customer with email {user_email} already exists in Razorpay.")
            else:
                print(f"⚠️ Razorpay customer creation failed: {e}.")
            return None
        except Exception as e:
            print(f"⚠️ Error creating Razorpay customer: {e}.")
            return None
    
    async def create_order(
        self,
        user_id: str,
        user_email: str,
        plan_name: str,
        user_name: Optional[str] = None,
    ) -> Dict:
        if not self.client:
            raise HTTPException(status_code=500, detail="Razorpay client not initialized")

        try:
            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found.")

            if plan.name == "free":
                raise HTTPException(status_code=400, detail="Free plan doesn't require payment")

            customer_id = await self.get_or_create_razorpay_customer(
                user_id, user_email, user_name
            )

            amount_paise = int(plan.price_monthly * 100)
            receipt_hash = hashlib.md5(
                f"{user_id}{int(time.time())}".encode()
            ).hexdigest()[:16]
            receipt = f"{plan_name[:4]}_{receipt_hash}"

            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "user_id": str(user_id),
                    "user_email": user_email,
                    "plan_name": plan_name,
                    "plan_id": str(plan.id),
                },
            }

            razorpay_order = self.client.order.create(order_data)

            return {
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "key_id": RAZORPAY_KEY_ID,
                "customer_id": customer_id,
                "metadata": {
                    "user_id": str(user_id),
                    "user_email": user_email,
                    "user_name": user_name,
                    "plan_name": plan_name,
                    "plan_id": str(plan.id),
                },
            }
        except razorpay.errors.BadRequestError as e:
            print(f"❌ Razorpay error creating order: {e}")
            raise HTTPException(status_code=500, detail=f"Razorpay error: {e}")
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
        order_id = payment.get("order_id")
        if not order_id:
            print("⚠️ No order_id in payment")
            return

        try:
            razorpay_order = self.client.order.fetch(order_id)
            notes = razorpay_order.get("notes", {})
            user_id = notes.get("user_id")
            user_email = notes.get("user_email")
            plan_name = notes.get("plan_name")

            if not all([user_id, user_email, plan_name]):
                print(f"⚠️ Missing user_id, user_email, or plan_name in order notes for order {order_id}")
                return

            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                return

            razorpay_payment_id = payment.get("id")
            if not razorpay_payment_id:
                print("⚠️ No payment ID in payment object")
                return

            period_start = datetime.now()
            period_end = period_start + timedelta(days=30)

            # Check for an existing subscription for the user
            stmt = select(Subscription).where(Subscription.user_id == user_id)
            result = await self.db.execute(stmt)
            subscription = result.scalar_one_or_none()

            if subscription:
                # Update existing subscription
                subscription.plan_id = plan.id
                subscription.plan = plan_name
                subscription.status = "active"
                subscription.razorpay_order_id = order_id
                subscription.razorpay_payment_id = razorpay_payment_id
                subscription.razorpay_customer_id = payment.get("customer_id")
                subscription.current_period_start = period_start
                subscription.current_period_end = period_end
                subscription.amount_cents = payment.get("amount")
                subscription.currency = payment.get("currency", "INR").upper()
                subscription.interval = "month"
            else:
                # Create new subscription
                new_subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan.id,
                    plan=plan_name,
                    status="active",
                    razorpay_order_id=order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_customer_id=payment.get("customer_id"),
                    current_period_start=period_start,
                    current_period_end=period_end,
                    amount_cents=payment.get("amount"),
                    currency=payment.get("currency", "INR").upper(),
                    interval="month",
                )
                self.db.add(new_subscription)
            
            await self.db.commit()

            print(f"✅ Payment captured for user {user_id} ({user_email}): {plan_name}")

        except Exception as e:
            print(f"❌ Error processing payment capture: {e}")
            await self.db.rollback()
    
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
    
    async def handle_subscription_cancelled(self, subscription_data: Dict):
        subscription_id = subscription_data.get("id")
        if not subscription_id:
            return

        stmt = select(Subscription).where(Subscription.razorpay_subscription_id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            print(f"⚠️ Subscription {subscription_id} not found")
            return

        free_plan = await self.get_plan_by_name("free")
        if not free_plan:
            return

        subscription.status = "canceled"
        subscription.plan_id = free_plan.id
        subscription.plan = "free"
        subscription.cancelled_at = datetime.now()
        
        await self.db.commit()
        print(f"❌ Subscription cancelled for user {subscription.user_id}: {subscription_id}")
    
    async def get_subscription_for_org(self, org_id: int) -> Optional[Dict]:
        """Get subscription details for an organization"""
        stmt = (
            select(
                Subscription.id.label("subscription_id"),
                Subscription.org_id,
                Subscription.plan_id,
                Subscription.plan.label("plan_name"),
                Subscription.status,
                Subscription.razorpay_order_id,
                Subscription.razorpay_payment_id,
                Subscription.current_period_start,
                Subscription.current_period_end,
                Subscription.amount_cents,
                Subscription.currency,
                Subscription.interval,
                Plan.name.label("plan_name_db"),
                Plan.price_cents,
                Plan.features,
            )
            .join(Plan, Subscription.plan_id == Plan.id, isouter=True)
            .where(Subscription.org_id == org_id, Subscription.status.in_(["active", "trialing"]))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.mappings().first()

        if not row:
            free_plan = await self.get_plan_by_name("free")
            if free_plan:
                return {
                    "plan_name": "free",
                    "plan_id": free_plan.id,
                    "status": "active",
                    "features": free_plan.features,
                    "price_cents": 0,
                }
            return None

        return dict(row)
    
    async def cancel_subscription(self, org_id: int) -> Dict:
        stmt = (
            select(Subscription)
            .where(Subscription.org_id == org_id, Subscription.status.in_(["active", "trialing"]))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")

        subscription.status = "canceled"
        subscription.cancelled_at = datetime.now()
        await self.db.commit()

        return {"status": "cancelled", "message": "Subscription cancelled successfully"}
    
    async def downgrade_expired_subscriptions(self):
        free_plan = await self.get_plan_by_name("free")
        if not free_plan:
            print("⚠️ Free plan not found")
            return

        stmt = (
            update(Subscription)
            .where(
                Subscription.status.in_(["active", "trialing"]),
                Subscription.current_period_end < datetime.now(),
            )
            .values(plan_id=free_plan.id, plan="free", status="expired")
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            print(f"✅ Downgraded {result.rowcount} expired subscriptions to free")
    
    async def get_all_plans(self) -> List[Plan]:
        stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.price_cents)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
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

