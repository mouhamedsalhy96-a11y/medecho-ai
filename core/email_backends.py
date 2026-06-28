from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class SendGridAPIEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "SENDGRID_API_KEY", "")
        if not api_key:
            if self.fail_silently:
                return 0
            raise ValueError("SENDGRID_API_KEY is not configured.")

        sent_count = 0

        for message in email_messages:
            try:
                self._send_message(api_key, message)
                sent_count += 1
            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count

    def _send_message(self, api_key, message):
        from_name, from_email = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)

        if not from_email:
            from_name, from_email = parseaddr(settings.DEFAULT_FROM_EMAIL)

        content = [
            {
                "type": "text/plain",
                "value": message.body or "",
            }
        ]

        for content_body, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                content.append(
                    {
                        "type": "text/html",
                        "value": content_body,
                    }
                )

        payload = {
            "personalizations": [
                {
                    "to": [{"email": email} for email in message.to],
                    "subject": message.subject,
                }
            ],
            "from": {
                "email": from_email,
                "name": from_name or "MedEcho AI",
            },
            "content": content,
        }

        if message.cc:
            payload["personalizations"][0]["cc"] = [{"email": email} for email in message.cc]

        if message.bcc:
            payload["personalizations"][0]["bcc"] = [{"email": email} for email in message.bcc]

        if message.reply_to:
            reply_name, reply_email = parseaddr(message.reply_to[0])
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
            timeout=15,
        )

        if response.status_code not in [200, 202]:
            raise RuntimeError(
                f"SendGrid API email failed with status {response.status_code}: {response.text}"
            )