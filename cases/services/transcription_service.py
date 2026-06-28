import os
import tempfile
from pathlib import Path

from openai import OpenAI


DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def transcribe_audio_file(uploaded_audio):
    client = get_openai_client()

    if client is None:
        return {
            "success": False,
            "text": "",
            "error": "OPENAI_API_KEY is missing.",
        }

    suffix = Path(uploaded_audio.name).suffix or ".webm"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in uploaded_audio.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", DEFAULT_TRANSCRIPTION_MODEL),
                file=audio_file,
            )

        transcript_text = getattr(transcription, "text", "")
        transcript_text = transcript_text.strip()

        if not transcript_text:
            return {
                "success": False,
                "text": "",
                "error": "Transcription returned empty text.",
            }

        return {
            "success": True,
            "text": transcript_text,
            "error": "",
        }

    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "error": str(exc),
        }

    finally:
        try:
            if "temp_file_path" in locals():
                Path(temp_file_path).unlink(missing_ok=True)
        except Exception:
            pass
