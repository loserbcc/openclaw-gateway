"""Token-based authentication for gateway connections."""

from __future__ import annotations

import hmac

from .config import settings


def verify_token(token: str) -> bool:
    """Constant-time comparison of the provided token against the configured one."""
    expected = settings.auth_token
    if not expected:
        return False
    return hmac.compare_digest(token, expected)
