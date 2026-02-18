<div align="center">

# Agora — Voice‑First Socratic Tutor

Multimodal tutoring with voice, retrieval‑augmented reasoning, and a collaborative whiteboard.

</div>

**Live stack:** FastAPI + LangGraph + Groq (Llama 3) + Qdrant + Next.js + Socket.IO + Groq Whisper + Edge TTS

## Highlights

- Voice push‑to‑talk with real‑time STT and TTS
- Socratic prompting with frustration monitoring and quiz mode
- Materials ingest (PDF/images/text) into Qdrant RAG store
- Shared JSON schemas for tight frontend/backend contracts
- Interactive whiteboard actions (create notes, highlight, load images)
- Structured JSON logging and sane defaults for local/dev/prod

## Tech Stack

- Backend: FastAPI, LangGraph, Groq (Llama 3), Qdrant, httpx, websockets
- Speech: Groq Whisper (STT), Edge TTS (TTS)  — *Free SOTA Tiers*
- Frontend: Next.js 16 (React 19), Tailwind, Zustand, socket.io‑client, Tldraw
- Data: Qdrant (vector DB), Docling (document parsing)
- Tooling: Pydantic v2, Ruff, MyPy, Vitest/Playwright (planned), Docker Compose

## Repository Layout

```
backend/                  # FastAPI app, services, LangGraph
	app/
		api/                  # HTTP + Socket.IO routes
		services/             # groq_llm, qdrant, stt (groq), tts (edge)
		graph/                # state + nodes + builder
		workers/              # chunking + ingest
	requirements.txt        # Python deps (pip)
frontend/            # Next.js app (App Router)
	app/, components/, lib/ # UI, hooks, stores, ws client
shared/schema/            # Pydantic + Zod message contracts
docker-compose.yml        # Qdrant + (backend + frontend) services
.env.example              # Backend + Compose example env
```

## Environment

API keys are required. Copy examples and fill in values.

```zsh
cp .env.example .env                    # Backend + compose
cp frontend/.env.local.example frontend/.env.local  # Frontend
```

Required keys and sensible defaults are documented in the example files.

## Local Development

### Prereqs

- Python 3.11+
- Node.js 20+
- pnpm 9+ (Corepack auto‑installs) or npm
- Docker (for Qdrant/dev compose)

### 1) Start Qdrant

```zsh
docker compose up -d qdrant
```

### 2) Backend (FastAPI)

Option A — venv (recommended)
```zsh
cd backend
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
```

Option B — Conda
```zsh
cd backend
conda env create -f environment.yml
conda activate agora
python -m app.main
```

Backend serves at `http://localhost:8000` and mounts Socket.IO at `/socket.io`.

### 3) Frontend (Next.js)

```zsh
cd frontend
pnpm install
pnpm dev
```

Frontend runs at `http://localhost:3000`.

## Docker Deployment

We provide Dockerfiles for backend and frontend and extend `docker-compose.yml` to run the full stack.

Build and start everything:
```zsh
docker compose up -d --build
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Qdrant: http://localhost:6333

To follow logs:
```zsh
docker compose logs -f backend frontend qdrant
```

To stop:
```zsh
docker compose down
```

Notes:
- **Groq & Edge TTS**: The system defaults to Groq for LLM/STT and Edge TTS for speech. These are free cloud tiers that arguably outperform local models without the resource cost.
- **Deepgram/ElevenLabs**: Supported in code but currently configured for free tier stack.
- Frontend `NEXT_PUBLIC_*` values are inlined at build time. Set them in `.env` (compose) or `frontend/.env.local` before building.

## Running Tests and Linters

Backend:
```zsh
cd backend
pytest
ruff check .
mypy .
```

Frontend:
```zsh
cd frontend
pnpm lint
pnpm build
```

## Key Features (Detail)

- Voice Loop: press‑to‑talk → Groq Whisper (STT) → LangGraph route → RAG → Socratic response (Llama 3) → Edge TTS stream
- Materials Ingest: `/api/materials/upload` processes PDFs/images/text via Docling, embeds with Gemini, upserts to Qdrant per `user_id`/`course_id`
- Shared Contracts: JSON message types validated on both sides under `shared/schema`
- Whiteboard Actions: backend emits `visual` messages (create/hightlight/load) → Tldraw updates
- Session Tracking: uuidv4 `user_id` (localStorage) + `session_id` per run

## Troubleshooting

- Qdrant: `curl http://localhost:6333/health`
- WebSocket: ensure `NEXT_PUBLIC_WS_URL` points to `http://localhost:8000`
- STT/TTS: verify keys in `.env`; switch providers with `STT_PROVIDER`/`TTS_PROVIDER`
- Logs: set `LOG_LEVEL=INFO` to reduce noise; optional `LOG_FILE=/tmp/agora_backend.log`

## License

MIT — Built for NYU Hackathon 2025
