from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    ConsultationSubmissionForm,
    DoctorMessageForm,
    InvestigationOrderForm,
    NewClinicalCaseForm,
)
from .models import (
    CaseUsageEvent,
    ClinicalCase,
    EncounterMessage,
    RealConsultationSession,
)
from .services.elevenlabs_service import generate_patient_voice_audio
from .services.feedback_service import generate_feedback_with_ai_or_fallback
from .services.openai_service import (
    generate_case_with_ai_or_fallback,
    generate_investigation_report_with_ai_or_fallback,
    generate_patient_reply_with_ai_or_fallback,
)
from .services.pdf import build_feedback_pdf
from .services.realtime_service import create_openai_realtime_answer
from .services.replicate_service import (
    generate_educational_image_with_replicate,
    is_image_investigation_name,
)
from .services.transcription_service import transcribe_audio_file
from .services.usage import get_usage_summary, record_usage_event

REAL_CONSULTATION_DURATION_SECONDS = 480


def create_clinical_case_from_generated_data(user, generated_case):
    clinical_case = ClinicalCase.objects.create(
        user=user,
        specialty=generated_case["specialty"],
        difficulty=generated_case["difficulty"],
        patient_name=generated_case["patient_name"],
        patient_age=generated_case["patient_age"],
        presenting_complaint=generated_case["presenting_complaint"],
        hidden_diagnosis=generated_case["hidden_diagnosis"],
        case_summary=generated_case["case_summary"],
        secret_prompt=generated_case["secret_prompt"],
        voice_style=generated_case["voice_style"],
        status=ClinicalCase.STATUS_ACTIVE,
    )

    EncounterMessage.objects.create(
        clinical_case=clinical_case,
        role=EncounterMessage.ROLE_SYSTEM,
        content=(
            "Case generated. This is an educational simulation only. "
            "Not for diagnosis or patient care."
        ),
    )

    return clinical_case


def add_initial_patient_greeting(clinical_case):
    has_patient_message = clinical_case.messages.filter(
        role=EncounterMessage.ROLE_PATIENT,
    ).exists()

    if not has_patient_message:
        EncounterMessage.objects.create(
            clinical_case=clinical_case,
            role=EncounterMessage.ROLE_PATIENT,
            content=(
                f"Hello doctor. I am {clinical_case.patient_name}. "
                f"I have come in because of {clinical_case.presenting_complaint.lower()}."
            ),
        )


def complete_related_real_consultations(clinical_case):
    active_sessions = clinical_case.real_consultation_sessions.filter(
        status__in=[
            RealConsultationSession.STATUS_SETUP,
            RealConsultationSession.STATUS_ACTIVE,
        ]
    )

    for session in active_sessions:
        session.status = RealConsultationSession.STATUS_COMPLETED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])

        record_usage_event(
            user=session.user,
            event_type=CaseUsageEvent.EVENT_REAL_CONSULTATION_COMPLETED,
            clinical_case=clinical_case,
            metadata={
                "real_consultation_session_id": session.id,
                "duration_seconds": session.duration_seconds,
                "source": "real_consultation_mode",
            },
        )


@login_required
def new_case(request):
    profile = request.user.profile
    usage = get_usage_summary(request.user)

    if request.method == "POST":
        form = NewClinicalCaseForm(request.POST)
        if form.is_valid():
            included_limit_reached = usage.text_cases_used_total >= usage.text_case_limit

            if included_limit_reached and profile.payg_credits <= 0:
                messages.error(
                    request,
                    "You have reached your included monthly text case limit and have no PAYG credits remaining.",
                )
                return redirect("dashboard")

            specialty = form.cleaned_data["specialty"]
            difficulty = form.cleaned_data["difficulty"]
            generated_case = generate_case_with_ai_or_fallback(
                specialty=specialty,
                difficulty=difficulty,
            )

            with transaction.atomic():
                if included_limit_reached:
                    profile.payg_credits -= 1
                    profile.save(update_fields=["payg_credits"])

                clinical_case = create_clinical_case_from_generated_data(
                    request.user,
                    generated_case,
                )
                add_initial_patient_greeting(clinical_case)

                record_usage_event(
                    user=request.user,
                    event_type=CaseUsageEvent.EVENT_TEXT_CASE,
                    clinical_case=clinical_case,
                    metadata={
                        "source": "normal_practice",
                        "charged_payg_credit": included_limit_reached,
                        "requested_specialty": specialty,
                        "requested_difficulty": difficulty,
                        "ai_generated": generated_case.get("ai_generated", False),
                        "fallback_reason": generated_case.get("fallback_reason", ""),
                    },
                )

            if generated_case.get("ai_generated"):
                messages.success(request, "New AI-generated practice case created.")
            else:
                messages.warning(
                    request,
                    "New fallback practice case created because OpenAI is not configured or returned an error.",
                )

            return redirect("case_chat", case_id=clinical_case.id)
    else:
        form = NewClinicalCaseForm()

    return render(
        request,
        "cases/new_case.html",
        {"form": form, "profile": profile, "usage": usage},
    )


@login_required
def case_history(request):
    cases = ClinicalCase.objects.filter(user=request.user).exclude(
        status=ClinicalCase.STATUS_DELETED,
    )
    return render(request, "cases/case_history.html", {"cases": cases})


@login_required
def case_chat(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )

    if request.method == "POST":
        form = DoctorMessageForm(request.POST)
        if form.is_valid():
            doctor_message_text = form.cleaned_data["message"].strip()
            if doctor_message_text:
                EncounterMessage.objects.create(
                    clinical_case=clinical_case,
                    role=EncounterMessage.ROLE_DOCTOR,
                    content=doctor_message_text,
                )
                patient_reply_data = generate_patient_reply_with_ai_or_fallback(
                    clinical_case=clinical_case,
                    doctor_message=doctor_message_text,
                )
                EncounterMessage.objects.create(
                    clinical_case=clinical_case,
                    role=EncounterMessage.ROLE_PATIENT,
                    content=patient_reply_data["content"],
                )

                if patient_reply_data.get("ai_generated"):
                    messages.success(request, "AI patient replied.")
                else:
                    messages.warning(
                        request,
                        "Fallback patient reply used because OpenAI is not configured or returned an error.",
                    )

                return redirect("case_chat", case_id=clinical_case.id)
    else:
        form = DoctorMessageForm()

    return render(
        request,
        "cases/case_chat.html",
        {
            "clinical_case": clinical_case,
            "messages_list": clinical_case.messages.all(),
            "form": form,
        },
    )


@login_required
def generate_patient_voice(request, case_id, message_id):
    if request.method != "POST":
        return redirect("case_chat", case_id=case_id)

    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )
    patient_message = get_object_or_404(
        EncounterMessage,
        id=message_id,
        clinical_case=clinical_case,
        role=EncounterMessage.ROLE_PATIENT,
    )

    if patient_message.audio_file:
        messages.info(request, "This patient reply already has generated audio.")
        return redirect("case_chat", case_id=clinical_case.id)

    profile = request.user.profile
    usage = get_usage_summary(request.user)
    included_voice_available = usage.voice_used_total < usage.voice_limit
    payg_required = not included_voice_available

    if payg_required and profile.payg_credits <= 0:
        messages.error(
            request,
            "No voice allowance or PAYG credits remaining for voice generation.",
        )
        return redirect("case_chat", case_id=clinical_case.id)

    audio_result = generate_patient_voice_audio(
        text=patient_message.content,
        voice_style=clinical_case.voice_style,
    )

    if not audio_result["success"]:
        messages.warning(
            request,
            f"Voice could not be generated: {audio_result['error']}",
        )
        return redirect("case_chat", case_id=clinical_case.id)

    with transaction.atomic():
        if payg_required:
            profile.payg_credits -= 1
            profile.save(update_fields=["payg_credits"])

        patient_message.audio_file.save(
            audio_result["filename"],
            ContentFile(audio_result["audio_bytes"]),
            save=False,
        )
        patient_message.voice_generated_at = timezone.now()
        patient_message.save(update_fields=["audio_file", "voice_generated_at"])

        record_usage_event(
            user=request.user,
            event_type=CaseUsageEvent.EVENT_VOICE_GENERATION,
            clinical_case=clinical_case,
            encounter_message=patient_message,
            metadata={
                "source": "normal_practice",
                "voice_style": clinical_case.voice_style,
                "charged_payg_credit": payg_required,
                "character_count": audio_result["character_count"],
            },
        )

    messages.success(request, "Patient voice generated.")
    return redirect("case_chat", case_id=clinical_case.id)


@login_required
def order_investigation(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )

    if request.method == "POST":
        form = InvestigationOrderForm(request.POST)
        if form.is_valid():
            profile = request.user.profile
            usage = get_usage_summary(request.user)
            selected_codes = form.cleaned_data.get("investigations") or []
            custom_names = form.cleaned_data.get("custom_investigations_list") or []
            clinical_reason = (form.cleaned_data.get("clinical_reason") or "").strip()
            generate_images = form.cleaned_data.get("generate_images", False)

            label_map = dict(form.INVESTIGATION_CHOICES)
            normal_names = [label_map[code] for code in selected_codes if code in label_map]
            all_names = normal_names + custom_names

            generated_count = 0
            fallback_count = 0
            image_success_count = 0
            image_failed_count = 0
            image_skipped_not_imaging_count = 0
            image_skipped_no_credit_count = 0
            image_charge_counter = 0

            for investigation_name in all_names:
                report_data = generate_investigation_report_with_ai_or_fallback(
                    clinical_case=clinical_case,
                    investigation_name=investigation_name,
                    clinical_reason=clinical_reason,
                )
                investigation_message = EncounterMessage.objects.create(
                    clinical_case=clinical_case,
                    role=EncounterMessage.ROLE_INVESTIGATION,
                    content=report_data["content"],
                )

                generated_count += 1
                if not report_data.get("ai_generated"):
                    fallback_count += 1

                if not generate_images:
                    continue

                if not is_image_investigation_name(investigation_name):
                    image_skipped_not_imaging_count += 1
                    continue

                projected_image_usage = usage.image_used_total + image_charge_counter
                included_image_available = projected_image_usage < usage.image_limit
                payg_required = not included_image_available

                if payg_required and profile.payg_credits <= 0:
                    image_skipped_no_credit_count += 1
                    continue

                image_result = generate_educational_image_with_replicate(
                    clinical_case=clinical_case,
                    investigation_name=investigation_name,
                    text_report=report_data["content"],
                )

                if not image_result["success"]:
                    image_failed_count += 1
                    continue

                with transaction.atomic():
                    if payg_required:
                        profile.payg_credits -= 1
                        profile.save(update_fields=["payg_credits"])

                    investigation_message.image_file.save(
                        image_result["filename"],
                        ContentFile(image_result["image_bytes"]),
                        save=True,
                    )
                    record_usage_event(
                        user=request.user,
                        event_type=CaseUsageEvent.EVENT_IMAGE_INVESTIGATION,
                        clinical_case=clinical_case,
                        encounter_message=investigation_message,
                        metadata={
                            "source": "normal_practice",
                            "investigation_name": investigation_name,
                            "charged_payg_credit": payg_required,
                            "educational_disclaimer": (
                                "AI-generated educational image only. "
                                "Not real clinical imaging. Not for diagnosis or patient care."
                            ),
                        },
                    )

                image_success_count += 1
                image_charge_counter += 1

            if fallback_count:
                messages.warning(
                    request,
                    f"{generated_count} investigation report(s) generated. {fallback_count} used fallback reports.",
                )
            else:
                messages.success(request, f"{generated_count} investigation report(s) generated.")

            if generate_images:
                if image_success_count:
                    messages.success(
                        request,
                        f"{image_success_count} educational image investigation(s) generated.",
                    )
                if image_failed_count:
                    messages.warning(
                        request,
                        (
                            f"{image_failed_count} image request(s) could not be generated. "
                            "Check REPLICATE_API_TOKEN and REPLICATE_IMAGE_MODEL_VERSION."
                        ),
                    )
                if image_skipped_not_imaging_count:
                    messages.info(
                        request,
                        f"{image_skipped_not_imaging_count} investigation(s) were text-only because they are not imaging-style tests.",
                    )
                if image_skipped_no_credit_count:
                    messages.error(
                        request,
                        (
                            f"{image_skipped_no_credit_count} image request(s) were skipped because "
                            "your included image limit is used and you have no PAYG credits."
                        ),
                    )

            return redirect("case_chat", case_id=clinical_case.id)
    else:
        form = InvestigationOrderForm()

    return render(
        request,
        "cases/order_investigation.html",
        {"clinical_case": clinical_case, "form": form},
    )


@login_required
def submit_consultation(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )

    if request.method == "POST":
        form = ConsultationSubmissionForm(request.POST)
        if form.is_valid():
            clinical_case.final_diagnosis = form.cleaned_data["final_diagnosis"].strip()
            clinical_case.differentials = form.cleaned_data["differentials"].strip()
            clinical_case.investigation_interpretation = form.cleaned_data[
                "investigation_interpretation"
            ].strip()
            clinical_case.management_plan = form.cleaned_data["management_plan"].strip()
            clinical_case.safety_netting = form.cleaned_data["safety_netting"].strip()
            clinical_case.status = ClinicalCase.STATUS_COMPLETED
            clinical_case.completed_at = timezone.now()
            clinical_case.save(
                update_fields=[
                    "final_diagnosis",
                    "differentials",
                    "investigation_interpretation",
                    "management_plan",
                    "safety_netting",
                    "status",
                    "completed_at",
                ]
            )

            feedback = generate_feedback_with_ai_or_fallback(clinical_case)

            clinical_case.overall_score = feedback["overall_score"]
            clinical_case.data_gathering_score = feedback["data_gathering_score"]
            clinical_case.clinical_reasoning_score = feedback["clinical_reasoning_score"]
            clinical_case.management_score = feedback["management_score"]
            clinical_case.ips_score = feedback["ips_score"]
            clinical_case.safety_netting_score = feedback["safety_netting_score"]
            clinical_case.overall_feedback = feedback["overall_feedback"]
            clinical_case.data_gathering_feedback = feedback["data_gathering_feedback"]
            clinical_case.clinical_reasoning_feedback = feedback["clinical_reasoning_feedback"]
            clinical_case.management_feedback = feedback["management_feedback"]
            clinical_case.ips_feedback = feedback["ips_feedback"]
            clinical_case.safety_netting_feedback = feedback["safety_netting_feedback"]
            clinical_case.critical_misses = feedback["critical_misses"]
            clinical_case.strengths = feedback["strengths"]
            clinical_case.improvement_plan = feedback["improvement_plan"]
            clinical_case.save(
                update_fields=[
                    "overall_score",
                    "data_gathering_score",
                    "clinical_reasoning_score",
                    "management_score",
                    "ips_score",
                    "safety_netting_score",
                    "overall_feedback",
                    "data_gathering_feedback",
                    "clinical_reasoning_feedback",
                    "management_feedback",
                    "ips_feedback",
                    "safety_netting_feedback",
                    "critical_misses",
                    "strengths",
                    "improvement_plan",
                ]
            )

            complete_related_real_consultations(clinical_case)
            messages.success(request, "Consultation completed and feedback generated.")
            return redirect("case_feedback", case_id=clinical_case.id)
    else:
        form = ConsultationSubmissionForm(
            initial={
                "final_diagnosis": clinical_case.final_diagnosis,
                "differentials": clinical_case.differentials,
                "investigation_interpretation": clinical_case.investigation_interpretation,
                "management_plan": clinical_case.management_plan,
                "safety_netting": clinical_case.safety_netting,
            }
        )

    return render(
        request,
        "cases/submit_consultation.html",
        {"clinical_case": clinical_case, "form": form},
    )


@login_required
def case_feedback(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )
    return render(request, "cases/feedback.html", {"clinical_case": clinical_case})


@login_required
def feedback_pdf(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )
    pdf_buffer = build_feedback_pdf(clinical_case)
    filename = f"medecho_feedback_case_{clinical_case.id}.pdf"
    return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


@login_required
def delete_case(request, case_id):
    clinical_case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        user=request.user,
    )

    if request.method == "POST":
        clinical_case.status = ClinicalCase.STATUS_DELETED
        clinical_case.save(update_fields=["status"])
        messages.success(
            request,
            "Case deleted from history. Usage ledger events were not reset.",
        )
        return redirect("case_history")

    return render(request, "cases/confirm_delete.html", {"clinical_case": clinical_case})


@login_required
def real_consultation_intro(request):
    profile = request.user.profile
    usage = get_usage_summary(request.user)

    if request.method == "POST":
        form = NewClinicalCaseForm(request.POST)
        if form.is_valid():
            if profile.real_consultation_credits <= 0:
                messages.error(
                    request,
                    "You have no Real Consultation credits remaining.",
                )
                return redirect("real_consultation_intro")

            specialty = form.cleaned_data["specialty"]
            difficulty = form.cleaned_data["difficulty"]
            generated_case = generate_case_with_ai_or_fallback(
                specialty=specialty,
                difficulty=difficulty,
            )

            with transaction.atomic():
                clinical_case = create_clinical_case_from_generated_data(
                    request.user,
                    generated_case,
                )
                session = RealConsultationSession.objects.create(
                    user=request.user,
                    clinical_case=clinical_case,
                    status=RealConsultationSession.STATUS_SETUP,
                    duration_seconds=REAL_CONSULTATION_DURATION_SECONDS,
                )

            messages.success(
                request,
                "Real Consultation case prepared. Complete setup before starting the timer.",
            )
            return redirect("real_consultation_setup", session_id=session.id)
    else:
        form = NewClinicalCaseForm()

    return render(
        request,
        "cases/real_consultation_intro.html",
        {"form": form, "profile": profile, "usage": usage},
    )


@login_required
def real_consultation_setup(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if request.method == "POST":
        profile = request.user.profile

        if session.status != RealConsultationSession.STATUS_SETUP:
            return redirect("real_consultation_realtime", session_id=session.id)

        if profile.real_consultation_credits <= 0:
            messages.error(
                request,
                "You have no Real Consultation credits remaining.",
            )
            return redirect("real_consultation_intro")

        with transaction.atomic():
            profile.real_consultation_credits -= 1
            profile.save(update_fields=["real_consultation_credits"])

            session.status = RealConsultationSession.STATUS_ACTIVE
            session.started_at = timezone.now()
            session.real_consultation_credit_charged = True
            session.save(
                update_fields=[
                    "status",
                    "started_at",
                    "real_consultation_credit_charged",
                ]
            )

            add_initial_patient_greeting(session.clinical_case)

            record_usage_event(
                user=request.user,
                event_type=CaseUsageEvent.EVENT_REAL_CONSULTATION_STARTED,
                clinical_case=session.clinical_case,
                metadata={
                    "real_consultation_session_id": session.id,
                    "duration_seconds": session.duration_seconds,
                    "source": "real_consultation_mode",
                    "credit_charged": True,
                },
            )

        messages.success(request, "Real Consultation started. Timer is running.")
        return redirect("real_consultation_realtime", session_id=session.id)

    return render(
        request,
        "cases/real_consultation_setup.html",
        {"session": session, "clinical_case": session.clinical_case},
    )


@login_required
def real_consultation_session(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if session.status == RealConsultationSession.STATUS_SETUP:
        return redirect("real_consultation_setup", session_id=session.id)

    return redirect("real_consultation_realtime", session_id=session.id)


@login_required
def real_consultation_upload_audio(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if request.method != "POST":
        return redirect("real_consultation_session", session_id=session.id)

    if session.status != RealConsultationSession.STATUS_ACTIVE:
        messages.error(request, "This Real Consultation session is not active.")
        return redirect("real_consultation_session", session_id=session.id)

    uploaded_audio = request.FILES.get("audio_file")

    if not uploaded_audio:
        messages.error(request, "No audio file was uploaded.")
        return redirect("real_consultation_session", session_id=session.id)

    transcription_result = transcribe_audio_file(uploaded_audio)

    if transcription_result["success"]:
        doctor_text = transcription_result["text"]
    else:
        doctor_text = (
            "Voice turn uploaded, but automatic transcription failed: "
            f"{transcription_result['error']}"
        )

    doctor_message = EncounterMessage.objects.create(
        clinical_case=session.clinical_case,
        role=EncounterMessage.ROLE_DOCTOR,
        content=doctor_text,
    )
    doctor_message.audio_file.save(uploaded_audio.name, uploaded_audio, save=True)

    if not transcription_result["success"]:
        messages.warning(
            request,
            "Audio uploaded, but transcription failed. The placeholder message was saved.",
        )
        return redirect("real_consultation_session", session_id=session.id)

    patient_reply_data = generate_patient_reply_with_ai_or_fallback(
        clinical_case=session.clinical_case,
        doctor_message=doctor_text,
    )

    patient_message = EncounterMessage.objects.create(
        clinical_case=session.clinical_case,
        role=EncounterMessage.ROLE_PATIENT,
        content=patient_reply_data["content"],
    )

    if not patient_reply_data.get("ai_generated"):
        messages.warning(
            request,
            "Fallback patient reply used because OpenAI patient reply generation failed.",
        )

    profile = request.user.profile
    usage = get_usage_summary(request.user)
    included_voice_available = usage.voice_used_total < usage.voice_limit
    payg_required = not included_voice_available

    if payg_required and profile.payg_credits <= 0:
        messages.info(
            request,
            "Patient text reply generated, but no voice allowance or PAYG credits remain for audio.",
        )
        return redirect("real_consultation_session", session_id=session.id)

    audio_result = generate_patient_voice_audio(
        text=patient_message.content,
        voice_style=session.clinical_case.voice_style,
    )

    if not audio_result["success"]:
        messages.info(
            request,
            f"Patient text reply generated, but voice generation failed: {audio_result['error']}",
        )
        return redirect("real_consultation_session", session_id=session.id)

    with transaction.atomic():
        if payg_required:
            profile.payg_credits -= 1
            profile.save(update_fields=["payg_credits"])

        patient_message.audio_file.save(
            audio_result["filename"],
            ContentFile(audio_result["audio_bytes"]),
            save=False,
        )
        patient_message.voice_generated_at = timezone.now()
        patient_message.save(update_fields=["audio_file", "voice_generated_at"])

        record_usage_event(
            user=request.user,
            event_type=CaseUsageEvent.EVENT_VOICE_GENERATION,
            clinical_case=session.clinical_case,
            encounter_message=patient_message,
            metadata={
                "source": "real_consultation_mode",
                "real_consultation_session_id": session.id,
                "voice_style": session.clinical_case.voice_style,
                "charged_payg_credit": payg_required,
                "character_count": audio_result["character_count"],
            },
        )

    messages.success(request, "Doctor audio transcribed and patient reply generated.")
    return redirect("real_consultation_session", session_id=session.id)


@login_required
def real_consultation_history(request):
    sessions = RealConsultationSession.objects.filter(
        user=request.user,
    ).select_related("clinical_case").order_by("-created_at")

    usage = get_usage_summary(request.user)

    return render(
        request,
        "cases/real_consultation_history.html",
        {"sessions": sessions, "usage": usage},
    )


@login_required
def real_consultation_realtime(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if session.status == RealConsultationSession.STATUS_SETUP:
        return redirect("real_consultation_setup", session_id=session.id)

    if session.started_at:
        elapsed = int((timezone.now() - session.started_at).total_seconds())
    else:
        elapsed = 0

    seconds_remaining = max(session.duration_seconds - elapsed, 0)

    if seconds_remaining <= 0 and session.status == RealConsultationSession.STATUS_ACTIVE:
        session.status = RealConsultationSession.STATUS_EXPIRED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])
        return redirect("submit_consultation", case_id=session.clinical_case.id)

    return render(
        request,
        "cases/real_consultation_realtime.html",
        {
            "session": session,
            "clinical_case": session.clinical_case,
            "messages_list": session.clinical_case.messages.all(),
            "seconds_remaining": seconds_remaining,
        },
    )


@login_required
def real_consultation_end(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if request.method != "POST":
        return redirect("real_consultation_realtime", session_id=session.id)

    auto_ended = request.POST.get("auto_ended") == "1"
    ended_now = False

    if session.status in [
        RealConsultationSession.STATUS_SETUP,
        RealConsultationSession.STATUS_ACTIVE,
    ]:
        session.status = RealConsultationSession.STATUS_COMPLETED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])
        ended_now = True

        record_usage_event(
            user=request.user,
            event_type=CaseUsageEvent.EVENT_REAL_CONSULTATION_COMPLETED,
            clinical_case=session.clinical_case,
            metadata={
                "real_consultation_session_id": session.id,
                "duration_seconds": session.duration_seconds,
                "source": "real_consultation_mode",
                "ended_by_user": not auto_ended,
                "auto_ended_by_timer": auto_ended,
            },
        )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "ended_now": ended_now,
                "auto_ended": auto_ended,
                "redirect_url": reverse(
                    "submit_consultation",
                    kwargs={"case_id": session.clinical_case.id},
                ),
            }
        )

    messages.success(request, "Real Consultation ended. Submit your diagnosis and management plan.")
    return redirect("submit_consultation", case_id=session.clinical_case.id)


@login_required
def real_consultation_realtime_connect(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required."}, status=405)

    if session.status != RealConsultationSession.STATUS_ACTIVE:
        return JsonResponse(
            {"success": False, "error": "Real Consultation session is not active."},
            status=400,
        )

    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
        offer_sdp = payload.get("sdp", "")
    except Exception as exc:
        return JsonResponse(
            {"success": False, "error": f"Invalid JSON SDP payload: {exc}"},
            status=400,
        )

    result = create_openai_realtime_answer(
        offer_sdp=offer_sdp,
        clinical_case=session.clinical_case,
    )

    if not result["success"]:
        return JsonResponse({"success": False, "error": result["error"]}, status=400)

    return JsonResponse({"success": True, "answer_sdp": result["answer_sdp"]})


@login_required
def real_consultation_realtime_transcript(request, session_id):
    session = get_object_or_404(
        RealConsultationSession,
        id=session_id,
        user=request.user,
    )

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required."}, status=405)

    allowed_statuses = [
        RealConsultationSession.STATUS_ACTIVE,
        RealConsultationSession.STATUS_COMPLETED,
    ]

    if session.status not in allowed_statuses:
        return JsonResponse(
            {"success": False, "error": "Real Consultation session is not accepting transcript saves."},
            status=400,
        )

    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        return JsonResponse({"success": False, "error": f"Invalid JSON: {exc}"}, status=400)

    role = (payload.get("role") or "").strip().lower()
    content = (payload.get("content") or "").strip()
    source_event_type = (payload.get("source_event_type") or "unknown").strip()

    if role not in ["doctor", "patient"]:
        return JsonResponse({"success": False, "error": "Invalid role."}, status=400)

    if not content:
        return JsonResponse({"success": False, "error": "Empty transcript content."}, status=400)

    clinical_case = session.clinical_case

    existing = clinical_case.messages.filter(role=role, content=content).first()
    if existing:
        return JsonResponse({"success": True, "message_id": existing.id, "duplicate": True})

    message = clinical_case.messages.create(role=role, content=content)

    return JsonResponse(
        {
            "success": True,
            "message_id": message.id,
            "duplicate": False,
            "source_event_type": source_event_type,
        }
    )
