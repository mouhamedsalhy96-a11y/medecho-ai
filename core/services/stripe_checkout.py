import os

import requests

from .billing_products import get_product_config, get_env_price_id


STRIPE_CHECKOUT_SESSIONS_URL = "https://api.stripe.com/v1/checkout/sessions"


def create_checkout_session(request, product_key):
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()

    if not secret_key:
        return {
            "success": False,
            "checkout_url": "",
            "error": "STRIPE_SECRET_KEY is missing.",
        }

    product_config = get_product_config(product_key)

    if not product_config:
        return {
            "success": False,
            "checkout_url": "",
            "error": "Unknown billing product.",
        }

    price_id = get_env_price_id(product_key)

    if not price_id:
        return {
            "success": False,
            "checkout_url": "",
            "error": f"{product_config['env_key']} is missing.",
        }

    success_url = request.build_absolute_uri("/billing/success/")
    cancel_url = request.build_absolute_uri("/billing/cancel/")
    success_url = success_url + "?session_id={CHECKOUT_SESSION_ID}"

    profile = request.user.profile

    data = {
        "mode": product_config["mode"],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(request.user.id),
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[user_id]": str(request.user.id),
        "metadata[product_key]": product_key,
        "metadata[product_label]": product_config["label"],
        "metadata[product_kind]": product_config["kind"],
    }

    if profile.stripe_customer_id:
        data["customer"] = profile.stripe_customer_id
    elif request.user.email:
        data["customer_email"] = request.user.email

    if product_config["mode"] == "subscription":
        data["subscription_data[metadata][user_id]"] = str(request.user.id)
        data["subscription_data[metadata][product_key]"] = product_key
        data["subscription_data[metadata][product_kind]"] = product_config["kind"]

    try:
        response = requests.post(
            STRIPE_CHECKOUT_SESSIONS_URL,
            auth=(secret_key, ""),
            data=data,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        checkout_url = payload.get("url", "")

        if not checkout_url:
            return {
                "success": False,
                "checkout_url": "",
                "error": "Stripe did not return a Checkout URL.",
            }

        return {
            "success": True,
            "checkout_url": checkout_url,
            "error": "",
        }

    except Exception as exc:
        return {
            "success": False,
            "checkout_url": "",
            "error": str(exc),
        }
