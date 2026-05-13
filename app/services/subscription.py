"""
Subscription Service

Manages user subscriptions, billing, and usage limits
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from fastapi import HTTPException

from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User
from app.core.config import settings


class SubscriptionService:
    """
    Subscription management service

    Handles:
    - Plan management (free, pro, enterprise)
    - Usage tracking and limits
    - Subscription tier enforcement
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_subscription(self, user_id) -> Optional[Subscription]:
        """Get user's ACTIVE subscription entitlement phase.

        Entitlement is resolved using subscriptions where:
        - status = 'active'
        - entitlement_start <= now < entitlement_end (preferred), or
        - current_period_start <= now < current_period_end for legacy rows.
        """
        import uuid
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        now = datetime.now(timezone.utc)

        ent_window = and_(
            Subscription.entitlement_start != None,
            Subscription.entitlement_start <= now,
            Subscription.entitlement_end > now,
        )

        legacy_window = and_(
            Subscription.entitlement_start == None,
            Subscription.current_period_start != None,
            Subscription.current_period_start <= now,
            Subscription.current_period_end > now,
        )

        result = await self.db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                or_(ent_window, legacy_window),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_subscription(self, user_id) -> Subscription:
        """Get existing ACTIVE subscription or create a free-tier entitlement.

        NOTE: This treats subscriptions as time-bounded entitlements. For new
        users we create a free plan phase starting now.
        """
        import uuid
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        subscription = await self.get_subscription(user_id)

        if subscription:
            return subscription

        now = datetime.now(timezone.utc)

        entitlement_end = now + timedelta(days=30)

        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            entitlement_start=now,
            entitlement_end=entitlement_end,
            max_repositories=settings.FREE_TIER_MAX_REPOS,
            max_docs_per_month=settings.FREE_TIER_MAX_DOCS_PER_MONTH,
            current_repositories=0,
            docs_generated_this_month=0,
            current_period_start=now,
            current_period_end=entitlement_end,
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def check_can_add_repository(self, user_id) -> bool:
        """Check if user can add another repository"""
        subscription = await self.get_or_create_subscription(user_id)

        # Unlimited repos for pro/enterprise (-1 means unlimited)
        if subscription.max_repositories == -1:
            return True

        return subscription.current_repositories < subscription.max_repositories

    async def enforce_repository_limit(self, user_id) -> None:
        """Raise exception if user exceeds repository limit"""
        if not await self.check_can_add_repository(user_id):
            subscription = await self.get_subscription(user_id)
            raise HTTPException(
                status_code=403,
                detail=f"Repository limit reached. Your {subscription.plan} plan allows {subscription.max_repositories} repositories. Upgrade to add more."
            )

    async def increment_repository_count(self, user_id) -> None:
        """Increment repository count after adding a repo"""
        subscription = await self.get_or_create_subscription(user_id)
        subscription.current_repositories += 1
        await self.db.commit()

    async def decrement_repository_count(self, user_id) -> None:
        """Decrement repository count after removing a repo"""
        subscription = await self.get_or_create_subscription(user_id)
        if subscription.current_repositories > 0:
            subscription.current_repositories -= 1
            await self.db.commit()

    async def check_can_generate_docs(self, user_id) -> bool:
        """Check if user can generate more docs this month"""
        subscription = await self.get_or_create_subscription(user_id)

        # Unlimited docs for enterprise
        if subscription.max_docs_per_month == -1:
            return True

        return subscription.docs_generated_this_month < subscription.max_docs_per_month

    async def enforce_doc_generation_limit(self, user_id) -> None:
        """Raise exception if user exceeds doc generation limit"""
        if not await self.check_can_generate_docs(user_id):
            subscription = await self.get_subscription(user_id)
            raise HTTPException(
                status_code=403,
                detail=f"Documentation generation limit reached. Your {subscription.plan} plan allows {subscription.max_docs_per_month} docs per month. Upgrade for more."
            )

    async def increment_docs_count(self, user_id) -> None:
        """Increment docs generated count"""
        subscription = await self.get_or_create_subscription(user_id)
        subscription.docs_generated_this_month += 1
        await self.db.commit()

    async def upgrade_subscription(self, user_id, plan: str) -> Subscription:
        """Upgrade user subscription"""
        subscription = await self.get_or_create_subscription(user_id)

        # Update plan and limits
        if plan == "pro":
            subscription.plan = SubscriptionPlan.PRO
            subscription.max_repositories = settings.PRO_TIER_MAX_REPOS
            subscription.max_docs_per_month = settings.PRO_TIER_MAX_DOCS_PER_MONTH
        elif plan == "enterprise":
            subscription.plan = SubscriptionPlan.ENTERPRISE
            subscription.max_repositories = settings.ENTERPRISE_TIER_MAX_REPOS
            subscription.max_docs_per_month = settings.ENTERPRISE_TIER_MAX_DOCS_PER_MONTH
        else:
            raise HTTPException(status_code=400, detail="Invalid plan")

        subscription.status = SubscriptionStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def get_plans(self) -> Dict[str, Any]:
        """Get available subscription plans"""
        return {
            "plans": [
                {
                    "name": "free",
                    "display_name": "Free",
                    "price_monthly": 0,
                    "max_repositories": settings.FREE_TIER_MAX_REPOS,
                    "max_docs_per_month": settings.FREE_TIER_MAX_DOCS_PER_MONTH,
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
                    "max_docs_per_month": settings.PRO_TIER_MAX_DOCS_PER_MONTH,
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


__all__ = ["SubscriptionService"]
