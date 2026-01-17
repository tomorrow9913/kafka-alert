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
        Sends an email via SMTP, correctly handling To, Cc, and Bcc.
        """
        # 1. Parse Payload & Normalize Destination
        if isinstance(destination, str):
            to_addrs = [destination]
        else:
            to_addrs = destination

        headers = payload.get("headers", {}) if isinstance(payload, dict) else {}
        body = (
            payload.get("body", str(payload))
            if isinstance(payload, dict)
            else str(payload)
        )

        # 2. Extract Recipients and Subject
        subject = headers.get("subject", "Alert Notification")
        cc_addrs = headers.get("cc", [])
        bcc_addrs = headers.get("bcc", [])

        # 3. Construct Message
        message = EmailMessage()
        message["From"] = settings.EMAIL_CONFIG.DEFAULT_FROM_EMAIL
        message["To"] = ",".join(to_addrs)
        if cc_addrs:
            message["Cc"] = ",".join(cc_addrs)
        message["Subject"] = subject
        message.set_content(body, subtype="html")

        # 4. Determine Envelope Recipients
        all_recipients = list(set(to_addrs + cc_addrs + bcc_addrs))

        # 5. Send via SMTP
        try:
            logger.info(
                f"Connecting to SMTP server {settings.EMAIL_CONFIG.SMTP_HOST}:{settings.EMAIL_CONFIG.SMTP_PORT}..."
            )
            await aiosmtplib.send(
                message,
                recipients=all_recipients,
                hostname=settings.EMAIL_CONFIG.SMTP_HOST,
                port=settings.EMAIL_CONFIG.SMTP_PORT,
                username=settings.EMAIL_CONFIG.SMTP_USER,
                password=settings.EMAIL_CONFIG.SMTP_PASSWORD,
                use_tls=settings.EMAIL_CONFIG.USE_TLS,
            )
            logger.info(f"Email sent successfully to {all_recipients}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {all_recipients}: {e}")
            return False
