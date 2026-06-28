import os


BILLING_PRODUCTS = {
    "starter": {
        "name": "Starter",
        "label": "Starter subscription",
        "kind": "subscription",
        "mode": "subscription",
        "env_key": "STRIPE_STARTER_PRICE_ID",
        "display_price": "$9/month",
        "description": "For regular text practice.",
        "features": [
            "25 text cases/month",
            "Text patient chat",
            "Text investigation reports",
            "Live Consultation packs sold separately",
        ],
        "plan": "starter",
    },
    "student": {
        "name": "Student",
        "label": "Student subscription",
        "kind": "subscription",
        "mode": "subscription",
        "env_key": "STRIPE_STUDENT_PRICE_ID",
        "display_price": "$19/month",
        "description": "For students and exam candidates.",
        "features": [
            "100 text cases/month",
            "20 patient voice generations/month",
            "20 educational image investigations/month",
            "Live Consultation packs sold separately",
        ],
        "plan": "student",
    },
    "pro": {
        "name": "Pro",
        "label": "Pro subscription",
        "kind": "subscription",
        "mode": "subscription",
        "env_key": "STRIPE_PRO_PRICE_ID",
        "display_price": "$39/month",
        "description": "For high-volume practice and tutors.",
        "features": [
            "300 text cases/month",
            "100 patient voice generations/month",
            "100 educational image investigations/month",
            "Live Consultation packs sold separately",
        ],
        "plan": "pro",
    },
    "credit_5": {
        "name": "5 practice credits",
        "label": "5 practice credits",
        "kind": "payg_credits",
        "mode": "payment",
        "env_key": "STRIPE_CREDIT_5_PRICE_ID",
        "display_price": "$5",
        "description": "Small top-up pack.",
        "amount": 5,
    },
    "credit_10": {
        "name": "10 practice credits",
        "label": "10 practice credits",
        "kind": "payg_credits",
        "mode": "payment",
        "env_key": "STRIPE_CREDIT_10_PRICE_ID",
        "display_price": "$10",
        "description": "Medium top-up pack.",
        "amount": 10,
    },
    "credit_25": {
        "name": "25 practice credits",
        "label": "25 practice credits",
        "kind": "payg_credits",
        "mode": "payment",
        "env_key": "STRIPE_CREDIT_25_PRICE_ID",
        "display_price": "$25",
        "description": "Best value practice credit pack.",
        "amount": 25,
    },
    "real_consultation_pack": {
        "name": "Live Consultation pack",
        "label": "Live Consultation credit pack",
        "kind": "real_consultation_credits",
        "mode": "payment",
        "env_key": "STRIPE_PRICE_REAL_CONSULTATION_PACK",
        "display_price": "$20",
        "description": "5 live consultations.",
        "amount_env_key": "STRIPE_REAL_CONSULTATION_PACK_CREDITS",
        "default_amount": 5,
    },
}


SUBSCRIPTION_PRODUCT_KEYS = ["starter", "student", "pro"]
PAYG_PRODUCT_KEYS = ["credit_5", "credit_10", "credit_25"]
LIVE_CONSULTATION_PRODUCT_KEYS = ["real_consultation_pack"]


def get_product_config(product_key):
    return BILLING_PRODUCTS.get(product_key)


def get_env_price_id(product_key):
    product_config = get_product_config(product_key)
    if not product_config:
        return ""
    return os.getenv(product_config["env_key"], "").strip()


def get_live_consultation_pack_amount():
    product_config = BILLING_PRODUCTS["real_consultation_pack"]
    raw_value = os.getenv(
        product_config["amount_env_key"],
        str(product_config["default_amount"]),
    ).strip()
    try:
        amount = int(raw_value)
    except ValueError:
        amount = product_config["default_amount"]
    return max(amount, 1)


def build_product_cards(product_keys):
    cards = []
    for product_key in product_keys:
        config = BILLING_PRODUCTS[product_key]
        card = {
            "key": product_key,
            "name": config["name"],
            "price": config["display_price"],
            "description": config["description"],
            "features": config.get("features", []),
            "configured": bool(get_env_price_id(product_key)),
        }
        if product_key == "real_consultation_pack":
            amount = get_live_consultation_pack_amount()
            card["description"] = f"{amount} live consultation{'s' if amount != 1 else ''}."
        cards.append(card)
    return cards
