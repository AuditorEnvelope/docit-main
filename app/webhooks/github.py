# app/webhooks/github.py
import hmac
import hashlib
import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.event.service import EventService
from app.services.github.service import GitHubService
from app.services.commit_bus import CommitBusService

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
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not await verify_github_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get event details
        event_type = request.headers.get("X-GitHub-Event")
        payload = json.loads(body)
        
        event_service = EventService(db)
        github_service = GitHubService(db_session=db)
        commit_bus = CommitBusService(db)

        # Dispatch based on event type
        if event_type == "installation":
            await github_service.handle_installation_event(payload)
        elif event_type == "installation_repositories":
            await github_service.handle_installation_repositories_event(payload)
        elif event_type == "push":
            commit_event = GitHubService.build_commit_event_data(payload)
            if not commit_event:
                logger.warning("Push payload missing commit data; ignoring")
                return {"status": "ignored"}

            event_id = await commit_bus.store_event(commit_event)
            logger.info("✅ Queued commit event %s for %s", event_id, commit_event["repo_id"])
            logger.info("📋 Event will be processed by worker within 5 seconds (polling interval)")
            return {"status": "queued", "event_id": str(event_id)}
        else:
            handler = getattr(github_service, f"handle_{event_type}_event", None)
            if handler:
                await handler(payload)
            else:
                logger.warning("No handler for GitHub event: %s", event_type)

        # Log non-push events for auditing
        event = await event_service.create_event(
            event_type=f"github.{event_type}",
            payload=payload,
            source="github_webhook"
        )

        return {"status": "accepted", "event_id": str(event.id)}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")