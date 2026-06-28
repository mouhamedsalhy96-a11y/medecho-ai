import json


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
    # Backwards compatibility with old cases.
    "easy": "Early learner",
    "moderate": "Intermediate learner",
    "hard": "Advanced learner",
}


def get_level_label(level):
    return LEVEL_LABELS.get(level, level.replace("_", " ").title() if level else "Healthcare learner")


def build_case_generation_prompt(specialty, difficulty):
    training_level = get_level_label(difficulty)
    return f"""
You are generating a fictional clinical education case for MedEcho AI.

Purpose:
- Healthcare education only.
- Not for diagnosis.
- Not for real patient care.
- The case should be realistic for UK OSCE, PLAB, UKMLA and healthcare communication/practical assessment style practice.

Generate one simulated patient case.

Requirements:
- Specialty: {specialty}
- Learner professional stage / training level: {training_level}
- The diagnosis must be hidden from the learner.
- The patient should present naturally.
- Include enough detail for history-taking, examination planning, investigations and management.
- Calibrate clinical complexity and expected reasoning to the learner's stated professional stage.
- For nursing, midwifery, physiotherapy, paramedic, pharmacy and advanced practitioner levels, keep the case relevant to consultation skills, escalation, safety, red flags, communication and scope-aware management.
- Include red flags if clinically relevant.
- Do not include real patient identifiers.

Return JSON only with exactly these keys:
{{
  "specialty": "string",
  "difficulty": "string",
  "patient_name": "string",
  "patient_age": integer,
  "presenting_complaint": "string",
  "hidden_diagnosis": "string",
  "case_summary": "string",
  "secret_prompt": "string",
  "voice_style": "neutral_adult | tired_low_energy | breathless_short_phrases | anxious_fast_speech | pain_discomfort | older_adult_slow | confused_slow"
}}

Rules for secret_prompt:
- Write instructions for the simulated patient.
- Include what symptoms to reveal only if asked.
- Include relevant positives and negatives.
- Include ideas, concerns and expectations if asked.
- Explicitly say not to reveal the diagnosis directly.
- Keep patient replies concise: usually 1 to 2 short sentences.
"""


def build_patient_reply_messages(clinical_case, previous_messages, doctor_message):
    training_level = get_level_label(getattr(clinical_case, "difficulty", ""))
    system_prompt = f"""
You are a simulated patient in MedEcho AI.

This is a healthcare education simulation only. Not for diagnosis or patient care.

You must behave like the patient, not like a clinician or examiner.

Patient details:
- Name: {clinical_case.patient_name}
- Age: {clinical_case.patient_age}
- Presenting complaint: {clinical_case.presenting_complaint}
- Hidden diagnosis: {clinical_case.hidden_diagnosis}
- Learner level: {training_level}
- Voice style: {clinical_case.voice_style}

Secret case instructions:
{clinical_case.secret_prompt}

Rules:
- Reply naturally as the patient.
- Answer only the question asked.
- Keep replies concise, usually 1 to 2 short sentences.
- Do not list all symptoms at once.
- Reveal information gradually when asked.
- If the learner asks a vague question, answer vaguely.
- If asked about red flags, answer according to the case.
- Do not give management advice.
- Do not break character.
- Do not reveal the diagnosis unless the learner has already clearly explained it and asks for confirmation.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    for message in previous_messages:
        if message.role == "doctor":
            messages.append(
                {
                    "role": "user",
                    "content": message.content,
                }
            )
        elif message.role == "patient":
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                }
            )

    messages.append(
        {
            "role": "user",
            "content": doctor_message,
        }
    )

    return messages


def build_investigation_report_prompt(clinical_case, investigation_name, clinical_reason):
    training_level = get_level_label(getattr(clinical_case, "difficulty", ""))
    return f"""
You are generating a fictional investigation result for MedEcho AI.

Purpose:
- Healthcare education only.
- Not for diagnosis.
- Not for real patient care.
- The result must fit the hidden fictional case.
- The result should be realistic for UK OSCE, PLAB, UKMLA and healthcare professional assessment practice.

Case:
- Patient name: {clinical_case.patient_name}
- Patient age: {clinical_case.patient_age}
- Presenting complaint: {clinical_case.presenting_complaint}
- Hidden diagnosis: {clinical_case.hidden_diagnosis}
- Learner level: {training_level}
- Case summary: {clinical_case.case_summary}
- Secret prompt: {clinical_case.secret_prompt}

Requested investigation:
{investigation_name}

Clinical reason given by learner:
{clinical_reason or "No clinical reason provided."}

Instructions:
- Generate a concise but useful text investigation report.
- If the test is appropriate, show plausible findings.
- If the test is less useful, still provide a realistic result and briefly state limitations.
- Do not reveal the hidden diagnosis directly unless the investigation would strongly suggest it.
- For ECG, include rate, rhythm, axis if relevant, intervals if relevant, and key abnormalities.
- For imaging, provide a radiology-style text report only in this phase.
- For blood tests, include relevant values with units and reference ranges where useful.
- Avoid pretending that this is a real clinical result.

Return plain text only.

Start with:
Investigation: [name]

Then include:
Result:
Interpretation:
Educational note:
"""


def parse_case_generation_json(raw_text):
    cleaned = raw_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    data = json.loads(cleaned)

    required_keys = [
        "specialty",
        "difficulty",
        "patient_name",
        "patient_age",
        "presenting_complaint",
        "hidden_diagnosis",
        "case_summary",
        "secret_prompt",
        "voice_style",
    ]

    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing key from generated case JSON: {key}")

    data["patient_age"] = int(data["patient_age"])

    return data
