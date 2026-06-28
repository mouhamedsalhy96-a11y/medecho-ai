import logging
import os

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services.stripe_webhook import parse_event, process_stripe_event, verify_stripe_signature
from .services.billing_products import (
    LIVE_CONSULTATION_PRODUCT_KEYS,
    PAYG_PRODUCT_KEYS,
    SUBSCRIPTION_PRODUCT_KEYS,
    build_product_cards,
)
from cases.services.usage import get_usage_summary
from .services.stripe_checkout import create_checkout_session
from .forms import CustomUserCreationForm, ProfileUpdateForm, ResendVerificationForm
from .models import UserProfile
from .tokens import email_verification_token

User = get_user_model()
logger = logging.getLogger(__name__)


def get_or_create_profile(user):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def send_verification_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    verification_path = reverse("verify_email", kwargs={"uidb64": uidb64, "token": token})
    verification_url = request.build_absolute_uri(verification_path)

    subject = "Verify your MedEcho AI email address"

    message = f"""
Hello {user.first_name or user.username},

Welcome to MedEcho AI.

Please verify your email address by opening this link:

{verification_url}

If you did not create this account, you can ignore this email.

MedEcho AI
Educational simulation only. Not for diagnosis or patient care.
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "Verification email failed. user_id=%s email=%s",
            user.pk,
            user.email,
        )
        messages.warning(
            request,
            "Your account was created, but the verification email could not be sent. Please use resend verification or contact support.",
        )
        return False

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/landing.html")


def pricing(request):
    return render(request, "core/pricing.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(request, user)
            request.session["verification_email"] = user.email
            return redirect("verification_sent")
    else:
        form = CustomUserCreationForm()
    return render(request, "core/register.html", {"form": form})


def verification_sent(request):
    email = request.session.get("verification_email", "")
    return render(request, "core/verification_sent.html", {"email": email})


def verify_email(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is None:
        return render(request, "core/verification_invalid.html")
    if not email_verification_token.check_token(user, token):
        return render(request, "core/verification_invalid.html")
    profile = get_or_create_profile(user)
    profile.email_verified = True
    profile.save()
    user.is_active = True
    user.save()
    messages.success(request, "Your email has been verified. You can now log in.")
    return render(request, "core/verification_success.html")


def resend_verification(request):
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            user = User.objects.filter(email__iexact=email).first()
            if user:
                profile = get_or_create_profile(user)
                if profile.email_verified and user.is_active:
                    messages.info(request, "This email address is already verified.")
                    return redirect("login")
                send_verification_email(request, user)
                request.session["verification_email"] = user.email
            messages.success(request, "If an unverified account exists for that email, a new verification link has been sent.")
            return redirect("verification_sent")
    else:
        form = ResendVerificationForm()
    return render(request, "core/resend_verification.html", {"form": form})


@login_required
def dashboard(request):
    profile = get_or_create_profile(request.user)
    usage = get_usage_summary(request.user)
    return render(request, "core/dashboard.html", {"profile": profile, "usage": usage})


@login_required
def account(request):
    profile = get_or_create_profile(request.user)
    usage = get_usage_summary(request.user)
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, user=request.user, profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Account details updated.")
            return redirect("account")
    else:
        form = ProfileUpdateForm(user=request.user, profile=profile)
    return render(request, "core/account.html", {"profile": profile, "usage": usage, "form": form})


@login_required
def billing(request):
    profile = request.user.profile
    usage = get_usage_summary(request.user)
    return render(
        request,
        "core/billing.html",
        {
            "profile": profile,
            "usage": usage,
            "plan_cards": build_product_cards(SUBSCRIPTION_PRODUCT_KEYS),
            "payg_packs": build_product_cards(PAYG_PRODUCT_KEYS),
            "real_consultation_packs": build_product_cards(LIVE_CONSULTATION_PRODUCT_KEYS),
        },
    )


@login_required
def billing_checkout_placeholder(request, product_key):
    if request.method != "POST":
        return redirect("billing")
    checkout_result = create_checkout_session(request=request, product_key=product_key)
    if not checkout_result["success"]:
        messages.error(request, f"Could not start checkout: {checkout_result['error']}")
        return redirect("billing")
    return redirect(checkout_result["checkout_url"])


@login_required
def billing_manage(request):
    profile = get_or_create_profile(request.user)
    if not profile.stripe_customer_id:
        messages.info(request, "You do not have an active billing portal yet. Start a plan or purchase first.")
        return redirect("billing")
    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not stripe_secret_key:
        messages.error(request, "Billing management is not available yet.")
        return redirect("billing")
    stripe.api_key = stripe_secret_key
    try:
        portal_session = stripe.billing_portal.Session.create(customer=profile.stripe_customer_id, return_url=request.build_absolute_uri(reverse("billing")))
        return redirect(portal_session.url)
    except Exception as exc:
        messages.error(request, f"Could not open billing management: {exc}")
        return redirect("billing")


@login_required
def billing_success(request):
    messages.success(request, "Payment successful. Your account will update as soon as Stripe confirms the checkout.")
    return render(request, "core/billing_success.html")


@login_required
def billing_cancel(request):
    return render(request, "core/billing_cancel.html")


@csrf_exempt
def stripe_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    payload = request.body
    signature_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    signature_result = verify_stripe_signature(payload_bytes=payload, signature_header=signature_header)
    if not signature_result["success"]:
        return JsonResponse({"error": signature_result["error"]}, status=400)
    event_result = parse_event(payload)
    if not event_result["success"]:
        return JsonResponse({"error": event_result["error"]}, status=400)
    process_result = process_stripe_event(event_result["event"])
    if not process_result["success"]:
        return JsonResponse({"error": process_result["message"]}, status=400)
    return JsonResponse({"received": True, "message": process_result["message"]})

def history_view(request):
    return render(request, 'core/history.html')

def contact_view(request):
    return render(request, 'core/contact.html')

def safety_view(request):
    return render(request, 'core/safety.html')

def privacy_policy_view(request):
    return render(request, 'core/privacy_policy.html')

def terms_of_service_view(request):
    return render(request, 'core/terms_of_service.html')