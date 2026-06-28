from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import render

from .models import ClinicalCase, RealConsultationSession
from .services.usage import get_usage_summary


LEVEL_LABELS = {
    "medical_student": "Medical student",
    "foundation_doctor": "Foundation doctor / FY1-FY2",
    "doctor_in_training": "Doctor in training / SHO level",
    "nurse": "Nurse",
    "midwife": "Midwife",
    "physiotherapist": "Physiotherapist",
    "paramedic": "Paramedic",
    "pharmacist": "Pharmacist",
    "advanced_practitioner": "Advanced practitioner",
    "other_healthcare_professional": "Other healthcare professional",
    "easy": "Early learner",
    "moderate": "Intermediate learner",
    "hard": "Advanced learner",
    "plab": "PLAB candidate",
    "ukmla": "UKMLA candidate",
    "doctor": "Doctor",
    "tutor": "Tutor",
    "other": "Other",
}


SPECIALTY_LABELS = {
    "general_practice": "General Practice",
    "emergency_medicine": "Emergency Medicine",
    "cardiology": "Cardiology",
    "respiratory": "Respiratory",
    "gastroenterology": "Gastroenterology",
    "neurology": "Neurology",
    "endocrinology": "Endocrinology",
    "paediatrics": "Paediatrics",
    "obstetrics_gynaecology": "Obstetrics and Gynaecology",
    "psychiatry": "Psychiatry",
    "random": "Random",
}


def label_from_map(value, mapping):
    if not value:
        return "Not recorded"
    return mapping.get(value, value.replace("_", " ").title())


@login_required
def practice_history(request):
    search_query = (request.GET.get("q") or "").strip()
    mode_filter = (request.GET.get("mode") or "all").strip()
    status_filter = (request.GET.get("status") or "visible").strip()
    specialty_filter = (request.GET.get("specialty") or "all").strip()
    level_filter = (request.GET.get("level") or "all").strip()
    order_filter = (request.GET.get("order") or "newest").strip()

    latest_sessions_prefetch = Prefetch(
        "real_consultation_sessions",
        queryset=RealConsultationSession.objects.order_by("-created_at"),
        to_attr="history_sessions",
    )

    cases = ClinicalCase.objects.filter(user=request.user).prefetch_related(
        latest_sessions_prefetch,
    )

    if status_filter == "deleted":
        cases = cases.filter(status=ClinicalCase.STATUS_DELETED)
    else:
        cases = cases.exclude(status=ClinicalCase.STATUS_DELETED)
        if status_filter in [ClinicalCase.STATUS_ACTIVE, ClinicalCase.STATUS_COMPLETED, ClinicalCase.STATUS_DRAFT]:
            cases = cases.filter(status=status_filter)

    if specialty_filter != "all":
        cases = cases.filter(specialty=specialty_filter)

    if level_filter != "all":
        cases = cases.filter(difficulty=level_filter)

    if search_query:
        cases = cases.filter(
            Q(patient_name__icontains=search_query)
            | Q(presenting_complaint__icontains=search_query)
            | Q(hidden_diagnosis__icontains=search_query)
            | Q(case_summary__icontains=search_query)
        )

    cases = cases.order_by("created_at" if order_filter == "oldest" else "-created_at")

    history_items = []
    live_count = 0
    practice_count = 0
    completed_count = 0
    active_count = 0

    for clinical_case in cases:
        sessions = list(getattr(clinical_case, "history_sessions", []))
        latest_session = sessions[0] if sessions else None
        is_live = latest_session is not None
        mode = "live" if is_live else "practice"

        if mode_filter == "practice" and is_live:
            continue
        if mode_filter == "live" and not is_live:
            continue

        if is_live:
            live_count += 1
        else:
            practice_count += 1

        if clinical_case.status == ClinicalCase.STATUS_COMPLETED:
            completed_count += 1
        if clinical_case.status == ClinicalCase.STATUS_ACTIVE:
            active_count += 1

        history_items.append(
            {
                "clinical_case": clinical_case,
                "latest_session": latest_session,
                "mode": mode,
                "mode_label": "Live Consultation" if is_live else "Practice",
                "specialty_label": label_from_map(clinical_case.specialty, SPECIALTY_LABELS),
                "level_label": label_from_map(clinical_case.difficulty, LEVEL_LABELS),
            }
        )

    usage = get_usage_summary(request.user)

    context = {
        "history_items": history_items,
        "usage": usage,
        "filters": {
            "q": search_query,
            "mode": mode_filter,
            "status": status_filter,
            "specialty": specialty_filter,
            "level": level_filter,
            "order": order_filter,
        },
        "specialty_options": sorted(SPECIALTY_LABELS.items(), key=lambda item: item[1]),
        "level_options": sorted(LEVEL_LABELS.items(), key=lambda item: item[1]),
        "summary": {
            "total": len(history_items),
            "practice": practice_count,
            "live": live_count,
            "active": active_count,
            "completed": completed_count,
        },
    }

    return render(request, "cases/practice_history.html", context)
