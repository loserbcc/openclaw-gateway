"""ASR (Automatic Speech Recognition) provider — speech-to-text.

Supports OpenAI Whisper API and compatible endpoints.
"""

from __future__ import annotations

import httpx

from ..config import settings


async def transcribe(audio_data: bytes, filename: str = "audio.wav") -> str | None:
    """Transcribe audio to text. Returns transcription or None if disabled."""
    provider = settings.asr_provider

    if provider == "disabled":
        return None

    if provider == "auto":
        if settings.asr_base_url:
            return await _whisper_api(settings.asr_base_url, audio_data, filename)
        if settings.asr_api_key:
            return await _whisper_api("https://api.openai.com/v1", audio_data, filename)
        return None

    if provider in ("openai", "whisper"):
        base_url = settings.asr_base_url or "https://api.openai.com/v1"
        return await _whisper_api(base_url, audio_data, filename)

    return None


async def _whisper_api(
    base_url: str,
    audio_data: bytes,
    filename: str,
) -> str | None:
    """Call the Whisper-compatible transcription endpoint."""
    headers: dict[str, str] = {}
    if settings.asr_api_key:
        headers["Authorization"] = f"Bearer {settings.asr_api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/audio/transcriptions",
                headers=headers,
                files={"file": (filename, audio_data, "audio/wav")},
                data={"model": "whisper-1"},
            )
            if resp.status_code == 200:
                result = resp.json()
                return result.get("text", "")
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    return None
