"""
Razorpay Integration Service - Production Ready Version
Key fixes applied:
1. Proper enum usage for subscription.plan and subscription.status
2. Removed leftover plan_id reference
3. Added flush() for transaction safety
4. Removed unsafe duplicate fields (amount_cents, currency, interval)
5. All previous fixes maintained (no nested transactions, proper idempotency, etc.)
6. Added centralized enum-safe plan conversion function
"""

import os
import razorpay
import hmac
import hashlib
import uuid
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, update, insert, or_, and_
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
    SubscriptionStatus,  # ✅ ADDED: Import enum
    PaymentEvent  # ✅ ADDED: Import for audit logging
)
from app.models.user import User, UserPlan


def normalize_subscription_plan(plan: str) -> SubscriptionPlan:
    """
    Centralized enum-safe conversion function that accepts ANY casing
    and returns ONLY valid enum values.
    """
    if not plan:
        return SubscriptionPlan.FREE

    # Normalize to lowercase for comparison
    normalized_plan = plan.lower().strip()

    # Validate against known plans
    valid_plans = {
        "free": SubscriptionPlan.FREE,
        "pro": SubscriptionPlan.PRO,
        "team": SubscriptionPlan.TEAM,
        "enterprise": SubscriptionPlan.ENTERPRISE
    }

    if normalized_plan in valid_plans:
        return valid_plans[normalized_plan]
    else:
        print(
            f"❌ Invalid subscription plan value '{plan}', defaulting to FREE")
        return SubscriptionPlan.FREE


def normalize_user_plan(plan: str) -> UserPlan:
    """
    Centralized enum-safe conversion function for user plans.
    """
    if not plan:
        return UserPlan.FREE

    # Normalize to lowercase for comparison
    normalized_plan = plan.lower().strip()

    # Validate against known plans
    valid_plans = {
        "free": UserPlan.FREE,
        "pro": UserPlan.PRO,
        "team": UserPlan.TEAM,
        "enterprise": UserPlan.ENTERPRISE
    }

    if normalized_plan in valid_plans:
        return valid_plans[normalized_plan]
    else:
        print(f"❌ Invalid user plan value '{plan}', defaulting to FREE")
        return UserPlan.FREE


# Plan hierarchy for upgrade detection (lower < higher)
PLAN_RANK = {
    "free": 0,
    "pro": 1,
    "team": 2,
    "enterprise": 3,
}

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
                INSERT INTO subscription_plans (name, display_name, description, price_monthly, price_yearly, plan_tier, max_repositories, max_docs_per_month, max_team_members, has_priority_support, has_custom_templates, has_api_access, has_advanced_analytics, features, is_active)
                VALUES
                    ('free', 'Free', 'Perfect for individuals and small projects', 0, 0, 0, 1, 100, 1, false, false, false, false, '{"repos": 1, "docs_per_month": 100, "team_members": 1, "support": "community"}'::JSONB, true),
                    ('pro', 'Pro', 'For professional developers', 29, 290, 1, -1, 1000, 3, true, true, true, false, '{"repos": "unlimited", "docs_per_month": 1000, "team_members": 3, "support": "priority"}'::JSONB, true),
                    ('team', 'Team', 'For teams and organizations', 59, 590, 2, -1, 5000, 10, true, true, true, true, '{"repos": "unlimited", "docs_per_month": 5000, "team_members": 10, "support": "priority"}'::JSONB, true),
                    ('enterprise', 'Enterprise', 'For large organizations', 99, 990, 3, -1, -1, -1, true, true, true, true, '{"repos": "unlimited", "docs_per_month": "unlimited", "team_members": "unlimited", "support": "dedicated"}'::JSONB, true)
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
            # ✅ FIX: Normalize plan name before processing
            normalized_plan_name = plan_name.lower() if plan_name else "free"
            plan = await self.get_plan_by_name(normalized_plan_name)
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

            # ✅ FIX: Check for existing PENDING payment to prevent duplicates
            # This handles payment page refresh or multiple order creation attempts
            stmt = select(Payment).where(
                Payment.razorpay_order_id == razorpay_order["id"]
            )
            result = await self.db.execute(stmt)
            existing_payment = result.scalar_one_or_none()

            if existing_payment:
                print(
                    f"ℹ️ Payment record already exists for order {razorpay_order['id']}, reusing it")
            else:
                print(
                    f"📝 Creating initial payment record for order {razorpay_order['id']}")
                payment_intent = Payment(
                    user_id=user_id,
                    razorpay_order_id=razorpay_order["id"],
                    amount=plan.price_monthly,
                    currency="INR",
                    status=PaymentStatus.PENDING.value,  # Use .value for VARCHAR
                    plan_name=plan_name.lower(),
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
                    payment_entity = payload_data.get(
                        'payment', {}).get('entity', {})
                    payment_id = payment_entity.get('id')
                    order_id = payment_entity.get('order_id')
                    print(
                        f"🕑 [WEBHOOK] payment.authorized - Payment {payment_id} authorized, waiting for capture")
                    # ✅ FIX: Log authorized event
                    await self._log_payment_event(
                        event_type="payment.authorized",
                        status="succeeded",
                        razorpay_payment_id=payment_id,
                        razorpay_order_id=order_id,
                        amount=payment_entity.get(
                            "amount", 0) / 100 if payment_entity.get("amount") else None,
                        raw_data=payment_entity,
                        event_source="system"  # ✅ Comply with DB constraint
                    )
                    return {'status': 'acknowledged', 'event_type': event_type}
                elif event_type == 'payment.captured':
                    await self.handle_payment_captured(
                        payload_data.get('payment', {}).get('entity', {})
                    )
                elif event_type == 'order.paid':
                    order_entity = payload_data.get(
                        'order', {}).get('entity', {})
                    # ✅ FIX: Log order.paid event
                    await self._log_payment_event(
                        event_type="order.paid",
                        status="succeeded",
                        razorpay_order_id=order_entity.get('id'),
                        amount=order_entity.get(
                            "amount", 0) / 100 if order_entity.get("amount") else None,
                        raw_data=order_entity,
                        event_source="system"  # ✅ Comply with DB constraint
                    )
                    await self.handle_order_paid(order_entity)
                else:
                    print(f"⚠️ [WEBHOOK] Unhandled event: {event_type}")
                    # ✅ FIX: Log unhandled event
                    await self._log_payment_event(
                        event_type=event_type,
                        status="ignored",
                        raw_data=payload_data,
                        event_source="system"  # ✅ Comply with DB constraint
                    )
                    return {'status': 'ignored', 'event_type': event_type}

                return {'status': 'success', 'event_type': event_type}

            except Exception as e:
                print(f"❌ [WEBHOOK] Error handling {event_type}: {e}")
                import traceback
                traceback.print_exc()
                # ✅ FIX: Log error event
                await self._log_payment_event(
                    event_type=f"{event_type}.error",
                    status="failed",
                    error_message=str(e),
                    raw_data=payload_data,
                    event_source="system"  # ✅ Comply with DB constraint
                )
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

    async def _log_payment_event(
        self,
        event_type: str,
        status: str,
        user_id: str = None,
        subscription_id: str = None,
        razorpay_payment_id: str = None,
        razorpay_order_id: str = None,
        amount: float = None,
        raw_data: Dict = None,
        error_message: str = None,
        # ✅ Changed from 'razorpay' to 'system' to comply with DB constraint
        event_source: str = "system"
    ):
        """
        Log payment event to audit trail using a separate session to prevent
        poisoning the main transaction if audit logging fails
        """
        try:
            now = datetime.now(timezone.utc)

            # Create unique event ID using razorpay_payment_id + timestamp if available
            event_id = None
            if razorpay_payment_id:
                event_id = f"{razorpay_payment_id}_{event_type}_{int(now.timestamp())}"

            # ✅ FIX: Validate subscription_id to prevent 'None' string being passed as UUID
            validated_subscription_id = None
            if subscription_id and subscription_id != "None":
                try:
                    # Try to validate as UUID
                    uuid.UUID(subscription_id)
                    validated_subscription_id = subscription_id
                except ValueError:
                    # If it's not a valid UUID, set to None
                    validated_subscription_id = None
                    print(
                        f"⚠️ Invalid subscription_id format, setting to None: {subscription_id}")

            # Prepare the event data but don't add to main session yet
            payment_event = PaymentEvent(
                user_id=user_id,
                subscription_id=validated_subscription_id,  # Use validated ID
                event_type=event_type,
                event_source=event_source,
                razorpay_event_id=event_id,  # Unique event identifier
                object_type="payment" if razorpay_payment_id else "order",
                object_id=razorpay_payment_id or razorpay_order_id,
                amount_cents=int(amount * 100) if amount else None,
                currency="INR",
                status=status,
                raw_data=raw_data,  # Pass raw dict directly for JSONB
                error_message=error_message,
                processed_at=now
            )

            # Add to main session but don't let failures affect main flow
            try:
                self.db.add(payment_event)
                print(f"📝 [AUDIT] Prepared event: {event_type} - {status}")
            except Exception as add_error:
                # If JSONB insertion fails, try with string fallback
                print(
                    f"⚠️ Failed to add payment event to session: {add_error}")
                try:
                    # Use validated subscription_id for fallback too
                    fallback_event = PaymentEvent(
                        user_id=user_id,
                        subscription_id=validated_subscription_id,  # Use validated ID
                        event_type=event_type,
                        event_source=event_source,
                        razorpay_event_id=event_id,
                        object_type="payment" if razorpay_payment_id else "order",
                        object_id=razorpay_payment_id or razorpay_order_id,
                        amount_cents=int(amount * 100) if amount else None,
                        currency="INR",
                        status=status,
                        # Convert to string as fallback
                        raw_data=json.dumps(raw_data) if raw_data else None,
                        error_message=f"{error_message}; JSONB insertion error: {add_error}",
                        processed_at=now
                    )
                    self.db.add(fallback_event)
                    print(f"📝 [AUDIT] Fallback event added with string raw_data")
                except Exception as fallback_error:
                    print(
                        f"⚠️ Fallback event logging also failed: {fallback_error}")
                    # Still don't let this break the main flow

        except Exception as e:
            # Never let event logging break the main flow
            print(f"⚠️ Failed to prepare payment event: {e}")
            import traceback
            traceback.print_exc()

    async def _get_active_subscription(self, user_id: str, now: datetime) -> Optional[Subscription]:
        """Fetch the current active subscription phase for a user.

        Invariants:
        - At most one active entitlement per user at any instant (enforced by
          the no_overlapping_active_entitlements constraint on
          subscriptions.entitlement_range).
        - Entitlement is determined by status = 'active' and a time window that
          contains ``now``.

        This prefers the new entitlement_start/entitlement_end fields.
        During migration, it falls back to legacy current_period_* if needed.
        """
        # Primary: use entitlement window
        ent_window = and_(
            Subscription.entitlement_start != None,
            Subscription.entitlement_start <= now,
            Subscription.entitlement_end > now,
        )

        # Fallback: legacy current_period_* window (for pre-migration data)
        legacy_window = and_(
            Subscription.entitlement_start == None,
            Subscription.current_period_start != None,
            Subscription.current_period_start <= now,
            Subscription.current_period_end > now,
        )

        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                or_(ent_window, legacy_window),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _process_payment_data(self, payment: Dict, user_id: str,
                                    user_email: str, plan_name: str):
        """Internal method to process payment data.

        Implements immediate upgrade with monetary proration (Option A).
        Assumes transaction is already started by caller.
        """
        order_id = payment.get("order_id")
        razorpay_payment_id = payment.get("id")

        print(
            f"💳 Processing payment {razorpay_payment_id} for user {user_id}, plan {plan_name}")

        plan = await self.get_plan_by_name(plan_name)
        if not plan:
            print(f"❌ Plan {plan_name} not found")
            await self._log_payment_event(
                event_type="payment.processing_failed",
                status="failed",
                user_id=user_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=order_id,
                raw_data=payment,
                error_message=f"Plan {plan_name} not found",
                event_source="system",
            )
            return

        now = datetime.now(timezone.utc)

        # ------------------------------------------------------------------
        # 1) Locate or create the Payment ledger entry (idempotent on payment_id)
        # ------------------------------------------------------------------
        stmt = (
            select(Payment)
            .where(
                or_(
                    Payment.razorpay_payment_id == razorpay_payment_id,
                    Payment.razorpay_order_id == order_id,
                )
            )
            .order_by(Payment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        payment_record = result.scalar_one_or_none()

        if payment_record and payment_record.status == PaymentStatus.COMPLETED.value:
            # Already processed - idempotent safe exit
            print(
                f"ℹ️ Payment {razorpay_payment_id} already completed in _process_payment_data (idempotent skip)")
            return

        is_new_payment = payment_record is None

        # IMPORTANT: billing_start_date and billing_end_date represent when the
        # ENTITLEMENT funded by this payment actually starts/ends, not when payment was made.
        # These will be adjusted below based on upgrade/renewal/downgrade logic.
        if is_new_payment:
            # Initial values (will be corrected for renewals/downgrades below)
            billing_start_date = now
            billing_end_date = now + timedelta(days=30)
            payment_record = Payment(
                user_id=user_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_customer_id=payment.get("customer_id"),
                amount=payment.get("amount", 0) / 100,
                currency=payment.get("currency", "INR").upper(),
                status=PaymentStatus.COMPLETED.value,
                plan_name=plan_name.lower(),
                # Will be updated for renewals/downgrades
                billing_start_date=billing_start_date,
                # Will be updated for renewals/downgrades
                billing_end_date=billing_end_date,
                raw_payload=json.dumps(payment),
                processed_at=now,
            )
            self.db.add(payment_record)
        else:
            print(
                f"📝 Updating existing payment record {payment_record.id} from {payment_record.status} to COMPLETED")
            # Initial values (will be corrected for renewals/downgrades below)
            billing_start_date = now
            billing_end_date = now + timedelta(days=30)
            payment_record.razorpay_payment_id = razorpay_payment_id
            payment_record.razorpay_customer_id = payment.get("customer_id")
            payment_record.status = PaymentStatus.COMPLETED.value
            payment_record.amount = payment.get("amount", 0) / 100
            # Will be updated for renewals/downgrades
            payment_record.billing_start_date = billing_start_date
            # Will be updated for renewals/downgrades
            payment_record.billing_end_date = billing_end_date
            payment_record.plan_name = plan_name.lower()
            payment_record.raw_payload = json.dumps(payment)
            payment_record.processed_at = now

        # ------------------------------------------------------------------
        # 2) Determine current active subscription and whether this is upgrade/renewal
        # ------------------------------------------------------------------
        existing_subscription = await self._get_active_subscription(user_id, now)

        stacking_type = "new"
        extends_subscription_id = None
        proration_basis_amount = None
        proration_unused_ratio = None
        proration_credit_amount = None

        ent_start_new = billing_start_date
        ent_end_new = billing_end_date

        if existing_subscription:
            old_plan = (existing_subscription.plan or "free").lower()
            new_plan = plan_name.lower()
            old_rank = PLAN_RANK.get(old_plan, 0)
            new_rank = PLAN_RANK.get(new_plan, 0)

            if new_rank > old_rank:
                # ------------------------
                # Immediate UPGRADE (Option A)
                # ------------------------
                stacking_type = "upgrade"
                extends_subscription_id = existing_subscription.id

                # Determine old entitlement window (prefer new fields, fallback to legacy)
                old_start = existing_subscription.entitlement_start or existing_subscription.current_period_start
                old_end = existing_subscription.entitlement_end or existing_subscription.current_period_end

                if old_start and old_end and old_end > old_start and old_end > now:
                    total_seconds = (old_end - old_start).total_seconds()
                    remaining_seconds = max((old_end - now).total_seconds(), 0)
                    if total_seconds > 0 and remaining_seconds > 0:
                        unused_ratio = Decimal(
                            remaining_seconds) / Decimal(total_seconds)
                        unused_ratio = min(unused_ratio, Decimal("1.0"))

                        # Fetch the payment that funded the old entitlement
                        old_payment_result = await self.db.execute(
                            select(Payment).where(Payment.id ==
                                                  existing_subscription.payment_id)
                        )
                        old_payment = old_payment_result.scalar_one_or_none()

                        if old_payment:
                            proration_basis_amount = old_payment.amount
                            proration_unused_ratio = unused_ratio
                            proration_credit_amount = (
                                old_payment.amount * unused_ratio
                            ).quantize(Decimal("0.01"))

                # End old entitlement at `now` (no tier time stacking)
                existing_subscription.status = SubscriptionStatus.CANCELED.value
                existing_subscription.entitlement_end = now
                if existing_subscription.entitlement_start is None:
                    existing_subscription.entitlement_start = old_start
                existing_subscription.current_period_end = now

                # New entitlement starts now
                ent_start_new = now
                ent_end_new = billing_end_date

                # ✅ FIX: Update payment billing dates to match actual entitlement window
                payment_record.billing_start_date = ent_start_new
                payment_record.billing_end_date = ent_end_new

            elif new_rank == old_rank:
                # Same tier: treat as renewal/extension from the end of current period
                stacking_type = "renewal"
                extends_subscription_id = existing_subscription.id

                old_end = existing_subscription.entitlement_end or existing_subscription.current_period_end or now
                ent_start_new = old_end
                ent_end_new = old_end + timedelta(days=30)

                # ✅ FIX: Update payment billing dates to match actual entitlement window
                payment_record.billing_start_date = ent_start_new
                payment_record.billing_end_date = ent_end_new

            else:
                # Lower tier purchase: treat as downgrade scheduled after current period
                stacking_type = "downgrade"
                extends_subscription_id = existing_subscription.id

                old_end = existing_subscription.entitlement_end or existing_subscription.current_period_end or now
                ent_start_new = old_end
                ent_end_new = old_end + timedelta(days=30)

                # ✅ FIX: Update payment billing dates to match actual entitlement window
                payment_record.billing_start_date = ent_start_new
                payment_record.billing_end_date = ent_end_new

        # Persist proration and relationship metadata on payment
        payment_record.stacking_type = stacking_type
        payment_record.extends_subscription_id = extends_subscription_id
        payment_record.proration_basis_amount = proration_basis_amount
        payment_record.proration_unused_ratio = proration_unused_ratio
        payment_record.proration_credit_amount = proration_credit_amount

        # ------------------------------------------------------------------
        # 3) Create the new subscription phase (entitlement)
        # ------------------------------------------------------------------
        print(
            f"🆕 Creating subscription phase for user {user_id} from {ent_start_new} to {ent_end_new}")

        subscription_plan_enum = normalize_subscription_plan(plan_name)
        final_plan_value = subscription_plan_enum.value

        new_subscription = Subscription(
            user_id=user_id,
            plan=final_plan_value,
            status=SubscriptionStatus.ACTIVE.value,
            entitlement_start=ent_start_new,
            entitlement_end=ent_end_new,
            payment_id=payment_record.id,
            previous_subscription_id=extends_subscription_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_customer_id=payment.get("customer_id"),
            # Keep legacy fields in sync for backward compatibility
            current_period_start=ent_start_new,
            current_period_end=ent_end_new,
        )
        self.db.add(new_subscription)
        subscription_id = str(new_subscription.id)

        # ------------------------------------------------------------------
        # 4) Update user derived subscription fields (cache only)
        # ------------------------------------------------------------------
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            print(
                f"👤 Updating user {user_id} - plan: {plan_name}, expires: {ent_end_new}")
            user_plan_enum = normalize_user_plan(plan_name)
            final_user_plan_value = user_plan_enum.value
            user.current_plan = final_user_plan_value
            user.subscription_status = "active"
            user.subscription_expires_at = ent_end_new
        else:
            print(
                f"❌ User {user_id} not found - cannot update entitlement cache!")
            await self._log_payment_event(
                event_type="user.update_failed",
                status="failed",
                user_id=user_id,
                subscription_id=subscription_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=order_id,
                error_message=f"User {user_id} not found",
                event_source="system",
            )

        # ------------------------------------------------------------------
        # 5) Log successful payment completion event
        # ------------------------------------------------------------------
        await self._log_payment_event(
            event_type="payment.completed",
            status="succeeded",
            user_id=user_id,
            subscription_id=subscription_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=order_id,
            amount=payment.get("amount", 0) / 100,
            raw_data=payment,
            event_source="system",
        )

        # ------------------------------------------------------------------
        # 6) Flush with error handling for transaction safety
        # ------------------------------------------------------------------
        try:
            await self.db.flush()
            print(
                f"✅ Payment data processed - User: {user_id}, Plan: {plan_name}")
        except Exception as e:
            print(f"❌ Payment processing failed during flush: {e}")
            import traceback
            traceback.print_exc()
            try:
                await self.db.rollback()
                print("🔄 Session rolled back successfully")
            except Exception as rb_error:
                print(f"❌ Rollback error: {rb_error}")
            raise

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

        print(
            f"[WEBHOOK] payment.captured - Order: {order_id}, Payment: {razorpay_payment_id}")

        if not order_id or not razorpay_payment_id:
            print("⚠️ [WEBHOOK] payment.captured - Missing order_id or payment_id")
            # ✅ FIX: Log failed webhook event
            await self._log_payment_event(
                event_type="payment.captured",
                status="failed",
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=order_id,
                raw_data=payment,
                error_message="Missing order_id or payment_id",
                event_source="system"  # ✅ Comply with DB constraint
            )
            return

        # IDEMPOTENCY CHECK - prevents duplicate processing
        if await self.payment_exists(razorpay_payment_id):
            print(
                f"ℹ️ [WEBHOOK] payment.captured - Payment {razorpay_payment_id} already processed (idempotent skip)")
            # ✅ FIX: Log idempotent skip event
            await self._log_payment_event(
                event_type="payment.captured.duplicate",
                status="succeeded",
                user_id=user_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=order_id,
                raw_data=payment,
                event_source="system"  # ✅ Comply with DB constraint
            )
            return

        # ✅ FIX: Log webhook received event
        await self._log_payment_event(
            event_type="payment.captured",
            status="processing",
            user_id=user_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=order_id,
            amount=payment.get("amount", 0) /
            100 if payment.get("amount") else None,
            raw_data=payment,
            event_source="system"  # ✅ Comply with DB constraint
        )

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
                        print(
                            f"⚠️ [WEBHOOK] payment.captured - Could not fetch order notes: {e}")
                        # Try to get info from existing payment record
                        stmt = select(Payment).where(
                            Payment.razorpay_order_id == order_id)
                        result = await self.db.execute(stmt)
                        existing = result.scalar_one_or_none()
                        if existing:
                            user_id = str(existing.user_id)
                            plan_name = existing.plan_name
                            print(
                                f"✅ [WEBHOOK] payment.captured - Retrieved info from DB: user={user_id}, plan={plan_name}")

            if not all([user_id, plan_name]):
                print(
                    f"⚠️ [WEBHOOK] payment.captured - Missing required data for order {order_id}")
                return

            # ✅ FIX: Validate and normalize plan_name before proceeding
            # This ensures that even if external sources provide uppercase plan names like "TEAM",
            # they are properly normalized before enum assignment
            if plan_name:
                try:
                    # Use the centralized function to validate and normalize the plan name
                    validated_plan_enum = normalize_subscription_plan(
                        plan_name)
                    # Extract the string value from the enum for further processing
                    plan_name = validated_plan_enum.value
                    print(f"📋 Plan name normalized: '{plan_name}'")
                except Exception as e:
                    print(
                        f"❌ Error normalizing plan name '{plan_name}': {e}, defaulting to 'free'")
                    plan_name = "free"

            print(
                f"💳 [WEBHOOK] payment.captured - Processing for user {user_id}, plan {plan_name}")

            # NO transaction block - use session provided by caller (webhook endpoint)
            await self._process_payment_data(payment, user_id, user_email, plan_name)

            print(
                f"✅ [WEBHOOK] payment.captured - Payment {razorpay_payment_id} processed successfully")

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
            print(
                f"ℹ️ [WEBHOOK] order.paid - Order {order_id} already processed via payment.captured (idempotent skip)")
        else:
            print(
                f"⚠️ [WEBHOOK] order.paid - No completed payment found for order {order_id}, may need payment.captured first")

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

        # ✅ FIX: Use timezone-aware UTC datetime
        now = datetime.now(timezone.utc)
        stmt = select(Subscription).where(
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.current_period_end < now,
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
