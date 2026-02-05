"""OpenClaw v3 protocol frame handling.

Frame types:
  - req:   Client request  {"type": "req", "id": "...", "method": "...", "params": {...}}
  - res:   Server response {"type": "res", "id": "...", "ok": true, "payload": {...}}
  - event: Server event    {"type": "event", "event": "...", "payload": {...}}
"""

from __future__ import annotations

import json
import uuid
from typing import Any


def make_response(req_id: str, payload: dict[str, Any], ok: bool = True) -> str:
    """Create a response frame for a request."""
    frame: dict[str, Any] = {"type": "res", "id": req_id, "ok": ok, "payload": payload}
    return json.dumps(frame)


def make_error(req_id: str, code: str, message: str) -> str:
    """Create an error response frame."""
    frame = {
        "type": "res",
        "id": req_id,
        "ok": False,
        "error": {"code": code, "message": message},
    }
    return json.dumps(frame)


def make_event(event: str, payload: dict[str, Any]) -> str:
    """Create an event frame to push to the client."""
    frame = {"type": "event", "event": event, "payload": payload}
    return json.dumps(frame)


def make_challenge() -> str:
    """Create the initial connect.challenge event."""
    return make_event(
        "connect.challenge",
        {
            "type": "connect_challenge",
            "protocols": [3],
            "server": {"id": "openclaw-gateway", "version": "0.1.0"},
        },
    )


def make_hello_ok(req_id: str) -> str:
    """Create the hello-ok response after successful auth."""
    return make_response(
        req_id,
        {"type": "hello-ok", "protocol": 3, "session": str(uuid.uuid4())},
    )


def make_tick() -> str:
    """Create a heartbeat tick event."""
    return make_event("tick", {})


def parse_frame(text: str) -> dict[str, Any] | None:
    """Parse a JSON frame from the client. Returns None on parse failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def make_chat_event(
    run_id: str,
    text: str,
    state: str = "delta",
    is_final: bool = False,
) -> str:
    """Create a chat streaming event."""
    payload: dict[str, Any] = {
        "runId": run_id,
        "state": state,
        "text": text,
    }
    if is_final:
        payload["state"] = "final"
    return make_event("chat", payload)


def make_agent_lifecycle(run_id: str, phase: str) -> str:
    """Create an agent lifecycle event (start/end)."""
    return make_event(
        "agent",
        {"runId": run_id, "stream": "lifecycle", "data": {"phase": phase}},
    )
