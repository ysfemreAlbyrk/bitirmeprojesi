from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

from app.api import books, reading, ambiance

app = FastAPI(
    title="VibeTale Backend API",
    description="Backend API for immersive e-book reading experience",
    version="1.0.0"
)

# CORS middleware for Flutter mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(books.router)
app.include_router(reading.router)
app.include_router(ambiance.router)


@app.get("/")
async def root():
    return {"message": "VibeTale Backend API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
