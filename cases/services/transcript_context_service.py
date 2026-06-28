from xml.sax.saxutils import escape


def get_case_messages(clinical_case):
    return clinical_case.messages.order_by("created_at", "id")


def build_consultation_transcript(clinical_case, min_chars=2):
    lines = []
    for message in get_case_messages(clinical_case):
        content = (message.content or "").strip()
        if len(content) < min_chars:
            continue
        role = (message.role or "").strip().lower()
        if role == "doctor":
            label = "Doctor"
        elif role == "patient":
            label = "Patient"
        elif role == "investigation":
            label = "Investigation"
        else:
            label = role.capitalize() if role else "Message"
        lines.append(f"{label}: {content}")
    return "\n".join(lines) if lines else "No consultation transcript was captured."


def build_feedback_transcript_context(clinical_case):
    transcript = build_consultation_transcript(clinical_case)
    return f"""
FULL CONSULTATION TRANSCRIPT:
{transcript}

Use the transcript above when assessing the candidate's history-taking, communication, clinical reasoning, risk assessment, safety-netting and consultation structure.
Do not assume the candidate asked or explained something unless it appears in the transcript or final submitted answer.
""".strip()


def append_transcript_to_feedback_prompt(base_prompt, clinical_case):
    return f"{base_prompt.rstrip()}\n\n{build_feedback_transcript_context(clinical_case)}\n"


def add_transcript_to_pdf_story(story, clinical_case, styles, Paragraph, Spacer, min_chars=2):
    story.append(Paragraph("Consultation Transcript", styles["SectionTitle"]))
    story.append(Spacer(1, 8))
    has_any_message = False
    for message in get_case_messages(clinical_case):
        content = (message.content or "").strip()
        if len(content) < min_chars:
            continue
        has_any_message = True
        role = (message.role or "message").strip().lower()
        if role == "doctor":
            label = "Doctor"
        elif role == "patient":
            label = "Patient"
        elif role == "investigation":
            label = "Investigation"
        else:
            label = role.capitalize()
        safe_label = escape(label)
        safe_content = escape(content).replace("\n", "<br/>")
        story.append(Paragraph(f"<b>{safe_label}:</b> {safe_content}", styles["BodyText"]))
        story.append(Spacer(1, 6))
    if not has_any_message:
        story.append(Paragraph("No consultation transcript was captured.", styles["BodyText"]))
        story.append(Spacer(1, 6))
    return story
