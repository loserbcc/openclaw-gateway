"""OpenClaw Gateway — WSS server for phone-to-moltbot communication.

Run with: openclaw-gateway
Or:       uvicorn openclaw_gateway.server:app --host 0.0.0.0 --port 8770
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from . import protocol, storage
from .auth import verify_token
from .config import settings
from .providers import asr, llm, tts

logger = logging.getLogger("openclaw")

# Connected clients
_clients: dict[str, WebSocket] = {}

# Conversation history per session (in-memory, reset on restart)
_conversations: dict[str, list[dict[str, str]]] = {}

SYSTEM_PROMPT = (
    "You are a helpful AI assistant connected via OpenClaw Gateway. "
    "Be concise and direct in your responses."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    token = settings.ensure_token()
    logger.info("=" * 50)
    logger.info("OpenClaw Gateway v0.1.0")
    logger.info("=" * 50)
    logger.info(f"WSS endpoint: ws://{settings.host}:{settings.port}/gateway")
    logger.info(f"REST endpoint: http://{settings.host}:{settings.port}")
    logger.info(f"Auth token: {token[:12]}...")

    provider_info = await llm.get_provider_info()
    logger.info(f"LLM: {provider_info['provider']} ({provider_info['model'] or 'none'})")
    logger.info("=" * 50)

    # Start heartbeat
    heartbeat_task = asyncio.create_task(_heartbeat_loop())

    yield

    # Shutdown
    heartbeat_task.cancel()
    await storage.close_db()


app = FastAPI(title="OpenClaw Gateway", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# WebSocket Gateway
# ---------------------------------------------------------------------------


@app.websocket("/gateway")
async def gateway_ws(ws: WebSocket):
    await ws.accept()
    client_id = str(uuid.uuid4())[:8]
    authenticated = False

    # Send challenge
    await ws.send_text(protocol.make_challenge())
    logger.info(f"[{client_id}] Connected, challenge sent")

    try:
        while True:
            text = await ws.receive_text()
            frame = protocol.parse_frame(text)
            if frame is None:
                continue

            frame_type = frame.get("type", "")
            req_id = frame.get("id", "")

            if frame_type == "req":
                method = frame.get("method", "")
                params = frame.get("params", {})

                if method == "connect":
                    # Auth handshake
                    auth = params.get("auth", {})
                    token = auth.get("token", "")
                    if verify_token(token):
                        authenticated = True
                        _clients[client_id] = ws
                        _conversations.setdefault(client_id, [])
                        await ws.send_text(protocol.make_hello_ok(req_id))
                        logger.info(f"[{client_id}] Authenticated")
                    else:
                        await ws.send_text(
                            protocol.make_error(req_id, "auth_failed", "Invalid token")
                        )
                        logger.warning(f"[{client_id}] Auth failed")
                        await ws.close(code=4001, reason="Authentication failed")
                        return

                elif method == "chat.send":
                    if not authenticated:
                        await ws.send_text(
                            protocol.make_error(req_id, "not_authenticated", "Not authenticated")
                        )
                        continue

                    message_text = params.get("message", "")
                    if not message_text:
                        continue

                    # Ack the request
                    run_id = str(uuid.uuid4())[:12]
                    await ws.send_text(
                        protocol.make_response(
                            req_id, {"status": "accepted", "runId": run_id}
                        )
                    )

                    # Store user message
                    await storage.store_message(source="human", text_content=message_text)

                    # Process in background
                    asyncio.create_task(
                        _handle_chat(ws, client_id, run_id, message_text)
                    )

                elif method == "approval.respond":
                    if not authenticated:
                        continue
                    # Placeholder for approval handling
                    await ws.send_text(
                        protocol.make_response(req_id, {"status": "acknowledged"})
                    )

                else:
                    await ws.send_text(
                        protocol.make_error(req_id, "unknown_method", f"Unknown: {method}")
                    )

    except WebSocketDisconnect:
        logger.info(f"[{client_id}] Disconnected")
    except Exception as e:
        logger.error(f"[{client_id}] Error: {e}")
    finally:
        _clients.pop(client_id, None)
        _conversations.pop(client_id, None)


async def _handle_chat(ws: WebSocket, client_id: str, run_id: str, text: str):
    """Process a chat message: stream LLM response, optionally TTS."""
    try:
        # Signal thinking start
        await ws.send_text(protocol.make_agent_lifecycle(run_id, "start"))

        # Build conversation
        history = _conversations.get(client_id, [])
        history.append({"role": "user", "content": text})

        # Stream LLM response
        full_response = ""
        async for token in llm.chat_stream(history, system=SYSTEM_PROMPT):
            full_response += token
            await ws.send_text(
                protocol.make_chat_event(run_id, full_response, state="delta")
            )

        # Final message
        await ws.send_text(
            protocol.make_chat_event(run_id, full_response, state="final", is_final=True)
        )
        await ws.send_text(protocol.make_agent_lifecycle(run_id, "end"))

        # Update conversation history
        history.append({"role": "assistant", "content": full_response})
        # Keep last 20 turns
        if len(history) > 40:
            history[:] = history[-40:]

        # Store response
        await storage.store_message(source="crab", text_content=full_response)

        # TTS (if enabled)
        audio = await tts.synthesize(full_response)
        if audio:
            audio_b64 = base64.b64encode(audio).decode("ascii")
            await ws.send_text(
                protocol.make_event(
                    "audio_broadcast",
                    {"audio_base64": audio_b64, "text": full_response},
                )
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[{client_id}] Chat error: {e}")
        try:
            await ws.send_text(
                protocol.make_event(
                    "agent",
                    {
                        "runId": run_id,
                        "stream": "error",
                        "data": {"message": str(e)},
                    },
                )
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {"name": "OpenClaw Gateway", "version": "0.1.0", "protocol": 3}


@app.get("/messages")
async def get_messages(limit: int = 50):
    return await storage.get_messages(limit=limit)


@app.post("/voice")
async def voice_upload(file: UploadFile):
    """Upload voice recording for transcription."""
    audio_data = await file.read()
    transcription = await asr.transcribe(audio_data, filename=file.filename or "audio.wav")
    if transcription:
        return {"transcription": transcription}
    return JSONResponse(
        status_code=503,
        content={"error": "ASR not available. Configure OPENCLAW_ASR_API_KEY."},
    )


@app.post("/files/upload")
async def file_upload(file: UploadFile):
    """Upload a file (from share extension or file picker)."""
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or f"{uuid.uuid4()}.bin"
    file_path = upload_dir / filename
    content = await file.read()
    file_path.write_bytes(content)

    return {"filename": filename, "size": len(content)}


@app.get("/health")
async def health():
    provider_info = await llm.get_provider_info()
    return {
        "status": "ok",
        "clients": len(_clients),
        "llm": provider_info,
    }


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


async def _heartbeat_loop():
    """Send periodic tick events to connected clients."""
    while True:
        await asyncio.sleep(30)
        tick = protocol.make_tick()
        for client_id, ws in list(_clients.items()):
            try:
                await ws.send_text(tick)
            except Exception:
                _clients.pop(client_id, None)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main():
    import uvicorn

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    uvicorn.run(
        "openclaw_gateway.server:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )


if __name__ == "__main__":
    main()
