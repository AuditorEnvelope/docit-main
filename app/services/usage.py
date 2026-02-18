"""
Usage Service - Ledger-Based Billing (Phase 2)
===============================================

This service implements the "Immutable Ledger" pattern for usage tracking.

Key Principles:
- APPEND-ONLY: Never update or delete usage records
- TIME-WINDOWED: Usage is calculated by querying within entitlement windows
- AUTOMATIC RESET: When a new billing cycle starts, old usage is ignored by queries
- RAZORPAY IS MASTER: Billing cycles are determined by subscription entitlement windows

Design Pattern:
--------------
Traditional (mutable counter):
    subscription.docs_generated_this_month += 1  # ❌ Can desync
    
Ledger (immutable events):
    usage_event = SubscriptionUsage(...)  # ✅ Permanent audit trail
    db.add(usage_event)
    
Calculating balance:
    SUM(usage WHERE consumed_at >= cycle_start)  # ✅ Always accurate

See: migrations/017_usage_ledger.sql for schema details
"""

from typing import Dict, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import uuid
import logging

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.usage import SubscriptionUsage, ResourceType


# ============================================================================
# PLAN LIMITS CONFIGURATION
# ============================================================================
# TODO: Eventually fetch from subscription_plans table instead of hardcoding
# For now, this matches the limits in app/core/config.py and subscription_plans

PLAN_LIMITS = {
    "free": {
        ResourceType.DOCS_GENERATED: 100,
        ResourceType.REPOS_CONNECTED: 1,
        ResourceType.API_CALLS: 1000,
        ResourceType.PAGES_PROCESSED: 500,
        ResourceType.TOKENS_USED: 50000,
    },
    "pro": {
        ResourceType.DOCS_GENERATED: 1000,
        ResourceType.REPOS_CONNECTED: -1,  # -1 = unlimited
        ResourceType.API_CALLS: 10000,
        ResourceType.PAGES_PROCESSED: 5000,
        ResourceType.TOKENS_USED: 500000,
    },
    "team": {
        ResourceType.DOCS_GENERATED: 5000,
        ResourceType.REPOS_CONNECTED: -1,  # unlimited
        ResourceType.API_CALLS: 50000,
        ResourceType.PAGES_PROCESSED: 25000,
        ResourceType.TOKENS_USED: 2500000,
    },
    "enterprise": {
        ResourceType.DOCS_GENERATED: -1,  # unlimited
        ResourceType.REPOS_CONNECTED: -1,  # unlimited
        ResourceType.API_CALLS: -1,  # unlimited
        ResourceType.PAGES_PROCESSED: -1,  # unlimited
        ResourceType.TOKENS_USED: -1,  # unlimited
    },
}


class UsageService:
    """
    Usage Ledger Service - The "Balance Calculator"

    This service manages subscription-based usage tracking using an
    immutable ledger pattern. Each consumption event is recorded as
    a permanent entry, and usage is calculated by summing events within
    the current billing cycle's time window.

    Methods:
    --------
    - record_usage(): Append a usage event to the ledger
    - get_usage_summary(): Calculate total usage in current cycle
    - check_limit(): Verify if user has remaining quota
    - enforce_limit(): Raise 403 if limit exceeded (convenience wrapper)

    Architecture:
    ------------
    This implements "Pillar 2" of the ledger-based billing architecture:

    1. Usage events are NEVER updated or deleted
    2. Billing cycles are defined by subscription.entitlement_start/end
    3. When a cycle changes (upgrade/renewal), the query automatically
       filters out old events, creating a "virtual reset"
    4. No manual reset scripts or cron jobs needed

    Example:
    --------
    >>> service = UsageService(db)
    >>> 
    >>> # Record a document generation
    >>> await service.record_usage(
    ...     user_id=user.id,
    ...     resource_type=ResourceType.DOCS_GENERATED,
    ...     amount=1,
    ...     resource_id=str(document.id)
    ... )
    >>> 
    >>> # Check if user can generate more
    >>> limit_check = await service.check_limit(
    ...     user_id=user.id,
    ...     resource_type=ResourceType.DOCS_GENERATED
    ... )
    >>> if not limit_check["allowed"]:
    ...     raise HTTPException(403, f"Limit reached: {limit_check['used']}/{limit_check['limit']}")
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the UsageService.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    # ========================================================================
    # CORE METHODS
    # ========================================================================

    async def record_usage(
        self,
        user_id: str,
        resource_type: str,
        amount: int = 1,
        resource_id: Optional[str] = None,
        # Phase 6: Shadow token tracking
        input_tokens: int = 0,
        output_tokens: int = 0,
        model_name: str = "unknown",
        cost: Optional[float] = None,
    ) -> SubscriptionUsage:
        """
        Append a usage event to the ledger.

        This is the WRITE operation in the ledger pattern. Each call creates
        a permanent, immutable record of consumption.

        Args:
            user_id: UUID of the user (string or UUID object)
            resource_type: Type of resource consumed (e.g., 'docs_generated')
            amount: Quantity consumed (default: 1)
            resource_id: Optional ID of the specific resource (for audit trail)
            input_tokens: LLM prompt tokens consumed (shadow metric)
            output_tokens: LLM completion tokens generated (shadow metric)
            model_name: LLM model used (e.g., 'gpt-4o', 'gemini-2.0-flash')
            cost: Estimated cost in USD (optional)

        Returns:
            SubscriptionUsage: The created usage record

        Raises:
            HTTPException: If no active subscription found or validation fails

        Example:
            >>> await service.record_usage(
            ...     user_id="123e4567-e89b-12d3-a456-426614174000",
            ...     resource_type=ResourceType.DOCS_GENERATED,
            ...     amount=1,
            ...     resource_id="doc_abc123",
            ...     input_tokens=1500,
            ...     output_tokens=2500,
            ...     model_name="gpt-4o"
            ... )

        Technical Details:
        -----------------
        - Validates resource_type against allowed values
        - Finds the currently active subscription (entitlement phase)
        - Creates a new row in subscription_usage table
        - Commits immediately (isolated transaction)
        - Records token usage for cost analysis (shadow metrics)

        Invariants:
        ----------
        - User MUST have an active subscription
        - resource_type MUST be valid (enforced by DB constraint)
        - amount MUST be positive (enforced by DB constraint)
        - consumed_at timestamp MUST be within or after entitlement_start
        """
        # Normalize user_id to UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Validate resource_type
        if not ResourceType.is_valid(resource_type):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resource_type '{resource_type}'. "
                f"Must be one of: {ResourceType.all()}"
            )

        # Validate amount
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Amount must be positive, got: {amount}"
            )

        # Get active subscription (required)
        active_sub = await self._get_active_subscription(user_id)
        if not active_sub:
            raise HTTPException(
                status_code=404,
                detail=f"No active subscription found for user {user_id}. "
                "User must have an active plan to record usage."
            )

        # Create usage record with token tracking
        now = datetime.now(timezone.utc)
        usage = SubscriptionUsage(
            subscription_id=active_sub.id,
            user_id=user_id,
            resource_type=resource_type,
            amount=amount,
            resource_id=resource_id,
            consumed_at=now,
            # Phase 6: Shadow token metrics
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            cost=cost,
        )

        self.db.add(usage)
        await self.db.commit()
        await self.db.refresh(usage)

        return usage

    async def get_usage_summary(self, user_id: str) -> Dict[str, int]:
        """
        Calculate total usage in the current billing cycle (THE MAGIC QUERY).

        This is the READ operation in the ledger pattern. It sums all usage
        events that occurred within the active subscription's entitlement window.

        Args:
            user_id: UUID of the user (string or UUID object)

        Returns:
            Dict[str, int]: Resource type to total usage mapping
            Example: {
                'docs_generated': 73,
                'repos_connected': 2,
                'api_calls': 150
            }
            Returns empty dict {} if no active subscription

        Technical Details:
        -----------------
        The query filters by:
        1. subscription_id = active_subscription.id
        2. consumed_at >= entitlement_start  ← THE MAGIC LINE
        3. consumed_at < entitlement_end

        When a new billing cycle starts (upgrade, renewal):
        - A new subscription row is created with new entitlement_start
        - This query now filters by the NEW start date
        - Old usage is automatically excluded (still in DB for audit)
        - No manual "reset" needed!

        Example:
            >>> summary = await service.get_usage_summary(user_id)
            >>> print(summary)
            {'docs_generated': 73, 'repos_connected': 2}
            >>> 
            >>> # After monthly renewal (new cycle starts):
            >>> summary = await service.get_usage_summary(user_id)
            >>> print(summary)
            {'docs_generated': 0}  # Automatically "reset"!
        """
        # Normalize user_id to UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Get active subscription
        active_sub = await self._get_active_subscription(user_id)
        if not active_sub:
            # No active subscription = no usage to report
            return {}

        # THE MAGIC QUERY: Sum usage within entitlement window
        stmt = (
            select(
                SubscriptionUsage.resource_type,
                func.sum(SubscriptionUsage.amount).label("total")
            )
            .where(
                SubscriptionUsage.subscription_id == active_sub.id,
                SubscriptionUsage.consumed_at >= active_sub.entitlement_start,
                SubscriptionUsage.consumed_at < active_sub.entitlement_end,
            )
            .group_by(SubscriptionUsage.resource_type)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Convert to dict
        usage_summary = {row.resource_type: int(row.total) for row in rows}

        return usage_summary

    async def get_token_usage_summary(self, user_id: str) -> Dict[str, any]:
        """
        Get token usage statistics for the current billing cycle (Phase 6).

        This provides shadow metrics for cost analysis and optimization.

        Args:
            user_id: UUID of the user

        Returns:
            Dict with token statistics:
            {
                "total_input_tokens": 15230,
                "total_output_tokens": 18450,
                "total_tokens": 33680,
                "generations_count": 12,
                "avg_input_tokens": 1269,
                "avg_output_tokens": 1537,
                "model_breakdown": {
                    "llama-3.3-70b-versatile": {
                        "count": 8,
                        "input_tokens": 10000,
                        "output_tokens": 12000
                    },
                    "gemini-2.0-flash": {
                        "count": 4,
                        "input_tokens": 5230,
                        "output_tokens": 6450
                    }
                }
            }
        """
        # Normalize user_id to UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Get active subscription
        active_sub = await self._get_active_subscription(user_id)
        if not active_sub:
            return {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "generations_count": 0,
                "avg_input_tokens": 0,
                "avg_output_tokens": 0,
                "model_breakdown": {}
            }

        # Query for token totals and averages
        totals_stmt = (
            select(
                func.count(SubscriptionUsage.id).label("count"),
                func.sum(SubscriptionUsage.input_tokens).label("total_input"),
                func.sum(SubscriptionUsage.output_tokens).label(
                    "total_output"),
                func.avg(SubscriptionUsage.input_tokens).label("avg_input"),
                func.avg(SubscriptionUsage.output_tokens).label("avg_output"),
            )
            .where(
                SubscriptionUsage.subscription_id == active_sub.id,
                SubscriptionUsage.consumed_at >= active_sub.entitlement_start,
                SubscriptionUsage.consumed_at < active_sub.entitlement_end,
                SubscriptionUsage.resource_type == ResourceType.DOCS_GENERATED,
            )
        )

        result = await self.db.execute(totals_stmt)
        totals = result.first()

        # Query for model breakdown
        breakdown_stmt = (
            select(
                SubscriptionUsage.model_name,
                func.count(SubscriptionUsage.id).label("count"),
                func.sum(SubscriptionUsage.input_tokens).label("input_tokens"),
                func.sum(SubscriptionUsage.output_tokens).label(
                    "output_tokens"),
            )
            .where(
                SubscriptionUsage.subscription_id == active_sub.id,
                SubscriptionUsage.consumed_at >= active_sub.entitlement_start,
                SubscriptionUsage.consumed_at < active_sub.entitlement_end,
                SubscriptionUsage.resource_type == ResourceType.DOCS_GENERATED,
            )
            .group_by(SubscriptionUsage.model_name)
        )

        breakdown_result = await self.db.execute(breakdown_stmt)
        breakdown_rows = breakdown_result.all()

        # Build model breakdown dict
        model_breakdown = {}
        for row in breakdown_rows:
            model_breakdown[row.model_name] = {
                "count": int(row.count),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
            }

        return {
            "total_input_tokens": int(totals.total_input or 0),
            "total_output_tokens": int(totals.total_output or 0),
            "total_tokens": int((totals.total_input or 0) + (totals.total_output or 0)),
            "generations_count": int(totals.count or 0),
            "avg_input_tokens": int(totals.avg_input or 0),
            "avg_output_tokens": int(totals.avg_output or 0),
            "model_breakdown": model_breakdown,
        }

    async def check_limit(
        self,
        user_id: str,
        resource_type: str,
    ) -> Dict[str, any]:
        """
        Check if user has remaining quota for a resource type.

        This combines usage calculation with plan limits to determine
        if a user can consume more of a given resource.

        Args:
            user_id: UUID of the user
            resource_type: Type of resource to check (e.g., 'docs_generated')

        Returns:
            Dict with keys:
            - allowed (bool): True if user can consume more
            - used (int): Amount already consumed in current cycle
            - limit (int): Total allowed by plan (-1 = unlimited)
            - remaining (int): Quota left (or -1 if unlimited)
            - plan (str): Current plan name
            - subscription_id (str): Active subscription UUID
            - cycle_start (str): ISO timestamp of cycle start
            - cycle_end (str): ISO timestamp of cycle end

        Example:
            >>> check = await service.check_limit(
            ...     user_id=user.id,
            ...     resource_type=ResourceType.DOCS_GENERATED
            ... )
            >>> print(check)
            {
                'allowed': True,
                'used': 73,
                'limit': 1000,
                'remaining': 927,
                'plan': 'pro',
                'subscription_id': '...',
                'cycle_start': '2026-01-01T00:00:00Z',
                'cycle_end': '2026-02-01T00:00:00Z'
            }
            >>> 
            >>> if not check['allowed']:
            ...     raise HTTPException(403, f"Limit reached: {check['used']}/{check['limit']}")

        Business Logic:
        --------------
        - Free tier: 100 docs/month
        - Pro tier: 1,000 docs/month
        - Team tier: 5,000 docs/month
        - Enterprise tier: Unlimited (-1)

        Raises:
            HTTPException: If user has no active subscription
        """
        # Normalize user_id to UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Validate resource_type
        if not ResourceType.is_valid(resource_type):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resource_type '{resource_type}'. "
                f"Must be one of: {ResourceType.all()}"
            )

        # Get active subscription (required)
        active_sub = await self._get_active_subscription(user_id)
        if not active_sub:
            raise HTTPException(
                status_code=404,
                detail=f"No active subscription found for user {user_id}"
            )

        # Get plan limits
        plan_name = (active_sub.plan or "free").lower()
        plan_limits_dict = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])
        limit = plan_limits_dict.get(resource_type, 0)

        # Get current usage
        usage_summary = await self.get_usage_summary(str(user_id))
        used = usage_summary.get(resource_type, 0)

        # Calculate remaining and allowed
        if limit == -1:
            # Unlimited
            remaining = -1
            allowed = True
        else:
            remaining = limit - used
            allowed = remaining > 0

        return {
            "allowed": allowed,
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "plan": plan_name,
            "subscription_id": str(active_sub.id),
            "cycle_start": active_sub.entitlement_start.isoformat() if active_sub.entitlement_start else None,
            "cycle_end": active_sub.entitlement_end.isoformat() if active_sub.entitlement_end else None,
        }

    async def enforce_limit(
        self,
        user_id: str,
        resource_type: str,
    ) -> None:
        """
        Enforce usage limits by raising HTTPException if exceeded.

        This is a convenience wrapper around check_limit() that raises
        an exception instead of returning a dict. Use this before
        expensive operations (e.g., doc generation) to fail fast.

        Args:
            user_id: UUID of the user
            resource_type: Type of resource to check

        Raises:
            HTTPException(403): If limit exceeded
            HTTPException(404): If no active subscription

        Example:
            >>> # Before generating a document:
            >>> await service.enforce_limit(
            ...     user_id=user.id,
            ...     resource_type=ResourceType.DOCS_GENERATED
            ... )
            >>> # If we reach here, user has quota remaining
            >>> document = await generate_documentation(...)
            >>> await service.record_usage(...)
        """
        check = await self.check_limit(user_id, resource_type)

        if not check["allowed"]:
            limit_str = "unlimited" if check["limit"] == - \
                1 else str(check["limit"])
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Usage limit reached for {resource_type}. "
                    f"You've used {check['used']} of your {limit_str} quota. "
                    f"Upgrade your plan to increase limits. "
                    f"Current plan: {check['plan']}. "
                    f"Cycle ends: {check['cycle_end']}"
                )
            )

    # ========================================================================
    # HELPER METHODS (Internal)
    # ========================================================================

    async def _get_active_subscription(self, user_id: uuid.UUID) -> Optional[Subscription]:
        """
        Fetch the current active subscription phase for a user.

        This is the "source of truth" query for determining which billing cycle
        a user is currently in. It matches the logic in RazorpayService.

        Invariants:
        ----------
        - At most one active entitlement per user at any instant
          (enforced by DB exclusion constraint)
        - Entitlement is determined by:
            status = 'active' AND (
                entitlement_start <= now < entitlement_end OR
                current_period_start <= now < current_period_end  -- legacy fallback
            )

        Returns:
            Subscription object if found, None otherwise
        """
        now = datetime.now(timezone.utc)
        logger = logging.getLogger(__name__)
        logger.info(f"Looking for active subscription for user {user_id} at {now}")

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
        subscription = result.scalar_one_or_none()
        
        if subscription:
            logger.info(f"Found active subscription {subscription.id} for user {user_id}: plan={subscription.plan}, status={subscription.status}")
        else:
            logger.warning(f"No active subscription found for user {user_id}")
            # Check what subscriptions exist for debugging
            all_stmt = select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.created_at.desc())
            all_result = await self.db.execute(all_stmt)
            all_subs = all_result.scalars().all()
            if all_subs:
                for sub in all_subs:
                    logger.warning(f"  Found subscription {sub.id}: plan={sub.plan}, status={sub.status}, entitlement_start={sub.entitlement_start}, entitlement_end={sub.entitlement_end}")
            else:
                logger.warning(f"  No subscriptions at all for user {user_id}")
        
        return subscription

    async def get_plan_limits(self, plan_name: str) -> Dict[str, int]:
        """
        Get usage limits for a specific plan.

        Args:
            plan_name: Plan name (free, pro, team, enterprise)

        Returns:
            Dict mapping resource types to limits (-1 = unlimited)

        Example:
            >>> limits = await service.get_plan_limits('pro')
            >>> print(limits[ResourceType.DOCS_GENERATED])
            1000
        """
        plan_name = plan_name.lower()
        return PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])

    async def get_usage_history(
        self,
        user_id: str,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[SubscriptionUsage]:
        """
        Get historical usage events for audit/analytics.

        Args:
            user_id: UUID of the user
            resource_type: Optional filter by resource type
            limit: Max number of events to return (default: 100)

        Returns:
            List of SubscriptionUsage objects, newest first

        Example:
            >>> history = await service.get_usage_history(
            ...     user_id=user.id,
            ...     resource_type=ResourceType.DOCS_GENERATED,
            ...     limit=50
            ... )
            >>> for event in history:
            ...     print(f"{event.consumed_at}: {event.amount} {event.resource_type}")
        """
        # Normalize user_id to UUID
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(SubscriptionUsage)
            .where(SubscriptionUsage.user_id == user_id)
            .order_by(SubscriptionUsage.consumed_at.desc())
            .limit(limit)
        )

        if resource_type:
            stmt = stmt.where(SubscriptionUsage.resource_type == resource_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# ============================================================================
# CONVENIENCE EXPORTS
# ============================================================================

__all__ = [
    "UsageService",
    "PLAN_LIMITS",
]
