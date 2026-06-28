from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import cost_views, views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("pricing/", views.pricing, name="pricing"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("account/", views.account, name="account"),

    path("register/", views.register, name="register"),
    path("verification-sent/", views.verification_sent, name="verification_sent"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),

    path("billing/", views.billing, name="billing"),
    path("billing/costs/", cost_views.cost_dashboard, name="cost_dashboard"),
    path("billing/manage/", views.billing_manage, name="billing_manage"),
    path("billing/checkout/<str:product_key>/", views.billing_checkout_placeholder, name="billing_checkout_placeholder"),
    path("billing/success/", views.billing_success, name="billing_success"),
    path("billing/cancel/", views.billing_cancel, name="billing_cancel"),
    path("billing/webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),

    path('our-story/', views.history_view, name='history'),
    path('contact/', views.contact_view, name='contact'),
    path('safety/', views.safety_view, name='safety'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
]
