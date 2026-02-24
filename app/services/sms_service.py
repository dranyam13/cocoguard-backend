from twilio.rest import Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_verification_sms(to_phone: str, code: str) -> bool:
    """Send verification code via SMS using Twilio"""
    try:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            logger.warning("Twilio credentials not configured, skipping SMS send")
            return False

        # Initialize Twilio client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # Format phone number to E.164 format if needed
        if not to_phone.startswith("+"):
            # Assume Philippine number if no country code
            to_phone = f"+63{to_phone.lstrip('0')}"

        # Send SMS
        message = client.messages.create(
            body=f"Your CocoGuard verification code is: {code}. This code will expire in 10 minutes.",
            from_=settings.twilio_phone_number,
            to=to_phone
        )

        logger.info(f"Verification SMS sent to {to_phone}, SID: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification SMS: {str(e)}")
        return False
