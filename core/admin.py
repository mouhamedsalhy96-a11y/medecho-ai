from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "plan",
        "payg_credits",
        "real_consultation_credits",
        "email_verified",
        "created_at",
    )
    list_filter = (
        "plan",
        "email_verified",
        "level",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "full_name",
        "phone_number",
        "stripe_customer_id",
    )
    readonly_fields = (
        "created_at",
    )