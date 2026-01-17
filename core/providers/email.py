from typing import Dict, Any, Union, List
from email.message import EmailMessage
import aiosmtplib

from .base import BaseProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)


class EmailProvider(BaseProvider):
    def apply_template_rules(self, template_name: str) -> str:
        return f"{template_name}.html.j2"

    def format_payload(
        self, rendered_content: Union[Dict[str, Any], str], metadata: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        if not isinstance(rendered_content, str):
            logger.error("EmailProvider requires a string to be rendered.")
            return {"subject": "Error", "body": ""}
        # Assumes the first line is the subject
        parts = rendered_content.split("\n", 1)
        subject = parts[0].strip()
        body = parts[1].strip() if len(parts) > 1 else ""
        return {"subject": subject, "body": body}

    def get_fallback_payload(
        self, error: Exception, context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        subject = f"🚨 Kafka Alert Error on Topic {context.get('topic', 'N/A')}"
        body = (
            f"<h1>An error occurred while processing a Kafka message.</h1>"
            f"<p><strong>Topic:</strong> {context.get('topic', 'N/A')}</p>"
            f"<p><strong>Partition:</strong> {context.get('partition', 'N/A')}</p>"
            f"<p><strong>Offset:</strong> {context.get('offset', 'N/A')}</p>"
            f"<p><strong>Error:</strong> <pre>{error}</pre></p>"
        )
        return {"subject": subject, "body": body}

    async def send(
        self, destination: Union[str, List[str]], payload: Union[Dict[str, Any], str]
    ) -> bool:
        """
        Sends an email via SMTP using aiosmtplib.

        Args:
            destination: Target email address.
            payload: Dict containing 'subject' and 'body'.
        """
        if (
            not isinstance(payload, dict)
            or "subject" not in payload
            or "body" not in payload
        ):
            logger.error(
                "EmailProvider requires a dict payload with 'subject' and 'body'."
            )
            return False

        subject = payload["subject"]
        body = payload["body"]

        message = EmailMessage()
        message["From"] = settings.EMAIL_CONFIG.DEFAULT_FROM_EMAIL
        if isinstance(destination, list):
            destination_str = ",".join(destination)
        else:
            destination_str = destination
        message["To"] = destination_str
        message["Subject"] = subject
        message.set_content(body, subtype="html")

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
