"""
Subscription API Endpoints

Handles subscription plans and upgrades
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.subscription import SubscriptionService
from app.services.razorpay_service import RazorpayService

router = APIRouter()


@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    # This doesn't need DB or authentication
    return {
        "plans": [
            {
                "name": "free",
                "display_name": "Free",
                "price_monthly": 0,
                "max_repositories": 1,
                "max_docs_per_month": 100,
                "features": [
                    "1 repository",
                    "100 docs/month",
                    "Community support"
                ]
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "price_monthly": 29,
                "max_repositories": "Unlimited",
                "max_docs_per_month": 1000,
                "features": [
                    "Unlimited repositories",
                    "1,000 docs/month",
                    "Priority support",
                    "Custom templates",
                    "API access"
                ]
            },
            {
                "name": "enterprise",
                "display_name": "Enterprise",
                "price_monthly": 99,
                "max_repositories": "Unlimited",
                "max_docs_per_month": "Unlimited",
                "features": [
                    "Unlimited repositories",
                    "Unlimited docs",
                    "Dedicated support",
                    "Custom templates",
                    "API access",
                    "Advanced analytics",
                    "SLA guarantee"
                ]
            }
        ]
    }


@router.get("/me")
async def get_my_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscription"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_or_create_subscription(user.id)

    return {
        "id": str(subscription.id),  # Convert UUID to string for JSON
        "user_id": str(subscription.user_id),
        "plan": subscription.plan.value if hasattr(subscription.plan, 'value') else subscription.plan,
        "status": subscription.status.value if hasattr(subscription.status, 'value') else subscription.status,
        "max_repositories": subscription.max_repositories,
        "current_repositories": subscription.current_repositories,
        "max_docs_per_month": subscription.max_docs_per_month,
        "docs_generated_this_month": subscription.docs_generated_this_month,
        "created_at": subscription.created_at,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end
    }


@router.post("/upgrade")
async def upgrade_subscription(
    plan: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upgrade subscription plan"""
    if plan not in ["pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan")

    razorpay_service = RazorpayService(db)
    order = await razorpay_service.create_order(
        user_id=str(user.id),
        user_email=user.email,
        plan_name=plan,
        user_name=user.name
    )
    return order


class PaymentVerificationPayload(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str = ""


@router.post("/verify-payment")
async def verify_payment(
    payload: PaymentVerificationPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment - READ ONLY (webhooks update DB)

    Note: This endpoint is automatically called from the payment success page.
    It does NOT write to the database - only reads payment status.
    Webhooks are the single source of truth for DB updates.
    """
    razorpay_service = RazorpayService(db)

    print(
        f"[MANUAL-VERIFY] Auto-invoked from success page for user {user.id}, payment {payload.razorpay_payment_id}")

    # Verify signature if provided
    if payload.razorpay_signature:
        try:
            is_valid = await razorpay_service.verify_payment(
                order_id=payload.razorpay_order_id,
                payment_id=payload.razorpay_payment_id,
                signature=payload.razorpay_signature,
            )

            if not is_valid:
                print(
                    f"[MANUAL-VERIFY] Invalid signature for payment {payload.razorpay_payment_id}")
                raise HTTPException(
                    status_code=400, detail="Invalid payment signature")
        except Exception as e:
            print(f"[MANUAL-VERIFY] Signature verification error: {e}")
            # Don't fail the entire request on signature verification issues
            # Continue to check payment status

    # Check payment status (READ ONLY - does not write to DB)
    try:
        status_result = await razorpay_service.check_payment_status(
            order_id=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id
        )

        print(
            f"[MANUAL-VERIFY] Status check result: {status_result.get('status')}")
        return status_result

    except HTTPException as he:
        # Re-raise HTTP exceptions with proper status codes
        print(f"[MANUAL-VERIFY] HTTP error: {he.detail}")
        raise
    except Exception as e:
        # Log error but return a user-friendly response
        print(f"[MANUAL-VERIFY] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

        # Return a safe response instead of 500 error
        return {
            "status": "checking",
            "message": "Payment status is being verified. Please wait a moment and refresh.",
            "payment_id": payload.razorpay_payment_id,
            "order_id": payload.razorpay_order_id
        }


__all__ = ["router"]
