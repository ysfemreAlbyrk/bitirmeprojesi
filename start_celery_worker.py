"""Script to start Celery worker for background task processing"""
from app.tasks.celery_app import celery_app
from app.utils.logger import setup_logger

# Setup logging
logger = setup_logger("vibetale")

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    celery_app.start(
        worker=[
            "--loglevel=info",
            "--concurrency=2",  # Adjust based on your CPU cores
            "--max-tasks-per-child=50"
        ]
    )
