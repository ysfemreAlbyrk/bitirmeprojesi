# Supabase Docker Setup — VibeTale

Self-hosted Supabase runs as **8 separate Docker services** orchestrated by `docker-compose.yml`. This replaces the old (broken) single-container approach.

## Service Map

| Container | Purpose | Port |
|---|---|---|
| `supabase-db` | PostgreSQL 15 | 5432 |
| `supabase-kong` | API Gateway | **8000** (HTTP), 8443 (HTTPS) |
| `supabase-auth` | GoTrue auth | internal |
| `supabase-rest` | PostgREST | internal |
| `supabase-storage` | File storage | internal |
| `supabase-imgproxy` | Image transform | internal |
| `supabase-meta` | DB management | internal |
| `supabase-studio` | Studio UI | **54323** (direct) |

FastAPI runs separately on **port 8080**.

## First-Time Setup

### Step 1 — Generate secrets

Run the key generator (Python stdlib, no installs needed):

```bash
python generate_keys.py
```

Select **y** when prompted to auto-update `.env`. Then manually set:

```env
POSTGRES_PASSWORD=your_strong_password_here
DASHBOARD_PASSWORD=your_dashboard_password_here
```

> `DASHBOARD_PASSWORD` must contain at least one letter (Kong basic-auth requirement).

### Step 2 — Create required directories

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path volumes\api, volumes\db\data, volumes\storage

# WSL2 / Linux
mkdir -p volumes/api volumes/db/data volumes/storage
```

### Step 3 — Pull images and start

```bash
docker compose pull
docker compose up -d
```

### Step 4 — Verify all services are healthy

```bash
docker compose ps
```

All containers should show `Up ... (healthy)` within ~60 seconds.  
Check a specific service log if something is stuck:

```bash
docker compose logs auth
docker compose logs storage
```

### Step 5 — Access Studio

Open **http://localhost:54323** — no login required (direct port).

Or open **http://localhost:8000** and enter `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` (through Kong with basic-auth).

## Database Schema

The migration at `supabase/migrations/001_initial_schema.sql` runs automatically on first DB start via `/docker-entrypoint-initdb.d`. It creates:

- `users`, `books`, `chapters`, `text_chunks`
- `reading_sessions`, `reading_progress`, `bookmarks`, `media_assets`
- RLS policies for all user-owned tables
- `media-assets` storage bucket

To verify tables were created:

```bash
docker exec -it supabase-db psql -U postgres -d postgres -c "\dt public.*"
```

To apply schema manually if needed:

```bash
docker exec -it supabase-db psql -U postgres -d postgres \
  -f /docker-entrypoint-initdb.d/001_initial_schema.sql
```

## Useful Commands

```bash
# Start
docker compose up -d

# Stop (keeps data)
docker compose down

# Stop + wipe all data (destructive!)
docker compose down -v && rm -rf volumes/db/data volumes/storage

# Tail logs
docker compose logs -f kong
docker compose logs -f db

# Open a psql shell
docker exec -it supabase-db psql -U postgres -d postgres

# Restart a single service
docker compose restart storage
```

## Connecting from FastAPI

The Supabase Python client connects through Kong on port 8000:

```python
# config.py reads these from .env automatically
SUPABASE_URL = "http://localhost:8000"
SUPABASE_KEY = "<your ANON_KEY>"        # for user-facing requests
SUPABASE_SERVICE_KEY = "<SERVICE_ROLE_KEY>"  # for backend/admin operations
```

## Updating Images

```bash
docker compose pull          # fetch latest images
docker compose down
docker compose up -d
```

Check [Supabase Docker Hub](https://hub.docker.com/u/supabase) for stable image tags to pin in `docker-compose.yml`.

## Troubleshooting

**`supabase-kong` exits immediately**  
→ Check `volumes/api/kong.yml` exists and `ANON_KEY` / `SERVICE_ROLE_KEY` are set (not `CHANGEME_*`) in `.env`.

**`supabase-db` unhealthy**  
→ `docker compose logs db` — usually a bad `POSTGRES_PASSWORD` or leftover data in `volumes/db/data` from a previous run. Delete `volumes/db/data` and restart.

**`supabase-auth` fails to start**  
→ Verify `JWT_SECRET` is at least 32 characters and `ANON_KEY` / `SERVICE_ROLE_KEY` are valid JWTs signed with that secret. Re-run `python generate_keys.py`.

**Port 8000 already in use**  
→ Change `KONG_HTTP_PORT` in `.env` to e.g. `8001`. Update `SUPABASE_URL` and `SUPABASE_PUBLIC_URL` accordingly.
