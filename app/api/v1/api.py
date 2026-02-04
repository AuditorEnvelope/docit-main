from fastapi import APIRouter, Depends

# Import all endpoint routers
from .endpoints import (
    auth,
    documentation,
    events,
    health,
    repositories,
    subscriptions,
    organizations,
    repos,
    docbook,
    docs,
    webhooks,
    workspace,
    usage,
)
from app.webhooks.github import router as github_webhook_router
from app.webhooks.razorpay import router as razorpay_webhook_router

# Create main API router
api_router = APIRouter()

# Authentication endpoints (no auth required)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
    responses={
        200: {"description": "Success"},
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"}
    },
)

# Repository endpoints (requires auth)
api_router.include_router(
    repositories.router,
    prefix="/repositories",
    tags=["Repositories"],
    responses={404: {"description": "Not found"}},
)

# Documentation endpoints (requires auth)
api_router.include_router(
    documentation.router,
    prefix="/documentation",
    tags=["Documentation"],
    responses={404: {"description": "Not found"}},
)

# Legacy docs endpoints (requires auth)
api_router.include_router(
    docs.router,
    prefix="/docs",
    tags=["Documentation"],
    responses={404: {"description": "Not found"}},
)

# Event endpoints (requires auth)
api_router.include_router(
    events.router,
    prefix="/events",
    tags=["Events"],
    responses={404: {"description": "Not found"}},
)

# Subscription endpoints
api_router.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=["Subscriptions"],
    responses={404: {"description": "Not found"}},
)

# Usage endpoints (ledger-based billing)
api_router.include_router(
    usage.router,
    prefix="/usage",
    tags=["Usage"],
    responses={
        200: {"description": "Success"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not found"},
    },
)

# Webhook endpoints (registration + GitHub delivery)
api_router.include_router(
    webhooks.router,
    tags=["Webhooks"],
    responses={
        200: {"description": "Webhook registered"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
api_router.include_router(
    github_webhook_router,
    prefix="/webhooks",
    tags=["Webhooks"],
    responses={
        202: {"description": "Webhook accepted for processing"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    },
)
api_router.include_router(
    razorpay_webhook_router,
    prefix="/razorpay",
    tags=["Webhooks"],
    responses={
        200: {"description": "Webhook processed"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    },
)

# Organization endpoints (requires auth)
api_router.include_router(
    organizations.router,
    tags=["Organizations"],
    responses={404: {"description": "Not found"}},
)

# Docbook helper endpoints (requires auth)
api_router.include_router(
    docbook.router,
    tags=["Docbook"],
    responses={404: {"description": "Not found"}},
)

# Repository/Docs endpoints (requires auth)
api_router.include_router(
    repos.router,
    tags=["Repositories"],
    responses={404: {"description": "Not found"}},
)

# Health check endpoints (no authentication required)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
    responses={200: {"description": "Service status"}},
)

# Workspace endpoints (requires auth)
api_router.include_router(
    workspace.router,
    tags=["Workspace"],
    responses={404: {"description": "Not found"}},
)
