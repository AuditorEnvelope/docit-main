"""
API Endpoints Module

Exports all endpoint routers for the API
"""

from . import auth
from . import documentation
from . import events
from . import health
from . import repositories
from . import subscriptions
from . import organizations
from . import repos
from . import docbook
from . import docs
from . import webhooks

__all__ = [
    "auth",
    "documentation",
    "events",
    "health",
    "repositories",
    "subscriptions",
    "organizations",
    "repos",
    "docbook",
    "docs",
    "webhooks",
]
