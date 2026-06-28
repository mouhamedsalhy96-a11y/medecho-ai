from dataclasses import dataclass

from django.utils import timezone

from cases.models import CaseUsageEvent


@dataclass
class UsageSummary:
    text_cases_used_total: int
    text_cases_included_used: int
    text_cases_extra_used: int
    text_case_limit: int

    voice_used_total: int
    voice_included_used: int
    voice_extra_used: int
    voice_limit: int

    image_used_total: int
    image_included_used: int
    image_extra_used: int
    image_limit: int

    real_consultations_started: int
    real_consultations_completed: int

    payg_credits_remaining: int
    real_consultation_credits_remaining: int


def get_current_month_range():
    now = timezone.localtime(timezone.now())
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)

    return start, next_month


def count_monthly_events(user, event_type):
    start, end = get_current_month_range()

    return CaseUsageEvent.objects.filter(
        user=user,
        event_type=event_type,
        created_at__gte=start,
        created_at__lt=end,
    ).count()


def get_usage_summary(user):
    profile = user.profile

    text_case_limit = profile.get_monthly_text_case_limit()
    voice_limit = profile.get_monthly_voice_generation_limit()
    image_limit = profile.get_monthly_image_investigation_limit()

    text_cases_used_total = count_monthly_events(
        user,
        CaseUsageEvent.EVENT_TEXT_CASE,
    )
    voice_used_total = count_monthly_events(
        user,
        CaseUsageEvent.EVENT_VOICE_GENERATION,
    )
    image_used_total = count_monthly_events(
        user,
        CaseUsageEvent.EVENT_IMAGE_INVESTIGATION,
    )

    real_consultations_started = count_monthly_events(
        user,
        CaseUsageEvent.EVENT_REAL_CONSULTATION_STARTED,
    )
    real_consultations_completed = count_monthly_events(
        user,
        CaseUsageEvent.EVENT_REAL_CONSULTATION_COMPLETED,
    )

    text_cases_included_used = min(text_cases_used_total, text_case_limit)
    voice_included_used = min(voice_used_total, voice_limit)
    image_included_used = min(image_used_total, image_limit)

    text_cases_extra_used = max(text_cases_used_total - text_case_limit, 0)
    voice_extra_used = max(voice_used_total - voice_limit, 0)
    image_extra_used = max(image_used_total - image_limit, 0)

    return UsageSummary(
        text_cases_used_total=text_cases_used_total,
        text_cases_included_used=text_cases_included_used,
        text_cases_extra_used=text_cases_extra_used,
        text_case_limit=text_case_limit,
        voice_used_total=voice_used_total,
        voice_included_used=voice_included_used,
        voice_extra_used=voice_extra_used,
        voice_limit=voice_limit,
        image_used_total=image_used_total,
        image_included_used=image_included_used,
        image_extra_used=image_extra_used,
        image_limit=image_limit,
        real_consultations_started=real_consultations_started,
        real_consultations_completed=real_consultations_completed,
        payg_credits_remaining=profile.payg_credits,
        real_consultation_credits_remaining=profile.real_consultation_credits,
    )


def record_usage_event(
    user,
    event_type,
    clinical_case=None,
    encounter_message=None,
    metadata=None,
):
    return CaseUsageEvent.objects.create(
        user=user,
        event_type=event_type,
        clinical_case=clinical_case,
        encounter_message=encounter_message,
        metadata=metadata or {},
    )