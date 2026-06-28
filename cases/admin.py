from django.contrib import admin

from .models import (
    CaseUsageEvent,
    ClinicalCase,
    EncounterMessage,
    RealConsultationSession,
)


class EncounterMessageInline(admin.TabularInline):
    model = EncounterMessage
    extra = 0
    readonly_fields = (
        "created_at",
        "voice_generated_at",
        "image_generated_at",
    )


@admin.register(ClinicalCase)
class ClinicalCaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "presenting_complaint",
        "specialty",
        "difficulty",
        "status",
        "created_at",
        "completed_at",
    )
    list_filter = (
        "status",
        "specialty",
        "difficulty",
        "created_at",
        "completed_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "patient_name",
        "presenting_complaint",
        "hidden_diagnosis",
    )
    readonly_fields = (
        "created_at",
        "completed_at",
    )
    inlines = [
        EncounterMessageInline,
    ]


@admin.register(EncounterMessage)
class EncounterMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "clinical_case",
        "role",
        "created_at",
        "voice_generated_at",
        "image_generated_at",
    )
    list_filter = (
        "role",
        "created_at",
        "voice_generated_at",
        "image_generated_at",
    )
    search_fields = (
        "clinical_case__presenting_complaint",
        "clinical_case__user__username",
        "content",
    )
    readonly_fields = (
        "created_at",
        "voice_generated_at",
        "image_generated_at",
    )


@admin.register(CaseUsageEvent)
class CaseUsageEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "event_type",
        "clinical_case",
        "encounter_message",
        "created_at",
    )
    list_filter = (
        "event_type",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "clinical_case__presenting_complaint",
    )
    readonly_fields = (
        "created_at",
    )


@admin.register(RealConsultationSession)
class RealConsultationSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "clinical_case",
        "status",
        "duration_seconds",
        "real_consultation_credit_charged",
        "turn_count",
        "started_at",
        "ended_at",
        "created_at",
    )
    list_filter = (
        "status",
        "real_consultation_credit_charged",
        "created_at",
        "started_at",
        "ended_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "clinical_case__presenting_complaint",
    )
    readonly_fields = (
        "created_at",
    )