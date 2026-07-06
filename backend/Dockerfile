# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    NLTK_DATA=/opt/nltk_data

# ffmpeg: required by yt-dlp for audio extraction (FFmpegExtractAudio)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uv: fast Python package manager (matches local dev workflow)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the app and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

# Pre-download the NLTK POS tagger used by g2p-en so the first IPA request
# does not stall on a network download (see app/services/ipa.py).
RUN uv run python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng', download_dir='/opt/nltk_data')"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
