from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    PLAN_FREE = "free"
    PLAN_STARTER = "starter"
    PLAN_STUDENT = "student"
    PLAN_PRO = "pro"

    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_STARTER, "Starter"),
        (PLAN_STUDENT, "Student"),
        (PLAN_PRO, "Pro"),
    ]

    TITLE_DR = "dr"
    TITLE_MR = "mr"
    TITLE_MISS = "miss"
    TITLE_MRS = "mrs"
    TITLE_MS = "ms"

    TITLE_CHOICES = [
        (TITLE_DR, "Dr"),
        (TITLE_MR, "Mr"),
        (TITLE_MISS, "Miss"),
        (TITLE_MRS, "Mrs"),
        (TITLE_MS, "Ms"),
    ]

    LEVEL_DOCTOR = "doctor"
    LEVEL_MEDICAL_STUDENT = "medical_student"
    LEVEL_NURSE = "nurse"
    LEVEL_MIDWIFE = "midwife"
    LEVEL_PHYSIOTHERAPIST = "physiotherapist"
    LEVEL_PARAMEDIC = "paramedic"
    LEVEL_PHARMACIST = "pharmacist"
    LEVEL_ADVANCED_PRACTITIONER = "advanced_practitioner"
    LEVEL_HEALTHCARE_ASSISTANT = "healthcare_assistant"
    LEVEL_OTHER_HEALTHCARE = "other_healthcare_professional"

    LEVEL_CHOICES = [
        (LEVEL_DOCTOR, "Doctor"),
        (LEVEL_MEDICAL_STUDENT, "Medical student"),
        (LEVEL_NURSE, "Nurse"),
        (LEVEL_MIDWIFE, "Midwife"),
        (LEVEL_PHYSIOTHERAPIST, "Physiotherapist"),
        (LEVEL_PARAMEDIC, "Paramedic"),
        (LEVEL_PHARMACIST, "Pharmacist"),
        (LEVEL_ADVANCED_PRACTITIONER, "Advanced practitioner"),
        (LEVEL_HEALTHCARE_ASSISTANT, "Healthcare assistant"),
        (LEVEL_OTHER_HEALTHCARE, "Other healthcare professional"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    full_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(
        max_length=50,
        choices=TITLE_CHOICES,
        default=TITLE_DR,
    )
    phone_number = models.CharField(max_length=50, blank=True)
    level = models.CharField(
        max_length=50,
        choices=LEVEL_CHOICES,
        default=LEVEL_OTHER_HEALTHCARE,
    )

    plan = models.CharField(
        max_length=30,
        choices=PLAN_CHOICES,
        default=PLAN_FREE,
    )

    payg_credits = models.PositiveIntegerField(default=0)
    real_consultation_credits = models.PositiveIntegerField(default=0)

    stripe_customer_id = models.CharField(max_length=255, blank=True)
    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        display_name = self.full_name or self.user.get_username()
        return f"{display_name} ({self.get_plan_display()})"

    @property
    def dashboard_greeting_name(self):
        if self.title == self.TITLE_DR and self.user.last_name:
            return f"Dr {self.user.last_name}"
        if self.title == self.TITLE_DR and self.full_name:
            name_parts = self.full_name.strip().split()
            return f"Dr {name_parts[-1]}" if name_parts else "Dr"
        return self.user.first_name or self.full_name or self.user.get_username()

    def get_monthly_text_case_limit(self):
        limits = {
            self.PLAN_FREE: 3,
            self.PLAN_STARTER: 25,
            self.PLAN_STUDENT: 100,
            self.PLAN_PRO: 300,
        }
        return limits.get(self.plan, 3)

    def get_monthly_voice_generation_limit(self):
        limits = {
            self.PLAN_FREE: 0,
            self.PLAN_STARTER: 0,
            self.PLAN_STUDENT: 20,
            self.PLAN_PRO: 100,
        }
        return limits.get(self.plan, 0)

    def get_monthly_image_investigation_limit(self):
        limits = {
            self.PLAN_FREE: 0,
            self.PLAN_STARTER: 0,
            self.PLAN_STUDENT: 20,
            self.PLAN_PRO: 100,
        }
        return limits.get(self.plan, 0)

    def can_use_real_consultation(self):
        return self.real_consultation_credits > 0


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)
