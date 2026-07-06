# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**learnland** — a shadowing / pronunciation practice app built on YouTube videos. Paste a URL, learnland pulls the transcript (existing captions, or Whisper transcription as fallback), generates IPA phonetics, and plays the video with a time-synced transcript for shadowing.

Monorepo: FastAPI backend + React frontend + Postgres.

## Layout

- `backend/` — FastAPI app, uv-managed (Python 3.12)
  - `app/routers/` — `transcribe` (SSE stream) and `transcripts` (read-only)
  - `app/services/` — `youtube`, `transcriber` (faster-whisper), `ipa` (g2p-en → ARPAbet → IPA), `vtt_parser`, `url_utils`
  - `app/repositories/` — DB access layer
  - `app/models.py` — `Transcript` ORM model; `alembic/` — migrations
- `frontend/` — Vite + React 19 + TypeScript, Tailwind v4, shadcn/ui, TanStack Query
  - `src/components/` — `shadowing-player`, `transcribe-form`, `transcript-view`, `history-sidebar`, `ui/`
  - `src/hooks/` — `use-transcribe` (SSE), `use-youtube-player`, `use-active-segment`
- `docker-compose.yml` — postgres, backend, frontend

## Commands

Backend:

```bash
cd backend
uv run alembic upgrade head          # migrate
uv run uvicorn app.main:app --reload # serve on :8000
uv run pytest                        # tests
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev     # :5173
pnpm build   # tsc -b && vite build
pnpm lint    # oxlint
```

Full stack: `docker compose up --build` (frontend :8080, backend :8000, postgres :5433).

## Conventions

- Frontend files: kebab-case. Components in `src/components/`, hooks in `src/hooks/`, API layer in `src/api/`.
- Backend: snake_case, service/repository/router separation. Keep pure conversion logic (e.g. `arpabet_ipa.py`) separate from I/O and singletons (e.g. `ipa.py`).
- UI text is in English.
- CORS is fully open (`allow_origins=["*"]`, no credentials) — this is a local/dev-facing service.
- Postgres host port is `5433` (5432 may be taken); in-network the backend hits `postgres:5432`.
- CI builds and pushes `learnland-backend` and `learnland-frontend` images to Docker Hub on version tags.

## Verify before done

Run `pnpm lint` (frontend) and `uv run pytest` (backend) for touched areas. The Docker backend applies Alembic migrations automatically before serving, so keep migrations current.
