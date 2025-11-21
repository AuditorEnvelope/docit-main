"""Webhook registration endpoints."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User


router = APIRouter()


class WebhookRegisterRequest(BaseModel):
    """Request payload for registering an organization webhook."""

    org_id: str


class WebhookRegisterResponse(BaseModel):
    """Response payload for registering an organization webhook."""

    status: str
    org_id: str
    webhook_url: str
    message: str


async def _get_user_token_id(db: AsyncSession, user_id: str) -> Optional[str]:
    query = text(
        """
        SELECT token_id
        FROM user_github_tokens
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    result = await db.execute(query, {"user_id": user_id})
    row = result.first()
    return row[0] if row else None


@router.post(
    "/webhook/register",
    response_model=WebhookRegisterResponse,
    status_code=status.HTTP_200_OK,
)
async def register_webhook(
    payload: WebhookRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookRegisterResponse:
    """Register a GitHub organization webhook for the authenticated user."""

    org_id = payload.org_id.strip()
    if not org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org_id cannot be empty")

    user_id = str(user.id)

    try:
        token_id = await _get_user_token_id(db, user_id)

        insert_registration = text(
            """
            INSERT INTO org_registrations (user_id, org_id, registered_at)
            VALUES (:user_id, :org_id, NOW())
            ON CONFLICT (user_id, org_id) DO UPDATE
            SET registered_at = NOW()
            """
        )
        await db.execute(insert_registration, {"user_id": user_id, "org_id": org_id})

        if token_id:
            insert_webhook = text(
                """
                INSERT INTO org_webhooks (user_id, org_id, webhook_secret, github_token_id)
                VALUES (:user_id, :org_id, :webhook_secret, :token_id)
                ON CONFLICT (user_id, org_id) DO UPDATE
                SET updated_at = NOW()
                """
            )
            await db.execute(
                insert_webhook,
                {
                    "user_id": user_id,
                    "org_id": org_id,
                    "token_id": token_id,
                    "webhook_secret": f"webhook_{org_id}",
                },
            )

        await db.commit()

        base_url = os.getenv("WEBHOOK_URL") or os.getenv("NGROK_URL") or "http://localhost:8000"
        webhook_url = base_url.rstrip("/") + "/webhook"

        return WebhookRegisterResponse(
            status="registered",
            org_id=org_id,
            webhook_url=webhook_url,
            message=f"Organization '{org_id}' registered! Configure webhook on GitHub with this URL.",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - log and rethrow as HTTP error
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
