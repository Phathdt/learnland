# learnland

Learn shadowing and practice English pronunciation from YouTube videos. Paste a URL and learnland pulls the transcript (existing captions, or Whisper transcription as a fallback), generates IPA phonetics, then plays the video with a time-synced transcript so you can listen and repeat.

Monorepo: FastAPI backend + React frontend + Postgres.

## Features

- Pull transcripts from YouTube captions, falling back to faster-whisper when a video has none
- Generate offline IPA phonetics (g2p-en → ARPAbet → IPA) per sentence
- Shadowing player: embedded YouTube video, transport controls, transcript highlighted in sync with playback
- Transcript history stored in Postgres, replayable anytime
- Realtime transcribe progress over Server-Sent Events (SSE)

## Stack

- Backend: Python 3.12, FastAPI, uv, SQLAlchemy, Alembic, faster-whisper, yt-dlp, g2p-en
- Frontend: React 19, Vite 8, TypeScript 6, Tailwind CSS v4, shadcn/ui, TanStack Query v5
- Database: PostgreSQL 16 (Docker)

## Prerequisites

- Docker Desktop or OrbStack
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- pnpm (`npm i -g pnpm`)

## Dev Setup

### 1. Database

```bash
docker compose up -d postgres
```

Postgres listens on `localhost:5433` (host port remapped — 5432 may be in use).

### 2. Backend

```bash
cd backend
cp .env.example .env  # edit if needed
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API available at http://localhost:8000. Health check: `GET /health`.

> Note: `faster-whisper` pulls `ctranslate2` which requires ~500 MB disk and benefits from 4 GB+ RAM.
> The default model is `base` (minimal). Change `WHISPER_MODEL` in `.env` to `small`, `medium`, or `large` as needed.

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

App available at http://localhost:5173. API calls hit the backend at `VITE_API_URL` (default http://localhost:8000).

## Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend: http://localhost:8000
- Postgres: localhost:5433

Backend applies Alembic migrations automatically before serving.

## API

- `POST /api/transcribe` — SSE stream: caption → whisper → IPA → save
- `GET /api/transcripts` — list transcripts (newest first)
- `GET /api/transcripts/{id}` — fetch a single transcript
- `GET /health` — health check

## Project Structure

```
learnland/
├── backend/                    # FastAPI app (uv managed)
│   ├── app/
│   │   ├── main.py             # FastAPI app + CORS
│   │   ├── config.py           # Pydantic settings
│   │   ├── db.py               # SQLAlchemy session
│   │   ├── models.py           # Transcript ORM model
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── routers/            # transcribe (SSE) + transcripts (read)
│   │   ├── repositories/       # DB access layer
│   │   └── services/           # youtube, transcriber, ipa, vtt_parser, url_utils
│   ├── alembic/                # migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/                   # Vite + React 19
│   ├── src/
│   │   ├── components/         # shadowing-player, transcribe-form, history-sidebar, ui/
│   │   ├── hooks/              # use-transcribe, use-youtube-player, use-active-segment
│   │   ├── api/                # client + transcripts
│   │   └── App.tsx
│   └── vite.config.ts
├── docker-compose.yml
└── .github/workflows/          # build + push images to Docker Hub (learnland-backend, learnland-frontend)
```

## Testing

```bash
cd backend
uv run pytest
```

Smoke test the full stack: `scripts/smoke-test.sh`.
