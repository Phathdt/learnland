# YouTube Transcript App

Monorepo: FastAPI backend + React frontend + Postgres.

## Stack

- Backend: Python 3.12, FastAPI, uv, SQLAlchemy, Alembic, faster-whisper, yt-dlp
- Frontend: React 19, Vite 8, TypeScript 6, Tailwind CSS v4, shadcn/ui, TanStack Query v5
- Database: PostgreSQL 16 (Docker)

## Prerequisites

- Docker Desktop or OrbStack
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- pnpm (`npm i -g pnpm`)

## Dev Setup

### 1. Database

```bash
docker compose up -d
```

Postgres listens on `localhost:5433` (host port remapped — 5432 may be in use).

### 2. Backend

```bash
cd backend
cp .env.example .env  # edit if needed
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

App available at http://localhost:5173. API calls proxied to http://localhost:8000 via `/api`.

## Project Structure

```
learnland/
├── backend/           # FastAPI app (uv managed)
│   ├── app/
│   │   ├── main.py    # FastAPI app + CORS
│   │   └── config.py  # Pydantic settings
│   ├── .env.example
│   └── pyproject.toml
├── frontend/          # Vite + React 19
│   ├── src/
│   │   ├── components/ui/  # shadcn/ui components
│   │   ├── lib/utils.ts    # cn helper
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── vite.config.ts
└── docker-compose.yml
```
