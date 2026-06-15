# VibeTale Backend

FastAPI backend for VibeTale — an immersive e-book reading app with AI-generated ambiance (audio + visuals).

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker Desktop (for local Supabase)

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

> **Note:** `stable-audio-3` is referenced as a local path dependency in `pyproject.toml`.  
> Clone it first if you haven't: `git clone https://github.com/Stability-AI/stable-audio-3.git`

### 2. Environment

```bash
cp .env.example .env
# Edit .env and set your keys (Gemini, Clipdrop, etc.)
```

### 3. Start Local Supabase

```bash
# First time only
supabase init

# Start services (Docker Desktop must be running)
supabase start

# Apply database schema & create storage bucket
supabase db reset
```

### 4. Run the Server

```bash
# API server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Celery worker (in a separate terminal)
uv run start_celery_worker.py
```

## API & Docs

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/admin/?key=change-me-in-production | Admin Dashboard |

## Admin Dashboard

A built-in monitoring dashboard is available at `/admin`:
- Database stats (books, chunks, sessions)
- Provider health (LLM, Audio, Image, Redis, Supabase)
- GPU / VRAM usage
- Recent error logs

Set `ADMIN_DASHBOARD_KEY` in `.env` to secure access.

## Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Web Framework | FastAPI |
| Database | Supabase PostgreSQL (local Docker) |
| Storage | Supabase Object Storage |
| Task Queue | Celery + Redis |
| LLM | Google Gemini / Ollama |
| Audio | Stable Audio 3.0 Small SFX |
| Images | Local SDXL-Turbo / Clipdrop API |
