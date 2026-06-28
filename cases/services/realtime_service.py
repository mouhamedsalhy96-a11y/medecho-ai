import json
import os

import requests
from urllib3.filepost import encode_multipart_formdata


OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"


def build_realtime_patient_instructions(clinical_case):
    return f"""
You are a simulated patient in an educational OSCE-style consultation.

Important rules:
- This is education only, not real medical advice.
- Stay in character as the patient.
- Do not reveal the diagnosis unless the learner gives a final explanation.
- Answer only the question asked.
- Keep most replies to 1-2 short sentences.
- Do not volunteer extra history unless directly asked.
- If asked an open question, give a brief natural answer and wait.
- Use realistic lay language.
- Do not act as an examiner.

Patient details:
Name: {clinical_case.patient_name}
Age: {clinical_case.patient_age}
Presenting complaint: {clinical_case.presenting_complaint}
Case summary: {clinical_case.case_summary}
Hidden diagnosis: {clinical_case.hidden_diagnosis}
Patient behaviour/instructions: {clinical_case.secret_prompt}
""".strip()


def normalise_sdp_for_openai(offer_sdp):
    offer_sdp = offer_sdp or ""
    offer_sdp = offer_sdp.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    if not offer_sdp.endswith("\r\n"):
        offer_sdp += "\r\n"
    return offer_sdp


def normalise_answer_sdp(answer_sdp):
    answer_sdp = answer_sdp or ""
    answer_sdp = answer_sdp.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return answer_sdp.strip() + "\r\n"


def validate_offer_sdp(offer_sdp):
    if not offer_sdp:
        return "Missing voice connection request."
    if not offer_sdp.startswith("v=0"):
        return "Invalid voice connection request."
    if "m=audio" not in offer_sdp:
        return "Invalid voice connection request."
    return ""


def create_openai_realtime_answer(offer_sdp, clinical_case):
    offer_sdp = normalise_sdp_for_openai(offer_sdp)

    validation_error = validate_offer_sdp(offer_sdp)
    if validation_error:
        return {"success": False, "answer_sdp": "", "error": validation_error}

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "answer_sdp": "",
            "error": "Voice consultation is not configured yet.",
        }

    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2").strip()
    voice = os.getenv("OPENAI_REALTIME_VOICE", "marin").strip()
    transcription_model = os.getenv(
        "OPENAI_REALTIME_TRANSCRIPTION_MODEL",
        "gpt-4o-mini-transcribe",
    ).strip()

    session_config = {
        "type": "realtime",
        "model": model,
        "instructions": build_realtime_patient_instructions(clinical_case),
        "audio": {
            "input": {
                "transcription": {
                    "model": transcription_model,
                },
            },
            "output": {
                "voice": voice,
            },
        },
    }

    body, content_type = encode_multipart_formdata(
        {
            "sdp": offer_sdp,
            "session": json.dumps(session_config),
        }
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type,
        "Accept": "application/sdp",
        "OpenAI-Safety-Identifier": f"medecho-user-{clinical_case.user_id}",
    }

    try:
        response = requests.post(
            OPENAI_REALTIME_CALLS_URL,
            headers=headers,
            data=body,
            timeout=45,
        )

        if response.status_code >= 400:
            return {
                "success": False,
                "answer_sdp": "",
                "error": f"Voice consultation could not start: {response.text[:700]}",
            }

        answer_sdp = normalise_answer_sdp(response.text)
        if not answer_sdp.startswith("v=0"):
            return {
                "success": False,
                "answer_sdp": "",
                "error": "Voice consultation could not connect.",
            }

        return {"success": True, "answer_sdp": answer_sdp, "error": ""}

    except Exception as exc:
        return {"success": False, "answer_sdp": "", "error": str(exc)}
