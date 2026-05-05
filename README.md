# OpenClaw Gateway

**Your bots, your phone, your data. No middleman.**

Open-source WebSocket gateway for connecting your phone directly to your AI agents. No Telegram. No Discord. No third-party servers seeing your messages.

> ⚠️ **Status: stale / unmaintained.** No first-party iOS client ever shipped publicly. Active development moved to **[BrainJack](https://brainjack.ai)** ([TestFlight](https://testflight.apple.com/join/z8H86Qfj)) — same WSS-channel, your-data-your-server thesis, plus voice in/out and an open backend that can speak OpenClaw v3 or any protocol you wire in. The gateway code here still works and the protocol is documented if you want to build your own client.

<p align="center">
  <a href="https://github.com/loserbcc/openclaw-gateway/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://scrappylabs.ai"><img src="https://img.shields.io/badge/Free_TTS-ScrappyLabs-orange" alt="ScrappyLabs"></a>
</p>

## Why?

Every bot platform sees everything:
- Telegram reads your bot conversations
- Discord logs every message
- "AI assistant" apps route through their servers

OpenClaw Gateway runs on **your hardware**. Messages travel directly from your phone to your server over encrypted WebSocket. Zero third-party visibility.

---

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/loserbcc/openclaw-gateway.git
cd openclaw-gateway
docker compose up
```

### Python

```bash
pip install openclaw-gateway
openclaw-gateway
```

The gateway starts on port `8770`. Your auth token is printed to the console on first run.

---

## Connect a Client

There is no first-party iOS client published. The gateway speaks the **OpenClaw v3** WebSocket protocol — connect any client that implements it, or roll your own.

- **URL**: `wss://your-server:8770/gateway`
- **Token**: auth token printed to the console on first run

For a built-and-shipped voice/agent app over WSS, see **[BrainJack](https://brainjack.ai)** instead.

### Remote Access (Tailscale)

For secure access from anywhere without port forwarding:

```bash
tailscale serve https 8770
```

Then use your Tailscale hostname: `wss://your-machine.ts.net/gateway`

---

## How It Works

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Any OpenClaw   │  WSS    │  OpenClaw        │         │  Your LLM       │
│  v3 client      │ ──────► │  Gateway         │ ──────► │  (ollama/etc)   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                    │
                                    ├──► TTS (ScrappyLabs / local)
                                    └──► ASR (ScrappyLabs / Whisper)
```

1. Phone connects via encrypted WebSocket
2. You send text or voice
3. Gateway routes to your LLM (local or cloud)
4. Response streams back in real-time
5. Optional: TTS audio for spoken responses

---

## Configuration

Environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_PORT` | `8770` | Server port |
| `OPENCLAW_AUTH_TOKEN` | auto | Auth token (auto-generated if not set) |
| `OPENCLAW_LLM_PROVIDER` | `auto` | `auto`, `openai`, `anthropic`, `ollama` |
| `OPENCLAW_LLM_BASE_URL` | — | Custom OpenAI-compatible endpoint |
| `OPENCLAW_LLM_API_KEY` | — | API key for cloud LLM |
| `OPENCLAW_TTS_PROVIDER` | `scrappylabs` | `scrappylabs`, `openai`, `local`, `disabled` |
| `OPENCLAW_ASR_PROVIDER` | `scrappylabs` | `scrappylabs`, `whisper`, `disabled` |

### Zero-Config Local LLM

If you have **ollama** running, the gateway auto-detects it. No config needed.

```bash
# Start ollama with any model
ollama run llama3

# Start gateway — it finds ollama automatically
openclaw-gateway
```

### ScrappyLabs Integration (Free)

TTS and speech recognition powered by [ScrappyLabs](https://scrappylabs.ai):

- 50+ voices including character clones
- Voice design from text descriptions
- Fast speech recognition

No API key needed. No account. No rate limits for reasonable use. Just works.

---

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server info |
| `/health` | GET | Health check |
| `/setup` | GET | QR code for phone connection |
| `/messages` | GET | Message history |
| `/voice` | POST | Upload audio for transcription |

---

## Roadmap

- [x] WebSocket gateway with OpenClaw v3 protocol
- [x] Auto-detect local ollama
- [x] ScrappyLabs TTS/ASR integration
- [ ] QR code connection setup (`--qr` flag + `/setup` endpoint)
- [ ] Web dashboard for message history
- [ ] Multi-user support
- [ ] Plugin system for custom handlers
- [ ] Matrix/XMPP bridge

---

## Community

This is a community project. Take it where you want.

- **Issues**: Bug reports, feature requests
- **PRs**: Contributions welcome
- **Discussions**: Ideas, use cases, show & tell

---

## License

MIT — do whatever you want with it.

---

<p align="center">
  <i>Part of the <a href="https://scrappylabs.ai">ScrappyLabs</a> ecosystem</i><br>
  <i>Free tools for builders. No money. No spam.</i>
</p>
