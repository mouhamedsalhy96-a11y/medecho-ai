from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .transcript_context_service import add_transcript_to_pdf_story


DISCLAIMER = "Educational simulation only. Not for diagnosis or patient care."


def safe_text(value):
    if value is None:
        return ""
    return str(value).replace("\n", "<br/>")


def format_score_out_of_10(score):
    if score is None:
        return "Not scored"

    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        return str(score)

    if numeric_score > 10:
        numeric_score = numeric_score / 10

    if numeric_score.is_integer():
        return f"{int(numeric_score)}/10"

    return f"{numeric_score:.1f}/10"


def add_section(story, title, body, styles):
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(Paragraph(safe_text(body) or "Not provided.", styles["BodyText"]))
    story.append(Spacer(1, 0.35 * cm))


def build_feedback_pdf(clinical_case):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="MedEcho AI Feedback",
    )

    base_styles = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "Title",
            parent=base_styles["Title"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=12,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=base_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=base_styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "BodyText": ParagraphStyle(
            "BodyText",
            parent=base_styles["BodyText"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=base_styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        ),
    }

    story = []

    story.append(Paragraph("MedEcho AI OSCE Feedback", styles["Title"]))
    story.append(Paragraph(DISCLAIMER, styles["Subtitle"]))

    case_intro = (
        f"Patient: {safe_text(clinical_case.patient_name)}, {safe_text(clinical_case.patient_age)}<br/>"
        f"Presenting complaint: {safe_text(clinical_case.presenting_complaint)}<br/>"
        f"Completed: {safe_text(clinical_case.completed_at or 'Not recorded')}"
    )

    story.append(Paragraph(case_intro, styles["BodyText"]))
    story.append(Spacer(1, 0.35 * cm))

    score_data = [
        ["Domain", "Score"],
        ["Overall", format_score_out_of_10(clinical_case.overall_score)],
        ["Data gathering", format_score_out_of_10(clinical_case.data_gathering_score)],
        ["Clinical reasoning", format_score_out_of_10(clinical_case.clinical_reasoning_score)],
        ["Management", format_score_out_of_10(clinical_case.management_score)],
        ["IPS", format_score_out_of_10(clinical_case.ips_score)],
        ["Safety-netting", format_score_out_of_10(clinical_case.safety_netting_score)],
    ]

    score_table = Table(score_data, colWidths=[10 * cm, 4 * cm])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )

    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    add_section(story, "Overall feedback", clinical_case.overall_feedback, styles)
    add_section(story, "Data gathering", clinical_case.data_gathering_feedback, styles)
    add_section(story, "Clinical reasoning", clinical_case.clinical_reasoning_feedback, styles)
    add_section(story, "Management", clinical_case.management_feedback, styles)
    add_section(story, "IPS", clinical_case.ips_feedback, styles)
    add_section(story, "Safety-netting", clinical_case.safety_netting_feedback, styles)
    add_section(story, "Critical misses", clinical_case.critical_misses, styles)
    add_section(story, "Strengths", clinical_case.strengths, styles)
    add_section(story, "Improvement plan", clinical_case.improvement_plan, styles)

    story.append(Spacer(1, 0.5 * cm))

    add_transcript_to_pdf_story(
        story=story,
        clinical_case=clinical_case,
        styles=styles,
        Paragraph=Paragraph,
        Spacer=Spacer,
    )

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Report prepared by MedEcho AI. " + DISCLAIMER, styles["Small"]))

    document.build(story)
    buffer.seek(0)

    return buffer