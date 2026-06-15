# VibeTale Backend - Setup Guide

This guide will walk you through setting up the VibeTale backend from scratch.

## Prerequisites

Before starting, ensure you have the following installed on your system:

- **Python 3.10 or higher**
- **Git**
- **NVIDIA GPU with CUDA** (for MMAudio and local image generation)
- **WSL2** (if on Windows)

### Check Prerequisites

```bash
# Check Python version
python --version

# Check GPU (Linux/WSL2)
nvidia-smi
```

## Step 1: Clone the Repository

```bash
git clone ysfemreAlbyrk/bitirmeprojesi
cd bitirmeprojesi
```

## Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

## Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note:** This may take several minutes, especially for PyTorch and diffusers packages.

### Troubleshooting Installation

If you encounter issues with PyTorch installation:

```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Step 4: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual configuration
nano .env  # or use your preferred editor
```

### Required Configuration

Update the following variables in `.env`:

```env
# Database Configuration
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=your_actual_supabase_key
SUPABASE_SERVICE_KEY=your_actual_supabase_service_key

# AI Configuration
LLM_PROVIDER=gemini  # or ollama
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# If using Ollama instead of Gemini:
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen3.5:4b

# MMAudio Configuration
MMAUDIO_PATH=~/mm/MMAudio  # Update with actual path

# Image Generation Configuration
IMAGE_GENERATION_MODEL=clipdrop
CLIPDROP_API_KEY=your_actual_clipdrop_api_key

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
```

### Getting API Keys

**Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste to `.env`

**Clipdrop API Key:**
1. Contact Clipdrop team at contact@clipdrop.co
2. Get your API key
3. Copy and paste to `.env`

**Supabase Keys:**
1. After setting up Supabase (Step 5), get keys from dashboard
2. Settings → API

## Step 5: Set Up Redis

Redis is used for caching and background task queue (Celery).

### 5.1 Install Redis

**On Windows (WSL2):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**On Linux:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**On Mac:**
```bash
brew install redis
brew services start redis
```

### 5.2 Verify Redis is Running

```bash
redis-cli ping
```

Expected response: `PONG`

### 5.3 Configure Redis in .env

Update your `.env` file:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0
```

If you set a password for Redis, include it in the configuration.

### 5.4 Test Redis Connection

```bash
# Test connection
redis-cli ping

# Test set/get
redis-cli set test "hello"
redis-cli get test
```

## Step 6: Set Up Supabase Cloud

### 6.1 Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up or log in
3. Click "New Project"
4. Choose a name (e.g., "vibetale")
5. Choose a database password (save it securely)
6. Select a region closest to you
7. Click "Create new project"

### 6.2 Get API Credentials

Once your project is created:

1. Go to **Settings** → **API**
2. Copy the following values to your `.env` file:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role** key → `SUPABASE_SERVICE_KEY`

### 6.3 Create Storage Bucket

1. Go to **Storage** in the left sidebar
2. Click "New bucket"
3. Name it `media-assets`
4. Make it **Public**
5. Click "Create bucket"

### 6.4 Apply Database Schema

1. Go to **SQL Editor** in the left sidebar
2. Copy the contents of `supabase/migrations/001_initial_schema.sql`
3. Paste it into the SQL Editor
4. Click "Run" to execute the schema

### 6.5 Verify Setup

Check that:
- Database tables are created (books, chapters, text_chunks, reading_progress, bookmarks, media_assets)
- Storage bucket `media-assets` exists
- API credentials are correctly configured in `.env`

You should see tables: users, books, chapters, text_chunks, reading_sessions, reading_progress, bookmarks, media_assets.

## Step 7: Set Up Ollama (Optional)

If you want to use Ollama instead of Gemini:

### 6.1 Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 6.2 Pull the Model

```bash
# Pull the model specified in .env
ollama pull qwen3.5:4b

# Or pull llama2
ollama pull llama2
```

### 6.3 Start Ollama Server

```bash
ollama serve
```

Ollama will run on `http://localhost:11434` by default.

### 6.4 Test Ollama

```bash
# Test in another terminal
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:4b",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

## Step 8: Verify MMAudio Installation

Ensure MMAudio is installed at the path specified in `.env`:

```bash
# Check MMAudio directory
ls ~/mm/MMAudio

# Verify demo.py exists
ls ~/mm/MMAudio/demo.py

# Test MMAudio (optional)
cd ~/mm/MMAudio
python demo.py --help
```

If MMAudio is not installed, follow the MMAudio installation instructions from their repository.

## Step 8: Start the FastAPI Server

### 8.1 Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 8.2 Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 8.3 Verify Server is Running

Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Step 11: Test the API

### 9.1 Test Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 9.2 Test Book Upload (Optional)

```bash
# Create a test EPUB file or use an existing one
curl -X POST http://localhost:8000/books/upload \
  -F "file=@test.epub" \
  -F "user_id=test_user_123"
```

### 9.3 Test AI Providers

Test that your AI providers are working:

```bash
# Test via Swagger UI at http://localhost:8000/docs
# Navigate to any endpoint and try it out
```

## Step 10: Common Issues and Solutions

### Issue: Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
# On Linux/Mac:
lsof -i :8000

# On Windows:
netstat -ano | findstr :8000

# Kill the process or change the port in .env
APP_PORT=8001
```

### Issue: GPU Not Detected

**Solution:**
```bash
# Check CUDA
nvidia-smi

# Install CUDA toolkit if needed
# For WSL2, ensure GPU passthrough is enabled
```

### Issue: Supabase Connection Failed

**Solution:**
```bash
# Verify your .env file has correct Supabase credentials
# Check SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

# Test connection to Supabase
curl https://your-project.supabase.co
```

### Issue: Ollama Connection Refused

**Solution:**
```bash
# Ensure Ollama is running
ollama serve

# Check if port is accessible
curl http://localhost:11434/api/tags
```

### Issue: Import Errors

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check Python version
python --version  # Should be 3.10+
```

## Step 11: Production Deployment Considerations

For production deployment:

1. **Security:**
   - Set `DEBUG=false` in `.env`
   - Use strong, randomly generated passwords
   - Enable HTTPS with a reverse proxy (nginx)
   - Use environment-specific API keys

2. **Performance:**
   - Use Gunicorn instead of Uvicorn for production
   - Enable caching (Redis)
   - Use CDN for static assets
   - Optimize database queries

3. **Monitoring:**
   - Set up logging
   - Monitor API usage
   - Track error rates
   - Set up alerts

4. **Scaling:**
   - Use load balancer
   - Horizontal scaling with multiple workers
   - Database connection pooling
   - Queue system for long-running tasks (Celery)

## Step 12: Next Steps

Once the server is running:

1. Review the API documentation at http://localhost:8000/docs
2. Test the book upload and processing pipeline
3. Integrate with the Flutter mobile app
4. Set up CI/CD pipeline
5. Configure monitoring and logging

## Quick Reference

### Start All Services

```bash
# Start Redis (if not running)
redis-server

# Start Supabase
docker-compose up -d

# Start Ollama (if using)
ollama serve

# Start Celery worker (in separate terminal)
python start_celery_worker.py

# Start FastAPI (in separate terminal)
uvicorn main:app --reload
```

### Stop All Services

```bash
# Stop FastAPI (Ctrl+C)

# Stop Celery worker (Ctrl+C)

# Stop Ollama (Ctrl+C)

# Stop Redis
redis-cli shutdown
```

### Check Service Status

```bash
# Redis
redis-cli ping

# Ollama
curl http://localhost:11434/api/tags

# Celery
# Check if worker is running (should be in its terminal output)

# FastAPI
curl http://localhost:8000/health
```

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Ollama Documentation](https://ollama.com/docs)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Clipdrop API Documentation](https://clipdrop.co/apis)

## Support

If you encounter issues not covered in this guide:

1. Check the logs for error messages
2. Review the environment configuration in `docs/ENV_CONFIGURATION.md`
3. Verify all prerequisites are installed
4. Check that all API keys are valid
5. Ensure all services are running

For specific component issues, refer to:
- Supabase: `docs/SUPABASE_SETUP.md`
- Environment: `docs/ENV_CONFIGURATION.md`
