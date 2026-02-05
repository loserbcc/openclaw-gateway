"""Configuration via environment variables or .env file."""

from __future__ import annotations

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Gateway configuration. All values can be set via environment variables
    or a .env file in the project root."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8770
    log_level: str = "info"

    # Auth — generated on first run if not set
    auth_token: str = ""

    # LLM provider
    llm_provider: str = "auto"  # auto | openai | anthropic | ollama
    llm_base_url: str = ""  # e.g. http://localhost:11434/v1 for ollama
    llm_api_key: str = ""
    llm_model: str = ""  # auto-detected if empty

    # TTS provider
    tts_provider: str = "auto"  # auto | openai | scrappylabs | disabled
    tts_base_url: str = ""
    tts_api_key: str = ""
    tts_voice: str = "alloy"

    # ASR provider
    asr_provider: str = "auto"  # auto | openai | whisper | disabled
    asr_base_url: str = ""
    asr_api_key: str = ""

    # Storage
    db_path: str = "data/openclaw.db"

    model_config = {"env_prefix": "OPENCLAW_", "env_file": ".env", "extra": "ignore"}

    def ensure_token(self) -> str:
        """Generate and persist a token if none exists."""
        if self.auth_token:
            return self.auth_token

        token = f"ocgw_{secrets.token_hex(24)}"
        env_path = Path(".env")

        # Append to .env
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()

        # Remove existing OPENCLAW_AUTH_TOKEN if present
        lines = [l for l in lines if not l.startswith("OPENCLAW_AUTH_TOKEN=")]
        lines.append(f"OPENCLAW_AUTH_TOKEN={token}")
        env_path.write_text("\n".join(lines) + "\n")

        self.auth_token = token
        return token


settings = Settings()
