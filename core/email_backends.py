import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class SendGridAPIEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "SENDGRID_API_KEY", "").strip()

        if not api_key:
            message = "SENDGRID_API_KEY is not configured."
            logger.error(message)
            if self.fail_silently:
                return 0
            raise ValueError(message)

        sent_count = 0

        for email_message in email_messages:
            try:
                self._send_message(api_key=api_key, email_message=email_message)
                sent_count += 1
            except Exception:
                logger.exception(
                    "SendGrid email send failed. subject=%r recipients=%r",
                    getattr(email_message, "subject", ""),
                    getattr(email_message, "to", []),
                )
                if not self.fail_silently:
                    raise

        return sent_count

    def _send_message(self, api_key, email_message):
        from_name, from_email = parseaddr(
            email_message.from_email or settings.DEFAULT_FROM_EMAIL
        )

        if not from_email:
            from_name, from_email = parseaddr(settings.DEFAULT_FROM_EMAIL)

        if not from_email:
            raise ValueError("No valid from_email configured for SendGrid.")

        recipients = [{"email": email} for email in email_message.to]

        if not recipients:
            raise ValueError("No recipients provided for SendGrid email.")

        content = [
            {
                "type": "text/plain",
                "value": email_message.body or "",
            }
        ]

        for alternative_body, mimetype in getattr(email_message, "alternatives", []):
            if mimetype == "text/html":
                content.append(
                    {
                        "type": "text/html",
                        "value": alternative_body,
                    }
                )

        personalization = {
            "to": recipients,
            "subject": email_message.subject or "",
        }

        if getattr(email_message, "cc", None):
            personalization["cc"] = [{"email": email} for email in email_message.cc]

        if getattr(email_message, "bcc", None):
            personalization["bcc"] = [{"email": email} for email in email_message.bcc]

        payload = {
            "personalizations": [personalization],
            "from": {
                "email": from_email,
                "name": from_name or "MedEcho AI",
            },
            "content": content,
        }

        if getattr(email_message, "reply_to", None):
            reply_name, reply_email = parseaddr(email_message.reply_to[0])
            if reply_email:
                payload["reply_to"] = {
                    "email": reply_email,
                    "name": reply_name or from_name or "MedEcho AI",
                }

        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )

        if response.status_code != 202:
            logger.error(
                "SendGrid API returned error. status=%s response=%s payload_from=%s payload_to=%s",
                response.status_code,
                response.text,
                from_email,
                [item["email"] for item in recipients],
            )
            raise RuntimeError(
                f"SendGrid API email failed with status {response.status_code}: {response.text}"
            )

        logger.info(
            "SendGrid email accepted. subject=%r to=%r",
            email_message.subject,
            [item["email"] for item in recipients],
        )