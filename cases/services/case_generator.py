import random


VOICE_STYLES = [
    "neutral_adult",
    "tired_low_energy",
    "breathless_short_phrases",
    "anxious_fast_speech",
    "pain_discomfort",
    "older_adult_slow",
    "confused_slow",
]


DUMMY_CASES = [
    {
        "specialty": "respiratory",
        "patient_name": "Aisha Khan",
        "patient_age": 42,
        "presenting_complaint": "Shortness of breath",
        "hidden_diagnosis": "Pulmonary embolism",
        "case_summary": "A 42-year-old patient presents with acute shortness of breath and pleuritic chest pain after a recent long journey.",
        "secret_prompt": "The patient has pulmonary embolism. Reveal symptoms gradually. Do not reveal the diagnosis directly. Mention pleuritic chest pain, mild haemoptysis only if asked, recent long-haul travel, and no fever.",
        "voice_style": "breathless_short_phrases",
    },
    {
        "specialty": "cardiology",
        "patient_name": "George Williams",
        "patient_age": 67,
        "presenting_complaint": "Central chest pain",
        "hidden_diagnosis": "Acute coronary syndrome",
        "case_summary": "A 67-year-old patient presents with central crushing chest pain radiating to the left arm.",
        "secret_prompt": "The patient has acute coronary syndrome. Do not reveal the diagnosis. Mention sweating, nausea, cardiovascular risk factors, and exertional onset when asked.",
        "voice_style": "pain_discomfort",
    },
    {
        "specialty": "gastroenterology",
        "patient_name": "Sarah Thompson",
        "patient_age": 29,
        "presenting_complaint": "Right lower abdominal pain",
        "hidden_diagnosis": "Acute appendicitis",
        "case_summary": "A 29-year-old patient presents with migrating abdominal pain, nausea, and anorexia.",
        "secret_prompt": "The patient has acute appendicitis. Do not reveal the diagnosis. Mention pain started around the umbilicus then moved to the right iliac fossa if asked.",
        "voice_style": "pain_discomfort",
    },
    {
        "specialty": "neurology",
        "patient_name": "Margaret Evans",
        "patient_age": 74,
        "presenting_complaint": "New confusion",
        "hidden_diagnosis": "Urinary tract infection causing delirium",
        "case_summary": "A 74-year-old patient presents with acute confusion, reduced oral intake, and urinary symptoms.",
        "secret_prompt": "The patient has delirium secondary to urinary tract infection. Answer slowly and inconsistently. Do not reveal diagnosis. Mention dysuria and frequency only if asked clearly.",
        "voice_style": "confused_slow",
    },
    {
        "specialty": "endocrinology",
        "patient_name": "Daniel Brown",
        "patient_age": 35,
        "presenting_complaint": "Weight loss and thirst",
        "hidden_diagnosis": "New type 1 diabetes mellitus",
        "case_summary": "A 35-year-old patient presents with weight loss, thirst, urinary frequency, and fatigue.",
        "secret_prompt": "The patient has new diabetes mellitus. Do not reveal the diagnosis. Mention polyuria, polydipsia, fatigue, and weight loss when asked.",
        "voice_style": "tired_low_energy",
    },
]


def generate_dummy_case(specialty, difficulty):
    matching_cases = [
        case for case in DUMMY_CASES
        if specialty == "random" or case["specialty"] == specialty
    ]

    if not matching_cases:
        matching_cases = DUMMY_CASES

    selected_case = random.choice(matching_cases).copy()

    selected_case["difficulty"] = difficulty

    if difficulty == "easy":
        selected_case["case_summary"] += " The case should be suitable for early learners with clear symptom patterns."
    elif difficulty == "hard":
        selected_case["case_summary"] += " The case should include subtle cues and require careful red flag screening."
    else:
        selected_case["case_summary"] += " The case should be balanced for OSCE-style practice."

    return selected_case


def generate_dummy_patient_reply(clinical_case, doctor_message):
    message_lower = doctor_message.lower()

    if any(word in message_lower for word in ["hello", "hi", "name"]):
        return f"Hello doctor. My name is {clinical_case.patient_name}. I came in because of {clinical_case.presenting_complaint.lower()}."

    if any(word in message_lower for word in ["pain", "hurt", "ache"]):
        if "chest" in clinical_case.presenting_complaint.lower():
            return "It feels like a heavy pressure in the middle of my chest. It is quite uncomfortable."
        if "abdominal" in clinical_case.presenting_complaint.lower():
            return "The pain is mostly on the lower right side now. It started more around my tummy button."
        return "Yes, I am uncomfortable. It has been bothering me enough to come in today."

    if any(word in message_lower for word in ["breath", "shortness", "sob"]):
        return "I feel short of breath, especially when I move around. I can speak, but I feel more breathless than usual."

    if any(word in message_lower for word in ["fever", "temperature", "hot"]):
        return "I do not think I have had a high temperature, but I have felt generally unwell."

    if any(word in message_lower for word in ["medication", "medicine", "tablets"]):
        return "I take my usual medications, but I am not sure if they are related to this problem."

    if any(word in message_lower for word in ["allergy", "allergies"]):
        return "I do not have any allergies that I know of."

    if any(word in message_lower for word in ["smoke", "alcohol"]):
        return "I do not smoke. I drink alcohol occasionally, mostly socially."

    if any(word in message_lower for word in ["travel", "flight", "journey"]):
        if "embolism" in clinical_case.hidden_diagnosis.lower():
            return "Yes, I recently came back from a long journey. I was sitting down for many hours."
        return "No, I have not travelled recently."

    if any(word in message_lower for word in ["worry", "concern", "ideas", "expect"]):
        return "I am worried because this does not feel normal for me. I wanted to make sure it is nothing serious."

    return "I am not completely sure, doctor. Could you ask me that in another way?"