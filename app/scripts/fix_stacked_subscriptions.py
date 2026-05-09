"""One-time migration script to fix previously stacked Pro + Team subscriptions.

This script:
- Detects users where Pro and Team payments were merged into a single Team subscription window.
- Splits the stacked window into two explicit entitlement phases:
  - Pro phase:   [original_start -> upgrade_time)
  - Team phase:  [upgrade_time     -> original_end)
- Backfills payment links and preserves the original stacked row as cancelled history.

Run with:
    python -m app.scripts.fix_stacked_subscriptions

Assumptions:
- Payments table is populated with COMPLETED records for both Pro and Team purchases.
- Stacked subscriptions appear as a single active Team subscription row with a long
  current_period_start -> current_period_end window and no entitlement_* set yet.
- Migration 015_proration_and_entitlements has been applied.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select

from app.db.session import async_session
from app.models.subscription import Subscription, Payment, SubscriptionStatus, PaymentStatus


async def _find_stacked_team_subscriptions(session) -> List[Subscription]:
    """Return candidate stacked Team subscriptions that need to be split.

    Heuristic:
    - plan = 'team'
    - status = 'active'
    - entitlement_start / entitlement_end are NULL (pre-migration rows)
    - current_period_start and current_period_end are both non-NULL.
    """
    result = await session.execute(
        select(Subscription).where(
            Subscription.plan == "team",
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.entitlement_start.is_(None),
            Subscription.entitlement_end.is_(None),
            Subscription.current_period_start.is_not(None),
            Subscription.current_period_end.is_not(None),
        )
    )
    return result.scalars().all()


async def _fix_user_stacked_subscription(session, sub: Subscription) -> bool:
    """Split a single stacked Team subscription into Pro + Team phases.

    Returns True if a fix was applied, False if this subscription was skipped.
    """
    # Fetch all completed payments for this user
    pay_result = await session.execute(
        select(Payment)
        .where(
            Payment.user_id == sub.user_id,
            Payment.status == PaymentStatus.COMPLETED.value,
        )
        .order_by(Payment.processed_at.asc().nulls_last(), Payment.created_at.asc())
    )
    payments = pay_result.scalars().all()

    if not payments:
        print(f"ℹ️ No completed payments for user {sub.user_id}, skipping")
        return False

    pro_payment = next((p for p in payments if (
        p.plan_name or "").lower() == "pro"), None)
    team_payment = next((p for p in payments if (
        p.plan_name or "").lower() == "team"), None)

    if not (pro_payment and team_payment):
        # Nothing to split if we don't see both Pro and Team purchases
        print(f"ℹ️ User {sub.user_id} has no Pro+Team payment pair, skipping")
        return False

    # Determine upgrade_time from the Team payment
    upgrade_time = (
        team_payment.billing_start_date
        or team_payment.processed_at
        or team_payment.created_at
    )

    if not upgrade_time:
        print(
            f"⚠️ Could not determine upgrade_time for user {sub.user_id}, skipping")
        return False

    start = sub.current_period_start
    end = sub.current_period_end

    if not (start and end and start < upgrade_time < end):
        print(
            f"ℹ️ Subscription window for user {sub.user_id} does not span upgrade_time, "
            f"start={start}, upgrade_time={upgrade_time}, end={end} - skipping"
        )
        return False

    print(
        f"🔧 Fixing stacked subscription for user {sub.user_id}: "
        f"Pro [{start} -> {upgrade_time}), Team [{upgrade_time} -> {end})"
    )

    # Create Pro phase (historical, non-active)
    pro_sub = Subscription(
        user_id=sub.user_id,
        plan="pro",
        status=SubscriptionStatus.CANCELED.value,
        entitlement_start=start,
        entitlement_end=upgrade_time,
        payment_id=pro_payment.id,
        previous_subscription_id=None,
        razorpay_customer_id=sub.razorpay_customer_id,
        razorpay_order_id=pro_payment.razorpay_order_id or sub.razorpay_order_id,
        razorpay_payment_id=pro_payment.razorpay_payment_id,
        current_period_start=start,
        current_period_end=upgrade_time,
    )
    session.add(pro_sub)
    await session.flush()  # get pro_sub.id

    # Create Team phase (becomes the canonical active entitlement)
    team_sub = Subscription(
        user_id=sub.user_id,
        plan="team",
        status=SubscriptionStatus.ACTIVE.value,
        entitlement_start=upgrade_time,
        entitlement_end=end,
        payment_id=team_payment.id,
        previous_subscription_id=pro_sub.id,
        razorpay_customer_id=sub.razorpay_customer_id,
        razorpay_order_id=team_payment.razorpay_order_id or sub.razorpay_order_id,
        razorpay_payment_id=team_payment.razorpay_payment_id,
        current_period_start=upgrade_time,
        current_period_end=end,
    )
    session.add(team_sub)

    # Preserve the original stacked row as cancelled historical record, but
    # clear its entitlement window so it does not participate in entitlements.
    sub.status = SubscriptionStatus.CANCELED.value
    sub.canceled_at = upgrade_time
    sub.entitlement_start = None
    sub.entitlement_end = None

    return True


async def main() -> None:
    async with async_session() as session:
        candidates = await _find_stacked_team_subscriptions(session)
        if not candidates:
            print("✅ No stacked Team subscriptions detected.")
            return

        print(
            f"🔍 Found {len(candidates)} candidate stacked Team subscriptions")

        fixed_count = 0
        for sub in candidates:
            try:
                applied = await _fix_user_stacked_subscription(session, sub)
                if applied:
                    fixed_count += 1
            except Exception as e:
                print(
                    f"❌ Error while fixing subscription {sub.id} for user {sub.user_id}: {e}")

        await session.commit()
        print(
            f"✅ Migration complete. Fixed {fixed_count} stacked subscriptions.")


if __name__ == "__main__":
    asyncio.run(main())
