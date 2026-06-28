import json
import os

from openai import OpenAI

from .transcript_context_service import build_feedback_transcript_context


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


FEEDBACK_KEYS = [
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


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def clean_json_text(raw_text):
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned


def score_to_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(number, 100))


def build_transcript(clinical_case):
    lines = []
    for message in clinical_case.messages.all().order_by("created_at", "id"):
        content = (message.content or "").strip()
        if not content:
            continue
        label = message.get_role_display()
        lines.append(f"{label}: {content}")
    return "\n\n".join(lines) if lines else "No consultation transcript was captured."


def build_feedback_prompt(clinical_case):
    transcript_context = build_feedback_transcript_context(clinical_case)

    return f"""
You are a strict but fair UK OSCE / PLAB / UKMLA examiner.

This is a fictional MedEcho AI medical education simulation only.
Do not provide real patient care advice.

Case information:
- Presenting complaint: {clinical_case.presenting_complaint}
- Hidden diagnosis: {clinical_case.hidden_diagnosis}
- Case summary: {clinical_case.case_summary}

{transcript_context}

Learner submission:
Final diagnosis:
{clinical_case.final_diagnosis}

Differential diagnoses:
{clinical_case.differentials}

Investigation interpretation:
{clinical_case.investigation_interpretation}

Management plan:
{clinical_case.management_plan}

Safety-netting:
{clinical_case.safety_netting}

Mark like a UK OSCE / PLAB / UKMLA examiner.
Be fair but strict.

Marking rules:
- Base data gathering and IPS mainly on the consultation transcript.
- Base diagnosis, reasoning, investigation interpretation, management and safety-netting on both the transcript and final submission.
- Do not give credit for questions, red flags, ICE, PMH, drug history, allergies, social history, examination plans, investigations, explanations or safety-netting unless they appear in the transcript or final submission.
- Penalise unsafe management, missed red flags, poor prioritisation, failure to escalate, and unsupported reassurance.
- Reward good structure, appropriate clinical reasoning, empathy, patient-centred language and clear safety-netting.
- If the transcript contains only patient turns and no doctor turns, explicitly state that doctor-side transcript capture appears incomplete and score data gathering cautiously.

Return JSON only with exactly these keys:
{{
  "overall_score": integer 0-100,
  "data_gathering_score": integer 0-100,
  "clinical_reasoning_score": integer 0-100,
  "management_score": integer 0-100,
  "ips_score": integer 0-100,
  "safety_netting_score": integer 0-100,
  "overall_feedback": "string",
  "data_gathering_feedback": "string",
  "clinical_reasoning_feedback": "string",
  "management_feedback": "string",
  "ips_feedback": "string",
  "safety_netting_feedback": "string",
  "critical_misses": "string",
  "strengths": "string",
  "improvement_plan": "string"
}}
""".strip()


def fallback_feedback(clinical_case, reason=""):
    diagnosis_text = (clinical_case.final_diagnosis or "").lower()
    hidden_text = (clinical_case.hidden_diagnosis or "").lower()
    transcript = build_transcript(clinical_case)
    has_doctor_transcript = "Doctor:" in transcript

    if hidden_text and hidden_text in diagnosis_text:
        reasoning_score = 75
        overall_score = 70
        reasoning_feedback = "The final diagnosis matches the intended case diagnosis. Clinical reasoning appears directionally appropriate."
    else:
        reasoning_score = 45
        overall_score = 50
        reasoning_feedback = "The final diagnosis does not clearly match the intended case diagnosis. Revisit the key positives, negatives and investigation findings."

    management_plan = (clinical_case.management_plan or "").strip()
    safety_netting = (clinical_case.safety_netting or "").strip()

    management_score = 60 if len(management_plan) > 80 else 40
    safety_score = 60 if len(safety_netting) > 60 else 35
    data_gathering_score = 55 if has_doctor_transcript else 35
    ips_score = 55 if has_doctor_transcript else 35

    transcript_capture_note = ""
    if not has_doctor_transcript:
        transcript_capture_note = " Doctor-side transcript was not clearly captured, so data gathering and IPS are scored cautiously."

    return {
        "overall_score": overall_score,
        "data_gathering_score": data_gathering_score,
        "clinical_reasoning_score": reasoning_score,
        "management_score": management_score,
        "ips_score": ips_score,
        "safety_netting_score": safety_score,
        "overall_feedback": "Fallback feedback generated because AI feedback was unavailable. Use this as a rough guide only." + transcript_capture_note,
        "data_gathering_feedback": "Review whether you explored the presenting complaint, red flags, relevant risk factors, past history, medications, allergies and patient concerns." + transcript_capture_note,
        "clinical_reasoning_feedback": reasoning_feedback,
        "management_feedback": "Management should include immediate priorities, escalation where appropriate, definitive treatment, follow-up and patient communication.",
        "ips_feedback": "Continue to use clear, patient-centred language and acknowledge concerns throughout the consultation." + transcript_capture_note,
        "safety_netting_feedback": "Safety-netting should include specific red flags, what to do if symptoms worsen, and when urgent help is needed.",
        "critical_misses": "Fallback mode cannot fully identify all critical misses. Review red flags and unsafe management manually.",
        "strengths": "You completed the consultation and submitted a structured answer.",
        "improvement_plan": "Practise summarising findings, linking evidence to differentials, and writing a structured emergency-safe management plan.",
        "fallback_reason": reason,
    }


def normalise_feedback(data):
    normalised = {}
    for key in FEEDBACK_KEYS:
        normalised[key] = data.get(key, "")

    score_keys = [
        "overall_score",
        "data_gathering_score",
        "clinical_reasoning_score",
        "management_score",
        "ips_score",
        "safety_netting_score",
    ]
    for key in score_keys:
        normalised[key] = score_to_int(normalised[key])

    return normalised


def generate_feedback_with_ai_or_fallback(clinical_case):
    client = get_openai_client()
    if client is None:
        return fallback_feedback(clinical_case, reason="OPENAI_API_KEY missing")

    try:
        prompt = build_feedback_prompt(clinical_case)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            messages=[
                {"role": "system", "content": "You are a UK OSCE examiner. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1600,
        )
        raw_text = response.choices[0].message.content
        data = json.loads(clean_json_text(raw_text))
        return normalise_feedback(data)

    except Exception as exc:
        return fallback_feedback(clinical_case, reason=f"AI feedback failed: {exc}")
