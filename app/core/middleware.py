from typing import Callable, Awaitable
from fastapi import Request, Response, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
import time

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT} per minute"],
    storage_uri="memory://"  # In-memory storage for development
)

class RateLimitMiddleware:
    """
    Middleware to handle rate limiting for all incoming requests.
    Integrates with slowapi for rate limiting functionality.
    """
    
    def __init__(self, app):
        self.app = app
        self.limiter = limiter
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        request = Request(scope, receive)
        
        # Skip rate limiting for health checks and public endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await self.app(scope, receive, send)
            
        # Check rate limit
        endpoint = f"{request.method}:{request.url.path}"
        
        try:
            # Simple rate limiting using in-memory counter
            # This is a basic implementation - for production use Redis
            if not hasattr(self.limiter, '_request_counts'):
                self.limiter._request_counts = {}
            
            key = get_remote_address(request)
            current_time = int(time.time())
            minute_key = f"{key}:{current_time // 60}"
            
            # Get current count for this minute
            current_count = self.limiter._request_counts.get(minute_key, 0)
            
            # Check if limit exceeded
            if current_count >= settings.RATE_LIMIT:
                response = Response(
                    content={"detail": "Too many requests"},
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(settings.RATE_LIMIT),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(current_time + 60),
                    }
                )
                await response(scope, receive, send)
                return
            
            # Increment counter
            self.limiter._request_counts[minute_key] = current_count + 1
            
            # Clean up old entries (older than 2 minutes)
            for k in list(self.limiter._request_counts.keys()):
                if int(k.split(':')[1]) < current_time // 60 - 2:
                    del self.limiter._request_counts[k]
                    
        except Exception as e:
            # Log the error but don't block the request
            import logging
            logging.warning(f"Rate limit check failed (continuing): {str(e)}")
            
        # Continue processing the request
        return await self.app(scope, receive, send)

def add_middleware(app):
    """Add rate limiting middleware to the FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    return app
