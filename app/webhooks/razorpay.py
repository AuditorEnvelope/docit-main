"""
Razorpay Webhook Handler

Handles Razorpay webhooks for payment processing and subscription updates.
"""
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.razorpay_service import RazorpayService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", status_code=200)
async def handle_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle Razorpay webhooks
    Receives payment, subscription, and order events from Razorpay
    """
    try:
        # Get raw payload and signature
        payload = await request.body()
        # Check for the signature header - FastAPI normalizes headers to lowercase
        signature = (request.headers.get("x-razorpay-signature") or
                     request.headers.get("X-Razorpay-Signature"))

        if not signature:
            logger.error("❌ Missing Razorpay signature in webhook")
            logger.error(f"Available headers: {dict(request.headers)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Razorpay-Signature header"
            )

        logger.info(
            f"🔔 Razorpay webhook received with signature: {signature[:10]}...")

        # Create Razorpay service instance
        razorpay_service = RazorpayService(db)

        # Handle the webhook
        result = await razorpay_service.handle_webhook(payload, signature)

        logger.info(f"✅ Razorpay webhook processed successfully: {result}")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON payload in Razorpay webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(
            f"❌ Error processing Razorpay webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook"
        )
