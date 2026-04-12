# VibeTale Backend

Backend API for VibeTale - an immersive e-book reading application.

## Tech Stack

- **FastAPI** - Web framework
- **Supabase** - Database and object storage (local Docker)
- **Gemini API** - Text analysis and prompt generation
- **MMAudio** - Local ambient sound generation
- **Image Generation** - Local scene visual generation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Configure `.env` with your API keys and local paths

4. Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── app/
│   ├── api/               # API endpoints
│   ├── models/            # Database models
│   ├── services/          # Business logic services
│   ├── providers/         # AI provider abstractions
│   └── utils/             # Utility functions
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
