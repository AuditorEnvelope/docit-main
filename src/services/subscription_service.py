"""
Subscription Service - Feature Gates & Billing
Manages subscription plans and enforces feature limits
"""

import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncpg
from dataclasses import dataclass
from enum import Enum

class Plan(str, Enum):
    FREE = "free"
    TEAM = "team"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

@dataclass
class PlanFeatures:
    """Features available in each plan"""
    repos: int  # -1 = unlimited
    indexing_frequency: str  # realtime|hourly|daily
    queries_per_day: int  # -1 = unlimited
    overlays: bool
    seats: int  # -1 = unlimited
    sso: bool
    audit_logs: bool
    on_premise: bool
    support: str  # community|priority|dedicated
    storage_gb: int  # -1 = unlimited

# Plan definitions
PLANS = {
    Plan.FREE: PlanFeatures(
        repos=1,
        indexing_frequency="daily",
        queries_per_day=100,
        overlays=False,
        seats=1,
        sso=False,
        audit_logs=False,
        on_premise=False,
        support="community",
        storage_gb=1
    ),
    Plan.TEAM: PlanFeatures(
        repos=10,
        indexing_frequency="realtime",
        queries_per_day=10000,
        overlays=True,
        seats=5,
        sso=True,  # Optional add-on
        audit_logs=False,
        on_premise=False,
        support="priority",
        storage_gb=50
    ),
    Plan.ENTERPRISE: PlanFeatures(
        repos=-1,  # Unlimited
        indexing_frequency="realtime",
        queries_per_day=-1,  # Unlimited
        overlays=True,
        seats=-1,  # Unlimited
        sso=True,
        audit_logs=True,
        on_premise=True,
        support="dedicated",
        storage_gb=-1  # Unlimited
    )
}

# Pricing (in cents)
PRICING = {
    Plan.FREE: 0,
    Plan.TEAM: 4900,  # $49/month
    Plan.ENTERPRISE: None  # Custom pricing
}

class SubscriptionService:
    """
    Subscription Service - Manage plans and feature gates
    
    Features:
    - Check feature access
    - Enforce limits
    - Track usage
    - Upgrade/downgrade
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def init_db(self):
        """Initialize database connection"""
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def get_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user's subscription"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM subscriptions
                WHERE user_id = $1 AND status IN ('active', 'trial')
                ORDER BY created_at DESC
                LIMIT 1
            """, user_id)
            
            if not row:
                # Return free plan by default
                return {
                    'user_id': user_id,
                    'plan': Plan.FREE,
                    'status': SubscriptionStatus.ACTIVE,
                    'features': PLANS[Plan.FREE].__dict__,
                    'limits': {}
                }
            
            return dict(row)
    
    async def check_feature(self, user_id: str, feature: str) -> bool:
        """
        Check if user has access to a feature
        
        Args:
            user_id: User ID
            feature: Feature name (e.g., 'overlays', 'sso')
        
        Returns: True if user has access
        """
        subscription = await self.get_subscription(user_id)
        plan = Plan(subscription['plan'])
        features = PLANS[plan]
        
        return getattr(features, feature, False)
    
    async def check_limit(self, user_id: str, resource: str, current_count: int) -> bool:
        """
        Check if user is within limits
        
        Args:
            user_id: User ID
            resource: Resource type (e.g., 'repos', 'queries_per_day')
            current_count: Current usage
        
        Returns: True if within limits
        """
        subscription = await self.get_subscription(user_id)
        plan = Plan(subscription['plan'])
        features = PLANS[plan]
        
        limit = getattr(features, resource, 0)
        
        # -1 means unlimited
        if limit == -1:
            return True
        
        return current_count < limit
    
    async def get_usage(self, user_id: str) -> Dict:
        """Get current usage statistics"""
        async with self.pool.acquire() as conn:
            # Get repo count
            repo_count = await conn.fetchval("""
                SELECT COUNT(*) FROM repositories
                WHERE subscription_id = (
                    SELECT id FROM subscriptions WHERE user_id = $1
                )
            """, user_id)
            
            # Get today's query count
            query_count = await conn.fetchval("""
                SELECT COUNT(*) FROM api_usage
                WHERE user_id = $1 AND date = CURRENT_DATE
            """, user_id)
            
            # Get storage usage (estimate)
            storage_mb = await conn.fetchval("""
                SELECT COALESCE(SUM(pg_column_size(content)), 0) / 1024 / 1024
                FROM doc_nodes
                WHERE repo_id IN (
                    SELECT repo_id FROM repositories
                    WHERE subscription_id = (
                        SELECT id FROM subscriptions WHERE user_id = $1
                    )
                )
            """, user_id)
            
            return {
                'repos': repo_count or 0,
                'queries_today': query_count or 0,
                'storage_mb': float(storage_mb or 0)
            }
    
    async def create_subscription(
        self,
        user_id: str,
        plan: Plan,
        billing_cycle: str = "monthly",
        trial_days: int = 14
    ) -> str:
        """Create a new subscription"""
        async with self.pool.acquire() as conn:
            features = PLANS[plan]
            
            # Calculate trial end date
            trial_ends_at = datetime.now() + timedelta(days=trial_days) if trial_days > 0 else None
            
            subscription_id = await conn.fetchval("""
                INSERT INTO subscriptions (
                    user_id, plan, status, features, limits, billing_cycle,
                    amount_cents, trial_ends_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                user_id, plan.value, 
                SubscriptionStatus.TRIAL if trial_days > 0 else SubscriptionStatus.ACTIVE,
                json.dumps(features.__dict__),
                json.dumps({}),
                billing_cycle,
                PRICING[plan],
                trial_ends_at
            )
            
            print(f"✨ Created {plan.value} subscription for {user_id}")
            return str(subscription_id)
    
    async def upgrade_subscription(self, user_id: str, new_plan: Plan) -> str:
        """Upgrade to a higher plan"""
        async with self.pool.acquire() as conn:
            # Get current subscription
            current = await self.get_subscription(user_id)
            
            if not current:
                # Create new subscription
                return await self.create_subscription(user_id, new_plan, trial_days=0)
            
            # Update plan
            features = PLANS[new_plan]
            
            await conn.execute("""
                UPDATE subscriptions
                SET plan = $1, features = $2, amount_cents = $3, updated_at = NOW()
                WHERE user_id = $4 AND status = 'active'
            """, new_plan.value, json.dumps(features.__dict__), PRICING[new_plan], user_id)
            
            print(f"⬆️  Upgraded {user_id} to {new_plan.value}")
            return current['id']
    
    async def cancel_subscription(self, user_id: str):
        """Cancel subscription (downgrade to free)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', cancelled_at = NOW()
                WHERE user_id = $1 AND status = 'active'
            """, user_id)
            
            print(f"❌ Cancelled subscription for {user_id}")
    
    async def track_api_usage(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        response_time_ms: int,
        status_code: int
    ):
        """Track API usage for rate limiting"""
        async with self.pool.acquire() as conn:
            # Get subscription ID
            subscription_id = await conn.fetchval("""
                SELECT id FROM subscriptions WHERE user_id = $1
            """, user_id)
            
            await conn.execute("""
                INSERT INTO api_usage (
                    user_id, subscription_id, endpoint, method,
                    response_time_ms, status_code
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id, subscription_id, endpoint, method, response_time_ms, status_code)


# FastAPI endpoints
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI(title="Subscription Service", version="1.0.0")
subscription_service = None

class CreateSubscriptionRequest(BaseModel):
    user_id: str
    plan: Plan
    billing_cycle: str = "monthly"
    trial_days: int = 14

@app.on_event("startup")
async def startup():
    global subscription_service
    import os
    db_url = os.getenv("DATABASE_URL")
    subscription_service = SubscriptionService(db_url)
    await subscription_service.init_db()
    print("✅ Subscription Service started")

@app.get("/")
async def root():
    return {"service": "Subscription Service", "status": "ok"}

@app.get("/plans")
async def list_plans():
    """List available plans"""
    return {
        "plans": {
            plan.value: {
                "features": features.__dict__,
                "price_cents": PRICING[plan],
                "price_display": f"${PRICING[plan]/100:.0f}/month" if PRICING[plan] else "Custom"
            }
            for plan, features in PLANS.items()
        }
    }

@app.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    """Get user's subscription"""
    subscription = await subscription_service.get_subscription(user_id)
    usage = await subscription_service.get_usage(user_id)
    return {
        "subscription": subscription,
        "usage": usage
    }

@app.post("/subscription")
async def create_subscription(request: CreateSubscriptionRequest):
    """Create new subscription"""
    subscription_id = await subscription_service.create_subscription(
        request.user_id,
        request.plan,
        request.billing_cycle,
        request.trial_days
    )
    return {"subscription_id": subscription_id, "status": "created"}

@app.post("/subscription/{user_id}/upgrade")
async def upgrade(user_id: str, new_plan: Plan):
    """Upgrade subscription"""
    subscription_id = await subscription_service.upgrade_subscription(user_id, new_plan)
    return {"subscription_id": subscription_id, "plan": new_plan.value}

@app.post("/subscription/{user_id}/cancel")
async def cancel(user_id: str):
    """Cancel subscription"""
    await subscription_service.cancel_subscription(user_id)
    return {"status": "cancelled"}

@app.get("/feature/{user_id}/{feature}")
async def check_feature(user_id: str, feature: str):
    """Check if user has access to feature"""
    has_access = await subscription_service.check_feature(user_id, feature)
    return {"has_access": has_access, "feature": feature}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
