from django.urls import path

from . import history_views, views


urlpatterns = [
    path("new/", views.new_case, name="new_case"),
    path("history/", history_views.practice_history, name="case_history"),
    path("<int:case_id>/chat/", views.case_chat, name="case_chat"),
    path(
        "<int:case_id>/investigations/order/",
        views.order_investigation,
        name="order_investigation",
    ),
    path(
        "<int:case_id>/messages/<int:message_id>/voice/",
        views.generate_patient_voice,
        name="generate_patient_voice",
    ),
    path(
        "<int:case_id>/submit/",
        views.submit_consultation,
        name="submit_consultation",
    ),
    path(
        "<int:case_id>/feedback/",
        views.case_feedback,
        name="case_feedback",
    ),
    path(
        "<int:case_id>/feedback/pdf/",
        views.feedback_pdf,
        name="feedback_pdf",
    ),
    path(
        "<int:case_id>/delete/",
        views.delete_case,
        name="delete_case",
    ),
    path(
        "real-consultation/",
        views.real_consultation_intro,
        name="real_consultation_intro",
    ),
    path(
        "real-consultation/<int:session_id>/setup/",
        views.real_consultation_setup,
        name="real_consultation_setup",
    ),
    path(
        "real-consultation/<int:session_id>/session/",
        views.real_consultation_session,
        name="real_consultation_session",
    ),
    path(
        "real-consultation/<int:session_id>/audio/upload/",
        views.real_consultation_upload_audio,
        name="real_consultation_upload_audio",
    ),
    path(
        "real-consultation/history/",
        history_views.practice_history,
        name="real_consultation_history",
    ),
    path(
        "real-consultation/<int:session_id>/realtime/",
        views.real_consultation_realtime,
        name="real_consultation_realtime",
    ),
    path(
        "real-consultation/<int:session_id>/end/",
        views.real_consultation_end,
        name="real_consultation_end",
    ),
    path(
        "real-consultation/<int:session_id>/realtime/connect/",
        views.real_consultation_realtime_connect,
        name="real_consultation_realtime_connect",
    ),
    path(
        "real-consultation/<int:session_id>/realtime/transcript/",
        views.real_consultation_realtime_transcript,
        name="real_consultation_realtime_transcript",
    ),
]
