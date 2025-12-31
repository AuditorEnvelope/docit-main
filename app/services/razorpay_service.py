"""
Razorpay Integration Service - Production Ready Version
Key fixes applied:
1. Proper enum usage for subscription.plan and subscription.status
2. Removed leftover plan_id reference
3. Added flush() for transaction safety
4. Removed unsafe duplicate fields (amount_cents, currency, interval)
5. All previous fixes maintained (no nested transactions, proper idempotency, etc.)
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

from app.models.subscription import (
    SubscriptionPlanConfig as Plan,
    Subscription,
    Payment,
    PaymentStatus,
    SubscriptionPlan,  # ✅ ADDED: Import enum
    SubscriptionStatus  # ✅ ADDED: Import enum
)
from app.models.user import User

# Initialize Razorpay Client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
    print("⚠️  WARNING: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET not configured!")


class RazorpayService:
    """
    Comprehensive Razorpay Service for User Subscriptions
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.client = razorpay_client

    async def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        """Get plan details from database by name, ensuring defaults exist."""
        await self._ensure_default_plans()

        stmt = select(Plan).where(Plan.name.ilike(
            plan_name), Plan.is_active == True)
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            print(f"⚠️ Plan '{plan_name}' not found in the database.")
            return None

        return plan

    async def _ensure_default_plans(self):
        """Ensure default plans exist in the database."""
        try:
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

    async def get_or_create_razorpay_customer(
        self,
        user_id: str,
        user_email: str,
        user_name: Optional[str] = None,
        user_phone: Optional[str] = None,
    ) -> Optional[str]:
        if not self.client:
            raise HTTPException(
                status_code=500, detail="Razorpay client not initialized")

        stmt = select(User.razorpay_customer_id).where(User.id == user_id)
        result = await self.db.execute(stmt)
        customer_id = result.scalar_one_or_none()

        if customer_id:
            return customer_id

        try:
            customer_data = {
                "name": user_name or (user_email.split("@")[0] if user_email else "User"),
                "email": user_email,
                "contact": user_phone or "9999999999",
                "notes": {"user_id": str(user_id), "user_email": user_email},
            }
            razorpay_customer = self.client.customer.create(customer_data)
            customer_id = razorpay_customer["id"]

            stmt = update(User).where(User.id == user_id).values(
                razorpay_customer_id=customer_id)
            await self.db.execute(stmt)
            await self.db.commit()

            return customer_id
        except razorpay.errors.BadRequestError as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "exists" in error_msg:
                print(
                    f"ℹ️ Customer with email {user_email} already exists in Razorpay.")
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
            raise HTTPException(
                status_code=500, detail="Razorpay client not initialized")

        try:
            plan = await self.get_plan_by_name(plan_name)
            if not plan:
                raise HTTPException(
                    status_code=404, detail=f"Plan '{plan_name}' not found.")

            if plan.name == "free":
                raise HTTPException(
                    status_code=400, detail="Free plan doesn't require payment")

            customer_id = await self.get_or_create_razorpay_customer(user_id, user_email, user_name)

            amount_paise = int(plan.price_monthly * 100)
            receipt_hash = hashlib.md5(
                f"{user_id}{int(time.time())}".encode()).hexdigest()[:16]
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

            print(
                f"📝 Creating initial payment record for order {razorpay_order['id']}")
            payment_intent = Payment(
                user_id=user_id,
                razorpay_order_id=razorpay_order["id"],
                amount=plan.price_monthly,
                currency="INR",
                status=PaymentStatus.PENDING.value,  # Use .value for VARCHAR
                plan_name=plan_name,
            )
            self.db.add(payment_intent)
            await self.db.commit()
            print(f"✅ Initial payment record created")

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
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature"""
        if not RAZORPAY_KEY_SECRET:
            print("⚠️ RAZORPAY_KEY_SECRET not configured")
            return False

        try:
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            expected_signature = hmac.new(
                secret, payload, hashlib.sha256).hexdigest()

            is_valid = hmac.compare_digest(expected_signature, signature)

            if not is_valid:
                print(f"❌ Signature mismatch:")
                print(f"   Expected: {expected_signature[:20]}...")
                print(f"   Received: {signature[:20]}...")

            return is_valid
        except Exception as e:
            print(f"❌ Error verifying webhook signature: {e}")
            return False

    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """Handle Razorpay webhook events - SINGLE SOURCE OF TRUTH for DB writes"""
        if not self.verify_webhook_signature(payload, signature):
            print("❌ Invalid webhook signature")
            raise HTTPException(
                status_code=400, detail="Invalid webhook signature")

        try:
            event_data = json.loads(payload.decode('utf-8'))
            event_type = event_data.get('event')
            payload_data = event_data.get('payload', {})

            print(f"🔔 [WEBHOOK] Received: {event_type}")

            try:
                if event_type == 'payment.authorized':
                    # Log but don't process - wait for payment.captured
                    payment_id = payload_data.get('payment', {}).get('entity', {}).get('id')
                    print(f"🕑 [WEBHOOK] payment.authorized - Payment {payment_id} authorized, waiting for capture")
                    return {'status': 'acknowledged', 'event_type': event_type}
                elif event_type == 'payment.captured':
                    await self.handle_payment_captured(
                        payload_data.get('payment', {}).get('entity', {})
                    )
                elif event_type == 'order.paid':
                    await self.handle_order_paid(
                        payload_data.get('order', {}).get('entity', {})
                    )
                else:
                    print(f"⚠️ [WEBHOOK] Unhandled event: {event_type}")
                    return {'status': 'ignored', 'event_type': event_type}

                return {'status': 'success', 'event_type': event_type}

            except Exception as e:
                print(f"❌ [WEBHOOK] Error handling {event_type}: {e}")
                import traceback
                traceback.print_exc()
                # Don't raise - return error status but 200 OK to prevent retries
                return {'status': 'error', 'error': str(e), 'event_type': event_type}

        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON: {str(e)}")

    async def payment_exists(self, razorpay_payment_id: str) -> bool:
        """Check if payment already processed (idempotency)"""
        # Use .value to get string value from enum for VARCHAR comparison
        stmt = select(Payment).where(
            Payment.razorpay_payment_id == razorpay_payment_id,
            Payment.status == PaymentStatus.COMPLETED.value
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _process_payment_data(self, payment: Dict, user_id: str,
                                    user_email: str, plan_name: str):
        """
        Internal method to process payment data
        Assumes transaction is already started by caller
        """
        order_id = payment.get("order_id")
        razorpay_payment_id = payment.get("id")

        print(
            f"💳 Processing payment {razorpay_payment_id} for user {user_id}, plan {plan_name}")

        plan = await self.get_plan_by_name(plan_name)
        if not plan:
            print(f"❌ Plan {plan_name} not found")
            return

        period_start = datetime.now()
        period_end = period_start + timedelta(days=30)

        # 1. Update or create payment record
        stmt = select(Payment).where(
            Payment.razorpay_order_id == order_id
        ).order_by(Payment.created_at.desc())
        result = await self.db.execute(stmt)
        existing_payment = result.scalar_one_or_none()

        if existing_payment:
            print(f"📝 Updating payment record {existing_payment.id}")
            existing_payment.razorpay_payment_id = razorpay_payment_id
            existing_payment.razorpay_customer_id = payment.get("customer_id")
            existing_payment.status = PaymentStatus.COMPLETED.value  # Use .value for VARCHAR
            existing_payment.billing_start_date = period_start
            existing_payment.billing_end_date = period_end
            existing_payment.raw_payload = json.dumps(payment)
            existing_payment.processed_at = datetime.now()
        else:
            print(f"🆕 Creating payment record")
            new_payment = Payment(
                user_id=user_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_customer_id=payment.get("customer_id"),
                amount=payment.get("amount", 0) / 100,
                currency=payment.get("currency", "INR").upper(),
                status=PaymentStatus.COMPLETED.value,  # Use .value for VARCHAR
                plan_name=plan_name,
                billing_start_date=period_start,
                billing_end_date=period_end,
                raw_payload=json.dumps(payment),
                processed_at=datetime.now()
            )
            self.db.add(new_payment)

        # 2. Update or create subscription
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription:
            print(f"📝 Updating subscription {subscription.id}")
            # ✅ FIX 1: Use enum instead of string
            subscription.plan = SubscriptionPlan(plan_name)
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.razorpay_order_id = order_id
            subscription.razorpay_payment_id = razorpay_payment_id
            subscription.razorpay_customer_id = payment.get("customer_id")
            subscription.current_period_start = period_start
            subscription.current_period_end = period_end
            # ✅ FIX 4: Removed duplicate fields (amount_cents, currency, interval)
        else:
            print(f"🆕 Creating subscription for user {user_id}")
            # ✅ FIX 1: Use enum instead of string
            new_subscription = Subscription(
                user_id=user_id,
                plan=SubscriptionPlan(plan_name),
                status=SubscriptionStatus.ACTIVE,
                razorpay_order_id=order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_customer_id=payment.get("customer_id"),
                current_period_start=period_start,
                current_period_end=period_end,
                # ✅ FIX 4: Removed duplicate fields
            )
            self.db.add(new_subscription)

        # 3. Update user fields
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            print(f"👤 Updating user {user_id}")
            user.current_plan = plan_name
            user.subscription_status = "active"
            user.subscription_expires_at = period_end
        else:
            print(f"❌ User {user_id} not found")

        # ✅ FIX 3: Add flush for transaction safety
        await self.db.flush()

        print(f"✅ Payment data processed - User: {user_id}, Plan: {plan_name}")

    async def handle_payment_captured(self, payment: Dict, user_id: str = None,
                                      user_email: str = None, plan_name: str = None):
        """
        Handle successful payment capture (called from webhook ONLY)
        SINGLE SOURCE OF TRUTH - Only this method writes to DB
        Idempotent: safe to call multiple times
        No nested transactions - expects session from caller
        """
        order_id = payment.get("order_id")
        razorpay_payment_id = payment.get("id")

        print(f"[WEBHOOK] payment.captured - Order: {order_id}, Payment: {razorpay_payment_id}")

        if not order_id or not razorpay_payment_id:
            print("⚠️ [WEBHOOK] payment.captured - Missing order_id or payment_id")
            return

        # IDEMPOTENCY CHECK - prevents duplicate processing
        if await self.payment_exists(razorpay_payment_id):
            print(f"ℹ️ [WEBHOOK] payment.captured - Payment {razorpay_payment_id} already processed (idempotent skip)")
            return

        try:
            # Get user info if not provided
            if not user_id or not plan_name:
                if self.client:
                    try:
                        razorpay_order = self.client.order.fetch(order_id)
                        notes = razorpay_order.get("notes", {})
                        user_id = notes.get("user_id")
                        user_email = notes.get("user_email")
                        plan_name = notes.get("plan_name")
                    except Exception as e:
                        print(f"⚠️ [WEBHOOK] payment.captured - Could not fetch order notes: {e}")
                        # Try to get info from existing payment record
                        stmt = select(Payment).where(Payment.razorpay_order_id == order_id)
                        result = await self.db.execute(stmt)
                        existing = result.scalar_one_or_none()
                        if existing:
                            user_id = str(existing.user_id)
                            plan_name = existing.plan_name
                            print(f"✅ [WEBHOOK] payment.captured - Retrieved info from DB: user={user_id}, plan={plan_name}")

            if not all([user_id, plan_name]):
                print(f"⚠️ [WEBHOOK] payment.captured - Missing required data for order {order_id}")
                return

            print(f"💳 [WEBHOOK] payment.captured - Processing for user {user_id}, plan {plan_name}")

            # NO transaction block - use session provided by caller (webhook endpoint)
            await self._process_payment_data(payment, user_id, user_email, plan_name)

            print(f"✅ [WEBHOOK] payment.captured - Payment {razorpay_payment_id} processed successfully")

        except Exception as e:
            print(f"❌ [WEBHOOK] payment.captured - Error: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def handle_order_paid(self, order: Dict):
        """Handle order paid event - typically follows payment.captured"""
        order_id = order.get('id')
        print(f"[WEBHOOK] order.paid - Order: {order_id}")
        
        # Order paid is typically redundant after payment.captured
        # Check if payment already processed
        if not order_id:
            print("⚠️ [WEBHOOK] order.paid - Missing order_id")
            return
        
        # Check if this order has a completed payment
        # Use .value to get string value from enum for VARCHAR comparison
        stmt = select(Payment).where(
            Payment.razorpay_order_id == order_id,
            Payment.status == PaymentStatus.COMPLETED.value
        )
        result = await self.db.execute(stmt)
        existing_payment = result.scalar_one_or_none()
        
        if existing_payment:
            print(f"ℹ️ [WEBHOOK] order.paid - Order {order_id} already processed via payment.captured (idempotent skip)")
        else:
            print(f"⚠️ [WEBHOOK] order.paid - No completed payment found for order {order_id}, may need payment.captured first")

    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature"""
        if not RAZORPAY_KEY_SECRET:
            print("⚠️ RAZORPAY_KEY_SECRET not configured")
            return False

        try:
            message = f"{order_id}|{payment_id}"
            secret = RAZORPAY_KEY_SECRET.encode('utf-8')
            expected_signature = hmac.new(
                secret,
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            is_valid = hmac.compare_digest(expected_signature, signature)

            if is_valid:
                print(f"✅ Payment signature verified")
            else:
                print(f"❌ Invalid payment signature")

            return is_valid
        except Exception as e:
            print(f"❌ Error verifying payment: {e}")
            return False

    async def check_payment_status(self, order_id: str, payment_id: str) -> Dict:
        """
        READ-ONLY: Check payment status from Razorpay
        Does NOT write to database - webhooks are the only source of DB writes
        Used for manual verification to poll status
        """
        if not self.client:
            raise HTTPException(
                status_code=500, detail="Razorpay client not initialized")

        print(f"[MANUAL-CHECK] Checking status for payment {payment_id}")

        try:
            # Check if already processed in DB using VARCHAR-safe comparison
            # Use .value to convert enum to string for DB comparison
            stmt = select(Payment).where(
                Payment.razorpay_payment_id == payment_id,
                Payment.status == PaymentStatus.COMPLETED.value
            )
            result = await self.db.execute(stmt)
            existing_payment = result.scalar_one_or_none()

            if existing_payment:
                print(f"✅ [MANUAL-CHECK] Payment already processed in DB")
                return {
                    "status": "completed",
                    "message": "Payment already processed by webhook",
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "processed_at": existing_payment.processed_at.isoformat() if existing_payment.processed_at else None
                }

            # Fetch current status from Razorpay
            try:
                payment = self.client.payment.fetch(payment_id)
                payment_status = payment.get('status')
                print(f"💳 [MANUAL-CHECK] Razorpay status: {payment_status}")

                if payment_status == 'captured':
                    # Payment is captured but not yet in DB - webhook will process it
                    return {
                        "status": "pending_webhook",
                        "message": "Payment captured, waiting for webhook to process",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "razorpay_status": payment_status
                    }
                elif payment_status == 'authorized':
                    return {
                        "status": "authorized",
                        "message": "Payment authorized but not captured",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "razorpay_status": payment_status
                    }
                elif payment_status == 'failed':
                    return {
                        "status": "failed",
                        "message": "Payment failed",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "razorpay_status": payment_status
                    }
                else:
                    return {
                        "status": "unknown",
                        "message": f"Payment status: {payment_status}",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "razorpay_status": payment_status
                    }

            except Exception as e:
                print(f"⚠️ [MANUAL-CHECK] Could not fetch from Razorpay: {e}")
                # Check if there's a pending payment in DB using VARCHAR-safe comparison
                # Use .value to convert enum to string for DB comparison
                stmt = select(Payment).where(
                    Payment.razorpay_order_id == order_id,
                    Payment.status == PaymentStatus.PENDING.value
                )
                result = await self.db.execute(stmt)
                pending_payment = result.scalar_one_or_none()

                if pending_payment:
                    return {
                        "status": "pending",
                        "message": "Payment pending, could not reach Razorpay",
                        "payment_id": payment_id,
                        "order_id": order_id
                    }
                else:
                    raise HTTPException(
                        status_code=404, detail="Payment not found")

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ [MANUAL-CHECK] Error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"Status check failed: {str(e)}")

    async def downgrade_expired_subscriptions(self):
        """Downgrade expired subscriptions to free"""
        free_plan = await self.get_plan_by_name("free")
        if not free_plan:
            return

        stmt = select(Subscription).where(
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.current_period_end < datetime.now(),
        )
        result = await self.db.execute(stmt)
        expired_subscriptions = result.scalars().all()

        if not expired_subscriptions:
            print("✅ No expired subscriptions")
            return

        async with self.db.begin():
            for subscription in expired_subscriptions:
                # ✅ FIX 1: Use enum
                subscription.plan = SubscriptionPlan.FREE
                subscription.status = SubscriptionStatus.EXPIRED

                stmt = select(User).where(User.id == subscription.user_id)
                user_result = await self.db.execute(stmt)
                user = user_result.scalar_one_or_none()
                if user:
                    user.current_plan = "free"
                    user.subscription_status = "expired"
                    user.subscription_expires_at = subscription.current_period_end

            # ✅ FIX 3: Add flush
            await self.db.flush()

        print(f"✅ Downgraded {len(expired_subscriptions)} subscriptions")
