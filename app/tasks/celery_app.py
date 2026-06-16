"""Celery application configuration"""
from celery import Celery
from config import settings
from app.utils.logger import get_logger

logger = get_logger("vibetale")

# Create Celery app
celery_app = Celery(
    "vibetale",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.book_tasks"]
)

# Development mode: run tasks synchronously without Redis broker
# Set CELERY_EAGER=1 in .env to use eager mode (no Redis required)
import os
EAGER_MODE = os.environ.get("CELERY_EAGER", "1").lower() in ("1", "true", "yes")

if EAGER_MODE:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = True
    logger.info("Celery configured in EAGER mode (tasks run synchronously, no broker needed)")
else:
    logger.info("Celery app configured with Redis broker")

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
