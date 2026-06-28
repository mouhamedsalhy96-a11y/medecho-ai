import os
import uuid

import requests


DEFAULT_ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
MAX_TTS_CHARACTERS = 1200


VOICE_STYLE_SETTINGS = {
    "neutral_adult": {
        "stability": 0.55,
        "similarity_boost": 0.75,
        "style": 0.20,
        "use_speaker_boost": True,
    },
    "tired_low_energy": {
        "stability": 0.70,
        "similarity_boost": 0.70,
        "style": 0.10,
        "use_speaker_boost": True,
    },
    "breathless_short_phrases": {
        "stability": 0.45,
        "similarity_boost": 0.70,
        "style": 0.35,
        "use_speaker_boost": True,
    },
    "anxious_fast_speech": {
        "stability": 0.35,
        "similarity_boost": 0.75,
        "style": 0.45,
        "use_speaker_boost": True,
    },
    "pain_discomfort": {
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.40,
        "use_speaker_boost": True,
    },
    "older_adult_slow": {
        "stability": 0.75,
        "similarity_boost": 0.70,
        "style": 0.15,
        "use_speaker_boost": True,
    },
    "confused_slow": {
        "stability": 0.65,
        "similarity_boost": 0.70,
        "style": 0.30,
        "use_speaker_boost": True,
    },
}


def prepare_patient_voice_text(text, voice_style):
    cleaned = " ".join(text.strip().split())

    if voice_style == "breathless_short_phrases":
        cleaned = cleaned.replace(". ", ". ... ")
    elif voice_style == "tired_low_energy":
        cleaned = f"[softly] {cleaned}"
    elif voice_style == "anxious_fast_speech":
        cleaned = f"[slightly anxious] {cleaned}"
    elif voice_style == "pain_discomfort":
        cleaned = f"[strained] {cleaned}"
    elif voice_style == "older_adult_slow":
        cleaned = f"[slowly] {cleaned}"
    elif voice_style == "confused_slow":
        cleaned = f"[hesitant] {cleaned}"

    if len(cleaned) > MAX_TTS_CHARACTERS:
        cleaned = cleaned[:MAX_TTS_CHARACTERS].rsplit(" ", 1)[0]

    return cleaned


def generate_patient_voice_audio(text, voice_style="neutral_adult"):
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    model_id = os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_ELEVENLABS_MODEL_ID).strip()

    if not api_key:
        return {
            "success": False,
            "error": "ELEVENLABS_API_KEY is missing.",
            "audio_bytes": None,
            "filename": "",
            "character_count": 0,
        }

    if not voice_id:
        return {
            "success": False,
            "error": "ELEVENLABS_VOICE_ID is missing.",
            "audio_bytes": None,
            "filename": "",
            "character_count": 0,
        }

    prepared_text = prepare_patient_voice_text(text, voice_style)
    voice_settings = VOICE_STYLE_SETTINGS.get(
        voice_style,
        VOICE_STYLE_SETTINGS["neutral_adult"],
    )

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    params = {
        "output_format": DEFAULT_OUTPUT_FORMAT,
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": prepared_text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }

    try:
        response = requests.post(
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        filename = f"patient_voice_{uuid.uuid4().hex}.mp3"

        return {
            "success": True,
            "error": "",
            "audio_bytes": response.content,
            "filename": filename,
            "character_count": len(prepared_text),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "audio_bytes": None,
            "filename": "",
            "character_count": len(prepared_text),
        }
