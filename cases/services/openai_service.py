import os
from openai import OpenAI
from .case_generator import generate_dummy_case, generate_dummy_patient_reply
from .prompts import build_case_generation_prompt, build_investigation_report_prompt, build_patient_reply_messages, parse_case_generation_json
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def generate_case_with_ai_or_fallback(specialty, difficulty):
    client = get_openai_client()
    if client is None:
        data = generate_dummy_case(specialty, difficulty)
        data["ai_generated"] = False
        data["fallback_reason"] = "OPENAI_API_KEY missing"
        return data
    try:
        prompt = build_case_generation_prompt(specialty, difficulty)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=[
                {"role": "system", "content": "You generate safe fictional healthcare education cases and return JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        data = parse_case_generation_json(response.choices[0].message.content)
        data["ai_generated"] = True
        data["fallback_reason"] = ""
        return data
    except Exception as exc:
        data = generate_dummy_case(specialty, difficulty)
        data["ai_generated"] = False
        data["fallback_reason"] = f"Case generation failed: {exc}"
        return data

def generate_patient_reply_with_ai_or_fallback(clinical_case, doctor_message):
    client = get_openai_client()
    if client is None:
        return {"content": generate_dummy_patient_reply(clinical_case, doctor_message), "ai_generated": False, "fallback_reason": "OPENAI_API_KEY missing"}
    try:
        previous_messages = clinical_case.messages.exclude(role="system").order_by("created_at")
        messages = build_patient_reply_messages(clinical_case=clinical_case, previous_messages=previous_messages, doctor_message=doctor_message)
        messages.append({"role": "system", "content": "Reply as the simulated patient. Answer only the question asked. Keep the reply concise, usually 1-2 short sentences. Do not volunteer extra history unless asked. Do not explain the diagnosis."})
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=messages,
            temperature=0.6,
            max_tokens=120,
        )
        reply = response.choices[0].message.content.strip()
        if not reply:
            raise ValueError("Empty patient reply.")
        return {"content": reply, "ai_generated": True, "fallback_reason": ""}
    except Exception as exc:
        return {"content": generate_dummy_patient_reply(clinical_case, doctor_message), "ai_generated": False, "fallback_reason": f"Patient reply failed: {exc}"}

def generate_investigation_report_with_ai_or_fallback(clinical_case, investigation_name, clinical_reason=""):
    client = get_openai_client()
    if client is None:
        return {"content": generate_fallback_investigation_report(clinical_case, investigation_name, clinical_reason), "ai_generated": False, "fallback_reason": "OPENAI_API_KEY missing"}
    try:
        prompt = build_investigation_report_prompt(clinical_case=clinical_case, investigation_name=investigation_name, clinical_reason=clinical_reason)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=[
                {"role": "system", "content": "You generate fictional healthcare education investigation reports. You do not provide real patient care."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        report = response.choices[0].message.content.strip()
        if not report:
            raise ValueError("Empty investigation report.")
        return {"content": report, "ai_generated": True, "fallback_reason": ""}
    except Exception as exc:
        return {"content": generate_fallback_investigation_report(clinical_case, investigation_name, clinical_reason), "ai_generated": False, "fallback_reason": f"Investigation report failed: {exc}"}

def generate_fallback_investigation_report(clinical_case, investigation_name, clinical_reason=""):
    result = f"""Investigation: {investigation_name}

Result:
Fictional educational result generated. Findings are clinically plausible for the case context but are not from a real patient.

Interpretation:
Interpret this result alongside the history, examination findings and clinical reasoning.

Educational note:
This is a fictional investigation report for education only. Not for diagnosis or patient care."""
    if clinical_reason:
        result += '\n\nClinical reason provided:\n' + str(clinical_reason) + '\n'
    return result.strip()
