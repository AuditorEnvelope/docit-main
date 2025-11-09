from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import psutil
import os

from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connection and return status"""
    try:
        start_time = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "latency_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    process = psutil.Process(os.getpid())
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": process.memory_percent(),
        "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
        "uptime_seconds": (datetime.utcnow() - datetime.fromtimestamp(process.create_time())).total_seconds()
    }

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint that verifies the status of the application and its dependencies.
    Returns a 200 status code if the application is healthy, 503 otherwise.
    """
    checks = {
        "database": await check_database(db),
        "system": await get_system_metrics(),
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check if any component is unhealthy
    is_healthy = all(
        check.get("status") != "unhealthy"
        for check in checks.values()
        if isinstance(check, dict) and "status" in check
    )
    
    status_code = 200 if is_healthy else 503
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        **checks
    }

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # This would be implemented with prometheus_client in a real application
    return {
        "status": "ok",
        "message": "Metrics endpoint would return Prometheus metrics in production"
    }
