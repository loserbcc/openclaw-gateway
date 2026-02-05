# OpenClaw Gateway

Open-source WSS gateway for connecting phones to moltbots. This is the backend server for [ClawPhone](https://github.com/loserbcc/claw-phone) — a direct hotline between your phone and your AI agents.

## Quick Start (Docker)

```bash
git clone https://github.com/loserbcc/openclaw-gateway.git
cd openclaw-gateway
cp .env.example .env
docker compose up
```

The gateway starts on port `8770`. Your auth token is auto-generated and printed to the console on first run.

## Quick Start (Python)

```bash
pip install openclaw-gateway
openclaw-gateway
```

Or from source:

```bash
git clone https://github.com/loserbcc/openclaw-gateway.git
cd openclaw-gateway
pip install -e .
cp .env.example .env
openclaw-gateway
```

## How It Works

```
Phone (ClawPhone)  ──WSS──►  OpenClaw Gateway  ──►  LLM (ollama/OpenAI/Claude)
                                    │
                                    ├──►  TTS (OpenAI-compatible)
                                    └──►  ASR (Whisper-compatible)
```

1. ClawPhone connects via WebSocket to `/gateway`
2. OpenClaw v3 handshake authenticates with your token
3. You send text/voice → gateway routes to your LLM
4. LLM response streams back to your phone in real-time
5. Optional: TTS audio sent back for spoken responses

## Configuration

All settings via environment variables (prefix `OPENCLAW_`) or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_PORT` | `8770` | Server port |
| `OPENCLAW_AUTH_TOKEN` | auto-generated | Auth token for phone connections |
| `OPENCLAW_LLM_PROVIDER` | `auto` | `auto`, `openai`, `anthropic`, `ollama` |
| `OPENCLAW_LLM_BASE_URL` | — | Custom OpenAI-compatible endpoint |
| `OPENCLAW_LLM_API_KEY` | — | API key for cloud LLM |
| `OPENCLAW_LLM_MODEL` | auto-detected | Model name |
| `OPENCLAW_TTS_PROVIDER` | `disabled` | `auto`, `openai`, `scrappylabs`, `disabled` |
| `OPENCLAW_ASR_PROVIDER` | `disabled` | `auto`, `openai`, `whisper`, `disabled` |

### Auto-Detection

With `OPENCLAW_LLM_PROVIDER=auto` (default), the gateway:

1. Checks for local **ollama** at `localhost:11434` — uses the first available model
2. Falls back to cloud API if `OPENCLAW_LLM_API_KEY` is set

This means if you have ollama running, it just works with zero config.

## Connecting ClawPhone

1. Start the gateway
2. Note the auth token from the console output
3. In ClawPhone, add a new gateway:
   - **URL**: `wss://your-server:8770/gateway` (or use Tailscale hostname)
   - **Token**: paste the auth token

### Tailscale (Recommended)

For secure remote access without port forwarding:

```bash
# On the machine running the gateway
tailscale serve https 8770
```

Then in ClawPhone, use your Tailscale hostname: `wss://your-machine.your-tailnet.ts.net/gateway`

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server info |
| `/health` | GET | Health check + provider status |
| `/messages` | GET | Message history |
| `/voice` | POST | Upload audio for transcription |
| `/files/upload` | POST | Upload files |

## Protocol

OpenClaw v3 — lightweight JSON frames over WebSocket.

### Frame Types

**Request** (client → server):
```json
{"type": "req", "id": "uuid", "method": "chat.send", "params": {"message": "hello"}}
```

**Response** (server → client):
```json
{"type": "res", "id": "uuid", "ok": true, "payload": {"status": "accepted", "runId": "abc123"}}
```

**Event** (server → client):
```json
{"type": "event", "event": "chat", "payload": {"runId": "abc123", "state": "delta", "text": "Hello"}}
```

### Connection Flow

1. Server sends `connect.challenge`
2. Client sends `connect` request with auth token
3. Server responds with `hello-ok`
4. Client sends `chat.send` requests
5. Server streams `chat` events (delta → final) + `agent` lifecycle events

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
