"""
Main FastAPI Application

This module initializes the FastAPI application and sets up all the necessary
middleware, routes, and background tasks.
"""

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Set
from urllib.parse import unquote

import httpx
from fastapi import FastAPI, Request, status, Depends, BackgroundTasks, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from app.core.config import settings
from app.core.middleware import RateLimitMiddleware, add_middleware
from app.db.session import async_session, get_session
from app.db.init_db import init_models
from app.models.events import EventStatus
from app.schemas.events import EventUpdate
from app.services.auth import get_current_user
from app.services.event.service import EventService
from app.services.event.processor import EventProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to hold background tasks
background_tasks: Set[asyncio.Task] = set()

# Import API routers
from app.api.v1 import api_router
from app.api.v1.endpoints.auth import (
    install_reader_app as api_install_reader_app,
    install_writer_app as api_install_writer_app,
)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    async def dispatch(self, request: StarletteRequest, call_next):
        start_time = time.time()
        
        # Skip logging for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        logger.info("Request: %s %s", request.method, request.url)
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            logger.info(
                "Response: %s %s - Status: %d - Time: %.2fms",
                request.method,
                request.url,
                response.status_code,
                process_time
            )
            
            return response
            
        except Exception as e:
            logger.error("Error processing request: %s", str(e), exc_info=True)
            raise

async def process_event_background(event_id: str) -> None:
    """Background task to process an event"""
    db = await get_session()
    try:
        event_service = EventService(db)
        event_processor = EventProcessor(db)
        
        # Get the event with a fresh session
        async with db.begin():
            event = await event_service.get_event(event_id, for_update=True)
            if not event:
                logger.error("Event %s not found for processing", event_id)
                return
            
            # Process the event
            success = await event_processor.process(event)
            
            # Update event status
            status = EventStatus.COMPLETED if success else EventStatus.FAILED
            await event_service.update_event(
                event_id,
                EventUpdate(
                    status=status,
                    processed_at=datetime.utcnow()
                )
            )
            
    except Exception as e:
        logger.error(
            "Error processing event %s in background: %s",
            event_id,
            str(e),
            exc_info=True
        )
        # Update event status to failed
        try:
            event_service = EventService(db)
            await event_service.update_event(
                event_id,
                EventUpdate(
                    status=EventStatus.FAILED,
                    error=str(e),
                    processed_at=datetime.utcnow()
                )
            )
        except Exception as update_error:
            logger.error("Failed to update event status: %s", str(update_error))
    finally:
        await db.close()

async def run_event_processor():
    """Background task to process events"""
    logger.info("Starting event processor...")
    
    while True:
        try:
            db = await get_session()
            try:
                event_service = EventService(db)
                event_processor = EventProcessor(db)
                
                # Get pending events
                pending_events = await event_service.get_pending_events()
                
                for event in pending_events:
                    try:
                        # Process the event in the background
                        task = asyncio.create_task(process_event_background(event.id))
                        background_tasks.add(task)
                        task.add_done_callback(background_tasks.discard)
                        
                    except Exception as e:
                        logger.error("Error processing event %s: %s", event.id, str(e))
                
                # Wait before checking for more events
                await asyncio.sleep(settings.EVENT_POLL_INTERVAL)
            finally:
                await db.close()
                
        except asyncio.CancelledError:
            logger.info("Event processor stopped")
            break
        except Exception as e:
            logger.error("Error in event processor: %s", str(e), exc_info=True)
            await asyncio.sleep(5)  # Back off on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup
    logger.info("Starting application...")
    await init_models()
    
    # Start the event processing loop if enabled
    if settings.ENABLE_EVENT_PROCESSOR:
        logger.info("Starting background event processor...")
        task = asyncio.create_task(run_event_processor())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
    
    try:
        yield  # The application runs here
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        # Create a copy of tasks to avoid "Set changed size during iteration"
        tasks_to_cancel = list(background_tasks)
        for task in tasks_to_cancel:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Application shutdown complete")


def _cors_wildcard_origin_regex(origins: list) -> str | None:
    """
    Map BACKEND_CORS_ORIGINS entries like https://*.docit.in to a regex Starlette can use.
    Browsers send an exact Origin (e.g. https://org.docit.in); wildcard strings are not
    valid in Access-Control-Allow-Origin, so they must be expressed via allow_origin_regex.
    """
    patterns: list[str] = []
    for origin in origins or []:
        o = str(origin).strip()
        if o.startswith("https://*."):
            domain = o.removeprefix("https://*.").strip("/")
            if domain:
                patterns.append(rf"^https://[a-zA-Z0-9-]+\.{re.escape(domain)}$")
        elif o.startswith("http://*."):
            domain = o.removeprefix("http://*.").strip("/")
            if domain:
                patterns.append(rf"^http://[a-zA-Z0-9-]+\.{re.escape(domain)}$")
    if not patterns:
        return None
    if len(patterns) == 1:
        return patterns[0]
    return "(?:" + "|".join(patterns) + ")"


def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="DocIt AI - Automated Documentation System",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        redoc_favicon_url="/static/favicon.ico" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add middleware
    application.add_middleware(LoggingMiddleware)
    application = add_middleware(application)  # Rate limiting
    application.add_middleware(RateLimitMiddleware)

    # Configure CORS - Always enable for development
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # Add configured origins if any (filter out wildcard patterns — handled via regex below)
    if settings.BACKEND_CORS_ORIGINS:
        for origin in settings.BACKEND_CORS_ORIGINS:
            origin_str = str(origin)
            if origin_str.startswith("https://*.") or origin_str.startswith(
                "http://*."
            ):
                continue
            cors_origins.append(origin_str)

    origin_regex = _cors_wildcard_origin_regex(settings.BACKEND_CORS_ORIGINS)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Legacy auth routes (without /api/v1 prefix) for GitHub app installs
    legacy_auth_router = APIRouter(prefix="/auth", tags=["Auth"])

    @legacy_auth_router.get("/install-reader-app")
    async def legacy_install_reader_app():
        return await api_install_reader_app()

    @legacy_auth_router.get("/install-writer-app")
    async def legacy_install_writer_app():
        return await api_install_writer_app()

    # Include API routers
    application.include_router(api_router, prefix=settings.API_V1_STR)
    application.include_router(legacy_auth_router)

    # Add security headers middleware
    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
    
    # Health check endpoint
    @application.get("/health", include_in_schema=False)
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "ok",
            "version": "1.0.0",
            "environment": "development" if settings.DEBUG else "production"
        }
    
    # Exception handlers
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error("Validation error: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
    
    @application.exception_handler(404)
    async def not_found_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Not Found"},
        )
    
    @application.exception_handler(500)
    async def server_error_exception_handler(request: Request, exc: Exception):
        logger.error("Server error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
    
    return application

# Create the FastAPI application
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=logging.getLevelName(settings.LOG_LEVEL).lower(),
    )
