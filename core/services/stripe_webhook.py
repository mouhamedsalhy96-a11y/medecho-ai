import hmac
import json
import os
import time
from hashlib import sha256

from django.contrib.auth import get_user_model
from django.utils import timezone

from cases.models import CaseUsageEvent
from cases.services.usage import record_usage_event

from .billing_products import BILLING_PRODUCTS, get_live_consultation_pack_amount


CHECKOUT_COMPLETED_EVENT_TYPE = "stripe_checkout_completed"
WEBHOOK_TOLERANCE_SECONDS = 300


def parse_stripe_signature_header(signature_header):
    parts = {}
    for item in signature_header.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts.setdefault(key, []).append(value)
    return parts


def verify_stripe_signature(payload_bytes, signature_header):
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

    if not endpoint_secret:
        return {
            "success": False,
            "error": "STRIPE_WEBHOOK_SECRET is missing.",
        }

    if not signature_header:
        return {
            "success": False,
            "error": "Stripe-Signature header is missing.",
        }

    try:
        signature_parts = parse_stripe_signature_header(signature_header)
        timestamp = signature_parts.get("t", [""])[0]
        signatures = signature_parts.get("v1", [])

        if not timestamp or not signatures:
            return {
                "success": False,
                "error": "Stripe-Signature header is malformed.",
            }

        timestamp_int = int(timestamp)
        now = int(time.time())

        if abs(now - timestamp_int) > WEBHOOK_TOLERANCE_SECONDS:
            return {
                "success": False,
                "error": "Stripe webhook timestamp is outside tolerance.",
            }

        signed_payload = timestamp.encode("utf-8") + b"." + payload_bytes
        expected_signature = hmac.new(
            endpoint_secret.encode("utf-8"),
            signed_payload,
            sha256,
        ).hexdigest()

        signature_matches = any(
            hmac.compare_digest(expected_signature, received_signature)
            for received_signature in signatures
        )

        if not signature_matches:
            return {
                "success": False,
                "error": "Stripe webhook signature verification failed.",
            }

        return {
            "success": True,
            "error": "",
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def parse_event(payload_bytes):
    try:
        return {
            "success": True,
            "event": json.loads(payload_bytes.decode("utf-8")),
            "error": "",
        }
    except Exception as exc:
        return {
            "success": False,
            "event": None,
            "error": str(exc),
        }


def stripe_session_already_processed(session_id):
    if not session_id:
        return False

    return CaseUsageEvent.objects.filter(
        event_type=CHECKOUT_COMPLETED_EVENT_TYPE,
        metadata__stripe_session_id=session_id,
    ).exists()


def grant_checkout_session(session_object):
    session_id = session_object.get("id", "")
    metadata = session_object.get("metadata") or {}
    product_key = metadata.get("product_key", "")
    user_id = metadata.get("user_id") or session_object.get("client_reference_id")

    if not session_id:
        return {
            "success": False,
            "message": "Checkout session ID missing.",
        }

    if stripe_session_already_processed(session_id):
        return {
            "success": True,
            "message": "Checkout session already processed.",
        }

    product_config = BILLING_PRODUCTS.get(product_key)

    if not product_config:
        return {
            "success": False,
            "message": f"Unknown product key: {product_key}",
        }

    if not user_id:
        return {
            "success": False,
            "message": "User ID missing from Checkout metadata.",
        }

    User = get_user_model()
    user = User.objects.get(id=user_id)
    profile = user.profile

    stripe_customer_id = session_object.get("customer", "") or ""
    stripe_subscription_id = session_object.get("subscription", "") or ""

    grant_kind = product_config["kind"]
    grant_summary = ""
    update_fields = []

    if stripe_customer_id and profile.stripe_customer_id != stripe_customer_id:
        profile.stripe_customer_id = stripe_customer_id
        update_fields.append("stripe_customer_id")

    if grant_kind == "subscription":
        profile.plan = product_config["plan"]
        update_fields.append("plan")
        grant_summary = f"Subscription plan set to {product_config['plan']}"

    elif grant_kind == "payg_credits":
        amount = product_config["amount"]
        profile.payg_credits += amount
        update_fields.append("payg_credits")
        grant_summary = f"Added {amount} practice credits"

    elif grant_kind == "real_consultation_credits":
        amount = get_live_consultation_pack_amount()
        profile.real_consultation_credits += amount
        update_fields.append("real_consultation_credits")
        grant_summary = f"Added {amount} Live Consultation credits"

    else:
        return {
            "success": False,
            "message": f"Unsupported grant kind: {grant_kind}",
        }

    if update_fields:
        profile.save(update_fields=list(dict.fromkeys(update_fields)))

    record_usage_event(
        user=user,
        event_type=CHECKOUT_COMPLETED_EVENT_TYPE,
        metadata={
            "stripe_session_id": session_id,
            "stripe_customer": stripe_customer_id,
            "stripe_subscription": stripe_subscription_id,
            "payment_status": session_object.get("payment_status", ""),
            "mode": session_object.get("mode", ""),
            "product_key": product_key,
            "grant_kind": grant_kind,
            "grant_summary": grant_summary,
            "processed_at": timezone.now().isoformat(),
        },
    )

    return {
        "success": True,
        "message": grant_summary,
    }


def process_stripe_event(event):
    event_type = event.get("type", "")

    if event_type != "checkout.session.completed":
        return {
            "success": True,
            "message": f"Ignored event type: {event_type}",
        }

    session_object = event.get("data", {}).get("object", {})

    payment_status = session_object.get("payment_status", "")
    mode = session_object.get("mode", "")

    if mode == "payment" and payment_status != "paid":
        return {
            "success": True,
            "message": f"Payment mode session ignored because payment_status is {payment_status}.",
        }

    return grant_checkout_session(session_object)
