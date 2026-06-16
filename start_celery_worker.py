"""Script to start Celery worker for background task processing"""
import os
import sys
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.utils.logger import setup_logger


class Tee:
    """Write to multiple file-like objects simultaneously."""
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()

    def isatty(self):
        # Allow tools that check for terminal (e.g. rich, click) to work
        return any(getattr(f, 'isatty', lambda: False)() for f in self.files)


# Ensure log directory exists and open tee target
os.makedirs("logs", exist_ok=True)
log_path = "logs/celery.log"
log_file = open(log_path, "a", encoding="utf-8")
log_file.write(f"\n{'='*60}\n[{datetime.now().isoformat()}] Celery worker started\n{'='*60}\n")
log_file.flush()

# Tee stdout and stderr to both terminal and log file
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

# Setup logging
logger = setup_logger("vibetale")

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=2",  # Adjust based on your CPU cores
        "--max-tasks-per-child=50"
    ])
