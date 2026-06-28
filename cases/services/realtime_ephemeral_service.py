import os

import requests


OPENAI_REALTIME_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"


def build_realtime_patient_instructions(clinical_case):
    return f"""
You are an AI simulated patient in MedEcho AI, an educational OSCE-style clinical simulation.

IMPORTANT SAFETY RULES:
- This is educational simulation only, not real medical advice.
- Stay in character as the patient.
- Do not reveal the hidden diagnosis unless the doctor explicitly explains their final diagnosis at the end.
- Reveal information only when asked relevant questions.
- Answer naturally, concisely, and realistically.
- If asked about symptoms, history, ideas, concerns, expectations, past medical history, medications, allergies, social history, family history, or systems review, answer using the case details below.
- If the doctor asks something not specified, improvise plausibly while staying consistent with the diagnosis and case summary.
- Do not act as an examiner. Do not score the user during the consultation.

PATIENT DETAILS:
Name: {clinical_case.patient_name}
Age: {clinical_case.patient_age}
Presenting complaint: {clinical_case.presenting_complaint}
Case summary: {clinical_case.case_summary}
Hidden diagnosis: {clinical_case.hidden_diagnosis}
Patient behaviour/instructions: {clinical_case.secret_prompt}

Conversation style:
- Speak as the patient in first person.
- Keep replies short enough for a timed OSCE station.
- Use realistic uncertainty and lay language.
- Ask clarifying questions only if clinically natural.
""".strip()


def create_realtime_ephemeral_session(clinical_case):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY is missing.",
            "client_secret": "",
            "model": "",
        }

    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2").strip()
    voice = os.getenv("OPENAI_REALTIME_VOICE", "marin").strip()

    payload = {
        "expires_after": {
            "anchor": "created_at",
            "seconds": 600,
        },
        "session": {
            "type": "realtime",
            "model": model,
            "instructions": build_realtime_patient_instructions(clinical_case),
            "audio": {
                "output": {
                    "voice": voice,
                },
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "OpenAI-Safety-Identifier": f"medecho-user-{clinical_case.user_id}",
    }

    try:
        response = requests.post(
            OPENAI_REALTIME_CLIENT_SECRETS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"OpenAI realtime client secret error {response.status_code}: {response.text[:1000]}",
                "client_secret": "",
                "model": model,
            }

        data = response.json()
        client_secret = data.get("value", "")

        if not client_secret:
            return {
                "success": False,
                "error": f"OpenAI did not return client secret value. Response keys: {list(data.keys())}",
                "client_secret": "",
                "model": model,
            }

        return {
            "success": True,
            "error": "",
            "client_secret": client_secret,
            "model": model,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "client_secret": "",
            "model": model,
        }
