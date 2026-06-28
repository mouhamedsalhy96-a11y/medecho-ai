from django.conf import settings
from django.db import models


class CaseUsageEvent(models.Model):
    EVENT_TEXT_CASE = "text_case"
    EVENT_VOICE_GENERATION = "voice_generation"
    EVENT_IMAGE_INVESTIGATION = "image_investigation"
    EVENT_REAL_CONSULTATION_STARTED = "real_consultation_started"
    EVENT_REAL_CONSULTATION_COMPLETED = "real_consultation_completed"

    EVENT_CHOICES = [
        (EVENT_TEXT_CASE, "Text case"),
        (EVENT_VOICE_GENERATION, "Voice generation"),
        (EVENT_IMAGE_INVESTIGATION, "Image investigation"),
        (EVENT_REAL_CONSULTATION_STARTED, "Real consultation started"),
        (EVENT_REAL_CONSULTATION_COMPLETED, "Real consultation completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_events",
    )

    clinical_case = models.ForeignKey(
        "ClinicalCase",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_events",
    )

    encounter_message = models.ForeignKey(
        "EncounterMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_events",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "event_type", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.get_event_type_display()} - {self.created_at:%Y-%m-%d %H:%M}"


class ClinicalCase(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_DELETED = "deleted"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_DELETED, "Deleted"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinical_cases",
    )

    specialty = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=50, blank=True)

    patient_name = models.CharField(max_length=255, blank=True)
    patient_age = models.PositiveIntegerField(null=True, blank=True)
    presenting_complaint = models.CharField(max_length=255, blank=True)

    hidden_diagnosis = models.CharField(max_length=255, blank=True)
    case_summary = models.TextField(blank=True)
    secret_prompt = models.TextField(blank=True)

    voice_style = models.CharField(max_length=100, default="neutral_adult")

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    final_diagnosis = models.TextField(blank=True)
    differentials = models.TextField(blank=True)
    investigation_interpretation = models.TextField(blank=True)
    management_plan = models.TextField(blank=True)
    safety_netting = models.TextField(blank=True)

    overall_score = models.PositiveIntegerField(null=True, blank=True)
    data_gathering_score = models.PositiveIntegerField(null=True, blank=True)
    clinical_reasoning_score = models.PositiveIntegerField(null=True, blank=True)
    management_score = models.PositiveIntegerField(null=True, blank=True)
    ips_score = models.PositiveIntegerField(null=True, blank=True)
    safety_netting_score = models.PositiveIntegerField(null=True, blank=True)

    overall_feedback = models.TextField(blank=True)
    data_gathering_feedback = models.TextField(blank=True)
    clinical_reasoning_feedback = models.TextField(blank=True)
    management_feedback = models.TextField(blank=True)
    ips_feedback = models.TextField(blank=True)
    safety_netting_feedback = models.TextField(blank=True)
    critical_misses = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    improvement_plan = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        complaint = self.presenting_complaint or "Clinical case"
        return f"{complaint} - {self.user}"


class EncounterMessage(models.Model):
    ROLE_DOCTOR = "doctor"
    ROLE_PATIENT = "patient"
    ROLE_INVESTIGATION = "investigation"
    ROLE_SYSTEM = "system"

    ROLE_CHOICES = [
        (ROLE_DOCTOR, "Doctor"),
        (ROLE_PATIENT, "Patient"),
        (ROLE_INVESTIGATION, "Investigation"),
        (ROLE_SYSTEM, "System"),
    ]

    clinical_case = models.ForeignKey(
        ClinicalCase,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    audio_file = models.FileField(
        upload_to="audio/",
        blank=True,
        null=True,
    )
    voice_generated_at = models.DateTimeField(null=True, blank=True)

    image_file = models.ImageField(
        upload_to="investigations/",
        blank=True,
        null=True,
    )
    image_generated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_role_display()} message for case {self.clinical_case_id}"


class RealConsultationSession(models.Model):
    STATUS_SETUP = "setup"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_SETUP, "Setup"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="real_consultation_sessions",
    )

    clinical_case = models.ForeignKey(
        ClinicalCase,
        on_delete=models.CASCADE,
        related_name="real_consultation_sessions",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_SETUP,
    )

    duration_seconds = models.PositiveIntegerField(default=480)

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    real_consultation_credit_charged = models.BooleanField(default=False)

    transcription_seconds_used = models.PositiveIntegerField(default=0)
    input_tokens_used = models.PositiveIntegerField(default=0)
    output_tokens_used = models.PositiveIntegerField(default=0)
    voice_characters_used = models.PositiveIntegerField(default=0)
    turn_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Real consultation {self.id} - {self.user} - {self.status}"
