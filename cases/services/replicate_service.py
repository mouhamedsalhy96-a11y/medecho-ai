import os
import time
import uuid

import requests


IMAGE_KEYWORDS = [
    "x-ray",
    "xray",
    "chest x-ray",
    "ct",
    "ctpa",
    "mri",
    "ultrasound",
    "scan",
    "ecg",
]


def is_image_investigation_name(investigation_name):
    name = investigation_name.lower()
    return any(keyword in name for keyword in IMAGE_KEYWORDS)


def build_educational_image_prompt(clinical_case, investigation_name, text_report):
    return f"""
Create a fictional AI-generated educational medical-style image.

This must look like an educational simulation, not real patient imaging.

Investigation:
{investigation_name}

Case context:
- Patient age: {clinical_case.patient_age}
- Presenting complaint: {clinical_case.presenting_complaint}
- Fictional hidden diagnosis: {clinical_case.hidden_diagnosis}

Text report context:
{text_report}

Important visual safety requirements:
- Educational simulation only.
- Not real clinical imaging.
- Not for diagnosis or patient care.
- Avoid patient identifiers.
- Avoid hospital names.
- Avoid real patient metadata.
- Image should be medically educational and clearly artificial or simulated.
"""


def extract_image_url(output):
    if isinstance(output, str):
        return output

    if isinstance(output, list) and output:
        first_item = output[0]
        if isinstance(first_item, str):
            return first_item
        if isinstance(first_item, dict):
            return first_item.get("url") or first_item.get("image")

    if isinstance(output, dict):
        return output.get("url") or output.get("image") or output.get("output")

    return None


def generate_educational_image_with_replicate(
    clinical_case,
    investigation_name,
    text_report,
):
    api_token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    model_version = os.getenv("REPLICATE_IMAGE_MODEL_VERSION", "").strip()

    if not api_token:
        return {
            "success": False,
            "error": "REPLICATE_API_TOKEN is missing.",
            "image_bytes": None,
            "filename": "",
        }

    if not model_version:
        return {
            "success": False,
            "error": "REPLICATE_IMAGE_MODEL_VERSION is missing.",
            "image_bytes": None,
            "filename": "",
        }

    prompt = build_educational_image_prompt(
        clinical_case=clinical_case,
        investigation_name=investigation_name,
        text_report=text_report,
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": model_version,
        "input": {"prompt": prompt},
    }

    try:
        create_response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        create_response.raise_for_status()

        prediction = create_response.json()
        get_url = prediction.get("urls", {}).get("get")
        if not get_url:
            return {
                "success": False,
                "error": "Replicate did not return a prediction polling URL.",
                "image_bytes": None,
                "filename": "",
            }

        final_prediction = None
        for _attempt in range(30):
            poll_response = requests.get(get_url, headers=headers, timeout=30)
            poll_response.raise_for_status()

            final_prediction = poll_response.json()
            status = final_prediction.get("status")

            if status == "succeeded":
                break
            if status in ["failed", "canceled"]:
                return {
                    "success": False,
                    "error": f"Replicate prediction ended with status: {status}",
                    "image_bytes": None,
                    "filename": "",
                }

            time.sleep(2)

        if not final_prediction or final_prediction.get("status") != "succeeded":
            return {
                "success": False,
                "error": "Replicate prediction timed out.",
                "image_bytes": None,
                "filename": "",
            }

        image_url = extract_image_url(final_prediction.get("output"))
        if not image_url:
            return {
                "success": False,
                "error": "Replicate prediction succeeded but no image URL was found.",
                "image_bytes": None,
                "filename": "",
            }

        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()

        filename = f"educational_investigation_{uuid.uuid4().hex}.png"
        return {
            "success": True,
            "error": "",
            "image_bytes": image_response.content,
            "filename": filename,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "image_bytes": None,
            "filename": "",
        }

