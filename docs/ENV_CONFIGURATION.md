# Environment Configuration Guide

This document explains all environment variables required to run the VibeTale backend.

## Database Configuration

### SUPABASE_URL
The URL of your Supabase instance.
- **Default**: `http://localhost:8000`
- **Example**: `http://localhost:8000` (local) or `https://your-project.supabase.co` (cloud)

### SUPABASE_KEY
Supabase anonymous/public API key.
- **Required**: Yes
- **How to get**: From Supabase dashboard → Settings → API

### SUPABASE_SERVICE_KEY
Supabase service role key (has elevated permissions).
- **Required**: Yes
- **How to get**: From Supabase dashboard → Settings → API
- **Security**: Never expose this key in client-side code

## AI Configuration

### GEMINI_API_KEY
Google Gemini API key for text analysis.
- **Required**: Yes (if using Gemini as LLM provider)
- **How to get**: https://makersuite.google.com/app/apikey
- **Free tier**: Available with rate limits

### GEMINI_MODEL
Gemini model to use for text analysis.
- **Default**: `gemini-pro`
- **Options**: `gemini-pro`, `gemini-pro-vision`, etc.

### LLM_PROVIDER
Which LLM provider to use for text analysis.
- **Default**: `gemini`
- **Options**: `gemini`, `ollama`
- **Note**: Set to `ollama` to use local models via Ollama

### OLLAMA_BASE_URL
Base URL for Ollama API when using local models.
- **Default**: `http://localhost:11434`
- **Required**: Only if `LLM_PROVIDER=ollama`

### OLLAMA_MODEL
Ollama model to use for text analysis.
- **Default**: `llama2`
- **Examples**: `llama2`, `mistral`, `codellama`, etc.
- **Required**: Only if `LLM_PROVIDER=ollama`

## MMAudio Configuration

### MMAUDIO_PATH
Path to MMAudio installation directory.
- **Default**: `~/mm/MMAudio`
- **Required**: Yes
- **Note**: MMAudio must be installed locally

## Image Generation Configuration

### IMAGE_GENERATION_MODEL
Which image generation provider to use.
- **Default**: `clipdrop`
- **Options**: `clipdrop`, `local`

### CLIPDROP_API_KEY
Clipdrop API key for image generation.
- **Required**: Yes (if using Clipdrop)
- **How to get**: https://clipdrop.co/contact
- **Free tier**: 100 images/day
- **Rate limit**: 60 requests/minute

### IMAGE_GENERATION_PATH
Path to local image generation model.
- **Default**: `~/models/sdxl-turbo`
- **Required**: Only if `IMAGE_GENERATION_MODEL=local`

## Application Configuration

### APP_HOST
Host address for the FastAPI server.
- **Default**: `0.0.0.0`
- **Note**: `0.0.0.0` allows connections from any IP

### APP_PORT
Port for the FastAPI server.
- **Default**: `8000`
- **Note**: Ensure port is not in use

### DEBUG
Enable debug mode for development.
- **Default**: `true`
- **Options**: `true`, `false`
- **Note**: Set to `false` in production

### MAX_FILE_SIZE
Maximum file size for book uploads (in bytes).
- **Default**: `50000000` (50MB)
- **Note**: Adjust based on your storage capacity

## Storage Configuration

### STORAGE_BUCKET_NAME
Name of the Supabase storage bucket for media assets.
- **Default**: `media-assets`
- **Required**: Yes
- **Note**: Bucket must be created in Supabase before use

## Example Configuration

```env
# Database
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# AI - Using Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-pro

# AI - Alternative: Using Ollama
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama2

# MMAudio
MMAUDIO_PATH=~/mm/MMAudio

# Image Generation - Using Clipdrop
IMAGE_GENERATION_MODEL=clipdrop
CLIPDROP_API_KEY=your_clipdrop_api_key

# Image Generation - Alternative: Using Local Model
# IMAGE_GENERATION_MODEL=local
# IMAGE_GENERATION_PATH=~/models/sdxl-turbo

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
MAX_FILE_SIZE=50000000

# Storage
STORAGE_BUCKET_NAME=media-assets
```

## Security Best Practices

1. **Never commit `.env` to version control** - Add it to `.gitignore`
2. **Use strong, randomly generated API keys**
3. **Rotate keys regularly in production**
4. **Use different keys for development and production**
5. **Restrict API key permissions to minimum required**
6. **Monitor usage and set up alerts for unusual activity**

## Troubleshooting

### Supabase Connection Issues
- Verify Docker container is running: `docker ps`
- Check Supabase logs: `docker-compose logs supabase`
- Ensure ports 8000 and 5432 are not in use

### Gemini API Errors
- Verify API key is correct
- Check rate limits (free tier has limits)
- Ensure network can reach Google APIs

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check Ollama is installed: `ollama --version`
- Verify model is downloaded: `ollama pull llama2`

### Clipdrop API Errors
- Verify API key is valid
- Check remaining credits (100/day free tier)
- Respect rate limits (60 requests/minute)

### MMAudio Issues
- Verify MMAudio is installed at specified path
- Check GPU is available and CUDA is configured
- Ensure demo.py exists in MMAudio directory
