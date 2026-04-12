# Supabase Docker Setup Guide

This guide explains how to set up Supabase locally using Docker for the VibeTale backend.

## Prerequisites

- Docker installed on your system
- Docker Compose installed
- At least 4GB RAM allocated to Docker

## Setup Steps

### 1. Pull Supabase Docker Image

```bash
docker pull supabase/supabase:latest
```

### 2. Create Docker Compose File

Create a `docker-compose.yml` file in the project root:

```yaml
version: '3.8'

services:
  supabase:
    image: supabase/supabase:latest
    container_name: vibetale_supabase
    ports:
      - "8000:8000"  # API
      - "5432:5432"  # PostgreSQL
    environment:
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: vibetale
      ANON_KEY: your_anon_key_here
      SERVICE_ROLE_KEY: your_service_role_key_here
    volumes:
      - ./supabase/data:/var/lib/postgresql/data
      - ./supabase/migrations:/docker-entrypoint-initdb.d
    restart: unless-stopped
```

### 3. Generate API Keys

Generate secure keys for your Supabase instance:

```bash
# Generate anon key
openssl rand -base64 32

# Generate service role key
openssl rand -base64 32
```

### 4. Update Environment Variables

Update your `.env` file with the Supabase configuration:

```env
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=your_generated_anon_key
SUPABASE_SERVICE_KEY=your_generated_service_role_key
```

### 5. Start Supabase

```bash
docker-compose up -d
```

### 6. Apply Database Schema

The SQL migration file will be automatically applied when the container starts because it's mounted to `/docker-entrypoint-initdb.d`.

If you need to apply the schema manually:

```bash
# Connect to the PostgreSQL database
docker exec -it vibetale_supabase psql -U postgres -d vibetale

# Apply the schema
\i /docker-entrypoint-initdb.d/001_initial_schema.sql
```

### 7. Create Storage Bucket

Connect to the Supabase SQL interface and create the storage bucket:

```sql
INSERT INTO storage.buckets (id, name, public) 
VALUES ('media-assets', 'media-assets', true);
```

## Verification

Check that Supabase is running:

```bash
docker ps
```

You should see the `vibetale_supabase` container running.

Test the API:

```bash
curl http://localhost:8000/health
```

## Useful Commands

### View Logs

```bash
docker-compose logs -f supabase
```

### Stop Supabase

```bash
docker-compose down
```

### Restart Supabase

```bash
docker-compose restart
```

### Access PostgreSQL Directly

```bash
docker exec -it vibetale_supabase psql -U postgres -d vibetale
```

## Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use, modify the ports in `docker-compose.yml`.

### Permission Issues

Ensure the `./supabase/data` directory has proper permissions:

```bash
mkdir -p supabase/data
chmod 777 supabase/data
```

### Container Won't Start

Check the logs for errors:

```bash
docker-compose logs supabase
```

## Production Considerations

For production deployment:
- Use strong, randomly generated passwords and keys
- Enable SSL/TLS
- Set up regular backups
- Configure proper resource limits
- Use a managed Supabase instance instead of Docker
- Enable Row Level Security (RLS) policies (already included in schema)
