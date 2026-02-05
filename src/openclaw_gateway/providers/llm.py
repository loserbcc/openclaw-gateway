"""LLM provider — auto-detects ollama (local) or uses configured cloud API.

Supports any OpenAI-compatible API (ollama, vLLM, LM Studio, OpenAI, etc.)
and Anthropic's Claude API.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config import settings


async def _detect_provider() -> tuple[str, str, str]:
    """Auto-detect available LLM. Returns (provider, base_url, model)."""
    # Try local ollama first
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if models:
                    model_name = models[0]["name"]
                    return "ollama", "http://localhost:11434/v1", model_name
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    # Try configured OpenAI-compatible endpoint
    if settings.llm_base_url and settings.llm_api_key:
        return "openai", settings.llm_base_url, settings.llm_model or "gpt-4o-mini"

    # Fall back to OpenAI if API key is set
    if settings.llm_api_key:
        return "openai", "https://api.openai.com/v1", settings.llm_model or "gpt-4o-mini"

    return "none", "", ""


async def get_provider_info() -> dict[str, str]:
    """Return current provider detection info for diagnostics."""
    if settings.llm_provider == "auto":
        provider, base_url, model = await _detect_provider()
    else:
        provider = settings.llm_provider
        base_url = settings.llm_base_url or "https://api.openai.com/v1"
        model = settings.llm_model or "gpt-4o-mini"
    return {"provider": provider, "base_url": base_url, "model": model}


async def chat_stream(
    messages: list[dict[str, str]],
    system: str | None = None,
) -> AsyncIterator[str]:
    """Stream chat completion tokens from the configured LLM."""
    if settings.llm_provider == "auto":
        provider, base_url, model = await _detect_provider()
    else:
        provider = settings.llm_provider
        base_url = settings.llm_base_url
        model = settings.llm_model

    if provider == "none":
        yield "No LLM provider configured. Set OPENCLAW_LLM_API_KEY or run ollama locally."
        return

    if provider in ("openai", "ollama", "auto"):
        async for token in _openai_compatible_stream(base_url, model, messages, system):
            yield token
    elif provider == "anthropic":
        async for token in _anthropic_stream(model, messages, system):
            yield token
    else:
        yield f"Unknown LLM provider: {provider}"


async def _openai_compatible_stream(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    system: str | None = None,
) -> AsyncIterator[str]:
    """Stream from any OpenAI-compatible API (OpenAI, ollama, vLLM, LM Studio)."""
    api_messages: list[dict[str, str]] = []
    if system:
        api_messages.append({"role": "system", "content": system})
    api_messages.extend(messages)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    payload: dict[str, Any] = {
        "model": model,
        "messages": api_messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    return
                try:
                    import json

                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (KeyError, IndexError, ValueError):
                    continue


async def _anthropic_stream(
    model: str,
    messages: list[dict[str, str]],
    system: str | None = None,
) -> AsyncIterator[str]:
    """Stream from Anthropic's Claude API."""
    model = model or "claude-sonnet-4-20250514"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
    }

    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "messages": messages,
        "stream": True,
    }
    if system:
        payload["system"] = system

    base_url = settings.llm_base_url or "https://api.anthropic.com"

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/v1/messages",
            json=payload,
            headers=headers,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    import json

                    event = json.loads(line[6:])
                    if event.get("type") == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        if text:
                            yield text
                except (ValueError, KeyError):
                    continue
