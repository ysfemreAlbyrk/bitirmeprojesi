"""Celery application configuration"""
import os
from celery import Celery
from config import settings
from app.utils.logger import get_logger

logger = get_logger("vibetale")

EAGER_MODE = os.environ.get("CELERY_EAGER", "1").lower() in ("1", "true", "yes")

if EAGER_MODE:
    celery_app = Celery(
        "vibetale",
        include=["app.tasks.book_tasks"]
    )
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = True
    logger.info("Celery configured in EAGER mode (tasks run synchronously, no broker needed)")
else:
    celery_app = Celery(
        "vibetale",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.tasks.book_tasks"]
    )
    logger.info("Celery app configured with Redis broker")

# Make this app the default so @shared_task binds to it
celery_app.set_default()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
