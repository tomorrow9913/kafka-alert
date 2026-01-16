from typing import Dict, Any, Union, List
from email.message import EmailMessage
import aiosmtplib

from .base import BaseProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)


class EmailProvider(BaseProvider):
    async def send(
        self, destination: Union[str, List[str]], payload: Union[Dict[str, Any], str]
    ) -> bool:
        """
        Sends an email via SMTP using aiosmtplib.

        Args:
            destination: Target email address.
            payload: Dict containing 'subject' and 'body', or just a string body.
        """
        # 1. Parse Payload (Envelope Extraction)
        subject = "Alert Notification"
        body = ""

        if isinstance(payload, dict):
            subject = payload.get("subject", subject)
            body = payload.get("body", str(payload))
        else:
            body = str(payload)

        # 2. Construct Message
        message = EmailMessage()
        message["From"] = settings.EMAIL_CONFIG.DEFAULT_FROM_EMAIL
        if isinstance(destination, list):
            destination_str = ",".join(destination)
        else:
            destination_str = destination
        message["To"] = destination_str
        message["Subject"] = subject
        message.set_content(body, subtype="html")

        # 3. Send via SMTP (Non-blocking)
        try:
            logger.info(
                f"Connecting to SMTP server {settings.EMAIL_CONFIG.SMTP_HOST}:{settings.EMAIL_CONFIG.SMTP_PORT}..."
            )

            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_CONFIG.SMTP_HOST,
                port=settings.EMAIL_CONFIG.SMTP_PORT,
                username=settings.EMAIL_CONFIG.SMTP_USER,
                password=settings.EMAIL_CONFIG.SMTP_PASSWORD,
                use_tls=settings.EMAIL_CONFIG.USE_TLS,
            )

            logger.info(f"Email sent successfully to {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {destination}: {e}")
            return False
