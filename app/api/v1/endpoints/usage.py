"""
Usage API Endpoints - Ledger-Based Billing (Phase 3)
====================================================

Exposes usage and entitlement data to the frontend using the
UsageService (immutable ledger pattern).

Key Endpoints:
- GET /usage/me - Get current cycle usage and limits for all resources
- GET /usage/history - Get usage event history (optional, for analytics)

Design:
- All endpoints require authentication (get_current_user)
- Usage is calculated from subscription_usage table (ledger)
- Limits come from PLAN_LIMITS configuration
- Data is scoped to the current billing cycle (entitlement window)
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.usage import UsageService, PLAN_LIMITS
from app.models.usage import ResourceType


router = APIRouter()


@router.get("/me")
async def get_my_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's usage summary for the active billing cycle.

    Returns usage, limits, and remaining quota for all tracked resources.
    The frontend uses this to show progress bars, warnings, and upgrade CTAs.

    Response Structure:
    ------------------
    {
        "plan": "team",
        "subscription_id": "uuid",
        "cycle_start": "2026-01-15T00:00:00Z",
        "cycle_end": "2026-02-14T23:59:59Z",
        "limits": {
            "docs_generated": {
                "used": 5,
                "limit": 5000,
                "remaining": 4995,
                "allowed": true
            },
            "repos_connected": {
                "used": 2,
                "limit": -1,  // -1 = unlimited
                "remaining": -1,
                "allowed": true
            },
            "api_calls": { ... },
            "pages_processed": { ... },
            "tokens_used": { ... }
        }
    }

    Business Logic:
    --------------
    - Iterates through all resource types in PLAN_LIMITS
    - Calls UsageService.check_limit() for each resource
    - Returns a unified view of current billing cycle status

    Frontend Use Cases:
    ------------------
    - Dashboard: Show "X / Y docs used" progress bars
    - Warnings: Alert at 80%, 90%, 100% thresholds
    - Upgrade CTA: Show when nearing limits
    - Cycle End: Display "Resets on Feb 14"

    Example:
    --------
    >>> GET /api/v1/usage/me
    >>> Authorization: Bearer <jwt_token>
    >>> 
    >>> Response: { "plan": "pro", "limits": { ... } }
    """
    service = UsageService(db)

    # Get user's active subscription (to extract plan and cycle info)
    # We need to call check_limit at least once to get subscription metadata
    try:
        # Check one resource to get subscription info
        first_check = await service.check_limit(
            user_id=str(user.id),
            resource_type=ResourceType.DOCS_GENERATED,
        )

        plan = first_check["plan"]
        subscription_id = first_check["subscription_id"]
        cycle_start = first_check["cycle_start"]
        cycle_end = first_check["cycle_end"]

    except HTTPException as e:
        # No active subscription found
        if e.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found. Please subscribe to a plan."
            )
        raise

    # Build limits dict by checking all resource types
    limits = {}

    # Get plan-specific resource types (from PLAN_LIMITS)
    plan_config = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    for resource_type in plan_config.keys():
        try:
            check = await service.check_limit(
                user_id=str(user.id),
                resource_type=resource_type,
            )

            limits[resource_type] = {
                "used": check["used"],
                "limit": check["limit"],
                "remaining": check["remaining"],
                "allowed": check["allowed"],
            }

        except Exception as e:
            # If a specific resource check fails, log and continue
            # (Don't fail entire request for one resource)
            print(f"⚠️ Failed to check limit for {resource_type}: {e}")
            limits[resource_type] = {
                "used": 0,
                "limit": 0,
                "remaining": 0,
                "allowed": False,
                "error": str(e),
            }

    return {
        "plan": plan,
        "subscription_id": subscription_id,
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
        "limits": limits,
        # Phase 6: Include token usage statistics
        "token_usage": await service.get_token_usage_summary(str(user.id)),
    }


@router.get("/history")
async def get_usage_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    resource_type: Optional[str] = Query(
        None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=500, description="Max number of events"),
):
    """
    Get usage event history for the current user.

    This endpoint is useful for:
    - Analytics dashboards
    - Debugging usage discrepancies
    - Detailed audit trails

    Query Parameters:
    ----------------
    - resource_type (optional): Filter by specific resource (e.g., 'docs_generated')
    - limit (default: 100, max: 500): Number of events to return

    Response:
    --------
    [
        {
            "id": "uuid",
            "subscription_id": "uuid",
            "resource_type": "docs_generated",
            "amount": 1,
            "resource_id": "doc-123",
            "consumed_at": "2026-01-15T10:30:00Z",
            "created_at": "2026-01-15T10:30:01Z"
        },
        ...
    ]

    Example:
    --------
    >>> GET /api/v1/usage/history?resource_type=docs_generated&limit=50
    >>> Authorization: Bearer <jwt_token>
    >>> 
    >>> Response: [ { "id": "...", "resource_type": "docs_generated", ... } ]
    """
    service = UsageService(db)

    # Validate resource_type if provided
    if resource_type and not ResourceType.is_valid(resource_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource_type '{resource_type}'. "
            f"Must be one of: {ResourceType.all()}"
        )

    # Get usage history
    history = await service.get_usage_history(
        user_id=str(user.id),
        resource_type=resource_type,
        limit=limit,
    )

    # Convert to dict for JSON response
    return [event.to_dict() for event in history]


@router.get("/summary")
async def get_usage_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get raw usage summary for current billing cycle (simplified version).

    Returns only the usage counts without limit checking.
    Useful for lightweight checks or internal dashboards.

    Response:
    --------
    {
        "docs_generated": 73,
        "repos_connected": 2,
        "api_calls": 150
    }

    Note: Use /me for full details including limits and remaining quota.

    Example:
    --------
    >>> GET /api/v1/usage/summary
    >>> Authorization: Bearer <jwt_token>
    >>> 
    >>> Response: { "docs_generated": 73, "repos_connected": 2 }
    """
    service = UsageService(db)

    try:
        summary = await service.get_usage_summary(str(user.id))
        return summary
    except Exception as e:
        # If no active subscription, return empty summary
        return {}


# ============================================================================
# ADMIN / DEBUG ENDPOINTS (Optional - comment out in production)
# ============================================================================

@router.get("/debug/plan-limits")
async def get_plan_limits_config(
    user: User = Depends(get_current_user),
):
    """
    Get the PLAN_LIMITS configuration (for debugging).

    This shows the hardcoded limits for each plan tier.
    Useful for frontend developers to understand available plans.

    Response:
    --------
    {
        "free": {
            "docs_generated": 100,
            "repos_connected": 1,
            ...
        },
        "pro": { ... },
        "team": { ... },
        "enterprise": { ... }
    }

    Note: In production, consider moving this to /subscriptions/plans
    or restricting to admin users only.
    """
    return PLAN_LIMITS


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router"]
