# app/webhooks/github.py
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import hmac
import hashlib
import json
import logging

from app.core.config import settings
from app.db.session import get_db
from app.services.event.service import EventService
from app.services.github.service import GitHubService

router = APIRouter()
logger = logging.getLogger(__name__)

async def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """Enhanced signature verification with better error handling"""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
        
    try:
        hash_object = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signature: {str(e)}"
        )

@router.post("/github", status_code=202)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Handle GitHub webhooks with event tracking"""
    try:
        # Verify signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()
        await verify_github_signature(body, signature)
        
        # Get event details
        event_type = request.headers.get("X-GitHub-Event")
        payload = json.loads(body)
        
        event_service = EventService(db)
        github_service = GitHubService(db_pool=settings.DB_POOL)

        # Log the event
        event = await event_service.create_event(
            event_type=f"github.{event_type}",
            payload=payload,
            source="github_webhook"
        )

        # Dispatch based on event type
        if event_type == "installation":
            await github_service.handle_installation_event(payload)
        elif event_type == "installation_repositories":
            await github_service.handle_installation_repositories_event(payload)
        else:
            handler = getattr(github_service, f"handle_{event_type}_event", None)
            if handler:
                await handler(payload)
            else:
                logger.warning("No handler for GitHub event: %s", event_type)

        return {"status": "accepted", "event_id": str(event.id)}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")