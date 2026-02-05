"""TTS provider — text-to-speech synthesis.

Supports OpenAI-compatible TTS APIs (including ScrappyLabs/local setups).
"""

from __future__ import annotations

import httpx

from ..config import settings


async def synthesize(text: str, voice: str | None = None) -> bytes | None:
    """Synthesize speech from text. Returns audio bytes (MP3) or None if disabled."""
    provider = settings.tts_provider

    if provider == "disabled":
        return None

    if provider == "auto":
        # Try local first, then cloud
        if settings.tts_base_url:
            return await _openai_compatible_tts(settings.tts_base_url, text, voice)
        if settings.tts_api_key:
            return await _openai_compatible_tts("https://api.openai.com/v1", text, voice)
        return None

    if provider in ("openai", "scrappylabs"):
        base_url = settings.tts_base_url or "https://api.openai.com/v1"
        return await _openai_compatible_tts(base_url, text, voice)

    return None


async def _openai_compatible_tts(
    base_url: str,
    text: str,
    voice: str | None = None,
) -> bytes | None:
    """Call any OpenAI-compatible TTS endpoint."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.tts_api_key:
        headers["Authorization"] = f"Bearer {settings.tts_api_key}"

    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice or settings.tts_voice,
        "response_format": "mp3",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/audio/speech",
                json=payload,
                headers=headers,
            )
            if resp.status_code == 200:
                return resp.content
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    return None
